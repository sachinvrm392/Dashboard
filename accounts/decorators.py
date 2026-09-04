from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def super_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_super_admin():
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def business_partner_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_business_partner():
            return redirect('home')
        if request.user.must_change_password:
            return redirect('accounts:change_password')
        if not hasattr(request.user, 'business_partner') or not request.user.business_partner.is_active:
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper
