from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Max, Count, Case, When, IntegerField
from datetime import timedelta


class MessageType(models.Model):
    """Model for different types of messages (Coffee Chat, Mentorship, etc.)"""
    
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    color_code = models.CharField(max_length=7, default="#00ffff", help_text="Hex color code")
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Conversation(models.Model):
    """Model for tracking conversations between users - kept for backward compatibility"""
    
    participants = models.ManyToManyField(User, related_name='conversations')
    created_date = models.DateTimeField(default=timezone.now)
    last_message_date = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_message_date']
    
    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()[:2]])
        if self.participants.count() > 2:
            participant_names += f" + {self.participants.count() - 2} others"
        return f"Conversation: {participant_names}"
    
    @property
    def latest_message(self):
        """Return the latest message in this conversation"""
        return self.messages.order_by('-timestamp').first()
    
    def mark_as_read_for_user(self, user):
        """Mark all messages in this conversation as read for a specific user"""
        self.messages.filter(receiver=user, is_read=False).update(is_read=True)


class Message(models.Model):
    """Simplified message model that can work with or without conversations"""
    
    # Core fields - these are the most important
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # Optional fields for backward compatibility
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    message_type = models.ForeignKey(MessageType, on_delete=models.SET_NULL, related_name='messages', null=True, blank=True)
    read_date = models.DateTimeField(null=True, blank=True)
    
    # Anonymous messaging system
    receiver_identity_revealed = models.BooleanField(default=False, help_text="True if receiver revealed their identity to sender")
    identity_revealed_at = models.DateTimeField(null=True, blank=True, help_text="When identity was revealed")
    
    # Legacy field mapping for compatibility
    @property
    def recipient(self):
        """Backward compatibility for recipient field"""
        return self.receiver
    
    @property
    def created_date(self):
        """Backward compatibility for created_date field"""
        return self.timestamp
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sender', 'receiver', '-timestamp']),
            models.Index(fields=['receiver', 'is_read', '-timestamp']),
        ]
    
    def __str__(self):
        sender_name = getattr(self.sender, 'username', 'Unknown')
        receiver_name = getattr(self.receiver, 'username', 'Unknown')
        return f"{sender_name} -> {receiver_name}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        # Auto-create or find conversation if not provided
        if not self.conversation_id:
            # Try to find existing conversation
            conversation = Conversation.objects.filter(
                participants=self.sender
            ).filter(
                participants=self.receiver
            ).first()
            
            if not conversation:
                # Create new conversation
                conversation = Conversation.objects.create()
                conversation.participants.add(self.sender, self.receiver)
            
            self.conversation = conversation
        
        super().save(*args, **kwargs)
        
        # Update conversation's last message date after saving
        if self.conversation_id:
            Conversation.objects.filter(id=self.conversation_id).update(
                last_message_date=self.timestamp
            )
    
    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_date = timezone.now()
            self.save(update_fields=['is_read', 'read_date'])
    
    @classmethod
    def get_conversations_for_user(cls, user):
        """Get all conversations for a user grouped by other participant and message type"""
        from django.db.models import Subquery, OuterRef
        
        # Get all unique combinations of user and message type
        sent_conversations = cls.objects.filter(sender=user).values('receiver', 'message_type').distinct()
        received_conversations = cls.objects.filter(receiver=user).values('sender', 'message_type').distinct()
        
        # Combine all unique conversation combinations
        conversation_combos = set()
        
        for conv in sent_conversations:
            conversation_combos.add((conv['receiver'], conv['message_type']))
            
        for conv in received_conversations:
            conversation_combos.add((conv['sender'], conv['message_type']))
        
        conversations = []
        for other_user_id, message_type_id in conversation_combos:
            try:
                other_user = User.objects.get(id=other_user_id)
                
                # Check if users are in the same community (superusers bypass this check)
                if not user.is_superuser:
                    user_communities = set(user.community_memberships.filter(is_active=True).values_list('community', flat=True))
                    other_user_communities = set(other_user.community_memberships.filter(is_active=True).values_list('community', flat=True))
                    
                    # Skip if they don't share at least one community
                    if not user_communities.intersection(other_user_communities):
                        continue
                message_type = None
                if message_type_id:
                    try:
                        message_type = MessageType.objects.get(id=message_type_id)
                    except MessageType.DoesNotExist:
                        pass
                
                # Get latest message between these two users for this message type
                message_filter = Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user)
                if message_type:
                    message_filter &= Q(message_type=message_type)
                else:
                    message_filter &= Q(message_type__isnull=True)
                
                latest_message = cls.objects.filter(message_filter).first()
                
                # Count unread messages from this user for this message type
                unread_filter = Q(sender=other_user, receiver=user, is_read=False)
                if message_type:
                    unread_filter &= Q(message_type=message_type)
                else:
                    unread_filter &= Q(message_type__isnull=True)
                    
                unread_count = cls.objects.filter(unread_filter).count()
                
                if latest_message:
                    conversations.append({
                        'other_user': other_user,
                        'latest_message': latest_message,
                        'unread_count': unread_count,
                        'timestamp': latest_message.timestamp,
                        'message_type': message_type
                    })
            except User.DoesNotExist:
                continue
        
        # Sort by latest message timestamp
        conversations.sort(key=lambda x: x['timestamp'], reverse=True)
        return conversations
    
    @classmethod
    def get_messages_between_users(cls, user1, user2, message_type=None, limit=50):
        """Get messages between two users in chronological order, optionally filtered by message type"""
        message_filter = Q(sender=user1, receiver=user2) | Q(sender=user2, receiver=user1)
        
        # Always filter by message type when provided
        if message_type is not None:
            message_filter &= Q(message_type=message_type)
        elif hasattr(cls, '_filter_by_message_type') and cls._filter_by_message_type is not None:
            # Use the filter flag to determine if we should filter by null message type
            message_filter &= Q(message_type__isnull=True)
        
        messages = cls.objects.filter(message_filter).order_by('-timestamp')[:limit]
        return list(reversed(messages))  # Return in chronological order


