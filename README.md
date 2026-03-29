# Operator Dashboard

AI-powered command center for solo founders. Dark mission-control aesthetic. Claude as the reasoning engine.

## Prerequisites

- **Node.js 18+** and **npm**
- **Python 3.11+**
- **Claude Code CLI** (handles all AI calls via your Claude Max/Pro subscription)
- **Git**

---

## Local Setup

### 1. Install Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
```

Then authenticate (opens browser):

```bash
claude
```

Log in with your Claude.ai account (Pro or Max subscription). Once authenticated, the CLI stores your OAuth token at `~/.claude/.credentials.json` — **no API key needed**.

```bash
claude --version
```

### 2. Clone and configure environment

```bash
git clone <your-repo-url>
cd operatorDashboard
cp .env.example .env
```

Edit `.env` and fill in your credentials. See [Credentials Setup](#credentials-setup) below.

### 3. Install backend

```bash
cd backend
python -m venv .venv

# Windows (Git Bash / PowerShell)
source .venv/Scripts/activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Install frontend

```bash
cd frontend
npm install
```

### 5. Create frontend local config

Create `frontend/.env.local` (gitignored — this is your personal config):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DISPLAY_NAME=@yourhandle
NEXT_PUBLIC_TAGLINE=solo founder mode
NEXT_PUBLIC_INITIALS=YH
```

### 6. Run

Open **two terminals**:

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/Scripts/activate   # or bin/activate on mac/linux
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** — log in with the credentials from your `.env` (`DASHBOARD_USER` / `DASHBOARD_PASS`, default: `123` / `123`).

API docs at **http://localhost:8000/docs**.

### 7. Connect YouTube (Google OAuth)

1. Make sure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`
2. Start the backend
3. Open **http://localhost:8000/auth/google/login** in your browser
4. Sign in with the Google account that owns your YouTube channel
5. Grant access to "YouTube readonly" permissions
6. The callback saves `GOOGLE_REFRESH_TOKEN` to your `.env` automatically
7. **Restart the backend** so it picks up the new token

After this, clicking "Sync Social" on the Analytics page will pull your YouTube videos.

### 8. Enable Gmail API (for email briefings)

1. Go to **https://console.cloud.google.com/apis/library**
2. Search for **Gmail API** → click **Enable**
3. This uses the same OAuth credentials as YouTube

### 9. First AI Generate

Click **AI Generate** on the Command Center. A progress bar appears at the bottom tracking:
- Priority tasks (5 tasks scored by urgency)
- AI suggestions (5 strategic insights)
- TikTok content draft + auto-schedule
- YouTube content draft + auto-schedule
- Today's briefing (5 industry news items)
- Market gap scan (5 opportunities)
- GitHub repo sync

First run takes ~2 minutes. The progress bar shows each step completing in real time.

### 10. Seed sample data (optional)

```bash
cd backend
python ../scripts/seed_data.py
```

---

## VPS Deployment (Production)

### Recommended VPS

**Hetzner CX22** — $4.35/mo (2 vCPU, 4GB RAM, 40GB SSD)
- Sign up: https://www.hetzner.com/cloud
- Location: **Ashburn, VA** (US East)
- Image: **Ubuntu 24.04**

### 1. Generate SSH key (if you don't have one)

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
cat ~/.ssh/id_ed25519.pub
```

Add the public key in Hetzner during server creation.

### 2. SSH into server and install Docker

```bash
ssh root@YOUR_IP

curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin git
```

### 3. Clone repo

```bash
cd /opt
git clone <your-repo-url> operatorDashboard
cd operatorDashboard
```

### 4. Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in all credentials:
- `GITHUB_TOKEN`, `GITHUB_OWNER`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
- `TIKTOK_SESSION_ID`
- `TWITTER_*` keys
- `DASHBOARD_USER`, `DASHBOARD_PASS` (your login credentials)
- `EMAIL_TO` (for daily email briefing)

Also add these for the frontend build:

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_DISPLAY_NAME=@yourhandle
NEXT_PUBLIC_TAGLINE=solo founder mode
NEXT_PUBLIC_INITIALS=YH
```

### 5. Install Claude CLI and authenticate

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
npm install -g @anthropic-ai/claude-code
claude    # opens URL — paste in browser to authenticate
```

Or copy credentials from your local machine:

```bash
# From your local terminal:
scp ~/.claude/.credentials.json root@YOUR_IP:/root/.claude/.credentials.json
scp ~/.claude.json root@YOUR_IP:/root/.claude.json
```

Verify: `claude -p 'say hello' --max-turns 1`

### 6. Launch everything

```bash
docker compose up -d --build
```

This starts:
- **Backend** on port 8000
- **Frontend** on port 3000
- **n8n** on port 5678

Check logs: `docker compose logs -f`

### 7. Buy a domain (optional but recommended)

Buy a domain from **Cloudflare** (~$10/year for .com).

Add 3 DNS A records pointing to your VPS IP:

| Type | Name | Content |
|------|------|---------|
| A | `@` | `YOUR_VPS_IP` |
| A | `api` | `YOUR_VPS_IP` |
| A | `n8n` | `YOUR_VPS_IP` |

**Turn proxy OFF** (grey cloud) for all three.

### 8. Install Caddy for automatic HTTPS

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy
```

