#!/bin/bash

# GrowComm Docker deployment with persistent volumes
echo "🚀 Deploying GrowComm with persistent database..."

# Stop and remove existing container
sudo docker stop growcomm-app || true
sudo docker rm growcomm-app || true

# Build new image
echo "🔨 Building Docker image..."
sudo docker build -t growcomm .

# Create volume if it doesn't exist
echo "📂 Creating persistent volume..."
sudo docker volume create growcomm-data || true

# Run container with volume mounted
echo "🚀 Starting container with persistent storage..."
sudo docker run -d \
    --name growcomm-app \
    -p 8000:8000 \
    -v growcomm-data:/app/data \
    --restart unless-stopped \
    growcomm

# Check status
echo "✅ Container started! Checking status..."
sleep 3
sudo docker ps --filter name=growcomm-app

echo ""
echo "🌐 Application available at:"
echo "   http://localhost:8000"
echo "   http://51.20.31.158:8000"
echo ""
echo "💾 Database is persistent in volume 'growcomm-data'"
echo "📋 View logs: sudo docker logs -f growcomm-app"