from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

def check_and_send_credit_alert(bp, subscription_info):
    if subscription_info.get('error'):
        return False
        
    character_count = subscription_info.get('character_count', 0)
    character_limit = subscription_info.get('character_limit', 0)
    
    if character_limit == 0:
        return False
        
    usage_percentage = (character_count / character_limit) * 100
    remaining_percentage = 100 - usage_percentage
    remaining = max(0, character_limit - character_count)
    
    # Alert if remaining credits are less than or equal to threshold (supports absolute credits e.g. 1000 or legacy percentage)
    is_alert = (remaining <= bp.credit_alert_threshold) if bp.credit_alert_threshold > 100 else (remaining_percentage <= bp.credit_alert_threshold)
    if is_alert:
        now = timezone.now()
        if bp.last_alert_sent and (now - bp.last_alert_sent) < timedelta(hours=24):
            return False
            
        context = {
            'company_name': bp.company_name,
            'character_limit': character_limit,
            'character_count': character_count,
            'remaining': max(0, character_limit - character_count),
            'remaining_percentage': round(remaining_percentage, 1),
            'usage_percentage': round(usage_percentage, 1)
        }
        
        html_message = render_to_string('dashboard/emails/credit_alert.html', context)
        subject = f'Credit Alert - {bp.company_name}'
        
        send_mail(
            subject=subject,
            message=f"Your credits are running low. You have {remaining_percentage:.1f}% remaining.",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[bp.email],
            html_message=html_message,
            fail_silently=True
        )
        
        bp.last_alert_sent = now
        bp.save(update_fields=['last_alert_sent'])
        return True
        
    return False
