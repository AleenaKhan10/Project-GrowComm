"""
Utility functions for audit tracking.

This module provides easy-to-use functions for logging audit events
throughout the application.
"""

from .models import AuditEvent


def log_user_action(user, action, detail=""):
    """
    Log a user action to the audit trail.
    
    Args:
        user: User instance who performed the action
        action: Action type (must match AuditEvent.ACTION_CHOICES)
        detail: Optional detail about the action
    
    Returns:
        AuditEvent instance if successful, None if failed
    """
    try:
        return AuditEvent.log_action(user, action, detail)
    except Exception as e:
        print(f"Failed to log audit action: {e}")
        return None


def log_signin(user, detail=""):
    """Log user sign in action."""
    return log_user_action(user, 'user_signin', detail)


def log_signout(user, detail=""):
    """Log user sign out action."""
    return log_user_action(user, 'user_signout', detail)


def log_registration(user, detail=""):
    """Log user registration action."""
    return log_user_action(user, 'user_registered', detail)


def log_invite_created(user, detail=""):
    """Log invite creation action."""
    return log_user_action(user, 'invite_created', detail)


def log_referral_sent(user, detail=""):
    """Log referral sent action."""
    return log_user_action(user, 'referral_sent', detail)


def log_slot_booked(user, detail=""):
    """Log message slot booking action."""
    return log_user_action(user, 'slot_booked', detail)


def log_message_answered(user, detail=""):
    """Log message answered for first time action."""
    return log_user_action(user, 'message_answered', detail)


def log_user_deleted(user, detail=""):
    """Log user deletion action."""
    return log_user_action(user, 'user_deleted', detail)


def log_profile_edited(user, detail=""):
    """Log profile edit action."""
    return log_user_action(user, 'profile_edited', detail)


# Action type constants for easy reference
ACTIONS = {
    'SIGNIN': 'user_signin',
    'SIGNOUT': 'user_signout',
    'REGISTRATION': 'user_registered',
    'INVITE_CREATED': 'invite_created',
    'REFERRAL_SENT': 'referral_sent',
    'SLOT_BOOKED': 'slot_booked',
    'MESSAGE_ANSWERED': 'message_answered',
    'USER_DELETED': 'user_deleted',
    'PROFILE_EDITED': 'profile_edited',
}