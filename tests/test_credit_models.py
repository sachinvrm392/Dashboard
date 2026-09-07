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

    def test_bp_dashboard_and_admin_detail_managed_credit_mode(self):
        from django.test import Client
        from django.urls import reverse
        
        superadmin = User.objects.create_user(
            username='admin_kpi',
            password='Password123!',
            role=User.Role.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True
        )
        bp_user = User.objects.create_user(
            username='bp_kpi',
            password='Password123!',
            role=User.Role.BUSINESS_PARTNER
        )
        bp = BusinessPartner.objects.create(
            user=bp_user,
            company_name='Omega Ledger',
            credit_alert_threshold=1000
        )
        CreditTransaction.objects.create(
            business_partner=bp,
            transaction_type=CreditTransaction.TransactionType.ALLOCATION,
            amount=10000,
            created_by=superadmin
        )
        
        client = Client()
        client.force_login(bp_user)
        res = client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['character_limit'], 10000)
        self.assertEqual(res.context['character_count'], 0)
        self.assertEqual(res.context['remaining'], 10000)
        self.assertEqual(res.context['usage_percentage'], 0.0)
        self.assertFalse(res.context['alert_status'])
        
        content = res.content.decode('utf-8')
        self.assertIn('10,000', content)
        self.assertIn('Managed Allocation', content)
        self.assertIn('&lt; 1,000 credits remaining', content)

        admin_client = Client()
        admin_client.force_login(superadmin)
        admin_res = admin_client.get(reverse('admin_panel:bp_detail', kwargs={'pk': bp.pk}))
        self.assertEqual(admin_res.status_code, 200)
        self.assertEqual(admin_res.context['character_limit'], 10000)
        self.assertEqual(admin_res.context['character_count'], 0)
        self.assertEqual(admin_res.context['remaining'], 10000)
