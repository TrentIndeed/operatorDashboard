# Deploying Operator Dashboard + n8n on a VPS

## Recommended VPS

**Hetzner CX22** — best value for this stack:
- 2 vCPU, 4 GB RAM, 40 GB SSD
- **$4.35/mo** (Ashburn or Hillsboro datacenter for US)
- Sign up: https://www.hetzner.com/cloud

Alternatives:
| Provider | Plan | Specs | Price |
|----------|------|-------|-------|
| **Hetzner CX22** | Cloud | 2 vCPU / 4GB / 40GB | $4.35/mo |
| DigitalOcean | Basic Droplet | 2 vCPU / 2GB / 50GB | $12/mo |
| Vultr | Cloud Compute | 2 vCPU / 2GB / 50GB | $12/mo |
| Railway | Starter | Auto-scaled | ~$5-10/mo |

Hetzner is the clear winner on price. 4GB RAM is enough to run the dashboard + n8n + Claude CLI comfortably.

## Setup Steps

### 1. Create VPS

1. Sign up at hetzner.com/cloud
2. Create a new server:
   - Location: Ashburn (US East) or Hillsboro (US West)
   - Image: **Ubuntu 24.04**
   - Type: **CX22** (Shared vCPU, 2 vCPU, 4GB RAM)
   - SSH Key: Add your public key
3. Note the IP address

### 2. SSH In and Install Docker

```bash
ssh root@YOUR_IP

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

### 3. Clone Your Repo

```bash
cd /opt
git clone <your-repo-url> operatorDashboard
cd operatorDashboard
```

### 4. Configure Environment

```bash
cp .env.example .env
nano .env
```

Fill in all your credentials:
- `GITHUB_TOKEN`, `GITHUB_OWNER`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
- `TIKTOK_SESSION_ID`
- `TWITTER_*` keys
- `EMAIL_TO` (your email for daily briefing)
- `WHATSAPP_PHONE_ID`, `WHATSAPP_TO`, `WHATSAPP_ACCESS_TOKEN`
- `N8N_USER`, `N8N_PASSWORD` (change from defaults!)

Also create the frontend env:
```bash
mkdir -p frontend
cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DISPLAY_NAME=@yourhandle
NEXT_PUBLIC_TAGLINE=solo founder mode
NEXT_PUBLIC_INITIALS=YH
EOF
```

### 5. Install Claude CLI and Authenticate

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Install Claude CLI
npm install -g @anthropic-ai/claude-code

# Authenticate (opens a URL — copy it to your browser)
claude

# Verify
claude --version
```

### 6. Launch Everything

```bash
docker compose up -d
```

This starts:
- **Backend** on port 8000
- **Frontend** on port 3000
- **n8n** on port 5678

Check logs:
```bash
docker compose logs -f
```

### 7. Set Up n8n Workflows

1. Open `http://YOUR_IP:5678`
2. Log in with your `N8N_USER`/`N8N_PASSWORD`
3. Import workflows:
   - Go to Workflows → Import from File
   - Import `n8n/daily-operator-briefing.json`
   - Import `n8n/whatsapp-reply-handler.json`
4. Configure credentials in n8n:
   - **Gmail**: OAuth2 connection for sending emails
   - **WhatsApp Business**: API token from Meta Business Suite
5. Activate both workflows

### 8. Set Up WhatsApp Business API

1. Go to https://developers.facebook.com/
2. Create a Meta App → Add WhatsApp product
3. In WhatsApp → Getting Started:
   - Note your **Phone Number ID**
   - Generate a **Permanent Access Token**
4. Set up the webhook:
   - Callback URL: `http://YOUR_IP:5678/webhook/whatsapp-webhook`
   - Verify token: (set in n8n webhook node)
   - Subscribe to: `messages`
5. Add your phone number as a test number

### 9. Set Up Domain + HTTPS (Optional but Recommended)

```bash
# Install Caddy (auto-HTTPS reverse proxy)
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy
```

Create `/etc/caddy/Caddyfile`:
```
dashboard.yourdomain.com {
    reverse_proxy localhost:3000
}

api.yourdomain.com {
    reverse_proxy localhost:8000
}

n8n.yourdomain.com {
    reverse_proxy localhost:5678
}
```

```bash
systemctl restart caddy
```

Point your DNS A records to your VPS IP.

## WhatsApp Commands

Once running, you can text your WhatsApp number:

| Command | What it does |
|---------|-------------|
| `done 1` | Mark task #1 as complete |
| `done 2` | Mark task #2 as complete |
| `add Build landing page` | Add a new task |
| `focus Ship the MVP` | Same as add |
| `tasks` | List all pending tasks |
| `status` | Get current dashboard status |

## Daily Flow

**7:00 AM** — n8n triggers automatically:
1. Calls `/ai/generate-all` → Claude generates tasks, drafts, market gaps
2. Waits 3 minutes for Claude to finish
3. Fetches all dashboard data
4. Sends you a formatted **email** with full briefing
5. Sends you a **WhatsApp** with your top 3 focus items

**Throughout the day** — Text back on WhatsApp to update tasks

## Maintenance

```bash
# View logs
docker compose logs -f

# Restart everything
docker compose restart

# Update code
cd /opt/operatorDashboard
git pull
docker compose up -d --build

# n8n data persists in a Docker volume
docker volume ls
```
