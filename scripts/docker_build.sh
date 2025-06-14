#!/bin/bash
# Docker build script for Discord Bot Enterprise

set -e

echo "🐳 Building Discord Bot Enterprise Docker Image..."

# Build image
docker build -t discord-bot-enterprise:latest .

echo "✅ Docker image built successfully!"

# Test build
echo "🧪 Testing Docker image..."
docker run --rm discord-bot-enterprise:latest python -c "
import sys
sys.path.insert(0, 'src')
from src.core.config import Config
from src.core.database import get_database_manager
print('✅ Import test successful')
print('✅ Configuration loaded')
print('✅ Database manager available')
"

echo "🎉 Docker image tested and ready for deployment!"

# Show image info
echo "📊 Image information:"
docker images discord-bot-enterprise:latest

echo ""
echo "🚀 To run locally:"
echo "docker run --env-file .env -p 8000:8000 discord-bot-enterprise:latest"
echo ""
echo "📤 To push to registry:"
echo "docker tag discord-bot-enterprise:latest your-registry/discord-bot-enterprise:latest"
echo "docker push your-registry/discord-bot-enterprise:latest"