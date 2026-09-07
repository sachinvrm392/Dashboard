from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        BUSINESS_PARTNER = 'BUSINESS_PARTNER', 'Business Partner'
    
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BUSINESS_PARTNER)
    must_change_password = models.BooleanField(default=False)
    
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN
    
    def is_business_partner(self):
        return self.role == self.Role.BUSINESS_PARTNER

class BusinessPartner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_partner')
    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(upload_to='bp_logos/', blank=True, null=True)
    elevenlabs_api_key = models.CharField(max_length=255, blank=True)
    elevenlabs_agent_id = models.CharField(max_length=255, blank=True, default='', help_text='11lab Agent ID')
    credit_alert_threshold = models.IntegerField(default=1000, help_text='Credit limit or alert threshold (credits)')
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    last_alert_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name
    
    def get_ledger_credits(self):
        """Calculate net credits from all credit transactions (allocations + topups + bonuses - deductions)."""
        txs = self.credit_transactions.all()
        positive = sum(t.amount for t in txs if t.transaction_type in ['ALLOCATION', 'TOP_UP', 'BONUS'])
        negative = sum(t.amount for t in txs if t.transaction_type == 'DEDUCTION')
        return positive - negative
    
    class Meta:
        ordering = ['-created_at']
