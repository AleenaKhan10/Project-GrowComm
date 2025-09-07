# GrowCommunity

A professional networking and messaging platform that connects verified community members through a referral-based verification system.

## Features

- **Anonymous Messaging System**: Users communicate using anonymous names until they choose to reveal their identity
- **Verification Through Referrals**: 3-referral system ensures community quality and trust
- **Custom Message Slots**: Users define their own message categories and limits
- **Community Management**: Role-based community system with moderators and admins
- **Progressive Web App**: Install on mobile devices for app-like experience
- **Professional Profiles**: Comprehensive profiles with skills, education, and company info

## Technology Stack

- **Backend**: Django 5.2.6 with Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: Django Templates with Tailwind CSS
- **Image Processing**: Pillow for profile picture optimization
- **Deployment**: Docker with Nginx and Gunicorn

## Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd growcommunity
   ```

2. **Create and activate virtual environment**
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

4. **Set up environment variables**
   ```bash
   cp .env.production.example .env.local
   # Edit .env.local with your settings
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to access the application.

## Project Structure

```
growcommunity/
├── accounts/           # User authentication
├── communities/        # Community management
├── invites/           # Invitation system
├── messaging/         # Messaging and slots
├── profiles/          # User profiles
├── legal/            # Terms and privacy pages
├── templates/        # HTML templates
├── static/           # Static files (CSS, JS, images)
├── media/            # User uploads
└── growcommunity/    # Django settings
```

## Key Models

- **UserProfile**: Extended user information with verification status
- **Community**: Groups of users with role-based permissions
- **Message**: Anonymous messaging with identity revelation options
- **CustomMessageSlot**: User-defined message categories with limits
- **Referral**: 3-level referral system for verification
- **InviteLink**: Unique invitation codes for new users

## Docker Deployment

### Development
```bash
docker-compose up --build
```

### Production
```bash
# Use the provided deployment script
./deploy-production.sh
```

## Environment Variables

Key environment variables (see `.env.production.example`):

- `DEBUG`: Set to False in production
- `SECRET_KEY`: Django secret key
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Database connection string (for production)
- `EMAIL_HOST`: SMTP server for email notifications
- `STATIC_ROOT`: Path for collected static files

## Features Overview

### Anonymous Messaging
- Users start with anonymous names in communities
- Can selectively reveal identity to specific users
- Message slots prevent spam and encourage quality interactions

### Verification System
- New users need 3 referrals from existing verified users
- Super admins can instantly verify users
- Verified users can send messages and create invites

### Community Features
- Role-based permissions (Member, Moderator, Admin, Owner)
- Community-specific member directories
- Professional networking focus

### PWA Support
- Installable on mobile devices
- Offline-ready static assets
- App-like experience with custom icons

## API Endpoints

The application includes REST API endpoints for:
- User authentication
- Message management  
- Community operations
- Profile updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests for new functionality
5. Submit a pull request

## Security Features

- CSRF protection on all forms
- User input sanitization
- Rate limiting on messaging
- Secure file upload handling
- Environment-based configuration

## Performance Optimizations

- Database query optimization with indexes
- Static file caching with WhiteNoise
- Image compression for profile pictures
- Efficient message retrieval with pagination

## License

This project is proprietary software. All rights reserved.

## Support

For support or questions, please contact the development team or create an issue in the project repository.