# Operator Dashboard

AI-powered command center for solo founders. Dark mission-control aesthetic. Claude as the reasoning engine.

## Prerequisites

- **Node.js 18+** and **npm**
- **Python 3.11+**
- **Claude Code CLI** (handles all AI calls via your Claude Max/Pro subscription)
- **Git**

## Setup

### 1. Install Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
```

Then authenticate (opens browser):

```bash
claude
```

Log in with your Claude.ai account (Pro or Max subscription). Once authenticated, the CLI stores your OAuth token at `~/.claude/.credentials.json` and all AI calls go through it automatically — **no API key needed**.

Verify it's working:

```bash
claude --version
```

### 2. Clone and configure environment

```bash
git clone <your-repo-url>
cd operatorDashboard
cp .env.example .env
```

Edit `.env` and fill in the credentials you need. See the [Credentials Setup](#credentials-setup) section below for how to get each one.

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

### 5. Run

Open **two terminals**:

**Terminal 1 — Backend (from repo root):**
```bash
cd backend
source .venv/Scripts/activate   # or bin/activate on mac/linux
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend (from repo root):**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** — you should see the Command Center.

API docs at **http://localhost:8000/docs**.

### 6. Connect YouTube (Google OAuth)

This is a one-time flow to get a refresh token for YouTube data sync:

1. Make sure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env` (see [Google Cloud Setup](#google-cloud-youtube) below)
2. Start the backend (`uvicorn main:app --reload --port 8000`)
3. Open **http://localhost:8000/auth/google/login** in your browser
4. Sign in with the Google account that owns your YouTube channel
5. Grant access to "YouTube readonly" permissions
6. The callback saves `GOOGLE_REFRESH_TOKEN` to your `.env` automatically
7. **Restart the backend** so it picks up the new token

After this, clicking "Sync Social" on the Analytics page will pull your YouTube videos, thumbnails, view counts, and channel stats.

### 7. Seed sample data (optional)

```bash
cd backend
python ../scripts/seed_data.py
```

Populates today's news briefing with realistic items for the Command Center.

### 8. First AI Generate

Once everything is running, click **AI Generate** on the Command Center. This triggers:
- Claude generates 5 priority tasks scored by urgency
- Claude generates 5 strategic AI suggestions
- Claude creates a TikTok content draft and schedules it
- Claude creates a YouTube content draft and schedules it
- Claude scans for 5 market gap opportunities
- GitHub repos are synced

The first run takes ~2 minutes (multiple Claude CLI calls). Subsequent runs are faster.

---

## Credentials Setup

### GitHub Token

1. Go to **https://github.com/settings/tokens** → Generate new token (classic)
2. Select scope: `repo` (full control of private repos)
3. Copy the token

```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=YourGitHubUsername
```

### Google Cloud (YouTube)

1. Go to **https://console.cloud.google.com/** → Create a new project (or use existing)
2. Enable the **YouTube Data API v3**:
   - APIs & Services → Library → search "YouTube Data API v3" → Enable
3. Create **OAuth 2.0 credentials**:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Web application**
   - Authorized redirect URIs: add `http://localhost:8000/auth/google/callback`
   - Copy the Client ID and Client Secret
4. Configure the **OAuth consent screen**:
   - APIs & Services → OAuth consent screen
   - User type: External (or Internal if using Google Workspace)
   - Add your email as a test user
   - Add scopes: `youtube.readonly`, `yt-analytics.readonly`

```env
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret
YOUTUBE_CLIENT_ID=your_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-your_secret
```

Then run the OAuth flow (Step 6 above) to get `GOOGLE_REFRESH_TOKEN`.

### TikTok Session Cookie

TikTok doesn't have a public API for personal accounts. We use the session cookie:

1. Open **https://www.tiktok.com** in your browser and log in
2. Open DevTools (F12) → Application → Cookies → `https://www.tiktok.com`
3. Find the cookie named `sessionid` (or `sessionid_ss`)
4. Copy its value

```env
TIKTOK_SESSION_ID=your_session_cookie_value
```

> **Note:** This cookie expires periodically. You'll need to re-copy it when TikTok sync stops working.

### Twitter/X API

1. Go to **https://developer.x.com/en/portal/dashboard**
2. Create a project and app (Free tier works for read-only)
3. Under your app → Keys and tokens:
   - Copy **Consumer Key** and **Consumer Secret** (API Key / API Key Secret)
   - Generate **Access Token and Secret** (with read permissions)

