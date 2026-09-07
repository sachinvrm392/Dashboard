import json
import math
import hashlib
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from accounts.decorators import business_partner_required
from .models import CreditSnapshot, CallConversation
from .services import ElevenLabsService
from .notifications import check_and_send_credit_alert

@business_partner_required
def bp_dashboard(request):
    try:
        bp = request.user.business_partner
    except Exception:
        return render(request, 'dashboard/index.html', {'error': 'Business partner profile not found.'})
        
    context = {'bp': bp}
    
    has_managed_credits = bp.credit_transactions.exists()
    ledger_credits = bp.get_ledger_credits()
    
    # 1. Fetch latest stored snapshot from DB if available as baseline
    latest_snapshot = CreditSnapshot.objects.filter(business_partner=bp).order_by('-snapshot_date', '-created_at').first()
    
    # Baseline defaults from DB snapshot or partner configured credit threshold
    character_limit = latest_snapshot.character_limit if (latest_snapshot and latest_snapshot.character_limit > 0) else (bp.credit_alert_threshold or 10000)
    character_count = latest_snapshot.character_count if latest_snapshot else 0
    
    api_error = None
    no_api_key = not bool(bp.elevenlabs_api_key)
    voices = []
    usage_history = []
    subscription_info = {}
    is_live = False
    
    if not no_api_key:
        api_key = bp.elevenlabs_api_key.strip()
        subscription_info = ElevenLabsService.get_subscription_info(api_key)
        
        if subscription_info.get('error'):
            api_error = subscription_info.get('message')
        else:
            is_live = True
            voices = ElevenLabsService.get_voices(api_key)
            usage_history = ElevenLabsService.get_usage_history(api_key)
            if not has_managed_credits:
                character_limit = subscription_info.get('character_limit', character_limit)
                character_count = subscription_info.get('character_count', character_count)

    # In Managed Credit Mode:
    # - Total credits is strictly net ledger credits
    # - Consumed credits is assumed 0 (per user specifications until call-duration deduction is implemented)
    if has_managed_credits:
        effective_character_limit = max(0, ledger_credits)
        effective_character_count = 0
    else:
        effective_character_limit = character_limit + ledger_credits if ledger_credits else character_limit
        effective_character_count = character_count

    # Record or update today's snapshot
    today = timezone.localdate()
    CreditSnapshot.objects.update_or_create(
        business_partner=bp,
        snapshot_date=today,
        defaults={
            'character_count': effective_character_count,
            'character_limit': effective_character_limit
        }
    )
    if is_live or has_managed_credits:
        check_and_send_credit_alert(bp, subscription_info)
            
    recent_snapshots = CreditSnapshot.objects.filter(business_partner=bp).order_by('-snapshot_date')[:30]

    remaining = max(0, effective_character_limit - effective_character_count)
    usage_percentage = round((effective_character_count / effective_character_limit * 100), 1) if effective_character_limit else 0.0
    remaining_percentage = round(max(0.0, 100.0 - usage_percentage), 1)
    
    alert_status = (remaining <= bp.credit_alert_threshold) if bp.credit_alert_threshold > 100 else (remaining_percentage <= bp.credit_alert_threshold)
    
    chart_labels = []
    chart_data = []
    
    if has_managed_credits:
        import datetime
        today = timezone.localdate()
        for i in range(6, -1, -1):
            d = today - datetime.timedelta(days=i)
            chart_labels.append(d.strftime('%b %d'))
            chart_data.append(0)
    elif usage_history and isinstance(usage_history, dict) and 'points' in usage_history and len(usage_history.get('points', [])) > 1:
        for point in usage_history.get('points', []):
            if 'time' in point and 'value' in point:
                import datetime
                dt = datetime.datetime.fromtimestamp(point['time']/1000)
                chart_labels.append(dt.strftime('%b %d'))
                chart_data.append(point['value'])
    elif len(recent_snapshots) > 1:
        sorted_snaps = sorted(recent_snapshots, key=lambda x: x.snapshot_date)
        for snap in sorted_snaps:
            chart_labels.append(snap.snapshot_date.strftime('%b %d'))
            chart_data.append(snap.character_count)
    else:
        import datetime
        today = timezone.localdate()
        base_val = effective_character_count if effective_character_count > 0 else 0
        ratios = [0.15, 0.28, 0.42, 0.58, 0.72, 0.88, 1.0]
        for i, ratio in enumerate(ratios):
            d = today - datetime.timedelta(days=(len(ratios) - 1 - i))
            chart_labels.append(d.strftime('%b %d'))
            chart_data.append(int(base_val * ratio))
            
    usage_chart_data = {
        'labels': chart_labels,
        'values': chart_data,
        'limit': [effective_character_limit] * len(chart_labels),
    }
    
    context.update({
        'subscription_info': subscription_info,
        'voices': voices,
        'recent_snapshots': recent_snapshots,
        'usage_chart_data': usage_chart_data,
        'character_limit': effective_character_limit,
        'base_character_limit': character_limit,
        'ledger_credits': ledger_credits,
        'has_managed_credits': has_managed_credits,
        'character_count': effective_character_count,
        'remaining': remaining,
        'usage_percentage': usage_percentage,
        'remaining_percentage': remaining_percentage,
        'alert_status': alert_status,
        'no_api_key': no_api_key,
        'api_error': api_error,
        'is_live': is_live,
        'active_nav': 'dashboard',
    })
    
    return render(request, 'dashboard/index.html', context)

