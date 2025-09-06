from django import template
from django.conf import settings
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def get_invite_url(context, invite_code):
    """
    Template tag to generate invite URLs based on configuration.
    
    Usage in template:
        {% load invite_tags %}
        {% get_invite_url invite.code %}
    """
    request = context['request']
    invite_path = reverse('accounts:register', kwargs={'invite_code': invite_code})
    
    # If SITE_URL is defined in settings, use it
    if hasattr(settings, 'SITE_URL') and settings.SITE_URL:
        # Remove trailing slash if present
        base_url = settings.SITE_URL.rstrip('/')
        return f"{base_url}{invite_path}"
    
    # Otherwise, build from request (backwards compatible)
    return request.build_absolute_uri(invite_path)