```env
TWITTER_CONSUMER_KEY=your_consumer_key
TWITTER_CONSUMER_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
```

Optional (for OAuth 2.0 flow):
```env
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
```

---

## How AI Works

The backend does **not** call the Anthropic API directly. It shells out to the `claude` CLI, which handles OAuth using your Claude Max subscription.

```
Frontend (Next.js)
  └── API call to FastAPI backend
        └── agents/reasoning.py
              └── subprocess: claude --model claude-sonnet-4-6 --output-format json
                    └── Claude Code CLI (handles OAuth)
                          └── Anthropic API
```

The prompt is piped via stdin (temp file) to avoid Windows command-line length limits. Responses are parsed from JSON, with fallback extraction for markdown-wrapped responses.

**Models used:**
- `claude-sonnet-4-6` — fast tasks, content drafts, market scans (default)
- `claude-opus-4-6` — deep reasoning, complex analysis (available but not default)

---

## Architecture

```
operatorDashboard/
├── frontend/           Next.js 14 + TypeScript + Tailwind + shadcn/ui
│   ├── app/            Page routes (command center, analytics, content, etc.)
│   ├── components/     Reusable UI components
│   └── lib/            API client + types
├── backend/            FastAPI + SQLite + Claude CLI gateway
│   ├── api/            REST routers (tasks, content, analytics, github, etc.)
│   ├── agents/         Claude AI agents (task prioritizer, content drafter,
│   │                   market intel, lead agent, reasoning core)
│   ├── services/       Social media integrations (youtube, tiktok, twitter)
│   ├── db/             SQLAlchemy ORM models + SQLite
│   └── models/         Pydantic request/response schemas
├── scripts/            Setup and seed scripts
├── data/               SQLite database (gitignored)
└── .env                Credentials (gitignored)
```

## Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| Command Center | `/` | Priority tasks, projects, goals, AI suggestions, daily briefing |
| Content Studio | `/content` | Generate, review, approve/decline/remix content drafts |
| Analytics | `/analytics` | Content scorecard with thumbnails, engagement trends, follower growth |
| Stats | `/stats` | Best performing content, engagement breakdown, platform comparison, posting heatmap |
| Schedule | `/schedule` | Calendar with scheduled content blocks + draft content needing approval |
| Market Intel | `/market` | Market gaps, competitor tracking with thumbnails, your content performance |
| Leads & Outreach | `/leads` | Leads, comment replies, waitlist signups |
| GitHub Progress | `/github` | Repository sync, commit history, project pipeline |

## Key Endpoints

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/ai/generate-all` | POST | One-click: tasks + drafts + schedule + market scan + GitHub sync |
| `/ai/generate-tasks` | POST | Claude generates 5 priority tasks |
| `/ai/generate-draft` | POST | Claude generates a content draft |
| `/social/sync` | POST | Pull latest from YouTube, TikTok, Twitter |
| `/github/sync-all` | POST | Sync all tracked GitHub repos |
| `/market/scan` | POST | Claude scans for market gap opportunities |
| `/content/generate-hooks` | POST | Claude generates 3 hook variations with virality scores |

Full API docs: **http://localhost:8000/docs**

---

## Troubleshooting

**"Claude CLI not found"**
- Make sure `claude` is installed globally: `npm install -g @anthropic-ai/claude-code`
- On Windows, verify it's at `%APPDATA%\npm\claude.cmd`
- Run `claude --version` to confirm

**AI Generate does nothing / tasks don't appear**
- Check the backend terminal for `[Claude]` and `[AI]` log lines
- Claude CLI calls take 30-120 seconds each — wait for them to complete
- The frontend polls every 5 seconds after triggering generate-all

**YouTube sync fails**
- Make sure `GOOGLE_REFRESH_TOKEN` is set in `.env`
- If expired, re-run the OAuth flow: http://localhost:8000/auth/google/login
- Restart the backend after the token is saved

**TikTok sync fails**
- The session cookie expires periodically — re-copy from browser DevTools
- Check `TIKTOK_SESSION_ID` in `.env`

**GitHub repos show 404**
- Only repos that exist under your `GITHUB_OWNER` account will sync
- Projects with non-existent repos log 404s gracefully — this is normal

**Private YouTube videos showing**
- Click "Sync Social" again — the backend now filters out private/unlisted videos
- Existing private videos in the DB will be filtered on the frontend

**Projects show progress on unconnected repos**
- Projects only show progress after a successful GitHub sync
- Projects without a synced repo show "N/A" for progress
