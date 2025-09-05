from django.contrib import admin
from .models import UserProfile, Referral


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'company', 'organization_level', 'is_verified', 'referral_count', 'created_date')
    list_filter = ('organization_level', 'name_visibility', 'is_verified', 'needs_referrals', 'created_date')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'company', 'tags')
    readonly_fields = ('created_date', 'updated_date')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Profile Information', {
            'fields': ('profile_picture', 'bio', 'tags')
        }),
        ('Professional', {
            'fields': ('company', 'team', 'organization_level', 'schools')
        }),
        ('Privacy', {
            'fields': ('name_visibility',)
        }),
        ('Contact', {
            'fields': ('phone_number',)
        }),
        ('Message Slots', {
            'fields': ('coffee_chat_slots', 'mentorship_slots', 'networking_slots', 'general_slots')
        }),
        ('Verification', {
            'fields': ('is_verified', 'needs_referrals', 'invite_source')
        }),
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        })
    )


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient_email', 'recipient_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('sender__username', 'sender__email', 'recipient_email', 'recipient_user__username')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Referral Details', {
            'fields': ('sender', 'recipient_email', 'recipient_user', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'recipient_user')
