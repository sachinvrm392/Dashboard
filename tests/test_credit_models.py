from django.test import TestCase
from accounts.models import User, BusinessPartner
from dashboard.models import CreditTransaction

class CreditModelTestCase(TestCase):
    def test_credit_transaction_net_calculation(self):
        user = User.objects.create_user(username='bp_ledger_test', password='password123')
        bp = BusinessPartner.objects.create(user=user, company_name='Ledger Test Corp', email='ledger@example.com')
        
        # Initially 0
        self.assertEqual(bp.get_ledger_credits(), 0)
        
        # Initial Allocation: +10,000
        t1 = CreditTransaction.objects.create(
            business_partner=bp,
            transaction_type=CreditTransaction.TransactionType.ALLOCATION,
            amount=10000,
            description="Initial allocation"
        )
        self.assertTrue(t1.is_credit)
        self.assertEqual(t1.signed_amount, 10000)
        self.assertEqual(bp.get_ledger_credits(), 10000)
        
        # Top-up: +5,000
        t2 = CreditTransaction.objects.create(
            business_partner=bp,
            transaction_type=CreditTransaction.TransactionType.TOP_UP,
            amount=5000,
            description="Q3 Campaign top-up"
        )
        self.assertTrue(t2.is_credit)
        self.assertEqual(bp.get_ledger_credits(), 15000)
        
        # Bonus: +2,000
        t3 = CreditTransaction.objects.create(
            business_partner=bp,
            transaction_type=CreditTransaction.TransactionType.BONUS,
            amount=2000,
            description="Welcome bonus"
        )
        self.assertEqual(bp.get_ledger_credits(), 17000)
        
        # Deduction: -3,000
        t4 = CreditTransaction.objects.create(
            business_partner=bp,
            transaction_type=CreditTransaction.TransactionType.DEDUCTION,
            amount=3000,
            description="Correction"
        )
        self.assertFalse(t4.is_credit)
        self.assertEqual(t4.signed_amount, -3000)
        self.assertEqual(bp.get_ledger_credits(), 14000)
