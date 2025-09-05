# GrowCommunity

> "Building stronger communities through shared knowledge and opportunities."

GrowCommunity is an invite-only community platform that connects professionals, entrepreneurs, and knowledge seekers in a curated environment. Built with Django and featuring a modern, responsive design using Tailwind CSS.

## Features

### 🔐 Invite-Only Access
- Secure registration system requiring valid invite codes
- 3-level approval system for referrals
- Invite link management with expiration dates

### 👤 Rich User Profiles
- Professional information (company, team, organization level)
- Skills and interests tagging
- Education history
- Customizable privacy settings
- Profile picture uploads

### 💬 Smart Messaging System
- Multiple message types: Coffee Chat, Mentorship, Networking, General
- Request-based messaging with approval workflow
- Monthly slot limits to prevent spam
- Conversation management
- Message request settings

### 🌟 Community Discovery
- Advanced search and filtering
- Card-based user display
- Tag-based skill matching
- Organization level filtering

### 🎨 Modern Design
- Clean, professional interface
- Electric cyan accent color (#00ffff)
- Mobile-first responsive design
- Tailwind CSS framework
- Modern typography and spacing

## Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone/Download the project**
   ```bash
   cd growcommunity
   ```

2. **Create and activate virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create initial data and admin user**
   ```bash
   python manage.py createsuperuser
   python manage.py setup_initial_data
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Usage Guide

### For New Users

1. **Getting an Invite**: Contact an existing member for an invite link
2. **Registration**: Use the invite link to create your account
3. **Profile Setup**: Complete your profile with professional information
4. **Discovery**: Browse the community and discover other members
5. **Connect**: Send message requests to start conversations

### For Existing Members

1. **Invite Others**: Create invite links from the Invites section
2. **Manage Messages**: Set your availability and preferences
3. **Browse Community**: Search and filter members by skills/interests
4. **Message Management**: Accept/decline requests, manage conversations

### For Administrators

1. **User Management**: Monitor user registrations and profiles
2. **Community Oversight**: Manage communities and memberships
3. **Message Types**: Configure available message categories
4. **Approval Workflow**: Handle referral approvals

## Project Structure

```
growcommunity/
├── manage.py                   # Django management script
├── requirements.txt           # Python dependencies
├── db.sqlite3                 # SQLite database
├── README.md                  # This file
├── growcommunity/             # Main project settings
│   ├── settings.py            # Django configuration
│   ├── urls.py                # URL routing
│   └── wsgi.py                # WSGI configuration
├── accounts/                  # Authentication app
│   ├── models.py              # User authentication
│   ├── views.py               # Login/register views
│   ├── forms.py               # Authentication forms
│   └── urls.py                # Auth URL patterns
├── profiles/                  # User profiles app
│   ├── models.py              # UserProfile model
│   ├── views.py               # Profile views
│   ├── forms.py               # Profile forms
│   └── admin.py               # Admin configuration
├── communities/               # Community features app
│   ├── models.py              # Community models
│   ├── views.py               # Community views
│   └── admin.py               # Community admin
├── messaging/                 # Messaging system app
│   ├── models.py              # Message models
│   ├── views.py               # Messaging views
│   ├── forms.py               # Message forms
│   └── management/            # Management commands
├── invites/                   # Invite system app
│   ├── models.py              # Invite models
│   ├── views.py               # Invite views
│   └── forms.py               # Invite forms
├── templates/                 # HTML templates
│   ├── base.html              # Base template
│   ├── accounts/              # Auth templates
│   ├── profiles/              # Profile templates
│   ├── communities/           # Community templates
│   ├── messaging/             # Message templates
│   └── invites/               # Invite templates
├── static/                    # Static files (CSS, JS, images)
└── media/                     # User uploads
```

## Key Models

### UserProfile
Extended user information including professional details, skills, privacy settings, and message slot configurations.

### InviteLink & ReferralApproval
Manages the invite-only system with expiring links and multi-level approval workflow.

### Community & CommunityMembership
Organizes users into communities with role-based permissions.

### Message, Conversation & MessageRequest
Handles the complete messaging workflow from request to conversation.

### MessageType
Categorizes different types of conversations (Coffee Chat, Mentorship, etc.).

## Configuration

### Environment Variables (Optional)
- `DEBUG`: Set to `False` for production
- `SECRET_KEY`: Change for production deployment
- `DATABASE_URL`: Configure external database

### Message Types
The system comes with four default message types:
- **Coffee Chat**: Casual conversations (brown color)
- **Mentorship**: Career guidance (green color)
- **Networking**: Professional networking (blue color)
- **General**: General discussions (cyan color)

### Customization
- Colors and styling: Edit `templates/base.html` Tailwind configuration
- Message slots: Adjust default values in UserProfile model
- Invite expiry: Modify in InviteLink form

## Security Features

- CSRF protection on all forms
- Invite-only registration
- Login required for authenticated views
- Input validation and sanitization
- Secure file upload handling
- Privacy controls for user information

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Collecting Static Files (for production)
```bash
python manage.py collectstatic
```

### Management Commands
- `setup_initial_data`: Creates default message types and community

## Deployment Considerations

1. **Database**: Switch from SQLite to PostgreSQL for production
2. **Static Files**: Configure proper static file serving
3. **Media Files**: Set up proper media file storage
4. **Environment Variables**: Use proper secret management
5. **HTTPS**: Configure SSL certificates
6. **Caching**: Implement Redis or Memcached
7. **Email**: Configure SMTP for password resets and notifications

## Technology Stack

- **Backend**: Django 5.2.6
- **Database**: SQLite (development), PostgreSQL (recommended for production)
- **Frontend**: HTML5, Tailwind CSS 3.x, Alpine.js
- **Authentication**: Django's built-in authentication
- **File Handling**: Pillow for image processing
- **Admin Interface**: Django Admin with custom configurations

## Contributing

1. Follow Django best practices and PEP 8 style guide
2. Add tests for new features
3. Update documentation for significant changes
4. Use meaningful commit messages
5. Ensure responsive design for all new UI

## License

This project is private and proprietary. All rights reserved.

## Support

For questions, issues, or feature requests, please contact the development team or create an issue in the project repository.

---

**GrowCommunity** - Building stronger communities through shared knowledge and opportunities.