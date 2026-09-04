from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.bp_dashboard, name='index'),
    path('api/refresh/', views.refresh_credits, name='refresh'),
    path('copilot/', views.copilot_view, name='copilot'),
]

