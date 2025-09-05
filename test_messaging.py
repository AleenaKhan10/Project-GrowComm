"""
Test script to verify the messaging system is working correctly.
Run this with: python manage.py shell < test_messaging.py
"""

from django.contrib.auth.models import User
from messaging.models import Message, MessageType
from django.utils import timezone

# Get or create test users
user1, _ = User.objects.get_or_create(username='testuser1', defaults={
    'email': 'test1@example.com',
    'first_name': 'Test',
    'last_name': 'User1'
})

user2, _ = User.objects.get_or_create(username='testuser2', defaults={
    'email': 'test2@example.com', 
    'first_name': 'Test',
    'last_name': 'User2'
})

print(f"Test users created: {user1.username}, {user2.username}")

# Get or create a message type
msg_type, _ = MessageType.objects.get_or_create(
    name='General',
    defaults={'description': 'General message', 'is_active': True}
)
print(f"Message type: {msg_type.name}")

# Create test messages
message1 = Message.objects.create(
    sender=user1,
    receiver=user2,
    content="Hello! This is a test message from user1 to user2.",
    message_type=msg_type
)
print(f"Created message 1: {message1}")

message2 = Message.objects.create(
    sender=user2,
    receiver=user1,
    content="Hi! This is a reply from user2 to user1.",
    message_type=msg_type
)
print(f"Created message 2: {message2}")

# Test the get_conversations_for_user method
print("\n--- Testing get_conversations_for_user ---")
conversations = Message.get_conversations_for_user(user1)
for conv in conversations:
    print(f"Conversation with {conv['other_user'].username}:")
    print(f"  Latest message: {conv['latest_message'].content[:50]}...")
    print(f"  Unread count: {conv['unread_count']}")
    print(f"  Timestamp: {conv['timestamp']}")

# Test get_messages_between_users method
print("\n--- Testing get_messages_between_users ---")
messages = Message.get_messages_between_users(user1, user2)
for msg in messages:
    print(f"{msg.sender.username} -> {msg.receiver.username}: {msg.content[:50]}...")

# Test marking messages as read
print("\n--- Testing mark_as_read ---")
unread_messages = Message.objects.filter(receiver=user1, is_read=False)
print(f"Unread messages for user1: {unread_messages.count()}")
for msg in unread_messages:
    msg.mark_as_read()
print(f"After marking as read: {Message.objects.filter(receiver=user1, is_read=False).count()}")

print("\n✅ All tests completed successfully!")