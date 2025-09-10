from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import AuditEvent
from .views import log_audit_action, get_time_filter
import json

User = get_user_model()


class AuditEventModelTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_audit_event_creation(self):
        """Test basic audit event creation"""
        event = AuditEvent.objects.create(
            user=self.user,
            action='user_signin',
            action_detail='Login from mobile app'
        )
        
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.action, 'user_signin')
        self.assertEqual(event.action_detail, 'Login from mobile app')
        self.assertIsNotNone(event.timestamp)
    
    def test_log_action_class_method(self):
        """Test the log_action class method"""
        event = AuditEvent.log_action(
            user=self.user,
            action='profile_edited',
            action_detail='Updated profile picture'
        )
        
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.action, 'profile_edited')
        self.assertEqual(event.action_detail, 'Updated profile picture')
    
    def test_get_stats_for_period(self):
        """Test the get_stats_for_period class method"""
        # Create some test events
        AuditEvent.log_action(self.user, 'user_signin')
        AuditEvent.log_action(self.user, 'user_signin')
        AuditEvent.log_action(self.user, 'user_signout')
        AuditEvent.log_action(self.user, 'invite_created')
        
        # Get stats for the last hour
        start_time = timezone.now() - timedelta(hours=1)
        stats = AuditEvent.get_stats_for_period(start_time)
        
        self.assertEqual(stats['total_signins'], 2)
        self.assertEqual(stats['total_signouts'], 1)
        self.assertEqual(stats['total_invites'], 1)
        self.assertEqual(stats['total_registrations'], 0)


class AuditViewsTests(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create some test events
        AuditEvent.log_action(self.user, 'user_signin', 'Test signin')
        AuditEvent.log_action(self.user, 'user_signout', 'Test signout')
        AuditEvent.log_action(self.user, 'invite_created', 'Test invite')
    
    def test_log_audit_action_utility(self):
        """Test the log_audit_action utility function"""
        result = log_audit_action(self.user, 'profile_edited', 'Updated name')
        self.assertTrue(result)
        
        # Verify the event was created
        event = AuditEvent.objects.filter(
            user=self.user,
            action='profile_edited'
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.action_detail, 'Updated name')
    
    def test_get_time_filter(self):
        """Test the get_time_filter function"""
        now = timezone.now()
        
        # Test today filter
        today_start = get_time_filter('today')
        self.assertEqual(today_start.hour, 0)
        self.assertEqual(today_start.minute, 0)
        
        # Test last 24 hours filter
        last_24h = get_time_filter('last_24_hours')
        self.assertLess(last_24h, now)
        
        # Test default filter (should default to today)
        default = get_time_filter('invalid_filter')
        self.assertEqual(default.hour, 0)
    
    def test_get_audit_statistics_view(self):
        """Test the get_audit_statistics API endpoint"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('audittrack:statistics')
        response = self.client.get(url, {'filter': 'today'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('total_signins', data)
        self.assertIn('total_signouts', data)
        self.assertIn('total_invites', data)
        self.assertIn('filter_applied', data)
        self.assertEqual(data['filter_applied'], 'today')
    
    def test_get_audit_logs_view(self):
        """Test the get_audit_logs API endpoint"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('audittrack:logs')
        response = self.client.get(url, {'page': 1, 'per_page': 10})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('logs', data)
        self.assertIn('pagination', data)
        self.assertGreater(len(data['logs']), 0)
    
    def test_create_audit_log_view(self):
        """Test the create_audit_log API endpoint"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('audittrack:create_log')
        payload = {
            'action': 'referral_sent',
            'action_detail': 'Referred friend via email'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify the event was created
        event = AuditEvent.objects.filter(
            user=self.user,
            action='referral_sent'
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.action_detail, 'Referred friend via email')
    
    def test_create_audit_log_invalid_action(self):
        """Test create_audit_log with invalid action"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('audittrack:create_log')
        payload = {
            'action': 'invalid_action',
            'action_detail': 'This should fail'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('valid_actions', data)
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access API endpoints"""
        url = reverse('audittrack:statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login