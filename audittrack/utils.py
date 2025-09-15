"""
Utility functions for audit tracking.

This module provides easy-to-use functions for logging audit events
throughout the application.
"""

from .models import AuditEvent


def log_user_action(user, action, detail="", target_user=None):
    """
    Log a user action to the audit trail.
    
    Args:
        user: User instance who performed the action
        action: Action type (must match AuditEvent.ACTION_CHOICES)
        detail: Optional detail about the action
        target_user: Optional user instance who was the target of the action
    
    Returns:
        AuditEvent instance if successful, None if failed
    """
    try:
        return AuditEvent.log_action(user, action, detail, target_user)
    except Exception as e:
        print(f"Failed to log audit action: {e}")
        return None


def log_signin(user, detail="", target_user=None):
    """Log user sign in action."""
    return log_user_action(user, 'user_signin', detail, target_user)


def log_signout(user, detail="", target_user=None):
    """Log user sign out action."""
    return log_user_action(user, 'user_signout', detail, target_user)


def log_registration(user, detail="", target_user=None):
    """Log user registration action."""
    return log_user_action(user, 'user_registered', detail, target_user)


def log_invite_created(user, detail="", target_user=None):
    """Log invite creation action."""
    return log_user_action(user, 'invite_created', detail, target_user)


def log_referral_sent(user, detail="", target_user=None):
    """Log referral sent action."""
    return log_user_action(user, 'referral_sent', detail, target_user)


def log_slot_booked(user, detail="", target_user=None):
    """Log message slot booking action."""
    return log_user_action(user, 'slot_booked', detail, target_user)


def log_message_answered(user, detail="", target_user=None):
    """Log message answered for first time action."""
    return log_user_action(user, 'message_answered', detail, target_user)


def log_user_deleted(user, detail="", target_user=None):
    """Log user deletion action."""
    return log_user_action(user, 'user_deleted', detail, target_user)


def log_profile_edited(user, detail="", target_user=None):
    """Log profile edit action."""
    return log_user_action(user, 'profile_edited', detail, target_user)


def log_user_reported(user, detail="", target_user=None):
    """Log user report action."""
    return log_user_action(user, 'user_reported', detail, target_user)


def log_user_unblocked(user, detail="", target_user=None):
    """Log user unblock action."""
    return log_user_action(user, 'user_unblocked', detail, target_user)


def log_page_focus_start(user, detail="", target_user=None):
    """Log page focus start action."""
    return log_user_action(user, 'page_focus_start', detail, target_user)


def log_page_focus_end(user, detail="", target_user=None):
    """Log page focus end action."""
    return log_user_action(user, 'page_focus_end', detail, target_user)


def log_credit_used(user, detail="", target_user=None):
    """Log credit usage action."""
    return log_user_action(user, 'credit_used', detail, target_user)


def log_credit_granted(user, detail="", target_user=None):
    """Log credit grant action."""
    return log_user_action(user, 'credit_granted', detail, target_user)


def log_weekly_credit_reset(user, detail="", target_user=None):
    """Log weekly credit reset action."""
    return log_user_action(user, 'weekly_credit_reset', detail, target_user)


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
    'USER_REPORTED': 'user_reported',
    'USER_UNBLOCKED': 'user_unblocked',
}