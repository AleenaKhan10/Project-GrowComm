from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from PIL import Image


class UserProfile(models.Model):
    """Extended user profile with professional and community information"""
    
    ORGANIZATION_LEVELS = [
        ('junior', 'Junior Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior Level'),
        ('lead', 'Lead/Manager'),
        ('executive', 'Executive'),
        ('founder', 'Founder/CEO'),
        ('student', 'Student'),
        ('other', 'Other'),
    ]
    
    NAME_VISIBILITY_CHOICES = [
        ('full', 'Full Name'),
        ('first_only', 'First Name Only'),
        ('initials', 'Initials Only'),
        ('anonymous', 'Anonymous'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Profile picture
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True,
        help_text="Upload a profile picture (max 5MB)"
    )
    
    # Professional information
    bio = models.TextField(
        max_length=500, 
        blank=True,
        help_text="Tell us about yourself (max 500 characters)"
    )
    location = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Your city, state/country (e.g., New York, NY)"
    )
    company = models.CharField(max_length=100, blank=True)
    team = models.CharField(max_length=100, blank=True)
    organization_level = models.CharField(
        max_length=20, 
        choices=ORGANIZATION_LEVELS,
        blank=True
    )
    
    # Education
    schools = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Schools, universities, or educational institutions"
    )
    
    # Skills and interests
    tags = models.TextField(
        blank=True,
        help_text="Tags representing your skills, interests, or expertise (comma-separated)"
    )
    
    # Privacy settings
    name_visibility = models.CharField(
        max_length=20,
        choices=NAME_VISIBILITY_CHOICES,
        default='full'
    )
    
    # Phone number for authentication
    phone_number = models.CharField(
        max_length=15, 
        blank=True,
        help_text="Phone number for authentication"
    )
    
    # Timestamps
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    # Message type slots for different conversation types
    coffee_chat_slots = models.PositiveIntegerField(default=5)
    mentorship_slots = models.PositiveIntegerField(default=3)
    networking_slots = models.PositiveIntegerField(default=10)
    general_slots = models.PositiveIntegerField(default=15)
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Resize profile picture if it exists
        if self.profile_picture:
            img = Image.open(self.profile_picture.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.profile_picture.path)
    
    @property
    def display_name(self):
        """Return name based on visibility preference"""
        if self.name_visibility == 'full':
            return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        elif self.name_visibility == 'first_only':
            return self.user.first_name or self.user.username
        elif self.name_visibility == 'initials':
            first_initial = self.user.first_name[0] if self.user.first_name else ''
            last_initial = self.user.last_name[0] if self.user.last_name else ''
            return f"{first_initial}{last_initial}".strip() or self.user.username[0]
        else:  # anonymous
            return "Anonymous User"
    
    @property
    def tag_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    @property
    def available_slots(self):
        """Return available message slots for each type"""
        from messaging.models import Message
        
        # Count used slots (messages sent in the last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        used_coffee_slots = Message.objects.filter(
            sender=self.user,
            message_type__name='Coffee Chat',
            created_date__gte=thirty_days_ago
        ).count()
        
        used_mentorship_slots = Message.objects.filter(
            sender=self.user,
            message_type__name='Mentorship',
            created_date__gte=thirty_days_ago
        ).count()
        
        used_networking_slots = Message.objects.filter(
            sender=self.user,
            message_type__name='Networking',
            created_date__gte=thirty_days_ago
        ).count()
        
        used_general_slots = Message.objects.filter(
            sender=self.user,
            message_type__name='General',
            created_date__gte=thirty_days_ago
        ).count()
        
        return {
            'coffee_chat': max(0, self.coffee_chat_slots - used_coffee_slots),
            'mentorship': max(0, self.mentorship_slots - used_mentorship_slots),
            'networking': max(0, self.networking_slots - used_networking_slots),
            'general': max(0, self.general_slots - used_general_slots),
        }


# Signal to create profile when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
