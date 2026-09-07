from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from accounts.models import BusinessPartner, User
from accounts.decorators import super_admin_required
from dashboard.services import ElevenLabsService
from .forms import BPCreateForm, BPUpdateForm, UserProfileForm, BPResetPasswordForm, CreditTransactionForm
from django.contrib.auth.decorators import login_required

import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from dashboard.models import CreditSnapshot, CreditTransaction, CallConversation

@super_admin_required
def admin_dashboard(request):
    bps = BusinessPartner.objects.filter(is_deleted=False)
    bp_data_list = []
    
    total_bps = bps.count()
    active_bps = bps.filter(is_active=True).count()
    inactive_bps = total_bps - active_bps
    total_credits_used_all = 0
    total_credit_limit_all = 0
    
    # Show only the latest 5 business partners in the registry section
    latest_bps = list(bps[:5])
    
    for bp in latest_bps:
        has_managed = bp.credit_transactions.exists()
        bp_info = {
            'bp': bp,
            'credit_info': None,
            'api_error': False,
            'remaining': 0,
            'usage_percentage': 0.0,
            'has_managed_credits': has_managed,
            'character_limit': 0,
            'character_count': 0,
        }
        
        if has_managed:
            char_limit = max(0, bp.get_ledger_credits())
            char_count = 0
            bp_info['remaining'] = max(0, char_limit - char_count)
            bp_info['usage_percentage'] = 0.0
            bp_info['character_limit'] = char_limit
            bp_info['character_count'] = char_count
            total_credits_used_all += char_count
            total_credit_limit_all += char_limit
            if bp.elevenlabs_api_key:
                try:
                    credit_info = ElevenLabsService.get_subscription_info(bp.elevenlabs_api_key)
                    if not credit_info.get('error'):
                        bp_info['credit_info'] = credit_info
                except Exception:
                    pass
        elif bp.elevenlabs_api_key:
            try:
                credit_info = ElevenLabsService.get_subscription_info(bp.elevenlabs_api_key)
                if not credit_info.get('error'):
                    bp_info['credit_info'] = credit_info
                    char_limit = credit_info.get('character_limit', 0)
                    char_count = credit_info.get('character_count', 0)
                    remaining = max(0, char_limit - char_count)
                    usage_pct = round((char_count / char_limit * 100), 1) if char_limit else 0
                    bp_info['remaining'] = remaining
                    bp_info['usage_percentage'] = usage_pct
                    bp_info['character_limit'] = char_limit
                    bp_info['character_count'] = char_count
                    total_credits_used_all += char_count
                    total_credit_limit_all += char_limit
                else:
                    bp_info['api_error'] = True
            except Exception:
                bp_info['api_error'] = True
                
        bp_data_list.append(bp_info)
        
    overall_usage_percentage = round((total_credits_used_all / total_credit_limit_all * 100), 1) if total_credit_limit_all else 0.0
    active_partner_ratio = round((active_bps / total_bps * 100), 1) if total_bps else 0.0

    # Past 7 days data from database
    today = timezone.localdate()
    days_labels = []
    days_values = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days_labels.append(day.strftime('%d %b'))
        day_sum = CreditSnapshot.objects.filter(snapshot_date=day).aggregate(total=Sum('character_count'))['total'] or 0
        days_values.append(day_sum)
    
    context = {
        'bp_data_list': bp_data_list,
        'total_bps': total_bps,
        'active_bps': active_bps,
        'inactive_bps': inactive_bps,
        'total_credits_used_all': total_credits_used_all,
        'total_credit_limit_all': total_credit_limit_all,
        'overall_usage_percentage': overall_usage_percentage,
        'active_partner_ratio': active_partner_ratio,
        'days_labels_json': json.dumps(days_labels),
        'days_values_json': json.dumps(days_values),
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


@super_admin_required
def bp_list(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    base_qs = BusinessPartner.objects.all().select_related('user')
    
    # Counts for tabs
    total_all = base_qs.filter(is_deleted=False).count()
    total_active = base_qs.filter(is_deleted=False, is_active=True).count()
    total_inactive = base_qs.filter(is_deleted=False, is_active=False).count()
    total_deleted = base_qs.filter(is_deleted=True).count()

    if status_filter in ['deleted', 'trash']:
        bps_qs = base_qs.filter(is_deleted=True)
    elif status_filter == 'active':
        bps_qs = base_qs.filter(is_deleted=False, is_active=True)
    elif status_filter == 'inactive':
        bps_qs = base_qs.filter(is_deleted=False, is_active=False)
    else:
        bps_qs = base_qs.filter(is_deleted=False)
    
    if search_query:
        bps_qs = bps_qs.filter(
            Q(company_name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # Pagination: 10 partners per page
    paginator = Paginator(bps_qs, 10)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
        
    bp_data_list = []
    bps_page_list = list(page_obj.object_list)
    for bp in bps_page_list:
        has_managed = bp.credit_transactions.exists()
        bp_info = {
            'bp': bp,
            'credit_info': None,
            'api_error': False,
            'remaining': 0,
            'usage_percentage': 0.0,
            'has_managed_credits': has_managed,
            'character_limit': 0,
            'character_count': 0,
        }
        if has_managed:
            char_limit = max(0, bp.get_ledger_credits())
            char_count = 0
            bp_info['remaining'] = max(0, char_limit - char_count)
            bp_info['usage_percentage'] = 0.0
            bp_info['character_limit'] = char_limit
            bp_info['character_count'] = char_count
            if bp.elevenlabs_api_key:
                try:
                    credit_info = ElevenLabsService.get_subscription_info(bp.elevenlabs_api_key)
                    if not credit_info.get('error'):
                        bp_info['credit_info'] = credit_info
                except Exception:
                    pass
        elif bp.elevenlabs_api_key:
            try:
                credit_info = ElevenLabsService.get_subscription_info(bp.elevenlabs_api_key)
                if not credit_info.get('error'):
                    bp_info['credit_info'] = credit_info
                    char_limit = credit_info.get('character_limit', 0)
                    char_count = credit_info.get('character_count', 0)
                    bp_info['remaining'] = max(0, char_limit - char_count)
                    bp_info['usage_percentage'] = round((char_count / char_limit * 100), 1) if char_limit else 0
                    bp_info['character_limit'] = char_limit
                    bp_info['character_count'] = char_count
                else:
                    bp_info['api_error'] = True
            except Exception:
                bp_info['api_error'] = True
        bp_data_list.append(bp_info)
        
    context = {
        'page_obj': page_obj,
        'bp_data_list': bp_data_list,
        'total_bps': total_all,
        'active_bps': total_active,
        'inactive_bps': total_inactive,
        'deleted_bps': total_deleted,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'admin_panel/bp_list.html', context)


@super_admin_required
def bp_create(request):
    if request.method == 'POST':
        form = BPCreateForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, 'Business Partner created successfully.')
            return redirect('admin_panel:bp_list')
    else:
        form = BPCreateForm()
        
    return render(request, 'admin_panel/bp_form.html', {'form': form, 'is_create': True})

@super_admin_required
def bp_update(request, pk):
    bp = get_object_or_404(BusinessPartner, pk=pk)
    if request.method == 'POST':
        form = BPUpdateForm(request.POST, request.FILES, instance=bp)
        if form.is_valid():
            form.save()
            messages.success(request, 'Business Partner updated successfully.')
            return redirect('admin_panel:bp_list')
    else:
        form = BPUpdateForm(instance=bp)
        
    return render(request, 'admin_panel/bp_form.html', {'form': form, 'is_create': False, 'bp': bp})

@require_POST
@super_admin_required
def bp_toggle_active(request, pk):
    bp = get_object_or_404(BusinessPartner, pk=pk)
    bp.is_active = not bp.is_active
    bp.save()
    
    bp.user.is_active = bp.is_active
    bp.user.save()
    
    status = "activated" if bp.is_active else "deactivated"
    messages.success(request, f'Business Partner {bp.company_name} has been {status}.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_panel:bp_list'
    return redirect(next_url)

@require_POST
@super_admin_required
def bp_soft_delete(request, pk):
    bp = get_object_or_404(BusinessPartner, pk=pk)
    bp.is_deleted = True
    bp.deleted_at = timezone.now()
    bp.is_active = False
    bp.save()
    
    bp.user.is_active = False
    bp.user.save()
    
    messages.success(request, f"Business Partner '{bp.company_name}' moved to trash.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_panel:bp_list'
    return redirect(next_url)

@require_POST
@super_admin_required
def bp_restore(request, pk):
    bp = get_object_or_404(BusinessPartner, pk=pk)
    bp.is_deleted = False
    bp.deleted_at = None
    bp.is_active = True
    bp.save()
    
    bp.user.is_active = True
    bp.user.save()
    
    messages.success(request, f"Business Partner '{bp.company_name}' restored successfully.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_panel:bp_list'
    return redirect(next_url)

@require_POST
@super_admin_required
def bp_hard_delete(request, pk):
    bp = get_object_or_404(BusinessPartner, pk=pk)
    company_name = bp.company_name
    user = bp.user
    with transaction.atomic():
        if user:
            user.delete()
        else:
            bp.delete()
    messages.success(request, f"Business Partner '{company_name}' permanently deleted.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_panel:bp_list'
    return redirect(next_url)

@require_POST
@super_admin_required
def bp_empty_trash(request):
    deleted_bps = BusinessPartner.objects.filter(is_deleted=True)
    count = deleted_bps.count()
    if count == 0:
        messages.info(request, "Trash is already empty.")
        return redirect('admin_panel:bp_list')
    
    with transaction.atomic():
        user_ids = list(deleted_bps.values_list('user_id', flat=True))
        User.objects.filter(id__in=user_ids).delete()
        deleted_bps.delete()
        
    messages.success(request, f"Permanently deleted {count} partner(s) from trash.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_panel:bp_list'
    return redirect(next_url)

@super_admin_required
def bp_detail(request, pk):
    bp = get_object_or_404(BusinessPartner, pk=pk)
    
    # 1. Fetch latest stored snapshot from DB if available as baseline
    latest_snapshot = CreditSnapshot.objects.filter(business_partner=bp).order_by('-snapshot_date', '-created_at').first()
    
    character_limit = latest_snapshot.character_limit if (latest_snapshot and latest_snapshot.character_limit > 0) else (bp.credit_alert_threshold or 10000)
    character_count = latest_snapshot.character_count if latest_snapshot else 0
    
    credit_info = {}
    voices = []
    api_error = None
    is_live = False
    
    has_managed_credits = bp.credit_transactions.exists()
    ledger_credits = bp.get_ledger_credits()

    if bp.elevenlabs_api_key:
        api_key = bp.elevenlabs_api_key.strip()
        credit_info = ElevenLabsService.get_subscription_info(api_key)
        if credit_info.get('error'):
            api_error = credit_info.get('message')
        else:
            is_live = True
            if not has_managed_credits:
                character_limit = credit_info.get('character_limit', character_limit)
                character_count = credit_info.get('character_count', character_count)
            voices = ElevenLabsService.get_voices(api_key)
            
    if has_managed_credits:
        effective_character_limit = max(0, ledger_credits)
        effective_character_count = 0
    else:
        effective_character_limit = character_limit + ledger_credits if ledger_credits else character_limit
        effective_character_count = character_count

    # Record or update today's snapshot
    if is_live or has_managed_credits:
        today = timezone.localdate()
        CreditSnapshot.objects.update_or_create(
            business_partner=bp,
            snapshot_date=today,
            defaults={
                'character_count': effective_character_count,
                'character_limit': effective_character_limit
            }
        )

    remaining = max(0, effective_character_limit - effective_character_count)
    usage_percentage = round((effective_character_count / effective_character_limit * 100), 1) if effective_character_limit else 0.0
    remaining_percentage = round(max(0.0, 100.0 - usage_percentage), 1)
    
    recent_snapshots = CreditSnapshot.objects.filter(business_partner=bp).order_by('-snapshot_date')[:30]
            
    context = {
        'bp': bp,
        'credit_info': credit_info,
        'character_limit': effective_character_limit,
        'base_character_limit': character_limit,
        'ledger_credits': ledger_credits,
        'has_managed_credits': has_managed_credits,
        'character_count': effective_character_count,
        'remaining': remaining,
        'usage_percentage': usage_percentage,
        'remaining_percentage': remaining_percentage,
        'voices': voices,
        'recent_snapshots': recent_snapshots,
        'api_error': api_error,
        'is_live': is_live,
        'active_nav': 'partners',
    }
    
    return render(request, 'admin_panel/bp_detail.html', context)


@login_required
def user_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile information has been updated successfully.')
            return redirect('admin_panel:profile')
    else:
        form = UserProfileForm(request.user)
        
    context = {
        'form': form,
        'user': request.user,
        'active_nav': 'profile',
    }
    return render(request, 'admin_panel/profile.html', context)


@super_admin_required
def bp_reset_password(request, pk=None):
    target_bp = None
    target_user = None
    if pk:
        target_bp = get_object_or_404(BusinessPartner, pk=pk)
        target_user = target_bp.user

    if request.method == 'POST':
        form = BPResetPasswordForm(request.POST, target_user=target_user)
        if form.is_valid():
            updated_user = form.save()
            company_name = updated_user.business_partner.company_name if hasattr(updated_user, 'business_partner') else updated_user.username
            messages.success(request, f"Password for business partner @{updated_user.username} ({company_name}) has been reset successfully.")
            if target_bp:
                return redirect('admin_panel:bp_detail', pk=target_bp.pk)
            return redirect('admin_panel:bp_list')
    else:
        form = BPResetPasswordForm(target_user=target_user)

    total_bps = BusinessPartner.objects.filter(is_deleted=False).count()
    context = {
        'form': form,
        'target_bp': target_bp,
        'active_nav': 'reset_password',
        'total_bps': total_bps,
    }
    return render(request, 'admin_panel/bp_reset_password.html', context)


@super_admin_required
def credit_list(request):
    """Master overview table of all credit transactions across all business partners."""
    transactions = CreditTransaction.objects.select_related('business_partner', 'created_by').all()

    # Filter by business partner
    bp_id = request.GET.get('bp')
    selected_bp = None
    if bp_id:
        transactions = transactions.filter(business_partner_id=bp_id)
        selected_bp = BusinessPartner.objects.filter(pk=bp_id).first()

    # Filter by transaction type
    tx_type = request.GET.get('type')
    if tx_type in dict(CreditTransaction.TransactionType.choices):
        transactions = transactions.filter(transaction_type=tx_type)

    # Search by keyword
    q = request.GET.get('q', '').strip()
    if q:
        transactions = transactions.filter(
            Q(description__icontains=q) |
            Q(reference_id__icontains=q) |
            Q(business_partner__company_name__icontains=q)
        )

    # Summary metrics across all transactions
    all_txs = CreditTransaction.objects.all()
    total_allocated = sum(t.amount for t in all_txs if t.is_credit)
    total_deducted = sum(t.amount for t in all_txs if not t.is_credit)
    net_credits = total_allocated - total_deducted
    active_bps_with_credits = BusinessPartner.objects.filter(credit_transactions__isnull=False, is_deleted=False).distinct().count()

    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    all_bps = BusinessPartner.objects.filter(is_deleted=False).order_by('company_name')

    context = {
        'page_obj': page_obj,
        'transactions': page_obj.object_list,
        'all_bps': all_bps,
        'selected_bp': selected_bp,
        'selected_type': tx_type,
        'q': q,
        'total_allocated': total_allocated,
        'total_deducted': total_deducted,
        'net_credits': net_credits,
        'active_bps_with_credits': active_bps_with_credits,
        'active_nav': 'credits',
    }
    return render(request, 'admin_panel/credit_list.html', context)


@super_admin_required
def bp_credit_ledger(request, bp_id):
    """Specific credit ledger for an individual business partner."""
    bp = get_object_or_404(BusinessPartner, pk=bp_id)
    transactions = bp.credit_transactions.select_related('created_by').all()

    total_allocated = sum(t.amount for t in transactions if t.is_credit)
    total_deducted = sum(t.amount for t in transactions if not t.is_credit)
    net_ledger = total_allocated - total_deducted

    context = {
        'bp': bp,
        'transactions': transactions,
        'total_allocated': total_allocated,
        'total_deducted': total_deducted,
        'net_ledger': net_ledger,
        'active_nav': 'credits',
    }
    return render(request, 'admin_panel/bp_credit_ledger.html', context)


@super_admin_required
def credit_create(request):
    """Create a new credit transaction (allocation, top-up, bonus, deduction)."""
    bp_id = request.GET.get('bp')
    initial = {}
    if bp_id:
        bp = BusinessPartner.objects.filter(pk=bp_id, is_deleted=False).first()
        if bp:
            initial['business_partner'] = bp

    if request.method == 'POST':
        form = CreditTransactionForm(request.POST)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.created_by = request.user
            tx.save()
            messages.success(
                request,
                f"Successfully recorded {tx.get_transaction_type_display()} of {tx.amount:,} credits for {tx.business_partner.company_name}."
            )
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('admin_panel:bp_credit_ledger', bp_id=tx.business_partner.pk)
    else:
        form = CreditTransactionForm(initial=initial)

    target_bp_id = bp_id or request.POST.get('business_partner')
    target_bp = BusinessPartner.objects.filter(pk=target_bp_id).first() if target_bp_id else None

    context = {
        'form': form,
        'target_bp': target_bp,
        'is_edit': False,
        'active_nav': 'credits',
    }
    return render(request, 'admin_panel/credit_form.html', context)


@super_admin_required
def credit_update(request, pk):
    """Update an existing credit transaction."""
    tx = get_object_or_404(CreditTransaction, pk=pk)

    if request.method == 'POST':
        form = CreditTransactionForm(request.POST, instance=tx)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Updated transaction #{tx.pk} for {tx.business_partner.company_name}."
            )
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('admin_panel:bp_credit_ledger', bp_id=tx.business_partner.pk)
    else:
        form = CreditTransactionForm(instance=tx)

    context = {
        'form': form,
        'transaction': tx,
        'target_bp': tx.business_partner,
        'is_edit': True,
        'active_nav': 'credits',
    }
    return render(request, 'admin_panel/credit_form.html', context)


@require_POST
@super_admin_required
def credit_delete(request, pk):
    """Delete/void an existing credit transaction."""
    tx = get_object_or_404(CreditTransaction, pk=pk)
    bp = tx.business_partner
    amount = tx.amount
    tx_type = tx.get_transaction_type_display()
    tx.delete()

    messages.success(
        request,
        f"Voided/Deleted {tx_type} of {amount:,} credits for {bp.company_name}."
    )
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_panel:credit_list'
    return redirect(next_url)


@super_admin_required
def admin_conversations(request):
    """
    Super Admin view of all call conversations across all Business Partners with BP filter.
    """
    bps = BusinessPartner.objects.filter(is_deleted=False).order_by('company_name')
    bp_id = request.GET.get('bp', '').strip()

    qs = CallConversation.objects.all().select_related('business_partner').order_by('-call_timestamp')
    selected_bp = None
    if bp_id:
        try:
            selected_bp = BusinessPartner.objects.get(pk=bp_id)
            qs = qs.filter(business_partner=selected_bp)
        except BusinessPartner.DoesNotExist:
            selected_bp = None

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(conversation_id__icontains=q) |
            Q(agent_id__icontains=q) |
            Q(caller_number__icontains=q) |
            Q(called_number__icontains=q) |
            Q(call_sid__icontains=q) |
            Q(caller_name__icontains=q) |
            Q(business_partner__company_name__icontains=q)
        )

    # Evaluation filter
    eval_filter = request.GET.get('evaluation', '').strip()
    if eval_filter:
        qs = qs.filter(evaluation__iexact=eval_filter)

    # Summary metrics
    total_calls = qs.count()
    aggregates = qs.aggregate(
        total_duration=Sum('duration'),
        total_cost=Sum('conversation_cost'),
        total_llm=Sum('credits_llm')
    )
    total_duration_secs = aggregates['total_duration'] or 0
    total_cost = aggregates['total_cost'] or 0.0
    total_llm = aggregates['total_llm'] or 0.0

    from dashboard.views import format_total_duration

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
        'bps': bps,
        'selected_bp': selected_bp,
        'selected_bp_id': bp_id,
        'page_obj': page_obj,
        'total_calls': total_calls,
        'total_duration_formatted': format_total_duration(total_duration_secs),
        'total_cost': total_cost,
        'total_llm': total_llm,
        'q': q,
        'eval_filter': eval_filter,
        'is_admin_view': True,
        'active_nav': 'conversations',
    }
    return render(request, 'dashboard/conversations.html', context)


@require_POST
@super_admin_required
def admin_sync_conversations_api(request):
    """
    Super Admin endpoint to trigger sync for a selected partner or all partners with API keys.
    """
    bp_id = request.POST.get('bp', '').strip()
    if bp_id:
        bp = get_object_or_404(BusinessPartner, pk=bp_id)
        res = ElevenLabsService.sync_conversations(bp)
        return JsonResponse(res)

    # Sync all active partners with API key
    active_bps = BusinessPartner.objects.filter(is_active=True, is_deleted=False).exclude(elevenlabs_api_key='')
    if not active_bps.exists():
        return JsonResponse({'error': True, 'message': 'No active Business Partners have an ElevenLabs API key configured.'}, status=400)

    total_synced = 0
    total_created = 0
    total_updated = 0
    for partner in active_bps:
        res = ElevenLabsService.sync_conversations(partner)
        if res.get('success'):
            total_synced += res.get('synced_count', 0)
            total_created += res.get('created_count', 0)
            total_updated += res.get('updated_count', 0)

    return JsonResponse({
        'success': True,
        'synced_count': total_synced,
        'created_count': total_created,
        'updated_count': total_updated,
        'message': f"Synchronized {len(active_bps)} partner(s): {total_synced} calls processed ({total_created} new, {total_updated} updated)."
    })


