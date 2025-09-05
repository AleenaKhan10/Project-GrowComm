from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Community(models.Model):
    """Model for communities within the platform"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    created_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_communities')
    
    # Community settings
    is_active = models.BooleanField(default=True)
    is_private = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Communities"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        """Return the number of active members in this community"""
        return self.memberships.filter(is_active=True).count()
    
    @property
    def active_members(self):
        """Return queryset of active community members"""
        return User.objects.filter(
            community_memberships__community=self,
            community_memberships__is_active=True
        )


class CommunityMembership(models.Model):
    """Model for tracking community membership"""
    
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
        ('owner', 'Owner'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_memberships')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_date = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'community']
        ordering = ['-joined_date']
    
    def __str__(self):
        return f"{self.user.username} in {self.community.name} ({self.role})"
    
    @property
    def can_moderate(self):
        """Check if user can moderate the community"""
        return self.role in ['moderator', 'admin', 'owner']
    
    @property
    def can_admin(self):
        """Check if user can admin the community"""
        return self.role in ['admin', 'owner']