class MessageRequest(models.Model):
    """Model for tracking message requests before conversations start"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    message_type = models.ForeignKey(MessageType, on_delete=models.CASCADE, related_name='requests')
    
    initial_message = models.TextField(help_text="Initial message to introduce the conversation")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_date = models.DateTimeField(default=timezone.now)
    responded_date = models.DateTimeField(null=True, blank=True)
    
    # Optional: Link to conversation if request is accepted
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['from_user', 'to_user', 'message_type']
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.message_type.name}): {self.status}"
    
    def accept(self):
        """Accept the message request and create a conversation"""
        if self.status == 'pending':
            # Create conversation
            conversation = Conversation.objects.create()
            conversation.participants.add(self.from_user, self.to_user)
            
            # Create initial message
            Message.objects.create(
                conversation=conversation,
                sender=self.from_user,
                receiver=self.to_user,
                message_type=self.message_type,
                content=self.initial_message
            )
            
            # Update request status
            self.status = 'accepted'
            self.responded_date = timezone.now()
            self.conversation = conversation
            self.save()
            
            return conversation
    
    def decline(self):
        """Decline the message request"""
        if self.status == 'pending':
            self.status = 'declined'
            self.responded_date = timezone.now()
            self.save()


class MessageSlotBooking(models.Model):
    """Model to track message slot bookings with 3-day expiry"""
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slot_bookings_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slot_bookings_received')
    message_type = models.ForeignKey(MessageType, on_delete=models.CASCADE, related_name='slot_bookings')
    
    created_date = models.DateTimeField(auto_now_add=True)
    expires_date = models.DateTimeField()
    
    # Reference to the actual message (optional, for tracking)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True, related_name='slot_booking')
    
    class Meta:
        unique_together = ['sender', 'receiver', 'message_type']
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['receiver', 'message_type', 'expires_date']),
            models.Index(fields=['sender', 'receiver', 'message_type']),
        ]
    
    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.message_type.name})"
    
    def save(self, *args, **kwargs):
        # Auto-set expiry date to 3 days from creation
        if not self.expires_date:
            from datetime import timedelta
            self.expires_date = timezone.now() + timedelta(days=3)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if this booking has expired"""
        return timezone.now() > self.expires_date
    
    @classmethod
    def cleanup_expired_bookings(cls):
        """Remove all expired bookings (can be called by management command)"""
        expired_count = cls.objects.filter(expires_date__lt=timezone.now()).count()
        cls.objects.filter(expires_date__lt=timezone.now()).delete()
        return expired_count
    
    @classmethod
    def get_active_bookings_for_receiver(cls, receiver, message_type):
        """Get active (non-expired) bookings for a receiver and message type"""
        return cls.objects.filter(
            receiver=receiver,
            message_type=message_type,
            expires_date__gt=timezone.now()
        )
    
    @classmethod
    def can_user_send_message(cls, sender, receiver, message_type):
        """Check if sender can send a message to receiver for given message type"""
        # Check if sender already has an active booking for this receiver and message type
        existing_booking = cls.objects.filter(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            expires_date__gt=timezone.now()
        ).exists()
        
        if existing_booking:
            return False, "already_sent"
        
        # Check if receiver has available slots
        active_bookings_count = cls.get_active_bookings_for_receiver(receiver, message_type).count()
        receiver_limit = cls._get_receiver_slot_limit(receiver, message_type)
        
        if receiver_limit == 0:
            return False, "invalid_slot_type"
            
        if active_bookings_count >= receiver_limit:
            return False, "slots_full"
        
        return True, "available"
    
    @classmethod
    def _get_receiver_slot_limit(cls, receiver, message_type):
        """Get the slot limit for a receiver based on custom message type"""
        try:
            # Only use custom slots (we removed default slots)
            # For custom slots, extract the actual slot name from the message type name
            if message_type.name.startswith(f'CUSTOM_{receiver.id}_'):
                actual_slot_name = message_type.name.replace(f'CUSTOM_{receiver.id}_', '')
                custom_slot = CustomMessageSlot.objects.filter(
                    user=receiver,
                    name=actual_slot_name,
                    is_active=True
                ).first()
                
                if custom_slot:
                    return custom_slot.slot_limit
            
            # If no custom slot found, return 0 to prevent any bookings for invalid slots
            return 0
        except Exception as e:
            return 0
    
    @classmethod
    def book_slot(cls, sender, receiver, message_type, message=None):
        """Book a slot for sender to message receiver"""
        # Check if sender has available credits
        credit_record = UserCredit.get_or_create_for_user(sender)
        if not credit_record.can_use_credit():
            return None, "no_credits"
        
        can_send, reason = cls.can_user_send_message(sender, receiver, message_type)
        if not can_send:
            return None, reason
        
        # Create the booking
        try:
            booking = cls.objects.create(
                sender=sender,
                receiver=receiver,
                message_type=message_type,
                message=message
            )
            
            # Use credit and log transaction
            balance_before = credit_record.available_credits
            if credit_record.use_credit():
                balance_after = credit_record.available_credits
                
                # Log the credit transaction
                CreditTransaction.log_transaction(
                    user=sender,
                    transaction_type='used',
                    amount=-1,  # Negative because credit was used
                    balance_before=balance_before,
                    balance_after=balance_after,
                    description=f"Credit used for message slot to {receiver.username}",
                    message_slot_booking=booking
                )
                
                # Also log to audit trail
                from audittrack.utils import log_credit_used
                log_credit_used(
                    sender, 
                    f"Used 1 credit for {message_type.name} message to {receiver.username}. Balance: {balance_after}/{credit_record.total_credits}",
                    receiver
                )
                
                return booking, "booked"
            else:
                # This shouldn't happen due to our check above, but just in case
                booking.delete()
                return None, "no_credits"
                
        except Exception as e:
            # Handle duplicate booking constraint
            return None, "already_sent"


