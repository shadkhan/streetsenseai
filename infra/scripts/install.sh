#!/bin/bash
set -e

echo "=== StreetSense AI — Server Bootstrap ==="
echo "Idempotent — safe to run multiple times."
echo ""

# System update
apt-get update -y && apt-get upgrade -y

# Docker — official installation
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Docker Compose plugin
apt-get install -y docker-compose-plugin

# Add current user to docker group
usermod -aG docker $USER

# Utilities
apt-get install -y git curl nano htop ufw fail2ban

# Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw --force enable

# Fail2ban — protect SSH
systemctl enable fail2ban
systemctl start fail2ban

# Project directory (server is reused across projects)
mkdir -p /opt/apps

echo ""
echo "=== Bootstrap complete ==="
echo "Docker version: $(docker --version)"
echo "Directory ready: /opt/apps"
echo ""
echo "Next step — run deploy.sh from your local machine:"
echo "  ./infra/scripts/deploy.sh <SERVER_IP> ./infra/.env.prod"
