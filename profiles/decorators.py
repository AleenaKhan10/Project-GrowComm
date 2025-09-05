from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def verified_user_required(view_func=None, *, message="You need 3 referrals to unlock this feature"):
    """
    Decorator that requires user to be verified (has 3 referrals or invited by superadmin).
    """
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Superadmins bypass all verification requirements
            if request.user.is_superuser:
                return func(request, *args, **kwargs)
            
            if not hasattr(request.user, 'profile'):
                messages.error(request, "Profile not found.")
                return redirect('accounts:login')
            
            profile = request.user.profile
            if not profile.is_verified:
                referrals_needed = profile.referrals_needed
                if referrals_needed > 0:
                    messages.warning(
                        request, 
                        f"{message} You have {profile.referral_count}/3 referrals. "
                        f"{referrals_needed} more needed."
                    )
                else:
                    messages.warning(request, message)
                return redirect('profiles:referrals')  # Redirect to referrals page
            
            return func(request, *args, **kwargs)
        return wrapper
    
    if view_func is None:
        return decorator
    else:
        return decorator(view_func)


def can_send_referrals(user):
    """
    Check if user can send referrals (must be verified or be superadmin)
    """
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    return user.profile.is_verified


def get_verification_status(user):
    """
    Get user's verification status with details
    """
    # Superadmins are always considered verified
    if user.is_superuser:
        return {
            'is_verified': True,
            'needs_referrals': False,
            'referral_count': 0,
            'referrals_needed': 0,
            'status_message': 'Superadmin - full access'
        }
    
    if not hasattr(user, 'profile'):
        return {
            'is_verified': False,
            'needs_referrals': True,
            'referral_count': 0,
            'referrals_needed': 3,
            'status_message': 'Profile not found'
        }
    
    profile = user.profile
    return {
        'is_verified': profile.is_verified,
        'needs_referrals': profile.needs_referrals,
        'referral_count': profile.referral_count,
        'referrals_needed': profile.referrals_needed,
        'status_message': get_status_message(profile, user.is_superuser)
    }


def get_status_message(profile, is_superuser=False):
    """
    Get appropriate status message for user's verification state
    """
    if is_superuser:
        return "Superadmin - full access"
    elif profile.is_verified:
        return "Account fully verified"
    elif not profile.needs_referrals:
        return "Verification not required"
    else:
        referrals_needed = profile.referrals_needed
        if referrals_needed == 0:
            return "Verification pending - processing referrals"
        elif referrals_needed == 3:
            return "No referrals received yet - 3 needed"
        else:
            return f"{profile.referral_count}/3 referrals received - {referrals_needed} more needed"