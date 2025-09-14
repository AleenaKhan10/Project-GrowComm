from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class AuditEvent(models.Model):
    """
    Simple audit event model with required fields only.
    """
    
    # Action Types
    ACTION_CHOICES = [
        ('invite_created', 'Invite Created'),
        ('user_registered', 'User Registered'),
        ('user_signin', 'User Sign In'),
        ('user_signout', 'User Sign Out'),
        ('referral_sent', 'Referral Sent'),
        ('slot_booked', 'Message Slot Booked'),
        ('message_answered', 'Message Answered for First Time'),
        ('user_deleted', 'User Deleted'),
        ('profile_edited', 'Profile Edited'),
        ('user_reported', 'User Reported'),
        ('user_unblocked', 'User Unblocked'),
        # User management actions
        ('user_suspended', 'User Suspended'),
        ('user_unsuspended', 'User Unsuspended'),
        ('user_soft_deleted', 'User Soft Deleted'),
        ('user_restored', 'User Restored'),
        ('bulk_user_action', 'Bulk User Action'),
        # Focus tracking actions
        ('page_focus_start', 'Page Focus Started'),
        ('page_focus_end', 'Page Focus Ended'),
    ]
    
    # Required Fields
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions_performed',
        help_text="User who performed the action"
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions_received',
        help_text="User who was the target of the action (if applicable)"
    )
    action = models.CharField(
        max_length=50, 
        choices=ACTION_CHOICES,
        help_text="Action that was performed"
    )
    action_detail = models.TextField(
        blank=True,
        help_text="Additional details about the action"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the action occurred"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Event'
        verbose_name_plural = 'Audit Events'
    
    def __str__(self):
        username = self.user.username if self.user else "Deleted User"
        return f"{self.get_action_display()} - {username} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def log_action(cls, user, action, action_detail="", target_user=None):
        """
        Class method to create audit event.
        
        Args:
            user: User instance who performed the action
            action: String matching one of the ACTION_CHOICES
            action_detail: Optional detail about the action
            target_user: Optional user instance who was the target of the action
        """
        return cls.objects.create(
            user=user,
            action=action,
            action_detail=action_detail,
            target_user=target_user
        )
    
    @classmethod
    def get_stats_for_period(cls, start_time):
        """
        Get statistics for a specific time period.
        
        Args:
            start_time: datetime object for filtering
            
        Returns:
            dict with statistics for all action types
        """
        events = cls.objects.filter(timestamp__gte=start_time)
        
        return {
            'total_signins': events.filter(action='user_signin').count(),
            'total_signouts': events.filter(action='user_signout').count(),
            'total_invites': events.filter(action='invite_created').count(),
            'total_registrations': events.filter(action='user_registered').count(),
            'total_referrals': events.filter(action='referral_sent').count(),
            'total_slots_opened': events.filter(action='slot_booked').count(),
            'total_users_deleted': events.filter(action='user_deleted').count(),
        }


class FocusLog(models.Model):
    """
    Model to track page focus events for user engagement analytics.
    """
    
    FOCUS_EVENT_CHOICES = [
        ('focus_start', 'Page Gained Focus'),
        ('focus_end', 'Page Lost Focus'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="User whose focus is being tracked"
    )
    page_url = models.URLField(
        max_length=500,
        help_text="URL of the page that gained/lost focus"
    )
    page_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Title of the page"
    )
    event_type = models.CharField(
        max_length=20,
        choices=FOCUS_EVENT_CHOICES,
        help_text="Type of focus event"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the focus event occurred"
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Browser session identifier"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser user agent string"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="User's IP address"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Focus Log'
        verbose_name_plural = 'Focus Logs'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['page_url', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else "Unknown"
        event = "📍" if self.event_type == 'focus_start' else "💤"
        return f"{event} {username} - {self.page_title or self.page_url} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @classmethod
    def log_focus_event(cls, user, page_url, event_type, page_title="", session_id="", user_agent="", ip_address=None):
        """
        Log a focus event.
        
        Args:
            user: User instance
            page_url: URL of the page
            event_type: 'focus_start' or 'focus_end'
            page_title: Title of the page (optional)
            session_id: Browser session ID (optional)
            user_agent: Browser user agent (optional)
            ip_address: User's IP address (optional)
        """
        return cls.objects.create(
            user=user,
            page_url=page_url,
            page_title=page_title,
            event_type=event_type,
            session_id=session_id,
            user_agent=user_agent,
            ip_address=ip_address
        )
    
    @classmethod
    def get_user_focus_duration(cls, user, start_time=None, end_time=None):
        """
        Calculate total focus duration for a user within a time period.
        
        Args:
            user: User instance
            start_time: Optional start datetime filter
            end_time: Optional end datetime filter
            
        Returns:
            Total focus duration in seconds
        """
        focus_events = cls.objects.filter(user=user)
        
        if start_time:
            focus_events = focus_events.filter(timestamp__gte=start_time)
        if end_time:
            focus_events = focus_events.filter(timestamp__lte=end_time)
            
        focus_events = focus_events.order_by('timestamp')
        
        total_duration = 0
        focus_start = None
        
        for event in focus_events:
            if event.event_type == 'focus_start':
                focus_start = event.timestamp
            elif event.event_type == 'focus_end' and focus_start:
                duration = (event.timestamp - focus_start).total_seconds()
                total_duration += duration
                focus_start = None
                
        return total_duration
    
    @classmethod
    def get_page_engagement_stats(cls, page_url, start_time=None, end_time=None):
        """
        Get engagement statistics for a specific page.
        
        Args:
            page_url: URL of the page to analyze
            start_time: Optional start datetime filter
            end_time: Optional end datetime filter
            
        Returns:
            Dictionary with engagement statistics
        """
        events = cls.objects.filter(page_url=page_url)
        
        if start_time:
            events = events.filter(timestamp__gte=start_time)
        if end_time:
            events = events.filter(timestamp__lte=end_time)
            
        total_focus_sessions = events.filter(event_type='focus_start').count()
        unique_users = events.values('user').distinct().count()
        
        return {
            'total_focus_sessions': total_focus_sessions,
            'unique_users': unique_users,
            'total_events': events.count(),
        }
