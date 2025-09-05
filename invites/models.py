from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class InviteLink(models.Model):
    """Model for managing invite links with unique codes"""
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_invite')
    is_used = models.BooleanField(default=False)
    created_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"Invite {self.code} by {self.created_by.username}"
    
    def is_valid(self):
        """Check if invite is still valid"""
        if self.is_used:
            return False
        if self.expiry_date and timezone.now() > self.expiry_date:
            return False
        return True
    
    def mark_as_used(self, user):
        """Mark invite as used by a user"""
        self.is_used = True
        self.used_by = user
        self.save()


class ReferralApproval(models.Model):
    """Model for 3-level approval system for referrals"""
    invited_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='approval_status')
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referred_users')
    
    # 3-level approval system
    auth1_approved = models.BooleanField(default=False)
    auth1_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='auth1_approvals')
    auth1_approved_date = models.DateTimeField(null=True, blank=True)
    
    auth2_approved = models.BooleanField(default=False)
    auth2_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='auth2_approvals')
    auth2_approved_date = models.DateTimeField(null=True, blank=True)
    
    auth3_approved = models.BooleanField(default=False)
    auth3_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='auth3_approvals')
    auth3_approved_date = models.DateTimeField(null=True, blank=True)
    
    created_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"Approval for {self.invited_user.username}"
    
    @property
    def auth_complete(self):
        """Returns True if all three levels of approval are complete"""
        return self.auth1_approved and self.auth2_approved and self.auth3_approved
    
    @property
    def approval_level(self):
        """Returns current approval level (0-3)"""
        if self.auth3_approved:
            return 3
        elif self.auth2_approved:
            return 2
        elif self.auth1_approved:
            return 1
        return 0