class IdentityRevelation(models.Model):
    """Model to track when users reveal their real identity to others for specific message types"""
    
    revealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='identity_revelations_made', help_text="User who revealed their identity")
    revealed_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='identity_revelations_received', help_text="User who can now see the real identity")
    message_type = models.ForeignKey(MessageType, on_delete=models.CASCADE, null=True, blank=True, help_text="Message type for which identity was revealed")
    revealed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['revealer', 'revealed_to', 'message_type']
        ordering = ['-revealed_at']
    
    def __str__(self):
        return f"{self.revealer.username} revealed identity to {self.revealed_to.username}"
    
    @classmethod
    def has_revealed_identity(cls, revealer, revealed_to, message_type=None):
        """Check if revealer has revealed their identity to revealed_to for specific message type"""
        return cls.objects.filter(
            revealer=revealer, 
            revealed_to=revealed_to,
            message_type=message_type
        ).exists()
    
    @classmethod
    def reveal_identity(cls, revealer, revealed_to, message_type=None):
        """Reveal identity from revealer to revealed_to for specific message type"""
        revelation, created = cls.objects.get_or_create(
            revealer=revealer,
            revealed_to=revealed_to,
            message_type=message_type
        )
        return revelation, created


class CustomMessageSlot(models.Model):
    """Model for custom message slot types defined by users"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_message_slots')
    name = models.CharField(max_length=50, help_text="Name for the custom slot type")
    slot_limit = models.PositiveIntegerField(default=5, help_text="Maximum number of slots for this type")
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.slot_limit} slots)"


class UserMessageSettings(models.Model):
    """Model for user's message settings and preferences"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='message_settings')
    
    # Enable/disable message types
    coffee_chat_enabled = models.BooleanField(default=True)
    mentorship_enabled = models.BooleanField(default=True)
    networking_enabled = models.BooleanField(default=True)
    general_enabled = models.BooleanField(default=True)
    
    # Allow custom slot types (now always True since we removed default slots)
    use_custom_slots = models.BooleanField(default=True, help_text="Use custom message slot types")
    
    # Auto-accept messages from certain roles
    auto_accept_from_moderators = models.BooleanField(default=False)
    auto_accept_from_admins = models.BooleanField(default=True)
    
    # Notification settings
    email_notifications = models.BooleanField(default=True)
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Message settings for {self.user.username}"
    
    def is_message_type_enabled(self, message_type_name):
        """Check if a specific message type is enabled for this user"""
        type_mapping = {
            'Coffee Chat': self.coffee_chat_enabled,
            'Mentorship': self.mentorship_enabled,
            'Networking': self.networking_enabled,
            'General': self.general_enabled,
        }
        return type_mapping.get(message_type_name, True)
    
    def get_slot_availability_for_user(self, requesting_user):
        """Get slot availability information for all message types when requesting_user wants to message this user"""
        from datetime import timedelta
        
        availability = {}
        
        # Always use custom slots (we removed default slots)
        # Get custom slots for this user ONLY
        custom_slots = CustomMessageSlot.objects.filter(user=self.user, is_active=True)
        
        for custom_slot in custom_slots:
            # Don't create global MessageType objects - handle custom slots separately
            # Count active bookings using custom slot name directly
            active_bookings = MessageSlotBooking.objects.filter(
                receiver=self.user,
                expires_date__gt=timezone.now()
            ).filter(
                # For custom slots, we'll match on a naming convention
                message_type__name=f"CUSTOM_{self.user.id}_{custom_slot.name}"
            ).count()
            
            # Check if requesting user already sent a message
            already_sent = MessageSlotBooking.objects.filter(
                sender=requesting_user,
                receiver=self.user,
                expires_date__gt=timezone.now()
            ).filter(
                message_type__name=f"CUSTOM_{self.user.id}_{custom_slot.name}"
            ).exists()
            
            # Calculate status
            available_slots = custom_slot.slot_limit - active_bookings
            
            if already_sent:
                status = "already_sent"
            elif available_slots <= 0:
                status = "full"
            else:
                status = "available"
            
            availability[custom_slot.name.lower().replace(' ', '_')] = {
                'message_type': {'name': custom_slot.name, 'id': f'custom_{custom_slot.id}'},
                'total_slots': custom_slot.slot_limit,
                'used_slots': active_bookings,
                'available_slots': max(0, available_slots),
                'status': status,
                'already_sent': already_sent,
                'is_custom': True,
                'custom_slot_id': custom_slot.id
            }
        
        return availability


