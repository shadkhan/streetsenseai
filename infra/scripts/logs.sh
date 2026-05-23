#!/bin/bash
SERVER_IP=$1
SERVICE=$2
COMPOSE_FILE="infra/docker-compose.hostinger.yml"

if [ -z "$SERVER_IP" ] || [ -z "$SERVICE" ]; then
  echo "Usage: ./infra/scripts/logs.sh <SERVER_IP> <SERVICE>"
  echo "Services: api | worker | beat | postgres | redis"
  exit 1
fi

echo "=== Tailing $SERVICE logs on $SERVER_IP ==="
echo "(Press Ctrl+C to stop)"
echo ""

ssh -t root@$SERVER_IP \
  "cd /opt/apps/streetsense && \
   docker compose -f $COMPOSE_FILE logs -f --tail=100 $SERVICE"
