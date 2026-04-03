# Operator Dashboard

AI-powered command center for solo founders focused on **business growth**. Dark mission-control aesthetic. Claude as the reasoning engine.

Every morning, Claude analyzes your projects, goals, and GitHub commits — then generates prioritized tasks (weighted toward outreach, networking, and content creation), content drafts, market opportunities, and a daily email briefing. Tasks fit your weekly availability schedule automatically.

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

### 3. Install backend + frontend

```bash
bash scripts/setup.sh
```

This installs Python venv + dependencies, npm packages, creates `frontend/.env.local`, and checks for Claude CLI.

Edit `frontend/.env.local` with your display name:

```env
NEXT_PUBLIC_DISPLAY_NAME=@yourhandle
NEXT_PUBLIC_INITIALS=YH
```

### 4. Run

```bash
bash scripts/start.sh
```

Starts both backend (port 8000) and frontend (port 3000) in one terminal. Press `Ctrl+C` to stop both.

Or run manually in two terminals:

```bash
# Terminal 1
cd backend && source .venv/Scripts/activate && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
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
2. Create an n8n account (first-time setup — local to your VPS, not a cloud account)
3. **Enable Gmail API** in Google Cloud Console:
   - Go to https://console.cloud.google.com/apis/library
   - Search "Gmail API" → click **Enable**
4. **Add n8n OAuth redirect URI** in Google Cloud Console:
   - Go to APIs & Credentials → your OAuth client → Authorized redirect URIs
   - Add: `https://n8n.yourdomain.com/rest/oauth2-credential/callback`
   - Save
5. **Create Gmail credential in n8n**:
   - In n8n: Credentials (key icon) → Add Credential → search "Gmail OAuth2"
   - Paste your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (same ones from `.env`)
   - Click **Sign in with Google** → authorize access
6. **Import the workflow**:
   - Workflows → click **+** or Import → Import from File
   - Upload `n8n/daily-operator-briefing.json` from your local machine
7. **Configure the Send Email node**:
   - Open the **Send Email** node (click on it → Open)
   - Replace `CHANGE_ME_TO_YOUR_EMAIL` in the **To** field with your actual email
   - In the **Credential** dropdown at the top, select your Gmail OAuth2 credential
   - The **Message** field should already have `={{ $json.emailHtml }}` — if it's empty, click the expression toggle (fx icon) and paste that
8. **Configure the Schedule Trigger**:
   - Open the **Every Morning 7am** node
   - Set to **Interval** → **Days** → time **07:00** (or whenever you want the email)
   - Don't use raw cron expressions — n8n's validation is strict, use the dropdown
9. **Test it**:
   - Click each node one at a time: **Trigger AI Generate** → Execute step (wait for response)
   - Then **Fetch Dashboard** → Execute step
   - Then **Fetch Drafts** → Execute step
   - Then **Format Briefing** → Execute step
   - Then **Send Email** → Execute step (check your inbox)
10. **Publish the workflow**: Click **Publish** (top right button) — this is required for the schedule to actually run. If it just says "Publish", the workflow is NOT active yet.
11. **Verify it's active**: After publishing, the button should change. Go to **Executions** tab (top center) the next day to confirm it ran.

> **Important**: The workflow will NOT run on schedule unless you click Publish. Just saving is not enough.

> **Note**: If you see "Invalid cron expression" when executing, delete the Schedule Trigger node, add a new one, and use the Interval/Days mode instead of Cron Expression mode.

> **n8n URL**: `https://n8n.yourdomain.com` — bookmark this. You'll need it to check execution logs and update the workflow.

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
| Landing | `/landing` | Marketing page (public) |
| Login | `/login` | Username/password auth with 30-day cookie (public) |
| Signup | `/signup` | Account creation with Local/Cloud toggle (public) |
| Onboarding | `/onboarding` | Add projects + goals, optional LLM paste (public) |
| Pricing | `/pricing` | Plan comparison: Local, Starter, Pro (public) |
| Command Center | `/dashboard` | Priority tasks, goals, projects, suggestions, briefing, AI generate with progress bar |
| Outreach | `/outreach` | Networking, DMs, comment replies, community engagement |
| Content Studio | `/content` | Generate, review, approve/decline/remix drafts (top 8 by hook score) |
| Schedule | `/schedule` | 2-week calendar with daily availability hours, off-day greying, draft blocks |
| Market Intel | `/market` | Growth opportunities, competitors, similar content |
| Analytics | `/analytics` | Scorecard, engagement trend, followers, views, pie chart, radar, heatmap |
| GitHub | `/github` | Auto-discovered repos, active/inactive split, project pipelines |
| Settings | `/settings` | Connections, weekly schedule, change password, delete account |

