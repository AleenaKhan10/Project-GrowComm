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
