from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, BusinessPartner
from dashboard.models import CallConversation

class CallConversationTestCase(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create_user(
            username='conv_admin',
            email='conv_admin@example.com',
            password='Password123!',
            role=User.Role.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.bp_user = User.objects.create_user(
            username='conv_bp',
            email='conv_bp@example.com',
            password='Password123!',
            role=User.Role.BUSINESS_PARTNER
        )
        self.bp = BusinessPartner.objects.create(
            user=self.bp_user,
            company_name='Cardano Call Center',
            email='conv_bp@example.com',
            elevenlabs_api_key='test_dummy_key_123',
            elevenlabs_agent_id='agent_test_999'
        )

        # Create sample conversations
        self.c1 = CallConversation.objects.create(
            business_partner=self.bp,
            conversation_id='conv_test_001',
            call_timestamp=timezone.now(),
            agent_id='agent_test_999',
            evaluation='Success',
            duration=277,
            messages=[
                {'role': 'agent', 'message': 'Hello, how can I help you today?', 'time_in_call_secs': 1},
                {'role': 'user', 'message': 'I would like to inquire about Cardano services.', 'time_in_call_secs': 5}
            ],
            conversation_cost=4977.0,
            credits_llm=2950.0,
            caller_number='+1234567890',
            called_number='+1987654321',
            call_sid='CA_test_sid_001',
            caller_name='John Doe'
        )

        self.c2 = CallConversation.objects.create(
            business_partner=self.bp,
            conversation_id='conv_test_002',
            call_timestamp=timezone.now(),
            agent_id='agent_test_999',
            evaluation='Failure',
            duration=45,
            messages=[
                {'role': 'agent', 'message': 'Hello?', 'time_in_call_secs': 0}
            ],
            conversation_cost=350.0,
            credits_llm=180.0,
            caller_number='+1122334455',
            called_number='+1987654321',
            call_sid='CA_test_sid_002',
            caller_name='Jane Smith'
        )

    def test_model_properties(self):
        self.assertEqual(self.c1.duration_formatted, '4m 37s')
        self.assertEqual(self.c1.message_count, 2)
        self.assertEqual(self.c2.duration_formatted, '45s')
        self.assertEqual(self.c2.message_count, 1)

    def test_bp_conversations_view(self):
        client = Client()
        client.force_login(self.bp_user)
        res = client.get(reverse('dashboard:conversations'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'conv_test_001')
        self.assertContains(res, 'conv_test_002')
        self.assertContains(res, '4m 37s')
        self.assertContains(res, 'John Doe')
        self.assertContains(res, 'Sync Conversations')

        # Test search filter
        res_search = client.get(reverse('dashboard:conversations') + '?q=Jane')
        self.assertContains(res_search, 'conv_test_002')
        self.assertNotContains(res_search, 'conv_test_001')

    def test_admin_conversations_view(self):
        client = Client()
        client.force_login(self.superadmin)
        res = client.get(reverse('admin_panel:conversations'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'conv_test_001')
        self.assertContains(res, 'Cardano Call Center')

    def test_transcript_api(self):
        client = Client()
        client.force_login(self.bp_user)
        res = client.get(reverse('dashboard:conversation_transcript', kwargs={'pk': self.c1.pk}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['messages']), 2)
        self.assertEqual(data['messages'][0]['role'], 'agent')
