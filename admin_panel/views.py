from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from accounts.models import BusinessPartner, User
from accounts.decorators import super_admin_required
from dashboard.services import ElevenLabsService
from .forms import BPCreateForm, BPUpdateForm, UserProfileForm
from django.contrib.auth.decorators import login_required

import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from dashboard.models import CreditSnapshot

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
    latest_bps = bps[:5]
    
    for bp in latest_bps:
        bp_info = {
            'bp': bp,
            'credit_info': None,
            'api_error': False,
            'remaining': 0,
            'usage_percentage': 0.0,
        }
        
        if bp.elevenlabs_api_key:
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
    for bp in page_obj:
        bp_info = {
            'bp': bp,
            'credit_info': None,
            'api_error': False,
            'remaining': 0,
            'usage_percentage': 0.0,
        }
        if bp.elevenlabs_api_key:
            try:
                credit_info = ElevenLabsService.get_subscription_info(bp.elevenlabs_api_key)
                if not credit_info.get('error'):
                    bp_info['credit_info'] = credit_info
                    char_limit = credit_info.get('character_limit', 0)
                    char_count = credit_info.get('character_count', 0)
                    bp_info['remaining'] = max(0, char_limit - char_count)
                    bp_info['usage_percentage'] = round((char_count / char_limit * 100), 1) if char_limit else 0
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

@super_admin_required
def bp_detail(request, pk):
    bp = get_object_or_404(BusinessPartner, pk=pk)
    
    credit_info = None
    voices = []
    api_error = False
    
    if bp.elevenlabs_api_key:
        try:
            credit_info = ElevenLabsService.get_subscription_info(bp.elevenlabs_api_key)
            voices = ElevenLabsService.get_voices(bp.elevenlabs_api_key)
        except Exception:
            api_error = True
            
    context = {
        'bp': bp,
        'credit_info': credit_info,
        'voices': voices,
        'api_error': api_error
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
