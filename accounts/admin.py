from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, BusinessPartner

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Permissions', {'fields': ('role', 'must_change_password')}),
    )

@admin.register(BusinessPartner)
class BusinessPartnerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'contact_person', 'email', 'is_active')
    search_fields = ('company_name', 'email', 'contact_person')
    list_filter = ('is_active',)
