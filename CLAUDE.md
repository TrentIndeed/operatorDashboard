# Operator Dashboard — Claude Code Instructions

## What This Project Is

AI-powered solo founder command center. Dark mission-control UI. Claude CLI as the AI backend — no API keys, uses OAuth from Claude Max subscription.

**Live at**: https://dragonoperator.com (VPS: 5.161.100.230, Hetzner CX11, Ashburn VA)

## Stack

- **Frontend**: `frontend/` — Next.js 16 + TypeScript + Tailwind + shadcn/ui + Recharts + Framer Motion
- **Backend**: `backend/` — FastAPI + SQLite + Claude CLI subprocess calls
- **Automations**: `n8n/` — n8n workflow JSONs (daily email briefing, WhatsApp bot)
- **Deploy**: Docker Compose (backend + frontend + n8n) + Caddy reverse proxy for HTTPS

## Running Locally

```bash
# Backend (from backend/)
uvicorn main:app --reload --port 8000

# Frontend (from frontend/)
npm run dev
```

Login: credentials from `.env` (`DASHBOARD_USER` / `DASHBOARD_PASS`, default `123`/`123`)

## Key Architecture Decisions

### Claude CLI Integration
- All AI calls go through `agents/reasoning.py` → `_call_claude()` → subprocess to `claude` CLI
- Prompts piped via **temp file to stdin** (not `-p` flag) to avoid Windows command-line truncation
- `--output-format json` wraps response in `{"result": "..."}` — we extract the inner `result`
- `--max-turns 3` (not 1) — Claude sometimes uses tools (web search) before responding
- Response parsing: `_extract_json()` handles markdown fences, dict wrappers, and raw JSON
- `encoding="utf-8"` on subprocess to prevent Windows cp1252 mojibake (garbled `â€"` symbols)

### Background Tasks
- **CRITICAL**: FastAPI `BackgroundTasks` cannot use `Depends(get_db)` sessions — the session closes before the task runs
- All background tasks create their own `SessionLocal()` with try/finally/db.close()
- Background task wrappers: `_bg_generate_tasks()`, `_bg_generate_suggestions()`, `_bg_generate_briefing()`, `_bg_scan_market()`, `_bg_sync_github()`, `_bg_generate_draft_and_schedule()`

### AI Generate (`/ai/generate-all`)
- One endpoint triggers everything: tasks, suggestions, 2 content drafts, briefing, market scan, GitHub sync
- Tasks: **replaces** old AI-generated pending tasks (no duplicates). Manual tasks never touched.
- Drafts: scheduled on different days (day_offset=1 for TikTok, day_offset=3 for YouTube)
- Briefing: 5 industry news items generated fresh each time
- Frontend shows bottom progress bar polling each endpoint for results

### Auth
- Login page at `/login` with cookie-based auth (30-day expiry)
- `middleware.ts` redirects unauthenticated users to login
- Backend `/auth/login` validates against `DASHBOARD_USER`/`DASHBOARD_PASS` env vars
- n8n calls backend internally via Docker network (no auth needed)

### VPS Deployment
- Docker Compose: backend, frontend, n8n containers
- Claude credentials mounted into backend container: `~/.claude:/root/.claude:ro` and `~/.claude.json:/root/.claude.json:ro`
- Caddy handles HTTPS with auto Let's Encrypt certs
- Domain: `dragonoperator.com` → frontend, `api.dragonoperator.com` → backend, `n8n.dragonoperator.com` → n8n
- Frontend `NEXT_PUBLIC_*` vars are Docker build args (baked at build time, not runtime)
- n8n timezone set to `America/New_York` via container env vars

## File Map

