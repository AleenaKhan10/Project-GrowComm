from django.contrib import admin
from .models import Community, CommunityMembership


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count', 'is_active', 'created_date')
    list_filter = ('is_active', 'is_private', 'created_date')
    search_fields = ('name', 'description')
    readonly_fields = ('created_date',)


@admin.register(CommunityMembership)
class CommunityMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'role', 'is_active', 'joined_date')
    list_filter = ('role', 'is_active', 'joined_date')
    search_fields = ('user__username', 'community__name')
