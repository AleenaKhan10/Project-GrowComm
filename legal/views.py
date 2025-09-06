from django.shortcuts import render
from datetime import date


def terms_of_service(request):
    """Display Terms of Service page"""
    context = {
        'today': date.today()
    }
    return render(request, 'legal/terms_of_service.html', context)


def privacy_policy(request):
    """Display Privacy Policy page"""
    context = {
        'today': date.today()
    }
    return render(request, 'legal/privacy_policy.html', context)