# Signals to create message settings and credits when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_message_settings(sender, instance, created, **kwargs):
    if created:
        UserMessageSettings.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def create_user_credit(sender, instance, created, **kwargs):
    if created:
        UserCredit.objects.get_or_create(user=instance)


class MessageReport(models.Model):
    """Simple model for reporting users in messages"""
    
    REPORT_TYPES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('inappropriate', 'Inappropriate Content'),
        ('fake', 'Fake Account'),
        ('other', 'Other'),
    ]
    
    # Who is reporting and who is being reported
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    
    # Report details
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    note = models.TextField(help_text="Additional details about the report")
    
    # Timestamp
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.reporter.username} reported {self.reported_user.username} - {self.get_report_type_display()}"


class UserBlock(models.Model):
    """Simple model for blocking users"""
    
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['blocker', 'blocked']
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"
    
    @classmethod
    def is_blocked(cls, user1, user2):
        """Check if either user has blocked the other"""
        return cls.objects.filter(
            Q(blocker=user1, blocked=user2) | 
            Q(blocker=user2, blocked=user1)
        ).exists()


class ChatBlock(models.Model):
    """Model for tracking chat blocks with report reasons"""
    
    # Chat participants
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_blocks_reported')
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_blocks_received')
    
    # Chat identifier (can be used to track specific conversation)
    chat_id = models.CharField(max_length=100, null=True, blank=True, help_text="Identifier for the specific chat")
    
    # Report that led to block
    report = models.ForeignKey(MessageReport, on_delete=models.CASCADE, related_name='chat_blocks')
    
    # Block status
    is_active = models.BooleanField(default=True, help_text="Whether the block is currently active")
    
    # Admin control
    reviewed_by_admin = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True, help_text="Admin notes about this block")
    
    # Timestamps
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['reporter', 'blocked_user']
        ordering = ['-created_date']
    
    def __str__(self):
        return f"Chat block: {self.reporter.username} blocked {self.blocked_user.username}"
    
    @classmethod
    def is_chat_blocked(cls, user1, user2):
        """Check if chat between two users is blocked"""
        return cls.objects.filter(
            Q(reporter=user1, blocked_user=user2, is_active=True) | 
            Q(reporter=user2, blocked_user=user1, is_active=True)
        ).exists()
    
    @classmethod
    def get_block_info(cls, user1, user2):
        """Get block information between two users"""
        return cls.objects.filter(
            Q(reporter=user1, blocked_user=user2, is_active=True) | 
            Q(reporter=user2, blocked_user=user1, is_active=True)
        ).first()


