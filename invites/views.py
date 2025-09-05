from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import InviteLink, ReferralApproval
from .forms import CreateInviteForm


@login_required
def my_invites(request):
    """Display user's sent invites and create new ones"""
    user_invites = InviteLink.objects.filter(created_by=request.user)
    
    if request.method == 'POST':
        form = CreateInviteForm(request.POST)
        if form.is_valid():
            invite = form.save(user=request.user)
            # Build the full invite URL
            invite_url = request.build_absolute_uri(
                reverse('accounts:register', kwargs={'invite_code': invite.code})
            )
            messages.success(
                request, 
                f'Invite link created successfully! Share this link: {invite_url}'
            )
            return redirect('invites:my_invites')
    else:
        form = CreateInviteForm()
    
    context = {
        'form': form,
        'invites': user_invites,
    }
    return render(request, 'invites/my_invites.html', context)


@login_required
def invite_detail(request, invite_id):
    """View details of a specific invite"""
    invite = get_object_or_404(InviteLink, id=invite_id, created_by=request.user)
    
    # Build the full invite URL
    invite_url = request.build_absolute_uri(
        reverse('accounts:register', kwargs={'invite_code': invite.code})
    )
    
    context = {
        'invite': invite,
        'invite_url': invite_url,
    }
    return render(request, 'invites/invite_detail.html', context)


@login_required
def referral_status(request):
    """View referral approval status for users invited by current user"""
    referrals = ReferralApproval.objects.filter(inviter=request.user).order_by('-created_date')
    
    context = {
        'referrals': referrals,
    }
    return render(request, 'invites/referral_status.html', context)