## Key Endpoints

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/auth/signup` | POST | Create account (with optional Stripe checkout for cloud plans) |
| `/auth/login` | POST | Authenticate and get session token |
| `/ai/generate-all` | POST | One-click: tasks + drafts + schedule + briefing + market scan + social sync + GitHub sync (rate limited) |
| `/ai/generate-tasks` | POST | Claude generates priority tasks that fit today's available hours (rate limited) |
| `/ai/generate-draft` | POST | Claude generates a content draft (topic sanitized, rate limited) |
| `/social/sync` | POST | Pull latest from YouTube, TikTok, Twitter |
| `/github/sync-all` | POST | Auto-discover and sync ALL user repos from GitHub API |
| `/market/scan` | POST | Claude scans for growth opportunities (rate limited) |
| `/content/generate-hooks` | POST | Claude generates 3 hook variations with virality scores |
| `/settings/schedule` | GET/POST | Get/set weekly availability hours per day |
| `/settings/config` | GET | Connection status for all integrations |
| `/settings/change-password` | POST | Change user password |
| `/settings/delete-account` | POST | Delete account and all data |
| `/billing/plans` | GET | Get available subscription plans |
| `/billing/checkout` | POST | Create Stripe checkout session |
| `/onboarding/parse` | POST | Claude extracts projects + goals from free text (rate limited) |

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

## AI Security

All AI calls are protected against prompt injection and token abuse:

- **Prompt injection filtering**: 13 known patterns stripped (case-insensitive): "ignore previous instructions", "you are now", "jailbreak", etc.
- **Rate limiting (two layers)**:
  - CLI level: `AI_MAX_CALLS_PER_HOUR=30` — max Claude subprocess calls
  - API level: `AI_ENDPOINT_LIMIT_PER_HOUR=10` — max endpoint hits per hour
  - Returns `429 Too Many Requests` when exceeded
- **Length caps**: prompts 8K chars, context 12K chars, user topics 500 chars
- **All configurable** via `.env` variables

## Weekly Availability

Users set available hours per day in Settings (sliders, 0-12h per day):

- AI Generate reads today's hours and creates tasks that fit the time budget
- 0 hours = day off, no tasks generated
- Calendar shows "off" badges on unavailable days, hour counts on work days
- Content drafts auto-schedule to next available day (skip off days)
- Example: Mon-Wed 2h (3 light tasks), Thu 0h (off), Fri-Sun 5h (7 tasks)

## Growth-First AI

AI prompts are tuned for business growth, not just development:

- **Tasks**: 2-3 growth tasks (outreach, networking, content) + 1-2 product tasks per day
- **Suggestions**: Must name specific platforms, subreddits, Discord servers — not generic advice
- **Market scan**: Finds communities to join, content gaps, people asking for your solution
- **Briefing**: Growth opportunities, platform changes, competitor moves
- **Content**: Build-in-public, tutorials, customer demos — not technical deep-dives

## Telegram Bot (Growth Mentor)

A personal AI growth mentor that texts you 3x/day on Telegram with contextual advice based on your actual tasks and goals.

### Setup

1. Open **Telegram** → search for **@BotFather** → send `/newbot`
2. Name it (e.g. "Operator Dashboard") and pick a username
3. Copy the **API token** BotFather gives you
4. Open your new bot in Telegram and send it "hi" (so it registers your chat ID)
5. Get your chat ID — the backend logs it, or check: `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Add to your `.env` (or VPS `.env`):
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
7. Restart the backend
8. Set up the Telegram webhook:
   ```
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://api.yourdomain.com/sms/webhook"
   ```
9. Set up cron jobs for daily messages (on VPS):
   ```bash
   # Create the mentor script
   cat > /opt/mentor-cron.sh << 'EOF'
   #!/bin/bash
   TYPE=$1
   curl -s -X POST http://localhost:8000/mentor/send \
     -H 'Content-Type: application/json' \
     -d "{\"type\": \"$TYPE\"}" > /dev/null 2>&1
   EOF
   chmod +x /opt/mentor-cron.sh

   # Add cron jobs (times in UTC — adjust for your timezone)
   # Eastern: 7am=11UTC, 1pm=17UTC, 9pm=01UTC
   crontab -e
   0 11 * * * /opt/mentor-cron.sh morning
   0 17 * * * /opt/mentor-cron.sh midday
   0 1 * * * /opt/mentor-cron.sh evening
   ```

### How It Works

