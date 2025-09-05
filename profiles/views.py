from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q
from .models import UserProfile, Referral
from .forms import UserProfileForm, SendReferralForm
from .decorators import verified_user_required


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


@login_required
def referrals_view(request):
    """View referrals page - shows both send and received referrals"""
    profile = request.user.profile
    
    # Get received referrals
    received_referrals = Referral.objects.filter(
        recipient_user=request.user
    ).select_related('sender').order_by('-created_at')
    
    # Get sent referrals
    sent_referrals = Referral.objects.filter(
        sender=request.user
    ).select_related('recipient_user').order_by('-created_at')
    
    context = {
        'profile': profile,
        'received_referrals': received_referrals,
        'sent_referrals': sent_referrals,
        'verification_status': {
            'is_verified': profile.is_verified,
            'referral_count': profile.referral_count,
            'referrals_needed': profile.referrals_needed,
            'needs_referrals': profile.needs_referrals,
        }
    }
    return render(request, 'profiles/referrals.html', context)


@login_required
@verified_user_required
def send_referral(request):
    """Send a referral to someone via email"""
    if request.method == 'POST':
        form = SendReferralForm(user=request.user, data=request.POST)
        if form.is_valid():
            referral = form.save()
            messages.success(
                request, 
                f'Referral sent successfully to {referral.recipient_email}!'
            )
            return redirect('profiles:referrals')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SendReferralForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'profiles/send_referral.html', context)


@login_required
def referral_stats(request):
    """AJAX endpoint for referral statistics"""
    profile = request.user.profile
    
    stats = {
        'is_verified': profile.is_verified,
        'referral_count': profile.referral_count,
        'referrals_needed': profile.referrals_needed,
        'needs_referrals': profile.needs_referrals,
    }
    
    from django.http import JsonResponse
    return JsonResponse(stats)


@login_required
def delete_profile(request):
    """Delete user profile with confirmation"""
    if request.method == 'POST':
        if request.POST.get('confirm_deletion') == 'yes':
            user = request.user
            username = user.username
            
            # Delete the user (this will cascade to profile and related objects)
            user.delete()
            
            # Log the user out
            logout(request)
            
            messages.success(request, f'Your profile has been permanently deleted. Thank you for being part of GrowComm, {username}.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Profile deletion was not confirmed.')
            return redirect('profiles:edit')
    
    # GET request - show confirmation page
    context = {
        'user': request.user,
    }
    return render(request, 'profiles/delete_profile.html', context)