class ChatHeading(models.Model):
    """Model for storing user-defined headings/notes for specific chats"""
    
    # User who set the heading (owner of the heading)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_headings', help_text="User who set this heading")
    
    # Chat participant (the other user in the conversation)
    other_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_headings_for', help_text="The other user in the conversation")
    
    # Optional message type (for conversations with specific message types)
    message_type = models.ForeignKey(MessageType, on_delete=models.CASCADE, null=True, blank=True, help_text="Message type for this conversation")
    
    # The heading/note text
    heading = models.CharField(max_length=100, help_text="Custom heading/note for this chat (max 100 characters)")
    
    # Timestamps
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'other_user', 'message_type']
        ordering = ['-updated_date']
    
    def __str__(self):
        message_type_name = self.message_type.name if self.message_type else "General"
        return f"{self.user.username} -> {self.other_user.username} ({message_type_name}): {self.heading}"
    
    @classmethod
    def get_heading_for_chat(cls, user, other_user, message_type=None):
        """Get the heading for a specific chat"""
        try:
            return cls.objects.get(
                user=user,
                other_user=other_user,
                message_type=message_type
            ).heading
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def set_heading_for_chat(cls, user, other_user, message_type, heading):
        """Set or update the heading for a specific chat"""
        if heading and heading.strip():
            heading_obj, created = cls.objects.update_or_create(
                user=user,
                other_user=other_user,
                message_type=message_type,
                defaults={'heading': heading.strip()[:100]}  # Limit to 100 characters
            )
            return heading_obj
        else:
            # If heading is empty, delete existing heading
            cls.objects.filter(
                user=user,
                other_user=other_user,
                message_type=message_type
            ).delete()
            return None


