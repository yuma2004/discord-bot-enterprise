#!/bin/bash
# Koyeb deployment script for Discord Bot Enterprise

set -e

echo "🚀 Deploying Discord Bot Enterprise to Koyeb..."

# Check if required environment variables are set
if [ -z "$DISCORD_TOKEN" ]; then
    echo "❌ Error: DISCORD_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable is required"
    exit 1
fi

if [ -z "$DISCORD_GUILD_ID" ]; then
    echo "❌ Error: DISCORD_GUILD_ID environment variable is required"
    exit 1
fi

# App name (customize as needed)
APP_NAME=${KOYEB_APP_NAME:-"discord-bot-enterprise"}
GITHUB_REPO=${GITHUB_REPO:-"your-username/discord-bot-enterprise"}

echo "📋 Deployment Configuration:"
echo "  App Name: $APP_NAME"
echo "  Repository: $GITHUB_REPO"
echo "  Environment: production"

# Deploy using Koyeb CLI
koyeb app create $APP_NAME \
  --git $GITHUB_REPO \
  --git-branch main \
  --instance-type nano \
  --regions fra \
  --env ENVIRONMENT=production \
  --env DISCORD_TOKEN="$DISCORD_TOKEN" \
  --env DISCORD_GUILD_ID="$DISCORD_GUILD_ID" \
  --env DATABASE_URL="$DATABASE_URL" \
  --env LOG_LEVEL=INFO \
  --env TIMEZONE=Asia/Tokyo \
  --env HEALTH_CHECK_PORT=8000 \
  --port 8000:http \
  --health-check-path /health

echo "✅ Deployment initiated!"
echo ""
echo "📊 Checking deployment status..."
koyeb app get $APP_NAME

echo ""
echo "🔗 Useful commands:"
echo "  View logs: koyeb logs -a $APP_NAME -f"
echo "  Check status: koyeb app get $APP_NAME"
echo "  Scale app: koyeb app scale $APP_NAME --instances 1"
echo "  Delete app: koyeb app delete $APP_NAME"

echo ""
echo "🎉 Deployment complete! Check Koyeb Console for details."