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
    
    if not bp.elevenlabs_api_key:
        context['no_api_key'] = True
        return render(request, 'dashboard/index.html', context)
        
    api_key = bp.elevenlabs_api_key
    
    subscription_info = ElevenLabsService.get_subscription_info(api_key)
    usage_history = ElevenLabsService.get_usage_history(api_key)
    voices = ElevenLabsService.get_voices(api_key)
    
    if subscription_info.get('error'):
        context['api_error'] = subscription_info.get('message')
        return render(request, 'dashboard/index.html', context)
        
    alert_sent = check_and_send_credit_alert(bp, subscription_info)
    
    today = timezone.localdate()
    CreditSnapshot.objects.update_or_create(
        business_partner=bp,
        snapshot_date=today,
        defaults={
            'character_count': subscription_info.get('character_count', 0),
            'character_limit': subscription_info.get('character_limit', 0)
        }
    )
    
    recent_snapshots = CreditSnapshot.objects.filter(business_partner=bp).order_by('-snapshot_date')[:30]
    
    chart_labels = []
    chart_data = []
    
    if usage_history and isinstance(usage_history, dict) and 'points' in usage_history:
        for point in usage_history.get('points', []):
            if 'time' in point and 'value' in point:
                import datetime
                dt = datetime.datetime.fromtimestamp(point['time']/1000)
                chart_labels.append(dt.strftime('%b %d'))
                chart_data.append(point['value'])
    else:
        # Fallback
        for snap in reversed(recent_snapshots):
            chart_labels.append(snap.snapshot_date.strftime('%b %d'))
            chart_data.append(snap.character_count)
            
    usage_chart_data = {
        'labels': chart_labels,
        'datasets': [{
            'label': 'Character Count',
            'data': chart_data,
            'borderColor': 'rgb(75, 192, 192)',
            'tension': 0.1
        }]
    }
    
    character_limit = subscription_info.get('character_limit', 0)
    character_count = subscription_info.get('character_count', 0)
    remaining = max(0, character_limit - character_count)
    usage_percentage = round((character_count / character_limit * 100), 1) if character_limit else 0
    remaining_percentage = 100 - usage_percentage
    
    alert_status = (remaining <= bp.credit_alert_threshold) if bp.credit_alert_threshold > 100 else (remaining_percentage <= bp.credit_alert_threshold)

    context.update({
        'subscription_info': subscription_info,
        'voices': voices,
        'recent_snapshots': recent_snapshots,
        'usage_chart_data': json.dumps(usage_chart_data),
        'character_limit': character_limit,
        'character_count': character_count,
        'remaining': remaining,
        'usage_percentage': usage_percentage,
        'alert_status': alert_status,
        'alert_sent': alert_sent
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

