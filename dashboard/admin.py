from django.contrib import admin
from .models import CreditSnapshot, CreditTransaction

@admin.register(CreditSnapshot)
class CreditSnapshotAdmin(admin.ModelAdmin):
    list_display = ('business_partner', 'snapshot_date', 'character_count', 'character_limit', 'usage_percentage')
    list_filter = ('snapshot_date', 'business_partner')
    search_fields = ('business_partner__company_name',)

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('business_partner', 'transaction_type', 'amount', 'transaction_date', 'created_by')
    list_filter = ('transaction_type', 'transaction_date', 'business_partner')
    search_fields = ('business_partner__company_name', 'description', 'reference_id')
