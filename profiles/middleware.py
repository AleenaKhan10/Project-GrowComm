from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone


class UserStatusMiddleware:
    """
    Middleware to check if user is deleted and handle accordingly.
    Suspended users can browse but not perform actions (like unverified users).
    Also updates last_seen timestamp for authenticated users.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Skip check for superusers
            if not request.user.is_superuser:
                try:
                    profile = request.user.profile
                    
                    # Check if user is deleted - force logout and redirect
                    if profile.is_deleted:
                        # Force logout deleted users
                        if request.path != reverse('profiles:account_deleted') and not request.path.startswith('/accounts/logout/'):
                            logout(request)
                            messages.error(request, 'Your account has been deleted.')
                            return redirect('profiles:account_deleted')
                    
                    # For suspended users: they stay logged in and can browse
                    # but actions will be blocked in views/templates (like unverified users)
                    
                    # Update last_seen timestamp for all authenticated users (except deleted)
                    if not profile.is_deleted:
                        profile.last_seen = timezone.now()
                        profile.save(update_fields=['last_seen'])
                            
                except AttributeError:
                    # Profile doesn't exist, continue normally
                    pass
            else:
                # Update last_seen for superusers too
                try:
                    profile = request.user.profile
                    profile.last_seen = timezone.now()
                    profile.save(update_fields=['last_seen'])
                except AttributeError:
                    pass
        
        response = self.get_response(request)
        return response