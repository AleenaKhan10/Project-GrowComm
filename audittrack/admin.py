from django.contrib import admin
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'action_detail', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'action_detail']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
