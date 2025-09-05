from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import UserProfile
from .forms import UserProfileForm


@login_required
def profile_view(request, user_id):
    """View a user's profile"""
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    
    # Check if current user can view this profile
    can_message = request.user != user and request.user.is_authenticated
    
    context = {
        'profile_user': user,
        'profile': profile,
        'can_message': can_message,
    }
    return render(request, 'profiles/profile_view.html', context)


@login_required
def profile_edit(request):
    """Edit current user's profile"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profiles:view', user_id=request.user.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'profiles/profile_edit.html', context)


@login_required
def user_search(request):
    """Search and filter users (AJAX endpoint)"""
    search_query = request.GET.get('search', '').strip()
    organization_level = request.GET.get('organization_level', '')
    tags_filter = request.GET.get('tags', '').strip()
    
    # Start with all users except current user
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(profile__company__icontains=search_query) |
            Q(profile__team__icontains=search_query) |
            Q(profile__bio__icontains=search_query) |
            Q(profile__tags__icontains=search_query) |
            Q(profile__schools__icontains=search_query)
        )
    
    # Apply organization level filter
    if organization_level:
        users = users.filter(profile__organization_level=organization_level)
    
    # Apply tags filter
    if tags_filter:
        # Split tags and filter for any matching tag
        tag_list = [tag.strip().lower() for tag in tags_filter.split(',') if tag.strip()]
        for tag in tag_list:
            users = users.filter(profile__tags__icontains=tag)
    
    # Limit results
    users = users[:50]
    
    context = {
        'users': users,
        'search_query': search_query,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'profiles/user_list_partial.html', context)
    
    return render(request, 'profiles/user_search.html', context)
