from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import home_redirect
from dashboard.views import copilot_view

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('copilot/', copilot_view, name='copilot'),
    path('command-center/', copilot_view, name='command_center'),
    path('', home_redirect, name='home'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
