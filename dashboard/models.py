from django.db import models
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
