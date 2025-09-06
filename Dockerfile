# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=growcommunity.settings \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        sqlite3 \
        libsqlite3-dev \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/


# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/data

# Expose the port (will be overridden by environment variable)
EXPOSE $PORT

# Run migrations, collect static files, create superuser, and start server
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell && \
    echo "Starting GrowComm on port $PORT" && \
    python manage.py runserver 0.0.0.0:$PORT