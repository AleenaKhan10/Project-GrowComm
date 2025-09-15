from django.contrib import admin
from django.utils.html import format_html
from .models import (MessageType, Conversation, Message, MessageRequest, UserMessageSettings, 
                    MessageReport, UserBlock, ChatBlock, UserCredit, CreditTransaction)


@admin.register(MessageType)
class MessageTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'color_code')
    list_filter = ('is_active',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'created_date', 'last_message_date', 'is_active')
    list_filter = ('is_active', 'created_date')
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'timestamp', 'is_read')
    list_filter = ('message_type', 'is_read', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')
    readonly_fields = ('timestamp', 'read_date')


@admin.register(MessageRequest)
class MessageRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'message_type', 'status', 'created_date')
    list_filter = ('status', 'message_type', 'created_date')
    search_fields = ('from_user__username', 'to_user__username')


@admin.register(UserMessageSettings)
class UserMessageSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'coffee_chat_enabled', 'mentorship_enabled', 'networking_enabled', 'general_enabled')
    list_filter = ('coffee_chat_enabled', 'mentorship_enabled', 'networking_enabled', 'general_enabled')
    search_fields = ('user__username',)


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'report_type', 'created_date')
    list_filter = ('report_type', 'created_date')
    search_fields = ('reporter__username', 'reported_user__username', 'note')
    readonly_fields = ('created_date',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reporter', 'reported_user')


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_date')
    list_filter = ('created_date',)
    search_fields = ('blocker__username', 'blocked__username')
    readonly_fields = ('created_date',)


@admin.register(ChatBlock)
class ChatBlockAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'blocked_user', 'report_type', 'is_active', 'reviewed_by_admin', 'created_date')
    list_filter = ('is_active', 'reviewed_by_admin', 'created_date', 'report__report_type')
    search_fields = ('reporter__username', 'blocked_user__username', 'report__note', 'admin_notes')
    readonly_fields = ('created_date', 'updated_date')
    
    def report_type(self, obj):
        return obj.report.get_report_type_display()
    report_type.short_description = 'Report Type'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reporter', 'blocked_user', 'report')


@admin.register(UserCredit)
class UserCreditAdmin(admin.ModelAdmin):
    list_display = ('user', 'available_credits_display', 'total_credits', 'base_credits', 'bonus_credits', 'credits_used_this_week', 'last_reset_date')
    list_filter = ('last_reset_date', 'total_credits', 'bonus_credits')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_date', 'updated_date')
    actions = ['grant_bonus_credits', 'reset_weekly_credits']
    
    def available_credits_display(self, obj):
        available = obj.available_credits
        color = 'green' if available > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, available
        )
    available_credits_display.short_description = 'Available Credits'
    
    def grant_bonus_credits(self, request, queryset):
        """Admin action to grant bonus credits"""
        from django import forms
        from django.shortcuts import render, redirect
        from django.contrib import messages
        
        class CreditGrantForm(forms.Form):
            amount = forms.IntegerField(min_value=1, help_text="Number of bonus credits to grant")
            description = forms.CharField(widget=forms.Textarea, required=False, help_text="Reason for granting credits")
        
        if 'apply' in request.POST:
            form = CreditGrantForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description'] or f"Admin granted {amount} bonus credits"
                
                for credit_record in queryset:
                    balance_before = credit_record.available_credits
                    credit_record.add_credits(amount, is_bonus=True)
                    balance_after = credit_record.available_credits
                    
                    # Log transaction
                    CreditTransaction.log_transaction(
                        user=credit_record.user,
                        transaction_type='admin_grant',
                        amount=amount,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        description=description,
                        created_by=request.user
                    )
                
                messages.success(request, f'Successfully granted {amount} bonus credits to {queryset.count()} users.')
                return redirect(request.get_full_path())
        else:
            form = CreditGrantForm()
            
        return render(request, 'admin/grant_credits.html', {
            'form': form,
            'users': queryset,
            'action': 'grant_bonus_credits'
        })
    
    grant_bonus_credits.short_description = "Grant bonus credits to selected users"
    
    def reset_weekly_credits(self, request, queryset):
        """Admin action to manually reset weekly credits"""
        count = 0
        for credit_record in queryset:
            old_total = credit_record.total_credits
            new_total = credit_record.reset_weekly_credits()
            
            # Log transaction
            CreditTransaction.log_transaction(
                user=credit_record.user,
                transaction_type='weekly_reset',
                amount=new_total - old_total,
                balance_before=old_total,
                balance_after=new_total,
                description="Manual weekly credit reset",
                created_by=request.user
            )
            count += 1
            
        self.message_user(request, f'Successfully reset weekly credits for {count} users.')
    
    reset_weekly_credits.short_description = "Reset weekly credits for selected users"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount_display', 'balance_before', 'balance_after', 'created_date', 'created_by')
    list_filter = ('transaction_type', 'created_date')
    search_fields = ('user__username', 'description')
    readonly_fields = ('created_date',)
    date_hierarchy = 'created_date'
    
    def amount_display(self, obj):
        color = 'green' if obj.amount > 0 else 'red'
        symbol = '+' if obj.amount > 0 else ''
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color, symbol, obj.amount
        )
    amount_display.short_description = 'Amount'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'created_by', 'message_slot_booking')
