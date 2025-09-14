from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
import string


class EmailOTP(models.Model):
    """Model to store OTP codes for email verification"""
    
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    # Store registration data temporarily
    username = models.CharField(max_length=150)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    password_hash = models.CharField(max_length=128)
    invite_code = models.CharField(max_length=32)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.email} - {self.otp_code}"
    
    @classmethod
    def generate_otp(cls):
        """Generate a 6-digit OTP code"""
        return ''.join(random.choices(string.digits, k=6))
    
    def is_expired(self):
        """Check if OTP is expired (10 minutes)"""
        expiry_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiry_time
    
    def is_valid(self):
        """Check if OTP is valid (not expired, not verified, under attempt limit)"""
        return (
            not self.is_expired() and 
            not self.is_verified and 
            self.attempts < self.max_attempts
        )
    
    def verify_otp(self, entered_otp):
        """Verify the entered OTP code"""
        self.attempts += 1
        self.save()
        
        if self.otp_code == entered_otp and self.is_valid():
            self.is_verified = True
            self.save()
            return True
        return False
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired OTP records"""
        expiry_time = timezone.now() - timedelta(minutes=10)
        cls.objects.filter(created_at__lt=expiry_time).delete()


class PasswordResetToken(models.Model):
    """Model to store password reset tokens"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Password reset for {self.user.email} - {self.token[:8]}..."
    
    @classmethod
    def generate_token(cls):
        """Generate a secure random token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def is_expired(self):
        """Check if token is expired (24 hours)"""
        expiry_time = self.created_at + timedelta(hours=24)
        return timezone.now() > expiry_time
    
    def is_valid(self):
        """Check if token is valid (not expired, not used)"""
        return not self.is_expired() and not self.is_used
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired tokens"""
        expiry_time = timezone.now() - timedelta(hours=24)
        cls.objects.filter(created_at__lt=expiry_time).delete()


# The accounts app uses Django's built-in User model
# Extended functionality is provided through UserProfile in the profiles app
# and ReferralApproval/InviteLink in the invites app
