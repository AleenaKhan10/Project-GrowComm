from django.contrib import admin
from .models import InviteLink, ReferralApproval


@admin.register(InviteLink)
class InviteLinkAdmin(admin.ModelAdmin):
    list_display = ('code', 'created_by', 'is_used', 'used_by', 'created_date', 'expiry_date')
    list_filter = ('is_used', 'created_date')
    search_fields = ('code', 'created_by__username', 'used_by__username')
    readonly_fields = ('code', 'created_date')


@admin.register(ReferralApproval)
class ReferralApprovalAdmin(admin.ModelAdmin):
    list_display = ('invited_user', 'inviter', 'approval_level', 'auth_complete', 'created_date')
    list_filter = ('auth1_approved', 'auth2_approved', 'auth3_approved', 'created_date')
    search_fields = ('invited_user__username', 'inviter__username')
    readonly_fields = ('created_date',)
    
    fieldsets = (
        ('Users', {
            'fields': ('invited_user', 'inviter')
        }),
        ('Level 1 Approval', {
            'fields': ('auth1_approved', 'auth1_approver', 'auth1_approved_date')
        }),
        ('Level 2 Approval', {
            'fields': ('auth2_approved', 'auth2_approver', 'auth2_approved_date')
        }),
        ('Level 3 Approval', {
            'fields': ('auth3_approved', 'auth3_approver', 'auth3_approved_date')
        }),
        ('Timestamps', {
            'fields': ('created_date',)
        })
    )