Create `/etc/caddy/Caddyfile`:

```
yourdomain.com {
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

Caddy automatically gets HTTPS certificates from Let's Encrypt.

### 9. Set up n8n automation

1. Open `https://n8n.yourdomain.com`
2. Create an n8n account (local to your VPS)
3. Import workflow: **Workflows → Import from File** → upload `n8n/daily-operator-briefing.json`
4. Open the **Send Email** node → replace `CHANGE_ME_TO_YOUR_EMAIL` with your email
5. Set up **Gmail OAuth2** credential in n8n:
   - Go to Credentials → Add → Gmail OAuth2
   - Use same Client ID / Client Secret from your `.env`
   - First add redirect URI in Google Cloud Console: `https://n8n.yourdomain.com/rest/oauth2-credential/callback`
   - Then click **Sign in with Google** in n8n
6. Enable **Gmail API** in Google Cloud Console if not already done
7. Select the Gmail credential in the Send Email node
8. Set the **Schedule Trigger** to your preferred time (e.g. every day at 7am)
9. Save and activate the workflow

### 10. Update Google OAuth redirect URIs

In **Google Cloud Console → APIs & Credentials → Your OAuth Client**, add these redirect URIs:

```
http://localhost:8000/auth/google/callback
https://n8n.yourdomain.com/rest/oauth2-credential/callback
```

### 11. Set n8n timezone

Update your VPS `.env` to include:

```env
N8N_WEBHOOK_URL=https://n8n.yourdomain.com
```

Then restart: `cd /opt/operatorDashboard && docker compose up -d n8n`

---

## Credentials Setup

### Dashboard Login

Set in `.env`:
```env
DASHBOARD_USER=123
DASHBOARD_PASS=123
```

Change to whatever you want. The login page uses cookies that last 30 days.

### GitHub Token

1. Go to **https://github.com/settings/tokens** → Generate new token (classic)
2. Select scope: `repo` (full control — needed for private repos)
3. Copy the token

```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=YourGitHubUsername
```

### Google Cloud (YouTube + Gmail)

1. Go to **https://console.cloud.google.com/** → Create a new project
2. Enable **YouTube Data API v3**: APIs & Services → Library → search → Enable
3. Enable **Gmail API**: APIs & Services → Library → search → Enable
4. Create **OAuth 2.0 credentials**:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Web application**
   - Authorized redirect URIs:
     - `http://localhost:8000/auth/google/callback`
     - `https://n8n.yourdomain.com/rest/oauth2-credential/callback` (if using VPS)
   - Copy Client ID and Client Secret
5. Configure **OAuth consent screen**:
   - User type: External
   - Add your email as a test user
   - Add scopes: `youtube.readonly`, `yt-analytics.readonly`, `gmail.send`

```env
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret
YOUTUBE_CLIENT_ID=your_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-your_secret
```

Then run the YouTube OAuth flow to get `GOOGLE_REFRESH_TOKEN`.

### TikTok Session Cookie

1. Open **https://www.tiktok.com** and log in
2. DevTools (F12) → Application → Cookies → `https://www.tiktok.com`
3. Copy the `sessionid` cookie value

```env
TIKTOK_SESSION_ID=your_session_cookie_value
```

> Expires periodically — re-copy when TikTok sync stops working.

### Twitter/X API

1. Go to **https://developer.x.com/en/portal/dashboard**
2. Create a project and app
3. Copy keys:

```env
TWITTER_CONSUMER_KEY=your_consumer_key
TWITTER_CONSUMER_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
```

---

## Personalizing Your Dashboard

Personal config lives in **gitignored files** so it never gets committed:

| What | Where | Example |
|------|-------|---------|
| API keys & credentials | `.env` | GitHub token, Google OAuth, etc. |
| Login credentials | `.env` | `DASHBOARD_USER=myname`, `DASHBOARD_PASS=mypass` |
| Display name in sidebar | `frontend/.env.local` | `NEXT_PUBLIC_DISPLAY_NAME=@yourhandle` |
| Initials avatar | `frontend/.env.local` | `NEXT_PUBLIC_INITIALS=YH` |
| Projects & goals | Dashboard UI or API | Edit via `/projects/` endpoint |
| n8n email recipient | n8n UI | Set in Send Email node |

On VPS, the frontend env vars go in `.env` (used as Docker build args):
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_DISPLAY_NAME=@yourhandle
NEXT_PUBLIC_INITIALS=YH
```

---

## How AI Works

```
Frontend (Next.js)
  └── API call to FastAPI backend
        └── agents/reasoning.py
              └── stdin pipe to Claude CLI
                    └── Claude Code CLI (handles OAuth)
                          └── Anthropic API
