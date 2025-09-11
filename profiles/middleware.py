from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse


class UserStatusMiddleware:
    """
    Middleware to check if user is suspended or deleted and handle accordingly.
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
                    
                    # Check if user is suspended
                    if profile.is_suspended:
                        # Allow viewing of suspension notice page
                        if request.path != reverse('profiles:account_suspended') and not request.path.startswith('/accounts/logout/'):
                            logout(request)
                            messages.error(request, 'Your account has been suspended. Please contact support for more information.')
                            return redirect('profiles:account_suspended')
                    
                    # Check if user is deleted
                    if profile.is_deleted:
                        # Force logout deleted users
                        if request.path != reverse('profiles:account_deleted') and not request.path.startswith('/accounts/logout/'):
                            logout(request)
                            messages.error(request, 'Your account has been deleted.')
                            return redirect('profiles:account_deleted')
                            
                except AttributeError:
                    # Profile doesn't exist, continue normally
                    pass
        
        response = self.get_response(request)
        return response