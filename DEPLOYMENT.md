# GrowCommunity Deployment Guide

This guide covers deploying GrowCommunity to production environments.

## Pre-Deployment Checklist

### Security Settings
Update `settings.py` for production:

```python
# Security settings for production
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Security headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_SSL_REDIRECT = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Generate new secret key
SECRET_KEY = 'your-long-random-secret-key-here'
```

### Database Configuration
Switch to PostgreSQL for production:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'growcommunity',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Static Files
Configure static file serving:

```python
STATIC_ROOT = '/var/www/growcommunity/static/'
MEDIA_ROOT = '/var/www/growcommunity/media/'

# For cloud storage (AWS S3, Google Cloud, etc.)
# Configure django-storages if needed
```

### Email Configuration
Set up email backend:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yourmailprovider.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@domain.com'
EMAIL_HOST_PASSWORD = 'your-email-password'
```

## Deployment Options

### Option 1: Traditional Server (Ubuntu/Debian)

1. **Install dependencies**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv postgresql nginx
   ```

2. **Set up PostgreSQL**
   ```bash
   sudo -u postgres createuser --interactive
   sudo -u postgres createdb growcommunity
   ```

3. **Deploy application**
   ```bash
   git clone your-repo.git /var/www/growcommunity
   cd /var/www/growcommunity
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn psycopg2-binary
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   python manage.py createsuperuser
   python manage.py setup_initial_data
   ```

5. **Configure Gunicorn**
   Create `/etc/systemd/system/growcommunity.service`:
   ```ini
   [Unit]
   Description=GrowCommunity Django App
   After=network.target
   
   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/growcommunity
   Environment="PATH=/var/www/growcommunity/venv/bin"
   ExecStart=/var/www/growcommunity/venv/bin/gunicorn --workers 3 --bind unix:/var/www/growcommunity/growcommunity.sock growcommunity.wsgi:application
   
   [Install]
   WantedBy=multi-user.target
   ```

6. **Configure Nginx**
   Create `/etc/nginx/sites-available/growcommunity`:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           proxy_pass http://unix:/var/www/growcommunity/growcommunity.sock;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location /static/ {
           alias /var/www/growcommunity/static/;
       }
       
       location /media/ {
           alias /var/www/growcommunity/media/;
       }
   }
   ```

### Option 2: Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   RUN python manage.py collectstatic --noinput
   
   EXPOSE 8000
   
   CMD ["gunicorn", "--bind", "0.0.0.0:8000", "growcommunity.wsgi:application"]
   ```

2. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   
   services:
     db:
       image: postgres:13
       environment:
         POSTGRES_DB: growcommunity
         POSTGRES_USER: postgres
         POSTGRES_PASSWORD: password
       volumes:
         - postgres_data:/var/lib/postgresql/data
   
     web:
       build: .
       ports:
         - "8000:8000"
       depends_on:
         - db
       environment:
         - DATABASE_URL=postgresql://postgres:password@db:5432/growcommunity
   
   volumes:
     postgres_data:
   ```

### Option 3: Platform as a Service (Heroku, Railway, etc.)

1. **Create Procfile**
   ```
   web: gunicorn growcommunity.wsgi:application
   release: python manage.py migrate && python manage.py setup_initial_data
   ```

2. **Install additional dependencies**
   Add to requirements.txt:
   ```
   gunicorn
   psycopg2-binary
   django-heroku
   ```

3. **Update settings for Heroku**
   ```python
   import django_heroku
   django_heroku.settings(locals())
   ```

## Post-Deployment

### 1. SSL Certificate
Set up SSL with Let's Encrypt:
```bash
sudo certbot --nginx -d yourdomain.com
```

### 2. Monitoring
- Set up application monitoring (Sentry, New Relic)
- Configure log aggregation
- Set up uptime monitoring

### 3. Backup Strategy
- Database backups (automated)
- Media file backups
- Code deployment backups

### 4. Performance Optimization
- Enable Redis caching
- Configure CDN for static files
- Optimize database queries

## Environment Variables

Create a `.env` file or set environment variables:

```bash
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@host:port/dbname
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Email settings
EMAIL_HOST=smtp.provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password

# Optional: Cloud storage
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
```

## Maintenance

### Regular Tasks
- Database backups
- Security updates
- Log rotation
- Performance monitoring

### Updates
1. Test in staging environment
2. Run database migrations
3. Update static files
4. Restart application servers

## Troubleshooting

### Common Issues
- **500 errors**: Check logs in `/var/log/nginx/` and application logs
- **Static files not loading**: Run `collectstatic` and check Nginx config
- **Database connection**: Verify PostgreSQL settings and user permissions
- **Email not sending**: Check SMTP settings and firewall rules

### Useful Commands
```bash
# Check application logs
sudo journalctl -u growcommunity.service

# Restart services
sudo systemctl restart growcommunity nginx

# Django shell on production
python manage.py shell

# Database shell
python manage.py dbshell
```

## Security Considerations

1. **Regular Updates**: Keep Django and dependencies updated
2. **Firewall**: Configure proper firewall rules
3. **Access Control**: Use strong passwords and 2FA where possible
4. **Monitoring**: Monitor for suspicious activities
5. **Backups**: Implement automated backup system
6. **SSL**: Use strong SSL configuration

For more detailed deployment instructions for specific platforms, consult their official documentation.