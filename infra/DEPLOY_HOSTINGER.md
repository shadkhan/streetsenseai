# StreetSense AI — Hostinger KVM 2 Deployment Guide

**Target:** Hostinger KVM 2 VPS (2 vCPU, 8 GB RAM, UK Coventry data centre)
**Stack:** docker-compose.hostinger.yml — 5 services (postgres, redis, api, worker, beat)
**SSL:** Handled by Hostinger on the hstgr.cloud default URL — no Nginx needed
**Access URL:** `https://<vps-id>.hstgr.cloud:8000`

---

## Three-Command Workflow (scripts)

The `infra/scripts/` directory contains five reusable scripts. This is the fastest path:

```bash
# 1. Bootstrap the server once (run on first use)
ssh root@89.116.20.11 'bash -s' < infra/scripts/install.sh

# 2. Deploy (run from your local machine, after filling in .env.prod)
./infra/scripts/deploy.sh 89.116.20.11 ./infra/.env.prod

# 3. Check status anytime
./infra/scripts/status.sh 89.116.20.11

# 4. Tail logs during debugging
./infra/scripts/logs.sh 89.116.20.11 api

# 5. Teardown when demo month ends
./infra/scripts/teardown.sh 89.116.20.11
```

> **Before running deploy.sh:** edit `infra/scripts/deploy.sh` and replace
> `YOUR_USERNAME/YOUR_REPO` with your actual GitHub repository URL.

---

## 10-Step Deployment Sequence (manual reference)

### Step 1 — SSH into the VPS

```bash
ssh root@<vps-ip>
```

### Step 2 — Install Docker + Docker Compose plugin

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
# Verify
docker --version
docker compose version
```

### Step 3 — Clone the repository

```bash
git clone https://github.com/<your-org>/streetsense-ai.git /opt/streetsense
cd /opt/streetsense
```

### Step 4 — Create and fill in `.env.prod`

```bash
cp infra/.env.prod.example infra/.env.prod
nano infra/.env.prod
```

Fill in every value — pay particular attention to:
- `DB_PASSWORD` — generate a strong random password
- `SM_EMAIL` / `SM_PASSWORD` — Street Manager sandbox credentials
- `ANTHROPIC_API_KEY`
- `NEXT_PUBLIC_MAPBOX_TOKEN`
- `OS_CLIENT_ID` / `OS_CLIENT_SECRET`
- `PUBLIC_API_URL` — set to `https://<vps-id>.hstgr.cloud:8000`
- `ADMIN_PASSWORD` / `ADMIN_SESSION_SECRET` / `ADMIN_API_KEY`

### Step 5 — Build images

```bash
cd /opt/streetsense
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod build
```

### Step 6 — Run database migrations

```bash
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod \
  run --rm api uv run alembic upgrade head
```

### Step 7 — Start all services

```bash
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod up -d
```

Verify all 5 services are running:

```bash
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod ps
```

Expected: postgres, redis, api, worker, beat — all `running`.

Health check:

```bash
curl http://localhost:8000/health
```

### Step 8 — Seed synthetic data

Run these three seed commands to populate the demo dataset:

```bash
# Synthetic Street Manager data (5,045 permits, seed=42)
curl -X POST http://localhost:8000/admin/seed/street-manager \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"

# Synthetic NUAR underground assets (395 assets, 6 owners, seed=42)
curl -X POST http://localhost:8000/nuar/admin/seed \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"

# Synthetic D-TRO orders (500 permanent + 200 TTROs, seed=42)
curl -X POST http://localhost:8000/dtro/admin/seed \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

### Step 9 — Re-register Street Manager webhooks

Street Manager requires your publicly accessible HTTPS URL to deliver permit events.
Update your SM sandbox registration with these three endpoint URLs:

| Event type  | Webhook URL |
|-------------|-------------|
| Permits     | `https://<vps-id>.hstgr.cloud:8000/webhooks/permits` |
| Activities  | `https://<vps-id>.hstgr.cloud:8000/webhooks/activities` |
| Section 58  | `https://<vps-id>.hstgr.cloud:8000/webhooks/section58` |

> The Admin console at `https://<vps-id>.hstgr.cloud:8000/admin` → System tab
> shows the three webhook URLs pre-formatted once `PUBLIC_API_URL` is set correctly.

### Step 10 — Update Vercel frontend environment variable

In the Vercel dashboard for the `apps/web` project:

1. Go to **Settings → Environment Variables**
2. Update `NEXT_PUBLIC_API_URL` to:
   ```
   https://<vps-id>.hstgr.cloud:8000
   ```
3. Trigger a **Redeploy** so the frontend picks up the new API base URL

---

## Useful day-to-day commands

```bash
# Tail API logs
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod logs -f api

# Restart a single service
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod restart api

# Stop everything
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod down

# Pull latest code and rebuild
git pull
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod build api worker beat
docker compose -f infra/docker-compose.hostinger.yml --env-file infra/.env.prod up -d
```

---

## Notes

- **SSL termination:** Hostinger terminates TLS on the hstgr.cloud subdomain — the API container
  itself serves plain HTTP on port 8000. Do not add Nginx or Certbot to this compose file.
- **beat service:** The Celery Beat scheduler (`beat`) is included here and was backported to
  `docker-compose.prod.yml` as well (it was previously missing — see ADR-029).
- **Demo lifetime:** This deployment is intended for a one-month demo. Before the month ends,
  either extend the VPS subscription or migrate to the permanent Hetzner CX23 setup using
  `docker-compose.prod.yml` (which includes Nginx + Certbot for a real domain + Let's Encrypt SSL).
