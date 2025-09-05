from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Max, Count, Case, When, IntegerField


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
        
        if active_bookings_count >= receiver_limit:
            return False, "slots_full"
        
        return True, "available"
    
    @classmethod
    def _get_receiver_slot_limit(cls, receiver, message_type):
        """Get the slot limit for a receiver based on message type"""
        try:
            profile = receiver.profile
            type_mapping = {
                'Coffee Chat': profile.coffee_chat_slots,
                'Mentorship': profile.mentorship_slots,
                'Networking': profile.networking_slots,
                'General': profile.general_slots,
            }
            return type_mapping.get(message_type.name, 0)
        except:
            return 0
    
    @classmethod
    def book_slot(cls, sender, receiver, message_type, message=None):
        """Book a slot for sender to message receiver"""
        can_send, reason = cls.can_user_send_message(sender, receiver, message_type)
        if not can_send:
            return None, reason
        
        # Create the booking
        booking = cls.objects.create(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            message=message
        )
        return booking, "booked"


class UserMessageSettings(models.Model):
    """Model for user's message settings and preferences"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='message_settings')
    
    # Enable/disable message types
    coffee_chat_enabled = models.BooleanField(default=True)
    mentorship_enabled = models.BooleanField(default=True)
    networking_enabled = models.BooleanField(default=True)
    general_enabled = models.BooleanField(default=True)
    
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
        
        message_types = MessageType.objects.filter(is_active=True)
        availability = {}
        
        for msg_type in message_types:
            # Get user's slot limit for this message type
            slot_limit = MessageSlotBooking._get_receiver_slot_limit(self.user, msg_type)
            
            # Count active bookings
            active_bookings = MessageSlotBooking.get_active_bookings_for_receiver(self.user, msg_type).count()
            
            # Check if requesting user already sent a message
            already_sent = MessageSlotBooking.objects.filter(
                sender=requesting_user,
                receiver=self.user,
                message_type=msg_type,
                expires_date__gt=timezone.now()
            ).exists()
            
            # Calculate status
            available_slots = slot_limit - active_bookings
            
            if already_sent:
                status = "already_sent"
            elif available_slots <= 0:
                status = "full"
            else:
                status = "available"
            
            availability[msg_type.name.lower().replace(' ', '_')] = {
                'message_type': msg_type,
                'total_slots': slot_limit,
                'used_slots': active_bookings,
                'available_slots': max(0, available_slots),
                'status': status,
                'already_sent': already_sent
            }
        
        return availability


# Signal to create message settings when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_message_settings(sender, instance, created, **kwargs):
    if created:
        UserMessageSettings.objects.get_or_create(user=instance)