The bot sends 3 messages daily:
- **Morning (7am)**: Top priorities, what to do first
- **Midday (1pm)**: Progress check-in, outreach reminder
- **Evening (9pm)**: Day recap, what to think about for tomorrow

Messages are AI-generated based on your actual task list, goals, and progress — not canned text.

### Replying to the Bot

You can text the bot back:

| You type | What happens |
|----------|-------------|
| `done 1` | Marks task #1 as complete |
| `done 2` | Marks task #2 as complete |
| `add Build landing page` | Creates a new task |
| `tasks` | Lists all pending tasks |
| Anything else | Claude responds as your growth mentor with personalized advice |

The bot reads your current tasks and goals and responds contextually. It can also update your goal progress if you tell it what you accomplished.

## Twilio SMS (Optional Alternative to Telegram)

If you prefer SMS over Telegram. Requires A2P 10DLC registration (takes 1-7 business days).

### Setup

1. Sign up at **https://www.twilio.com/try-twilio**
2. Buy a **local** phone number (not toll-free) — ~$1.15/mo
3. Register for A2P 10DLC:
   - **Messaging → Regulatory Compliance → Brands**: Register your brand ($4 one-time)
   - **Campaigns**: Create a campaign ($15 one-time)
     - Campaign description: "Personal productivity notifications. This app sends the account owner daily task reminders, goal updates, and business growth tips."
     - Sample messages: Use examples of actual mentor messages
     - Privacy Policy URL: `https://yourdomain.com/privacy`
     - Terms URL: `https://yourdomain.com/terms`
     - Opt-in description: "The account owner manually configures their own phone number in the application settings. Only the account holder receives messages."
   - Wait for approval (1-7 business days)
4. Add to `.env`:
   ```env
   TWILIO_SID=ACxxxxxxxxxx
   TWILIO_TOKEN=your_auth_token
   TWILIO_PHONE=+1your_twilio_number
   TWILIO_TO=+1your_personal_number
   ```
5. The backend supports both Telegram and Twilio — Telegram is used by default if configured.

## Claude Credential Auto-Refresh

Claude CLI OAuth tokens expire every ~12-24 hours. On the VPS, a Windows scheduled task on your PC pushes fresh credentials every 6 hours:

- Script: `scripts/auto-refresh-creds.bat`
- Scheduled task: "RefreshClaudeCreds" (runs every 6h when PC is on)
- Manual refresh: `bash scripts/refresh-vps-creds.sh`
- Health check cron on VPS at 6am detects auth failures before the 7am n8n run
- If auth expires overnight (PC off), the mentor bot shows a friendly fallback instead of error messages

To set up the auto-refresh on a new machine:
```powershell
# Create scheduled task (PowerShell)
$action = New-ScheduledTaskAction -Execute 'scripts\auto-refresh-creds.bat'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration (New-TimeSpan -Days 365)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName 'RefreshClaudeCreds' -Action $action -Trigger $trigger -Settings $settings -Force
```

## Instagram Graph API (Optional)

1. Create a **Meta Developer App** at https://developers.facebook.com/
2. Add **Instagram Graph API** product
3. Your Instagram must be a **Business account** (not personal) linked to a **Facebook Page**
4. Go to **App Review → Permissions and Features** and request:
   - `instagram_basic`
   - `instagram_manage_insights`
   - `pages_show_list`
   - `pages_read_engagement`
5. Generate access token via **Tools → Graph API Explorer**
6. Extend to long-lived token (60 days):
   ```
   https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN
   ```
7. Add to `.env`:
   ```env
   INSTAGRAM_ACCESS_TOKEN=your_long_lived_token
   INSTAGRAM_BUSINESS_ID=your_ig_business_id
   ```

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

**Login says "invalid" after VPS rebuild**
- `AUTH_SECRET` must be persistent in `.env` — if missing, password hashes change on restart
- Fix: set `AUTH_SECRET=some_fixed_value` in VPS `.env` and recreate the account

**429 Too Many Requests on AI endpoints**
- Rate limit exceeded — wait an hour or increase `AI_ENDPOINT_LIMIT_PER_HOUR` in `.env`

**New DB column not found after code update**
- SQLAlchemy `create_all` only creates new tables, not columns
- Fix: `ALTER TABLE tablename ADD COLUMN columnname TYPE DEFAULT value` manually

**Data lost after docker rebuild**
- DB must be at `/app/data/operator.db` (mounted volume), not `/data/operator.db`
- Dockerfile should have `ENV DATABASE_URL=sqlite:////app/data/operator.db`
- Remove any `DATABASE_URL` from `.env` on VPS — let the Dockerfile set it

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
