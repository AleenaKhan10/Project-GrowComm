# GrowCommunity Database Schema

## Core Tables

```
USER (Django built-in)
├── id (PK)
├── username
├── email
├── first_name
├── last_name
└── date_joined

USER_PROFILE
├── id (PK)
├── user_id (FK → USER)
├── profile_picture
├── bio
├── company
├── location
├── gender
├── phone_number
├── organization_level
├── is_verified
├── invite_source_id (FK → USER)
├── anonymous_name
├── created_date
└── updated_date

COMMUNITY
├── id (PK)
├── name
├── description
├── created_by_id (FK → USER)
├── is_active
├── is_private
└── created_date

COMMUNITY_MEMBERSHIP
├── id (PK)
├── user_id (FK → USER)
├── community_id (FK → COMMUNITY)
├── role (member/moderator/admin/owner)
├── joined_date
└── is_active

MESSAGE_TYPE
├── id (PK)
├── name
├── description
├── is_active
└── color_code

CONVERSATION
├── id (PK)
├── participants (M2M → USER)
├── created_date
├── last_message_date
└── is_active

MESSAGE
├── id (PK)
├── sender_id (FK → USER)
├── receiver_id (FK → USER)
├── conversation_id (FK → CONVERSATION)
├── message_type_id (FK → MESSAGE_TYPE)
├── content
├── timestamp
├── is_read
├── read_date
└── receiver_identity_revealed

MESSAGE_SLOT_BOOKING
├── id (PK)
├── sender_id (FK → USER)
├── receiver_id (FK → USER)
├── message_type_id (FK → MESSAGE_TYPE)
├── message_id (FK → MESSAGE)
├── created_date
└── expires_date

CUSTOM_MESSAGE_SLOT
├── id (PK)
├── user_id (FK → USER)
├── name
├── slot_limit
├── is_active
└── created_date

USER_MESSAGE_SETTINGS
├── id (PK)
├── user_id (FK → USER)
├── coffee_chat_enabled
├── mentorship_enabled
├── networking_enabled
├── general_enabled
├── use_custom_slots
├── email_notifications
└── auto_accept_from_admins

INVITE_LINK
├── id (PK)
├── code (UUID)
├── created_by_id (FK → USER)
├── used_by_id (FK → USER)
├── is_used
├── created_date
└── expiry_date

REFERRAL
├── id (PK)
├── sender_id (FK → USER)
├── recipient_email
├── recipient_user_id (FK → USER)
├── created_at
└── status

IDENTITY_REVELATION
├── id (PK)
├── revealer_id (FK → USER)
├── revealed_to_id (FK → USER)
├── message_type_id (FK → MESSAGE_TYPE)
└── revealed_at
```

## Relationships Summary

- User has one UserProfile (1:1)
- User can have multiple CommunityMemberships (1:M)
- Community has multiple CommunityMemberships (1:M)  
- User can send/receive multiple Messages (1:M)
- Conversation has multiple participants via M2M relationship
- Message belongs to one Conversation (M:1)
- User can create multiple InviteLinks (1:M)
- User can send/receive multiple Referrals (1:M)
- User can create multiple CustomMessageSlots (1:M)
- MessageSlotBooking tracks message sending permissions

## Key Features

- **Anonymous Messaging**: Users have anonymous_name for community interactions
- **Message Slots**: Custom slot system limits messages per user
- **Verification System**: 3-referral system for user verification  
- **Community Management**: Role-based community membership
- **Identity Revelation**: Users can reveal real identity selectively