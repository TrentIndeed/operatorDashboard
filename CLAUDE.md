# Operator Dashboard — Claude Code Instructions

## What This Project Is

AI-powered solo founder command center focused on **business growth**. Dark mission-control UI. Claude CLI as the AI backend — no API keys, uses OAuth from Claude Max subscription.

**Live at**: https://dragonoperator.com (VPS: 5.161.100.230, Hetzner CX11, Ashburn VA)

## Stack

- **Frontend**: `frontend/` — Next.js 16 + TypeScript + Tailwind + shadcn/ui + Recharts + Framer Motion
- **Backend**: `backend/` — FastAPI + SQLite + Claude CLI subprocess calls
- **Automations**: `n8n/` — n8n workflow JSONs (daily email briefing, WhatsApp bot)
- **Infra**: `backend/services/infra/` — Stripe billing, Hetzner provisioning, deploy pipeline (reusable)
- **Deploy**: Docker Compose (backend + frontend + n8n) + Caddy reverse proxy for HTTPS

## Running Locally

```bash
bash scripts/setup.sh   # install backend + frontend
bash scripts/start.sh   # start both
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
- When Claude hits max-turns, returns metadata envelope with no `result` — detect `subtype: "error_max_turns"`

### AI Security
- **Prompt injection filtering**: 13 known patterns stripped case-insensitively
- **Rate limiting**: `AI_MAX_CALLS_PER_HOUR=30` (CLI level), `AI_ENDPOINT_LIMIT_PER_HOUR=10` (API level)
- **Length caps**: prompts 8K chars, context 12K chars, user topics 500 chars, onboarding paste 5K chars
- **429 response** when limits exceeded

### Background Tasks
- **CRITICAL**: FastAPI `BackgroundTasks` cannot use `Depends(get_db)` sessions — the session closes before the task runs
- All background tasks create their own `SessionLocal()` with try/finally/db.close()
- Background task wrappers: `_bg_generate_tasks()`, `_bg_generate_suggestions()`, `_bg_generate_briefing()`, `_bg_scan_market()`, `_bg_sync_github()`, `_bg_sync_social()`, `_bg_generate_draft_and_schedule()`

### AI Generate (`/ai/generate-all`)
- One endpoint triggers everything: tasks, suggestions, 2 content drafts, briefing, market scan, GitHub sync, social sync
- Tasks: **replaces** old AI-generated pending tasks (no duplicates). Manual tasks never touched.
- Tasks respect **weekly availability** — reads user's per-day hours, generates tasks that fit the time budget. 0 hours = no tasks (day off).
- Drafts: scheduled on next available day (skips off days), one per platform
- Briefing: 5 items — 2 growth opportunities, 1 competitor, 1 platform change, 1 industry
- Market scan: finds communities to join, content gaps, outreach opportunities
- Project stages auto-update by analyzing last 10 GitHub commits via Claude
- Social media (YouTube/TikTok/Twitter) syncs automatically

### AI Prompts — Growth-First Philosophy
- System prompt prioritizes GROWTH over development: "distribution > development"
- Tasks mix: 2-3 growth tasks (outreach, networking, content), 1-2 product tasks, 0-1 admin
- Suggestions must name specific platforms/communities — not generic advice
- Categories: outreach, content, growth, market (not product-centric)
- Content drafts focus on build-in-public, tutorials, and customer-facing demos

### Auth
- Login page at `/login` with cookie-based auth (30-day expiry)
- `middleware.ts` redirects unauthenticated users to `/landing`
- Backend `/auth/login` and `/auth/signup` with User table in DB
- `AUTH_SECRET` must be persistent in `.env` — random generation on restart invalidates all password hashes
- n8n calls backend internally via Docker network (no auth needed)

### VPS Deployment
- Docker Compose: backend, frontend, n8n containers
- Claude credentials mounted into backend container: `~/.claude:/root/.claude:ro` and `~/.claude.json:/root/.claude.json:ro`
- `DATABASE_URL` hardcoded in Dockerfile as `sqlite:////app/data/operator.db` — `.env` value was being overridden
- `./data:/app/data` volume mount ensures DB survives container rebuilds
- `.env.vps` file for VPS-specific overrides that don't get clobbered when copying local `.env`
- Caddy handles HTTPS with auto Let's Encrypt certs
- Domain: `dragonoperator.com` → frontend, `api.dragonoperator.com` → backend, `n8n.dragonoperator.com` → n8n
- Frontend `NEXT_PUBLIC_*` vars are Docker build args (baked at build time, not runtime)
- n8n timezone set to `America/New_York` via container env vars
- Claude creds expire periodically — `scripts/refresh-vps-creds.sh` pushes fresh ones from local machine
- Health check cron at 6am detects auth failures before the 7am n8n run

