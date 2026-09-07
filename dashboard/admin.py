from django.contrib import admin
from .models import CreditSnapshot, CreditTransaction, CallConversation

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

@admin.register(CallConversation)
class CallConversationAdmin(admin.ModelAdmin):
    list_display = ('conversation_id', 'business_partner', 'call_timestamp', 'duration', 'evaluation', 'conversation_cost', 'credits_llm')
    list_filter = ('evaluation', 'call_timestamp', 'business_partner')
    search_fields = ('conversation_id', 'agent_id', 'caller_number', 'called_number', 'call_sid', 'caller_name')