```
backend/
  main.py              — FastAPI app, seed data, AI endpoints, auth, background task wrappers
  agents/
    reasoning.py        — Core _call_claude(), _extract_json(), reason_json()
    content_drafter.py  — generate_draft(), generate_hooks(), remix, repurpose
    task_prioritizer.py — generate_priority_tasks() (replaces old), generate_suggestions()
    market_intel.py     — scan_market_gaps() (reads projects from DB for context)
    lead_agent.py       — generate_dm_draft(), generate_comment_reply()
  api/
    tasks.py            — CRUD for tasks, goals, suggestions, briefing, command center aggregation
    content.py          — Drafts CRUD, schedule CRUD, hook generation
    analytics.py        — Metrics, content scores, engagement trends
    github_sync.py      — Repo sync via GitHub API (creates own DB sessions for background)
    social_sync.py      — YouTube/TikTok/Twitter sync
    market_intel.py     — Market gaps, competitors, competitor posts
    leads.py            — Lead management, comment replies, waitlist
    google_auth.py      — One-time OAuth flow for YouTube/Gmail refresh token
  services/
    youtube.py          — Fetch videos (filters private/unlisted), channel stats
    tiktok.py           — TikTok session-based scraping
    twitter.py          — Twitter API integration
  db/database.py        — All SQLAlchemy models, SessionLocal, init_db
  models/schemas.py     — Pydantic schemas for all endpoints

frontend/
  middleware.ts         — Auth gate (checks operator_token cookie)
  app/
    login/page.tsx      — Login page with dark theme
    page.tsx            — Home (renders CommandCenterClient)
    CommandCenterClient.tsx — Command center with stat cards, tasks, goals, projects,
                             suggestions, briefing, AI generate with progress bar
    analytics/page.tsx  — Content scorecard (thumbnails, stats below), charts
    stats/page.tsx      — Best performing (same card style as analytics), charts, heatmap
    content/page.tsx    — Content studio (top 8 drafts by hook score), hook generator
    schedule/page.tsx   — Calendar (2-week default, 3-col layout), draft blocks with "needs approval"
    market/page.tsx     — Market gaps, competitors, similar content sidebar
    github/page.tsx     — GitHub repo sync status
    leads/page.tsx      — Lead management
  components/
    layout/Sidebar.tsx  — Client-only render (avoids Dark Reader hydration mismatch),
                          reads NEXT_PUBLIC_* env vars for display name/initials
    dashboard/          — TaskCard, ProjectCard, GoalsPanel, SuggestionsPanel, BriefingPanel, StatCard
  lib/api.ts            — API client with all types and endpoints

n8n/
  daily-operator-briefing.json  — 7am cron → generate-all → fetch data → format → send Gmail
  whatsapp-reply-handler.json   — Webhook → parse command → update tasks → reply
```

## Known Issues / Gotchas

- **YouTube private videos**: Backend filters by `privacyStatus === "public"`. Frontend also filters titles starting with "Private video". If old private videos are in DB, re-sync to clear them.
- **GitHub 404s**: Repos that don't exist under `GITHUB_OWNER` log 404s gracefully — not an error.
- **Engagement rate**: Stored as ratio (0.0645 = 6.45%), NOT percentage. YouTube service was fixed from `* 100` to raw ratio.
- **Seed data**: Generic project names for git. User personalizes via DB (API or dashboard).
- **n8n env vars**: `$env.EMAIL_TO` doesn't work in n8n expressions — hardcode email in the Send Email node after import.
- **n8n cron**: Use Schedule Trigger's "Interval → Days" mode, not raw cron expressions (n8n validation is strict).
- **Dark Reader**: Causes hydration mismatch — Sidebar uses client-only mount pattern to avoid it.

## Design System

- Base: `#0A0A0B`, cards: `elevated-card` / `glass-card`
- Accents: purple `#A855F7`, pink `#EC4899`, cyan `#06B6D4`, amber `#F59E0B`
- Fonts: Inter (body), JetBrains Mono (code)
- Reference: Linear meets Bloomberg Terminal meets Vercel Dashboard
- All pages: no `max-w` constraint — content fills available width
