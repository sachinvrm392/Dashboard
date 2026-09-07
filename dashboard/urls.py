from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.bp_dashboard, name='index'),
    path('api/refresh/', views.refresh_credits, name='refresh'),
    path('copilot/', views.copilot_view, name='copilot'),
    path('conversations/', views.bp_conversations, name='conversations'),
    path('conversations/sync/', views.sync_conversations_api, name='conversations_sync'),
    path('conversations/<int:pk>/transcript/', views.conversation_transcript_api, name='conversation_transcript'),
]

