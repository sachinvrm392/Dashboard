from accounts.models import BusinessPartner

def admin_sidebar_context(request):
    if request.user.is_authenticated and hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
        total_bps = BusinessPartner.objects.filter(is_deleted=False).count()
        return {'total_bps': total_bps}
    return {'total_bps': 0}
