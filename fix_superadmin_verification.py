#!/usr/bin/env python3
"""
Script to fix verification status for superadmins and their invitees.
This ensures all superadmins bypass verification requirements.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'growcommunity.settings')
django.setup()

from django.contrib.auth.models import User
from profiles.models import UserProfile

def fix_superadmin_verification():
    """Fix verification status for all superadmins and their invitees."""
    
    print("🔧 Starting superadmin verification fix...")
    
    # Fix all superadmins
    superadmins = User.objects.filter(is_superuser=True)
    superadmin_count = 0
    
    for superadmin in superadmins:
        profile, created = UserProfile.objects.get_or_create(user=superadmin)
        
        # Ensure superadmin profiles are properly configured
        if not profile.is_verified or profile.needs_referrals:
            profile.is_verified = True
            profile.needs_referrals = False
            profile.save()
            superadmin_count += 1
            print(f"✅ Fixed superadmin: {superadmin.username}")
    
    # Fix users invited by superadmins
    invitee_count = 0
    profiles_with_superadmin_source = UserProfile.objects.filter(
        invite_source__is_superuser=True
    )
    
    for profile in profiles_with_superadmin_source:
        if not profile.is_verified or profile.needs_referrals:
            profile.is_verified = True
            profile.needs_referrals = False
            profile.save()
            invitee_count += 1
            print(f"✅ Fixed superadmin invitee: {profile.user.username}")
    
    print(f"\n🎉 Verification fix complete!")
    print(f"   📊 Superadmins fixed: {superadmin_count}")
    print(f"   📊 Superadmin invitees fixed: {invitee_count}")
    print(f"   📊 Total users fixed: {superadmin_count + invitee_count}")
    
    if superadmin_count == 0 and invitee_count == 0:
        print("   ✨ No fixes needed - all users already have correct verification status!")

if __name__ == "__main__":
    fix_superadmin_verification()