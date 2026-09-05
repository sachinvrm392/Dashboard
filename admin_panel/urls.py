from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('partners/', views.bp_list, name='bp_list'),
    path('bp/create/', views.bp_create, name='bp_create'),
    path('bp/<int:pk>/edit/', views.bp_update, name='bp_update'),
    path('bp/<int:pk>/toggle/', views.bp_toggle_active, name='bp_toggle'),
    path('bp/<int:pk>/delete/', views.bp_soft_delete, name='bp_soft_delete'),
    path('bp/<int:pk>/restore/', views.bp_restore, name='bp_restore'),
    path('bp/<int:pk>/hard-delete/', views.bp_hard_delete, name='bp_hard_delete'),
    path('bp/empty-trash/', views.bp_empty_trash, name='bp_empty_trash'),
    path('bp/reset-password/', views.bp_reset_password, name='bp_reset_password_general'),
    path('bp/<int:pk>/reset-password/', views.bp_reset_password, name='bp_reset_password'),
    path('bp/<int:pk>/', views.bp_detail, name='bp_detail'),
    path('profile/', views.user_profile, name='profile'),
]
