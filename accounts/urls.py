from django.urls import path
from .views import CustomLoginView, custom_logout, ChangePasswordView

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
