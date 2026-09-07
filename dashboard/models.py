from django.db import models
from django.utils import timezone
from accounts.models import BusinessPartner

class CreditSnapshot(models.Model):
    business_partner = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE, related_name='credit_snapshots')
    character_count = models.IntegerField(default=0)  # used
    character_limit = models.IntegerField(default=0)  # total
    snapshot_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-snapshot_date']
        unique_together = ['business_partner', 'snapshot_date']
    
    @property
    def remaining(self):
        return max(0, self.character_limit - self.character_count)
    
    @property
    def usage_percentage(self):
        if self.character_limit == 0:
            return 0
        return round((self.character_count / self.character_limit) * 100, 1)
    
    def __str__(self):
        return f'{self.business_partner.company_name} - {self.snapshot_date}'


class CreditTransaction(models.Model):
    class TransactionType(models.TextChoices):
        ALLOCATION = 'ALLOCATION', 'Initial / Cycle Allocation'
        TOP_UP = 'TOP_UP', 'Credit Top-Up'
        BONUS = 'BONUS', 'Bonus Credits'
        DEDUCTION = 'DEDUCTION', 'Deduction / Correction'

    business_partner = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE, related_name='credit_transactions')
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, default=TransactionType.TOP_UP)
    amount = models.PositiveIntegerField(help_text="Amount in credits/characters")
    description = models.CharField(max_length=255, blank=True, help_text="Reason or note for this transaction")
    reference_id = models.CharField(max_length=100, blank=True, help_text="Invoice, PO, or external reference number")
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_credit_transactions')
    transaction_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    @property
    def is_credit(self):
        return self.transaction_type in [self.TransactionType.ALLOCATION, self.TransactionType.TOP_UP, self.TransactionType.BONUS]

    @property
    def signed_amount(self):
        return self.amount if self.is_credit else -self.amount

    def __str__(self):
        return f"{self.business_partner.company_name} - {self.get_transaction_type_display()} ({self.amount})"