## File Map

```
backend/
  main.py              — FastAPI app, seed data, AI endpoints, auth, background task wrappers,
                         rate limiting, onboarding parse
  agents/
    reasoning.py        — Core _call_claude(), _extract_json(), reason_json(),
                         _sanitize_prompt(), _check_rate_limit()
    content_drafter.py  — generate_draft(), generate_hooks(), remix, repurpose
    task_prioritizer.py — generate_priority_tasks() (replaces old, respects schedule),
                         generate_suggestions()
    market_intel.py     — scan_market_gaps() (reads projects from DB, finds growth opportunities)
    lead_agent.py       — generate_dm_draft(), generate_comment_reply()
  api/
    tasks.py            — CRUD for tasks, goals, suggestions, briefing, command center aggregation
    content.py          — Drafts CRUD, schedule CRUD, hook generation
    analytics.py        — Metrics, content scores, engagement trends
    github_sync.py      — Auto-discover ALL user repos via GitHub API, sync, background wrapper
    social_sync.py      — YouTube/TikTok/Twitter sync
    market_intel.py     — Market gaps, competitors, competitor posts
    leads.py            — Lead management, comment replies, waitlist
    settings.py         — Change password, delete account, weekly schedule, config status
    billing.py          — Stripe checkout, webhooks, customer portal, auto-provisioning
    google_auth.py      — One-time OAuth flow for YouTube/Gmail refresh token
  services/
    youtube.py          — Fetch videos (filters private/unlisted), channel stats
    tiktok.py           — TikTok session-based scraping
    twitter.py          — Twitter API integration
    infra/
      billing.py        — Stripe: create customer, checkout, portal, webhooks (reusable)
      provisioning.py   — Hetzner API: create/destroy/monitor VPS (reusable)
      deploy.py         — SSH + Docker deploy to user VPS (reusable)
  db/database.py        — All SQLAlchemy models (incl User with weekly_hours), SessionLocal, init_db
  models/schemas.py     — Pydantic schemas for all endpoints
  tests/
    test_ai_generate.py — Integration test: AI Generate fills all tabs (requires Claude CLI)
    test_connections.py — Unit tests: auth, CRUD, persistence, all endpoints (no Claude needed)

frontend/
  middleware.ts         — Auth gate (checks operator_token cookie)
  app/
    landing/page.tsx    — Marketing landing page (public)
    login/page.tsx      — Login page with dark theme (public)
    signup/page.tsx     — Signup with Local/Cloud toggle (public)
    onboarding/page.tsx — Projects + goals setup, optional LLM paste (public)
    pricing/page.tsx    — Plan comparison: Local, Starter, Pro (public)
    page.tsx            — Root redirect (→ landing or dashboard)
    (dashboard)/        — Route group with sidebar layout (protected)
      layout.tsx        — Sidebar wrapper
      CommandCenterClient.tsx — Command center with stat cards, tasks, goals, projects,
                               suggestions, briefing, AI generate with progress bar
      dashboard/page.tsx     — Renders CommandCenterClient
      outreach/page.tsx      — Networking & outreach (renamed from leads)
      content/page.tsx       — Content studio (top 8 drafts by hook score), hook generator
      schedule/page.tsx      — Calendar (2-week default, 5-col layout), availability hours,
                               off-day greying, draft blocks with "needs approval"
      analytics/page.tsx     — Content scorecard, engagement trend, followers, views,
                               engagement pie, platform radar, posting heatmap (merged stats)
      market/page.tsx        — Market gaps, competitors, similar content sidebar
      github/page.tsx        — Auto-discovered repos, active/inactive split, project pipelines
      settings/page.tsx      — Connections status, weekly schedule sliders, env var guide,
                               change password, delete account
  components/
    layout/Sidebar.tsx  — Client-only render (avoids Dark Reader hydration mismatch),
                          reads NEXT_PUBLIC_* env vars, mobile hamburger menu, logout button
    dashboard/          — TaskCard (auto-color tags), ProjectCard, GoalsPanel,
                         SuggestionsPanel (title/subtitle split), BriefingPanel, StatCard

n8n/
  daily-operator-briefing.json  — Schedule → generate-all → fetch all data → format HTML email
                                  with game plan, tasks, full drafts, schedule, market gaps,
                                  GitHub repos, goals, suggestions, news → Send Gmail
  whatsapp-reply-handler.json   — Webhook → parse command → update tasks → reply

scripts/
  setup.sh              — Install backend venv + frontend npm + create .env
  start.sh              — Start both backend + frontend in one terminal
  refresh-vps-creds.sh  — Push local Claude creds to VPS + restart backend
  seed_data.py          — Optional sample briefing data

docker-compose.yml      — Backend + frontend + n8n with volume mounts + env files
DEPLOY.md               — Full VPS deployment guide
```

