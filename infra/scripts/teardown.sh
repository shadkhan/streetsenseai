#!/bin/bash
set -e

SERVER_IP=$1
COMPOSE_FILE="infra/docker-compose.hostinger.yml"

if [ -z "$SERVER_IP" ]; then
  echo "Usage: ./infra/scripts/teardown.sh <SERVER_IP>"
  exit 1
fi

echo "============================================"
echo "WARNING: This will DELETE all StreetSense AI"
echo "data, containers, images and volumes from:"
echo "Server: $SERVER_IP"
echo ""
echo "What gets removed:"
echo "  - All Docker containers (API, Celery, Postgres, Redis)"
echo "  - All Docker images (~3-4GB freed)"
echo "  - All data volumes (database, Redis)"
echo "  - /opt/apps/streetsense/ directory"
echo ""
echo "What stays:"
echo "  - Docker and Docker Compose"
echo "  - Git, UFW, Fail2ban"
echo "  - /opt/apps/ (ready for next project)"
echo "============================================"
echo ""
read -p "Type DELETE STREETSENSE to confirm: " CONFIRM

if [ "$CONFIRM" != "DELETE STREETSENSE" ]; then
  echo "Cancelled. Nothing was deleted."
  exit 0
fi

echo ""
echo "=== Starting teardown ==="

ssh root@$SERVER_IP << EOF
  set -e

  if [ ! -d "/opt/apps/streetsense" ]; then
    echo "StreetSense not found at /opt/apps/streetsense"
    exit 1
  fi

  cd /opt/apps/streetsense

  echo "Stopping and removing containers and volumes..."
  docker compose -f $COMPOSE_FILE down --volumes --remove-orphans

  echo "Removing all unused Docker resources..."
  docker system prune -af

  echo "Removing application directory..."
  rm -rf /opt/apps/streetsense

  echo ""
  echo "=== Teardown complete ==="
  echo "Disk space available:"
  df -h /
  echo ""
  echo "Remaining in /opt/apps/:"
  ls -la /opt/apps/ 2>/dev/null || echo "(empty)"
  echo ""
  echo "Server is ready for the next project."
EOF
