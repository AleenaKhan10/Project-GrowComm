from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'company', 'organization_level', 'created_date')
    list_filter = ('organization_level', 'name_visibility', 'created_date')
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
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        })
    )
