#!/bin/bash

# GrowComm Production Deployment Script
echo "🚀 Deploying GrowComm with SQLite Database..."

# Function to deploy with docker-compose (recommended)
deploy_with_compose() {
    echo "📦 Using Docker Compose deployment..."
    
    # Check if .env.production exists
    if [ ! -f .env.production ]; then
        echo "📝 Creating .env.production from example..."
        cp .env.production.example .env.production
        echo "⚠️  Please edit .env.production with your actual values!"
        echo "   Required: SECRET_KEY, ALLOWED_HOSTS, email settings"
    fi

    # Stop existing containers
    echo "🛑 Stopping existing containers..."
    docker-compose down

    # Build and start containers
    echo "🔨 Building and starting containers..."
    docker-compose up -d --build

    # Wait for services to start
    echo "⏳ Waiting for services to start..."
    sleep 15

    # Run migrations
    echo "🗄️  Running database migrations..."
    docker-compose exec web python manage.py migrate

    # Check container status
    echo "✅ Checking container status..."
    docker-compose ps
}

# Function to deploy with single container (simple)
deploy_simple() {
    echo "🐳 Using simple Docker deployment..."
    
    # Stop and remove existing container
    docker stop growcomm-app 2>/dev/null || true
    docker rm growcomm-app 2>/dev/null || true

    # Build new image
    echo "🔨 Building Docker image..."
    docker build -t growcomm .

    # Create data directory for SQLite
    mkdir -p ./data

    # Run container with SQLite volume
    echo "🚀 Starting container..."
    docker run -d \
        --name growcomm-app \
        -p 80:8000 \
        -p 443:8000 \
        -v $(pwd)/data:/app/data \
        -v $(pwd)/media:/app/media \
        -v $(pwd)/staticfiles:/app/staticfiles \
        -e DEBUG=False \
        -e ALLOWED_HOSTS=grwcomm.com,www.grwcomm.com,51.20.31.158,localhost \
        --restart unless-stopped \
        growcomm

    # Wait and run migrations
    echo "⏳ Waiting for container to start..."
    sleep 10
    
    echo "🗄️  Running database migrations..."
    docker exec growcomm-app python manage.py migrate
}

# Main menu
echo "Choose deployment method:"
echo "1) Docker Compose (with Nginx, SSL support) - Recommended"
echo "2) Simple Docker (single container)"
echo ""
read -p "Enter choice (1 or 2): " -n 1 -r
echo ""

case $REPLY in
    1)
        deploy_with_compose
        ;;
    2)
        deploy_simple
        ;;
    *)
        echo "Invalid choice. Using Docker Compose by default..."
        deploy_with_compose
        ;;
esac

# Create superuser if needed
echo ""
read -p "Create a superuser account? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ "$deployment_method" = "compose" ]; then
        docker-compose exec web python manage.py createsuperuser
    else
        docker exec -it growcomm-app python manage.py createsuperuser
    fi
fi

# Display final status
echo ""
echo "✨ Deployment complete!"
echo ""
echo "🌐 Your application is available at:"
if [[ $REPLY == "1" ]]; then
    echo "   https://grwcomm.com (with SSL)"
    echo "   https://www.grwcomm.com (with SSL)"
else
    echo "   http://grwcomm.com"
    echo "   http://www.grwcomm.com"
    echo "   http://51.20.31.158"
fi
echo ""
echo "💾 SQLite database is preserved in:"
if [[ $REPLY == "1" ]]; then
    echo "   Docker volume: db_volume"
    echo "   Container path: /app/data/db.sqlite3"
else
    echo "   Host directory: ./data/"
    echo "   Database file: ./data/db.sqlite3"
fi
echo ""
echo "📋 Useful commands:"
if [[ $REPLY == "1" ]]; then
    echo "   View logs:        docker-compose logs -f"
    echo "   Stop services:    docker-compose down"
    echo "   Restart:          docker-compose restart"
    echo "   Django shell:     docker-compose exec web python manage.py shell"
    echo "   Backup DB:        docker cp growcomm-web:/app/data/db.sqlite3 ./backup-$(date +%Y%m%d).sqlite3"
else
    echo "   View logs:        docker logs -f growcomm-app"
    echo "   Stop service:     docker stop growcomm-app"
    echo "   Restart:          docker restart growcomm-app"
    echo "   Django shell:     docker exec -it growcomm-app python manage.py shell"
    echo "   Backup DB:        cp ./data/db.sqlite3 ./backup-$(date +%Y%m%d).sqlite3"
fi