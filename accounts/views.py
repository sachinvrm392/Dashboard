from django.shortcuts import redirect
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, CustomPasswordChangeForm

@login_required
def home_redirect(request):
    if request.user.is_super_admin():
        return redirect('/admin-panel/')
    elif request.user.is_business_partner():
        return redirect('/dashboard/')
    return redirect('accounts:login')

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    
    def get_success_url(self):
        user = self.request.user
        if user.must_change_password:
            return reverse_lazy('accounts:change_password')
        if user.is_super_admin():
            return '/admin-panel/'
        return '/dashboard/'

from django.contrib.auth import logout

def custom_logout(request):
    logout(request)
    return redirect('accounts:login')

class CustomLogoutView(LogoutView):
    next_page = 'accounts:login'

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

class ChangePasswordView(PasswordChangeView):
    template_name = 'accounts/change_password.html'
    form_class = CustomPasswordChangeForm
    
    def get_success_url(self):
        user = self.request.user
        if user.is_super_admin():
            return '/admin-panel/'
        return '/dashboard/'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.must_change_password = False
        self.request.user.save()
        return response
