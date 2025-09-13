from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Community, CommunityMembership


def community_member_required(view_func):
    """
    Decorator that checks if user is a member of the community specified in URL parameter.
    Redirects to community list with error message if not a member.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, community_id, *args, **kwargs):
        # Get the community
        community = get_object_or_404(Community, id=community_id)
        
        # Check if user is a member or superuser
        if request.user.is_superuser:
            # Superusers have access to all communities
            return view_func(request, community_id=community_id, community=community, *args, **kwargs)
        
        # Check membership
        try:
            membership = CommunityMembership.objects.get(
                user=request.user, 
                community=community, 
                is_active=True
            )
            # User is a member, proceed
            return view_func(request, community_id=community_id, community=community, membership=membership, *args, **kwargs)
        except CommunityMembership.DoesNotExist:
            # User is not a member
            messages.error(request, f'You are not a member of {community.name}. Please join the community to access this feature.')
            return redirect('communities:community_list')
    
    return wrapper


def community_exists_required(view_func):
    """
    Decorator that just checks if community exists (for public views).
    """
    @wraps(view_func)
    def wrapper(request, community_id, *args, **kwargs):
        # Get the community
        community = get_object_or_404(Community, id=community_id)
        return view_func(request, community_id=community_id, community=community, *args, **kwargs)
    
    return wrapper