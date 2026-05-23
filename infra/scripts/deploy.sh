#!/bin/bash
set -e

SERVER_IP=$1
ENV_FILE=$2
REPO_URL="https://github.com/shadkhan/streetsenseai.git"
APP_DIR="/opt/apps/streetsense"
COMPOSE_FILE="infra/docker-compose.hostinger.yml"

# Validate inputs
if [ -z "$SERVER_IP" ] || [ -z "$ENV_FILE" ]; then
  echo "Usage: ./infra/scripts/deploy.sh <SERVER_IP> <ENV_FILE>"
  echo "Example: ./infra/scripts/deploy.sh 89.116.20.11 ./infra/.env.prod"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found"
  exit 1
fi

echo "=== Deploying StreetSense AI to $SERVER_IP ==="

# Copy env file to server
echo "Copying environment file..."
ssh root@$SERVER_IP "mkdir -p $APP_DIR"
scp $ENV_FILE root@$SERVER_IP:$APP_DIR/.env

# Deploy on server
ssh root@$SERVER_IP << EOF
  set -e

  cd /opt/apps

  # Clone or update repo
  if [ -d "streetsense/.git" ]; then
    echo "Updating existing repo..."
    cd streetsense && git pull
  else
    echo "Cloning repo..."
    git clone $REPO_URL streetsense
    cd streetsense
  fi

  # Start database and Redis first
  echo "Starting database and Redis..."
  docker compose -f $COMPOSE_FILE --env-file .env up -d postgres redis

  echo "Waiting 20 seconds for database to be ready..."
  sleep 20

  # Run migrations
  echo "Running database migrations..."
  docker compose -f $COMPOSE_FILE --env-file .env \
    run --rm api uv run alembic upgrade head

  # Start all services
  echo "Starting all services..."
  docker compose -f $COMPOSE_FILE --env-file .env up -d

  echo "Waiting 15 seconds for API to start..."
  sleep 15

  # Health check
  echo "Running health check..."
  curl -f http://localhost:8000/health || {
    echo "Health check failed. Check logs:"
    docker compose -f $COMPOSE_FILE logs api --tail=50
    exit 1
  }

  echo ""
  echo "=== All services running ==="
  docker compose -f $COMPOSE_FILE ps
EOF

echo ""
echo "=== Running data seed ==="

echo "Seeding Street Manager synthetic data..."
ssh root@$SERVER_IP "curl -s -X POST http://localhost:8000/works/admin/seed"
echo ""

echo "Seeding NUAR synthetic data..."
ssh root@$SERVER_IP "curl -s -X POST http://localhost:8000/nuar/admin/seed"
echo ""

echo "Seeding D-TRO synthetic data..."
ssh root@$SERVER_IP "curl -s -X POST http://localhost:8000/dtros/admin/seed"
echo ""

echo "Running corridor scoring (30-60 seconds)..."
ssh root@$SERVER_IP "curl -s -X POST http://localhost:8000/corridors/admin/score"

echo ""
echo "============================================"
echo "=== StreetSense AI is LIVE ==="
echo "============================================"
echo "API URL:        http://$SERVER_IP:8000"
echo "Health check:   http://$SERVER_IP:8000/health"
echo "Admin console:  http://$SERVER_IP:8000/admin"
echo ""
echo "NEXT STEPS:"
echo "1. Update Vercel: NEXT_PUBLIC_API_URL=http://$SERVER_IP:8000"
echo "2. Re-register Street Manager webhooks:"
echo "   Permits:    http://$SERVER_IP:8000/webhooks/permits"
echo "   Activities: http://$SERVER_IP:8000/webhooks/activities"
echo "   Section 58: http://$SERVER_IP:8000/webhooks/section58"
echo "============================================"