```

Prompts are piped via temp files to avoid Windows command-line limits. Responses parsed with fallback JSON extraction for markdown-wrapped responses.

**Models:** `claude-sonnet-4-6` (default, fast) · `claude-opus-4-6` (deep reasoning)

---

## Architecture

```
operatorDashboard/
├── frontend/           Next.js + TypeScript + Tailwind + shadcn/ui
│   ├── app/            Pages (command center, analytics, content, etc.)
│   ├── components/     Reusable UI components
│   ├── lib/            API client + types
│   └── middleware.ts   Auth gate (redirects to /login)
├── backend/            FastAPI + SQLite + Claude CLI
│   ├── api/            REST routers
│   ├── agents/         AI agents (task prioritizer, content drafter,
│   │                   market intel, lead agent, reasoning core)
│   ├── services/       Social integrations (youtube, tiktok, twitter)
│   ├── db/             SQLAlchemy models + SQLite
│   └── models/         Pydantic schemas
├── n8n/                n8n workflow JSON configs
│   ├── daily-operator-briefing.json
│   └── whatsapp-reply-handler.json
├── docker-compose.yml  One-command deploy (backend + frontend + n8n)
├── DEPLOY.md           Detailed VPS deployment guide
├── data/               SQLite database (gitignored)
└── .env                Credentials (gitignored)
```

## Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | Username/password auth with 30-day cookie |
| Command Center | `/` | Priority tasks, projects, goals, AI suggestions, daily briefing |
| Content Studio | `/content` | Generate, review, approve/decline/remix content drafts (top 8 by hook score) |
| Analytics | `/analytics` | Content scorecard with thumbnails, engagement trends, follower growth |
| Stats | `/stats` | Best performing content, engagement breakdown, platform radar, posting heatmap |
| Schedule | `/schedule` | 2-week/week/month calendar with content blocks + drafts needing approval |
| Market Intel | `/market` | Market gaps, competitor tracking, similar content with thumbnails |
| Leads & Outreach | `/leads` | Leads, comment replies, waitlist signups |
| GitHub Progress | `/github` | Repository sync, commit history, project pipeline |

## Key Endpoints

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/auth/login` | POST | Authenticate and get session token |
| `/ai/generate-all` | POST | One-click: tasks + drafts + schedule + briefing + market scan + GitHub sync |
| `/ai/generate-tasks` | POST | Claude generates 5 priority tasks (replaces old AI tasks) |
| `/ai/generate-draft` | POST | Claude generates a content draft |
| `/social/sync` | POST | Pull latest from YouTube, TikTok, Twitter |
| `/github/sync-all` | POST | Sync all tracked GitHub repos |
| `/market/scan` | POST | Claude scans for market gap opportunities |
| `/content/generate-hooks` | POST | Claude generates 3 hook variations with virality scores |

---

## Daily Automation (n8n)

When set up, the **Daily Operator Briefing** workflow runs every morning:

1. Triggers `/ai/generate-all` — Claude generates fresh tasks, drafts, market gaps
2. Waits 3 minutes for Claude to finish
3. Fetches command center data + content drafts
4. Sends you a styled HTML email with:
   - **Today's Game Plan** — top 3 tasks with why they matter
   - **All Priority Tasks** — full table with scores and time estimates
   - **Content Drafts** — titles, hooks, body previews, platform badges
   - **Weekly & Monthly Goals** — progress tracking
   - **AI Suggestions** — top 3 actionable insights
   - **Industry News** — relevant headlines
   - **Blockers** — highlighted if any projects are stuck

## WhatsApp Commands (optional, requires Meta Business API)

| Command | What it does |
|---------|-------------|
| `done 1` | Mark task #1 as complete |
| `add Build landing page` | Add a new task |
| `tasks` | List all pending tasks |

---

## Troubleshooting

**"Claude CLI not found"**
- `npm install -g @anthropic-ai/claude-code`
- On Windows: verify at `%APPDATA%\npm\claude.cmd`

**"Not logged in" in backend logs**
- On VPS: mount Claude credentials into Docker container (see docker-compose volumes)
- Verify: `docker exec operatordashboard-backend-1 claude -p 'say hello' --max-turns 1`

**AI Generate does nothing / tasks don't appear**
- Check backend logs: `docker compose logs -f backend`
- Look for `[Claude]` and `[AI]` lines
- Claude calls take 30-120 seconds each

**YouTube sync fails**
- Check `GOOGLE_REFRESH_TOKEN` in `.env`
- Re-run OAuth: `http://localhost:8000/auth/google/login`
- Restart backend after token is saved

**TikTok sync fails**
- Session cookie expires — re-copy from browser DevTools

**GitHub repos 404**
- Only repos under your `GITHUB_OWNER` account sync
- Private repos need `repo` scope on your GitHub token

**Private YouTube videos showing**
- Click "Sync Social" — backend filters out private/unlisted videos

**n8n "Invalid cron expression"**
- Use the Schedule Trigger's **Interval** mode instead of raw cron
- Set to "Every Day" at your preferred time

**n8n Gmail "Forbidden"**
- Enable Gmail API: https://console.cloud.google.com/apis/library → Gmail API → Enable

**Garbled text (â€" symbols)**
- Backend encoding issue — restart backend to pick up UTF-8 fix

**Hydration mismatch errors in browser**
- Caused by Dark Reader browser extension — disable for your dashboard URL

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

# Check container status
docker compose ps
```
