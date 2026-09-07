from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, BusinessPartner
from dashboard.models import CreditTransaction

class CreditCRUDE2ETestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Create Super Admin
        self.super_admin = User.objects.create_superuser(
            username='admin_boss',
            email='admin@example.com',
            password='adminpassword123',
            role=User.Role.SUPER_ADMIN
        )
        
        # 2. Create BP User & Partner
        self.bp_user = User.objects.create_user(
            username='cardano_partner',
            email='cardano@example.com',
            password='bppassword123',
            role=User.Role.BUSINESS_PARTNER
        )
        self.bp = BusinessPartner.objects.create(
            user=self.bp_user,
            company_name='Cardano Innovations',
            contact_person='Charles C',
            email='cardano@example.com',
            credit_alert_threshold=1000
        )

    def test_security_non_superadmin_blocked(self):
        # Anonymous
        response = self.client.get(reverse('admin_panel:credit_list'))
        self.assertEqual(response.status_code, 302)
        
        # Business Partner User
        self.client.force_login(self.bp_user)
        response = self.client.get(reverse('admin_panel:credit_list'))
        # Should redirect to home/dashboard
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse('admin_panel:credit_list'))

    def test_credit_crud_lifecycle_and_balance_impact(self):
        self.client.force_login(self.super_admin)
        
        # 1. READ: Master Credit List
        res = self.client.get(reverse('admin_panel:credit_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Manage Business Partner Credits")
        
        # 2. CREATE: Add a credit top-up of 25,000
        add_url = reverse('admin_panel:credit_create')
        res = self.client.get(add_url)
        self.assertEqual(res.status_code, 200)
        
        post_data = {
            'business_partner': self.bp.pk,
            'transaction_type': CreditTransaction.TransactionType.TOP_UP,
            'amount': 25000,
            'description': 'Q3 High-Usage Top-Up',
            'reference_id': 'INV-9901',
            'transaction_date': '2026-09-07',
        }
        res = self.client.post(add_url, post_data)
        # Should redirect to bp credit ledger
        self.assertEqual(res.status_code, 302)
        
        # Verify in DB
        tx = CreditTransaction.objects.filter(business_partner=self.bp).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, 25000)
        self.assertEqual(tx.created_by, self.super_admin)
        self.assertEqual(self.bp.get_ledger_credits(), 25000)
        
        # 3. READ: BP Credit Ledger
        ledger_url = reverse('admin_panel:bp_credit_ledger', kwargs={'bp_id': self.bp.pk})
        res = self.client.get(ledger_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "25,000")
        self.assertContains(res, "Q3 High-Usage Top-Up")
        
        # 4. Check BP Detail page reflects ledger credits
        bp_detail_url = reverse('admin_panel:bp_detail', kwargs={'pk': self.bp.pk})
        res = self.client.get(bp_detail_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['ledger_credits'], 25000)
        # Base was 1,000 credit_alert_threshold; effective should be 1,000 + 25,000 = 26,000
        self.assertEqual(res.context['character_limit'], self.bp.credit_alert_threshold + 25000)
        
        # 5. UPDATE: Edit the transaction amount to 30,000
        update_url = reverse('admin_panel:credit_update', kwargs={'pk': tx.pk})
        res = self.client.get(update_url)
        self.assertEqual(res.status_code, 200)
        
        edit_data = {
            'business_partner': self.bp.pk,
            'transaction_type': CreditTransaction.TransactionType.TOP_UP,
            'amount': 30000,
            'description': 'Q3 High-Usage Top-Up (Revised)',
            'reference_id': 'INV-9901-REV',
            'transaction_date': '2026-09-07',
        }
        res = self.client.post(update_url, edit_data)
        self.assertEqual(res.status_code, 302)
        
        tx.refresh_from_db()
        self.assertEqual(tx.amount, 30000)
        self.assertEqual(self.bp.get_ledger_credits(), 30000)
        
        # 6. DELETE: Void / Delete the transaction
        delete_url = reverse('admin_panel:credit_delete', kwargs={'pk': tx.pk})
        res = self.client.post(delete_url)
        self.assertEqual(res.status_code, 302)
        
        self.assertEqual(CreditTransaction.objects.filter(pk=tx.pk).count(), 0)
        self.assertEqual(self.bp.get_ledger_credits(), 0)
