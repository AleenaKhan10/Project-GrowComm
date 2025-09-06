from django.conf import settings
from django.urls import reverse


def build_invite_url(request, invite_code):
    """
    Build the complete invite URL based on configuration.
    
    Uses SITE_URL from settings if defined, otherwise builds from request.
    This allows for easy configuration between HTTP/HTTPS and different domains.
    
    Args:
        request: Django request object
        invite_code: The invite code UUID
    
    Returns:
        Complete URL string for the invite
    """
    invite_path = reverse('accounts:register', kwargs={'invite_code': invite_code})
    
    # If SITE_URL is defined in settings, use it
    if hasattr(settings, 'SITE_URL') and settings.SITE_URL:
        # Remove trailing slash if present
        base_url = settings.SITE_URL.rstrip('/')
        return f"{base_url}{invite_path}"
    
    # Otherwise, build from request (backwards compatible)
    # This will use the protocol and domain from the current request
    return request.build_absolute_uri(invite_path)