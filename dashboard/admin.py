from django.contrib import admin
from .models import CreditSnapshot

@admin.register(CreditSnapshot)
class CreditSnapshotAdmin(admin.ModelAdmin):
    list_display = ('business_partner', 'snapshot_date', 'character_count', 'character_limit', 'usage_percentage')
    list_filter = ('snapshot_date', 'business_partner')
    search_fields = ('business_partner__company_name',)
