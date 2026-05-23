#!/bin/bash
SERVER_IP=$1
COMPOSE_FILE="infra/docker-compose.hostinger.yml"

if [ -z "$SERVER_IP" ]; then
  echo "Usage: ./infra/scripts/status.sh <SERVER_IP>"
  exit 1
fi

echo "=== StreetSense AI Status — $SERVER_IP ==="
echo ""

ssh root@$SERVER_IP << EOF
  echo "--- Containers ---"
  cd /opt/apps/streetsense
  docker compose -f $COMPOSE_FILE ps

  echo ""
  echo "--- API Health ---"
  curl -s http://localhost:8000/health/detail | python3 -m json.tool

  echo ""
  echo "--- Memory ---"
  free -h

  echo ""
  echo "--- Disk ---"
  df -h /

  echo ""
  echo "--- Container Resources ---"
  docker stats --no-stream --format \
    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
EOF