@require_POST
@business_partner_required
def refresh_credits(request):
    try:
        bp = request.user.business_partner
        if not bp.elevenlabs_api_key:
            return JsonResponse({'error': 'No API key'}, status=400)
            
        api_key = bp.elevenlabs_api_key
        sub_cache_key = f'elevenlabs_sub_{hashlib.md5(api_key.encode()).hexdigest()}'
        cache.delete(sub_cache_key)
        
        subscription_info = ElevenLabsService.get_subscription_info(api_key)
        
        if subscription_info.get('error'):
            return JsonResponse({'error': subscription_info.get('message')}, status=400)
            
        has_managed_credits = bp.credit_transactions.exists()
        if has_managed_credits:
            character_limit = max(0, bp.get_ledger_credits())
            character_count = 0
        else:
            character_limit = subscription_info.get('character_limit', 0)
            character_count = subscription_info.get('character_count', 0)
            
        remaining = max(0, character_limit - character_count)
        usage_percentage = round((character_count / character_limit * 100), 1) if character_limit else 0
        
        return JsonResponse({
            'success': True,
            'character_limit': character_limit,
            'character_count': character_count,
            'remaining': remaining,
            'usage_percentage': usage_percentage,
            'has_managed_credits': has_managed_credits
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def copilot_view(request):
    """
    Renders the Sainou AI Recruiter Co-Pilot command center GUI.
    """
    return render(request, 'copilot.html')


def format_total_duration(total_secs):
    if not total_secs:
        return "0s"
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


@business_partner_required
def bp_conversations(request):
    bp = request.user.business_partner
    qs = CallConversation.objects.filter(business_partner=bp).order_by('-call_timestamp')

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(conversation_id__icontains=q) |
            Q(agent_id__icontains=q) |
            Q(caller_number__icontains=q) |
            Q(called_number__icontains=q) |
            Q(call_sid__icontains=q) |
            Q(caller_name__icontains=q)
        )

    # Evaluation filter
    eval_filter = request.GET.get('evaluation', '').strip()
    if eval_filter:
        qs = qs.filter(evaluation__iexact=eval_filter)

    # KPI summary metrics
    total_calls = qs.count()
    aggregates = qs.aggregate(
        total_duration=Sum('duration'),
        total_cost=Sum('conversation_cost'),
        total_llm=Sum('credits_llm')
    )
    total_duration_secs = aggregates['total_duration'] or 0
    total_llm = aggregates['total_llm'] or 0.0

    if bp.cost_per_minute and bp.cost_per_minute > 0:
        total_cost = int((total_duration_secs / 60.0) * float(bp.cost_per_minute))
    else:
        total_cost = int(aggregates['total_cost'] or 0.0)

    # Credit Balance metrics
    has_managed_credits = bp.credit_transactions.exists()
    ledger_credits = bp.get_ledger_credits()

    if has_managed_credits:
        bp_total_credits = int(ledger_credits)
    elif bp.available_credit_balance and bp.available_credit_balance > 0:
        bp_total_credits = int(float(bp.available_credit_balance))
    else:
        bp_total_credits = int(bp.credit_alert_threshold or 10000)

    bp_consumed_credits = int(total_cost)
    bp_remaining_credits = max(0, bp_total_credits - bp_consumed_credits)

    # Pagination: 15 per page
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'bp': bp,
        'page_obj': page_obj,
        'total_calls': total_calls,
        'total_duration_formatted': format_total_duration(total_duration_secs),
        'total_cost': total_cost,
        'total_llm': total_llm,
        'bp_total_credits': bp_total_credits,
        'bp_consumed_credits': bp_consumed_credits,
        'bp_remaining_credits': bp_remaining_credits,
        'q': q,
        'eval_filter': eval_filter,
        'active_nav': 'conversations',
    }
    return render(request, 'dashboard/conversations.html', context)


@require_POST
@business_partner_required
def sync_conversations_api(request):
    try:
        bp = request.user.business_partner
        res = ElevenLabsService.sync_conversations(bp)
        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({'error': True, 'message': str(e)}, status=500)


@login_required
def conversation_transcript_api(request, pk):
    try:
        conv = get_object_or_404(CallConversation, pk=pk)
        # Security check: User must be super admin or the partner who owns this conversation
        if not request.user.is_super_admin():
            if not hasattr(request.user, 'business_partner') or request.user.business_partner != conv.business_partner:
                return JsonResponse({'error': True, 'message': 'Permission denied.'}, status=403)

        return JsonResponse({
            'success': True,
            'conversation_id': conv.conversation_id,
            'agent_id': conv.agent_id,
            'caller_name': conv.caller_name or 'Anonymous Caller',
            'duration': conv.duration_formatted,
            'call_timestamp': conv.call_timestamp.strftime('%b %d, %Y %H:%M:%S UTC'),
            'evaluation': conv.evaluation,
            'messages': conv.messages,
        })
    except Exception as e:
        return JsonResponse({'error': True, 'message': str(e)}, status=500)


