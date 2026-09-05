import json
import hashlib
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.cache import cache
from accounts.decorators import business_partner_required
from .models import CreditSnapshot
from .services import ElevenLabsService
from .notifications import check_and_send_credit_alert

@business_partner_required
def bp_dashboard(request):
    try:
        bp = request.user.business_partner
    except Exception:
        return render(request, 'dashboard/index.html', {'error': 'Business partner profile not found.'})
        
    context = {'bp': bp}
    
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
            character_limit = subscription_info.get('character_limit', character_limit)
            character_count = subscription_info.get('character_count', character_count)
            voices = ElevenLabsService.get_voices(api_key)
            usage_history = ElevenLabsService.get_usage_history(api_key)
            
            # Record or update today's snapshot
            today = timezone.localdate()
            CreditSnapshot.objects.update_or_create(
                business_partner=bp,
                snapshot_date=today,
                defaults={
                    'character_count': character_count,
                    'character_limit': character_limit
                }
            )
            check_and_send_credit_alert(bp, subscription_info)
            
    recent_snapshots = CreditSnapshot.objects.filter(business_partner=bp).order_by('-snapshot_date')[:30]
    
    remaining = max(0, character_limit - character_count)
    usage_percentage = round((character_count / character_limit * 100), 1) if character_limit else 0.0
    remaining_percentage = round(max(0.0, 100.0 - usage_percentage), 1)
    
    alert_status = (remaining <= bp.credit_alert_threshold) if bp.credit_alert_threshold > 100 else (remaining_percentage <= bp.credit_alert_threshold)
    
    chart_labels = []
    chart_data = []
    
    if usage_history and isinstance(usage_history, dict) and 'points' in usage_history and len(usage_history.get('points', [])) > 1:
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
        base_val = character_count if character_count > 0 else 0
        ratios = [0.15, 0.28, 0.42, 0.58, 0.72, 0.88, 1.0]
        for i, ratio in enumerate(ratios):
            d = today - datetime.timedelta(days=(len(ratios) - 1 - i))
            chart_labels.append(d.strftime('%b %d'))
            chart_data.append(int(base_val * ratio))
            
    usage_chart_data = {
        'labels': chart_labels,
        'values': chart_data,
        'limit': [character_limit] * len(chart_labels),
    }
    
    context.update({
        'subscription_info': subscription_info,
        'voices': voices,
        'recent_snapshots': recent_snapshots,
        'usage_chart_data': usage_chart_data,
        'character_limit': character_limit,
        'character_count': character_count,
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
            
        character_limit = subscription_info.get('character_limit', 0)
        character_count = subscription_info.get('character_count', 0)
        remaining = max(0, character_limit - character_count)
        usage_percentage = round((character_count / character_limit * 100), 1) if character_limit else 0
        
        return JsonResponse({
            'success': True,
            'character_limit': character_limit,
            'character_count': character_count,
            'remaining': remaining,
            'usage_percentage': usage_percentage
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def copilot_view(request):
    """
    Renders the Sainou AI Recruiter Co-Pilot command center GUI.
    """
    return render(request, 'copilot.html')