class UserCredit(models.Model):
    """Model to track user credits for new message slots"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='credit_balance',
        help_text="User who owns these credits"
    )
    
    # Current credit balance
    total_credits = models.IntegerField(
        default=3, 
        help_text="Total available credits (base + purchased + admin granted)"
    )
    
    # Base credits (reset weekly)
    base_credits = models.IntegerField(
        default=3,
        help_text="Base credits reset weekly (always 3)"
    )
    
    # Additional credits (purchased or admin granted)
    bonus_credits = models.IntegerField(
        default=0,
        help_text="Additional credits from purchases or admin grants"
    )
    
    # Credit tracking
    credits_used_this_week = models.IntegerField(
        default=0,
        help_text="Credits used in current week"
    )
    
    # Weekly reset tracking
    last_reset_date = models.DateTimeField(
        default=timezone.now,
        help_text="Last time credits were reset"
    )
    
    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Credit'
        verbose_name_plural = 'User Credits'
    
    def __str__(self):
        return f"{self.user.username}: {self.total_credits} credits"
    
    @property
    def available_credits(self):
        """Calculate available credits (total - used this week)"""
        return max(0, self.total_credits - self.credits_used_this_week)
    
    def can_use_credit(self):
        """Check if user has available credits"""
        return self.available_credits > 0
    
    def use_credit(self, amount=1):
        """Use credits and return success status"""
        if self.available_credits >= amount:
            self.credits_used_this_week += amount
            self.save(update_fields=['credits_used_this_week', 'updated_date'])
            return True
        return False
    
    def add_credits(self, amount, is_bonus=True):
        """Add credits to user balance"""
        old_total = self.total_credits
        
        if is_bonus:
            self.bonus_credits += amount
        self.total_credits += amount
        self.save(update_fields=['bonus_credits', 'total_credits', 'updated_date'])
        
        # Log to audit trail
        from audittrack.utils import log_credit_granted
        credit_type = "bonus" if is_bonus else "base"
        log_credit_granted(
            self.user,
            f"Granted {amount} {credit_type} credits: {old_total} → {self.total_credits} total credits"
        )
    
    def should_reset_weekly_credits(self):
        """Check if weekly credits should be reset"""
        week_ago = timezone.now() - timedelta(days=7)
        return self.last_reset_date < week_ago
    
    def reset_weekly_credits(self):
        """Reset weekly credits - gives base 3 credits plus any bonus credits"""
        old_total = self.total_credits
        
        # Always get 3 base credits per week
        self.base_credits = 3
        
        # Total credits = base credits + any bonus credits
        self.total_credits = self.base_credits + self.bonus_credits
        
        # Reset weekly usage counter
        self.credits_used_this_week = 0
        self.last_reset_date = timezone.now()
        
        self.save(update_fields=[
            'base_credits', 'total_credits', 'credits_used_this_week', 
            'last_reset_date', 'updated_date'
        ])
        
        # Log to audit trail
        from audittrack.utils import log_weekly_credit_reset
        log_weekly_credit_reset(
            self.user,
            f"Weekly credit reset: {old_total} → {self.total_credits} credits (Base: {self.base_credits}, Bonus: {self.bonus_credits})"
        )
        
        return self.total_credits
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create credit record for user"""
        credit_record, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'total_credits': 3,
                'base_credits': 3,
                'bonus_credits': 0,
                'credits_used_this_week': 0,
                'last_reset_date': timezone.now()
            }
        )
        
        # Check if weekly reset is needed
        if credit_record.should_reset_weekly_credits():
            credit_record.reset_weekly_credits()
        
        return credit_record
    
    @classmethod
    def check_and_reset_all_weekly_credits(cls):
        """Management command helper - reset credits for all users who need it"""
        week_ago = timezone.now() - timedelta(days=7)
        users_to_reset = cls.objects.filter(last_reset_date__lt=week_ago)
        
        reset_count = 0
        for credit_record in users_to_reset:
            credit_record.reset_weekly_credits()
            reset_count += 1
            
        return reset_count


class CreditTransaction(models.Model):
    """Model to track credit usage and grants for audit purposes"""
    
    TRANSACTION_TYPES = [
        ('used', 'Credits Used'),
        ('weekly_reset', 'Weekly Reset'),
        ('admin_grant', 'Admin Grant'),
        ('purchase', 'Purchase'),
        ('bonus', 'Bonus Credits'),
        ('refund', 'Refund'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='credit_transactions'
    )
    
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES
    )
    
    amount = models.IntegerField(help_text="Positive for grants, negative for usage")
    
    # Optional references
    message_slot_booking = models.ForeignKey(
        'MessageSlotBooking', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Reference to slot booking if credit was used for messaging"
    )
    
    # Description for admin grants or other special cases
    description = models.TextField(blank=True)
    
    # Balances after transaction
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()
    
    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='credit_transactions_created',
        help_text="Admin user who created this transaction (for admin grants)"
    )
    
    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Credit Transaction'
        verbose_name_plural = 'Credit Transactions'
    
    def __str__(self):
        action = "used" if self.amount < 0 else "gained"
        return f"{self.user.username} {action} {abs(self.amount)} credits - {self.get_transaction_type_display()}"
    
    @classmethod
    def log_transaction(cls, user, transaction_type, amount, balance_before, balance_after, 
                       description="", created_by=None, message_slot_booking=None):
        """Log a credit transaction"""
        return cls.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            created_by=created_by,
            message_slot_booking=message_slot_booking
        )