## Known Issues / Gotchas

- **Windows cp1252 encoding**: Always use `encoding="utf-8"` on subprocess calls or em dashes become mojibake
- **BackgroundTasks + Depends(get_db)**: Session closes before task runs. Create own SessionLocal().
- **SQLite path in Docker**: Relative paths resolve differently. Hardcode absolute path in Dockerfile ENV.
- **Claude CLI `--max-turns 1`**: Fails when Claude uses web search. Use 3.
- **`--output-format json` empty result**: Returns metadata envelope on max-turns. Check `subtype`.
- **n8n `$env` variables**: Don't work in expressions. Hardcode values in nodes after import.
- **AUTH_SECRET must be persistent**: Random generation on restart invalidates all password hashes.
- **Next.js NEXT_PUBLIC_* vars**: Baked at build time. Must be Docker build args.
- **`.env` copy overwrites VPS vars**: Use `.env.vps` as second env_file layer.
- **Dark Reader hydration**: Sidebar uses client-only mount pattern to avoid mismatch.
- **YouTube private videos**: Backend filters by `privacyStatus === "public"`. Frontend also filters titles starting with "Private video".
- **Engagement rate**: Stored as ratio (0.0645 = 6.45%), NOT percentage.
- **n8n cron**: Use Schedule Trigger's "Interval → Days" mode, not raw cron expressions.
- **n8n workflow must be Published**: Just saving doesn't activate the schedule.
- **GitHub auto-discover**: Syncs ALL user repos via API, splits into active (14 days) and inactive.
- **New DB columns**: SQLAlchemy `create_all` only creates new tables, not columns. Use `ALTER TABLE` manually on existing DBs.
- **Content draft dedup**: `_bg_generate_draft_and_schedule` deletes old AI drafts for the same platform before creating new ones.
- **Schedule skips off days**: Draft scheduling walks forward to find next available day from user's weekly hours.

## Design System

- Base: `#0A0A0B`, cards: `elevated-card` / `glass-card`
- Accents: purple `#A855F7`, pink `#EC4899`, cyan `#06B6D4`, amber `#F59E0B`
- Fonts: Inter (body), JetBrains Mono (code)
- Reference: Linear meets Bloomberg Terminal meets Vercel Dashboard
- All pages: no `max-w` constraint — content fills available width
- Mobile: responsive sidebar (hamburger menu), stat cards stack, tighter padding
- Sidebar order (growth-first): Command Center, Outreach, Content Studio, Schedule, Market Intel, Analytics, GitHub, Settings
