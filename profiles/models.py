from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from PIL import Image


class UserProfile(models.Model):
    """Extended user profile with professional and community information"""
    
    ORGANIZATION_LEVELS = [
        ('student', 'Student'),
        ('junior', 'Junior Level'),
        ('senior', 'Senior Level'),
        ('lead', 'Lead Level'),
        ('director', 'Director Level'),
        ('executive', 'Executive Level'),
        ('founder', 'Startup Founder'),
        ('owner', 'Business Owner'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
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
    
    # Personal information
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        default='prefer_not_to_say'
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="Your city (e.g., New York)"
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Your country (e.g., United States)"
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
    
    # Education - Now supports multiple schools
    schools = models.TextField(
        blank=True,
        help_text="Schools, universities, or educational institutions (one per line or comma-separated)"
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
    
    # Legacy fields - kept for backward compatibility
    # Message slot limits are now handled through CustomMessageSlot and UserMessageSettings
    coffee_chat_slots = models.PositiveIntegerField(default=5)
    mentorship_slots = models.PositiveIntegerField(default=3)
    networking_slots = models.PositiveIntegerField(default=10)
    general_slots = models.PositiveIntegerField(default=15)
    
    # Verification and referral system
    is_verified = models.BooleanField(default=False, help_text="User can perform actions if verified")
    invite_source = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='invited_users',
        help_text="User who sent the original invite"
    )
    needs_referrals = models.BooleanField(default=True, help_text="True if user needs 3 referrals to be verified")
    
    # Anonymous messaging system
    anonymous_name = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Anonymous name displayed to other users in community"
    )
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def save(self, *args, **kwargs):
        # Generate anonymous name if not set
        if not self.anonymous_name:
            self.anonymous_name = self._generate_anonymous_name()
        
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
    def real_name(self):
        """Return the real full name of the user"""
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return full_name or self.user.username
    
    @property
    def anonymous_display_name(self):
        """Return anonymous name for community display"""
        return self.anonymous_name or "Anonymous User"
    
    def _generate_anonymous_name(self):
        """Generate a unique anonymous name"""
        import random
        
        # List of anonymous name patterns
        adjectives = [
            'Curious', 'Bright', 'Creative', 'Thoughtful', 'Ambitious', 'Dynamic', 
            'Innovative', 'Strategic', 'Visionary', 'Talented', 'Focused', 'Driven',
            'Inspiring', 'Bold', 'Smart', 'Clever', 'Wise', 'Sharp', 'Quick', 'Keen'
        ]
        
        nouns = [
            'Explorer', 'Builder', 'Innovator', 'Creator', 'Thinker', 'Leader',
            'Analyst', 'Designer', 'Developer', 'Strategist', 'Visionary', 'Pioneer',
            'Entrepreneur', 'Professional', 'Expert', 'Specialist', 'Consultant', 
            'Manager', 'Director', 'Founder'
        ]
        
        # Generate a random combination
        adjective = random.choice(adjectives)
        noun = random.choice(nouns)
        number = random.randint(100, 999)
        
        return f"{adjective} {noun} #{number}"
    
    @property
    def tag_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    @property
    def school_list(self):
        """Return schools as a list"""
        if self.schools:
            # Support both comma and newline separated
            schools_text = self.schools.replace('\n', ',')
            return [school.strip() for school in schools_text.split(',') if school.strip()]
        return []
    
    @property
    def current_slot_configuration(self):
        """Return the current slot configuration based on user's settings"""
        from messaging.models import CustomMessageSlot, UserMessageSettings
        
        # Get user's message settings
        try:
            settings = UserMessageSettings.objects.get(user=self.user)
            use_custom = settings.use_custom_slots
        except UserMessageSettings.DoesNotExist:
            use_custom = False
        
        if use_custom:
            # Return custom slots
            custom_slots = CustomMessageSlot.objects.filter(
                user=self.user, 
                is_active=True
            ).order_by('name')
            
            return {
                'type': 'custom',
                'slots': [
                    {
                        'name': slot.name,
                        'limit': slot.slot_limit,
                        'key': slot.name.lower().replace(' ', '_')
                    }
                    for slot in custom_slots
                ]
            }
        else:
            # Return default slots
            return {
                'type': 'default',
                'slots': [
                    {'name': 'Coffee Chat', 'limit': self.coffee_chat_slots, 'key': 'coffee_chat'},
                    {'name': 'Mentorship', 'limit': self.mentorship_slots, 'key': 'mentorship'},
                    {'name': 'Networking', 'limit': self.networking_slots, 'key': 'networking'},
                    {'name': 'General', 'limit': self.general_slots, 'key': 'general'},
                ]
            }
    
    @property
    def available_slots(self):
        """Return available message slots for each type"""
        from messaging.models import Message
        
        # Count used slots (messages sent in the last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        config = self.current_slot_configuration
        available = {}
        
        for slot in config['slots']:
            # Count used slots for this category
            used_count = Message.objects.filter(
                sender=self.user,
                message_type__name=slot['name'],
                timestamp__gte=thirty_days_ago
            ).count()
            
            available[slot['key']] = {
                'name': slot['name'],
                'total': slot['limit'],
                'used': used_count,
                'available': max(0, slot['limit'] - used_count)
            }
        
        return available
    
    @property
    def referral_count(self):
        """Return the number of approved referrals received"""
        return Referral.objects.filter(
            recipient_user=self.user,
            status='accepted'
        ).count()
    
    @property
    def referrals_needed(self):
        """Return how many more referrals are needed for verification"""
        if not self.needs_referrals or self.is_verified:
            return 0
        return max(0, 3 - self.referral_count)


class Referral(models.Model):
    """Referral system for user verification"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
    ]
    
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_referrals',
        help_text="User who sends the referral"
    )
    recipient_email = models.EmailField(help_text="Email address of the referral recipient")
    recipient_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='received_referrals',
        help_text="User once they register (populated automatically)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    class Meta:
        unique_together = ['sender', 'recipient_email']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Referral from {self.sender.username} to {self.recipient_email}"
    
    def accept_referral(self):
        """Mark referral as accepted and check if user should be verified"""
        if self.status != 'accepted' and self.recipient_user:
            self.status = 'accepted'
            self.save()
            
            # Auto-verify if referral is from super admin
            if self.sender.is_superuser:
                profile = self.recipient_user.profile
                profile.is_verified = True
                profile.needs_referrals = False
                profile.save()
                
                # Send verification complete email
                self._send_verification_complete_email()
            else:
                # Check if user now has enough referrals
                profile = self.recipient_user.profile
                if profile.needs_referrals and profile.referral_count >= 3:
                    profile.is_verified = True
                    profile.save()
                    
                    # Send verification complete email
                    self._send_verification_complete_email()
    
    def _send_verification_complete_email(self):
        """Send email notification when user becomes verified"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        try:
            user = self.recipient_user
            subject = "🎉 Your GrwCommunity account is now verified!"
            
            message_lines = [
                f"Congratulations {user.first_name or user.username}!",
                f"",
                f"You've received 3 referrals from community members and your GrwCommunity account is now fully verified!",
                f"",
                f"You can now:",
                f"• Send messages to other community members",
                f"• Create invite links to bring new people to the community",
                f"• Send referrals to help others get verified",
                f"• Access all community features",
                f"",
                f"Welcome to the verified GrwCommunity family!",
                f"",
                f"Best regards,",
                f"The GrwCommunity Team"
            ]
            
            message = '\n'.join(message_lines)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@growcommunity.com'),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send verification complete email: {e}")


# Signal to create profile when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
