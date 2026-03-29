# CLAUDE_INSTRUCTIONS.md — CEO Operator Dashboard

## Project Overview

The Operator Dashboard is a self-hosted, AI-powered command center for a solo founder building two products simultaneously:

1. **mesh2param** — a mesh-to-parametric CAD reverse engineering SaaS (waitlist model)
2. **AI Automation Tools** — open-source AI automation workflows and pipelines

The dashboard orchestrates daily operations, content creation, social media management, lead generation, market intelligence, and project tracking — all driven by Claude as the reasoning agent. The goal is to reduce the founder's decision overhead to **review → approve/decline/remix** on everything the system generates.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    OPERATOR DASHBOARD                    │
│               Next.js + React + Tailwind                 │
│            (21st.dev components + UI UX Pro Max)          │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Command  │ │ Content  │ │  Social  │ │   Market   │ │
│  │ Center   │ │ Studio   │ │ Analytics│ │   Intel    │ │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├────────────┤ │
│  │ Leads &  │ │ Schedule │ │  GitHub  │ │  Waitlist  │ │
│  │ Outreach │ │ Calendar │ │ Progress │ │  & Funnel  │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│           Claude API (reasoning engine)                  │
│           SQLite/PostgreSQL (data store)                 │
│           Background task scheduler                      │
└──────┬──────────┬──────────┬──────────┬─────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌────────┐ ┌──────────────────┐
│ n8n      │ │ GitHub  │ │ Social │ │ AI Video Editor  │
│ (always  │ │ API     │ │ APIs   │ │ Pipeline         │
│  on jobs)│ │         │ │        │ │ (auto-editor +   │
│          │ │         │ │        │ │  whisper + ffmpeg)│
└──────────┘ └─────────┘ └────────┘ └──────────────────┘
```

---

## Infrastructure & Tools

### Required Services

| Tool | Purpose | How to Run |
|------|---------|------------|
| **Next.js + React** | Dashboard frontend | Local dev, deploy to Vercel or VPS |
| **FastAPI** | Backend API + Claude reasoning | Local dev, move to VPS for 24/7 |
| **Claude API** | All reasoning, drafting, analysis | Anthropic API key in `.env` |
| **n8n Community Edition** | Always-on automations (scheduled posts, daily intel, webhook triggers) | Docker local or $5 VPS when ready |
| **SQLite** | Data storage (switch to Postgres when scaling) | Built-in, no setup |
| **Cloud VPS** | 24/7 operation when ready | Hetzner/DigitalOcean $5-10/mo |

### Claude Ecosystem Tools

| Tool | Purpose |
|------|---------|
| **Claude Code** | Build and iterate on all code in the repo via terminal |
| **Claude Cowork** | Non-code tasks: draft blog posts, remix content, generate strategies, research — operates on local files without terminal |
| **CLAUDE.md** | Project instructions file at repo root so Claude Code understands the full system |

### MCP Servers & Skills to Connect

Install these as MCP servers in Claude Code or Claude Desktop:

| MCP Server | Purpose | Source |
|------------|---------|--------|
| **Google Workspace MCP** | Read/write Google Docs, Sheets, Slides, Drive — content drafts, analytics sheets, editorial calendar | `@anthropic/google-workspace-mcp` or community server |
| **GitHub MCP** | Check repo progress, read issues/PRs, track commits across mesh2param and other repos | Built-in to Claude Code |
| **n8n MCP** | Let Claude build and trigger n8n workflows directly | `github.com/czlonkowski/n8n-mcp` |
| **coreyhaines31/marketing** | Marketing strategy skills — content frameworks, audience analysis, growth tactics | `github.com/coreyhaines31/marketing` (Claude Code skill) |
| **Brave Search / Web Search** | Daily market intel, competitor monitoring, trend research | Built-in to Claude |

### UI/UX Stack

| Tool | Purpose |
|------|---------|
| **21st.dev** | Pre-built React component library for polished, production-grade UI components — cards, tables, charts, calendars, modals | Import components via `npx shadcn@latest add` or 21st.dev CLI |
| **UI UX Pro Max** | Design system skill for Claude — ensures the dashboard avoids generic AI aesthetics, uses bold typography, intentional color palettes, and memorable layouts | Load as a Claude Code skill |
| **Tailwind CSS** | Utility-first styling | Standard install |
| **Recharts / Tremor** | Dashboard charts and analytics visualizations | npm install |
| **Framer Motion** | Micro-interactions and page transitions | npm install |

### Design Direction

The dashboard should feel like a **mission control for a solo operator** — not a corporate SaaS admin panel. Think dark theme, high contrast, information-dense but scannable. Reference aesthetic: Linear meets Bloomberg Terminal meets Vercel Dashboard.

- **Typography**: Use a distinctive monospace or geometric sans for headers (JetBrains Mono, Geist, or Satoshi), clean sans for body
- **Color**: Dark base (#0A0A0B), accent color for priority items (electric blue or amber), red for alerts, green for completed
- **Layout**: Dense grid, no wasted space, but clear visual hierarchy. Sidebar nav, main content area, collapsible right panel for AI suggestions
- **Motion**: Subtle — smooth page transitions, number count-ups on stats, gentle pulse on items needing attention

---

## Environment Variables

All secrets in `.env` at project root. **Never committed to git.** Add `.env` to `.gitignore`.

```env
# ===== API Keys =====
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...

# ===== Social Media =====
TIKTOK_SESSION_ID=...
YOUTUBE_API_KEY=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
INSTAGRAM_SESSION_ID=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...

# ===== Google Workspace =====
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...

# ===== n8n =====
N8N_WEBHOOK_URL=http://localhost:5678
N8N_API_KEY=...

# ===== Business =====
WAITLIST_DB_PATH=./data/waitlist.db
STRIPE_SECRET_KEY=...  # when ready

# ===== App Config =====
DATABASE_URL=sqlite:///./data/operator.db
OPENAI_API_KEY=...  # for whisper if not using faster-whisper locally
```

---

## Dashboard Pages & Features

### Page 1: Command Center (Home)

**The daily briefing. First thing the founder sees.**

#### Priority Tasks Panel
- Shows today's top 3-5 tasks ranked by impact
- Tasks are auto-generated by Claude based on: project deadlines, content calendar, pending approvals, market opportunities
- Each task has: title, why it matters, estimated time, project tag (mesh2param / AI automation / content / business)
- Drag to reorder, click to mark done, swipe to defer

#### Project Progress Cards
- **mesh2param**: Current stage (3 of 6), blockers, next milestone, days since last commit
- **AI Video Editor**: Pipeline status, features remaining
- **AI Automations**: Repos, open issues, community engagement
- **Operator Dashboard**: Meta — this project's own progress

#### Weekly & Monthly Goals
- Kanban-style columns: This Week / This Month / This Quarter
- Each goal has a progress bar (auto-calculated from sub-tasks and GitHub commits)
- Goals are set by the founder, progress tracked automatically
- Claude suggests new goals when current ones are >80% complete or when market conditions shift

#### AI Suggestions Panel (Right Sidebar)
- "Based on competitor X's recent launch, consider prioritizing feature Y in mesh2param"
- "Your TikTok about RANSAC got 3x avg engagement — create a follow-up series"
- "Market gap detected: no one is offering mesh-to-Onshape specifically for 3D printing shops"
- Suggestions refresh daily from the market intel engine

#### Daily News Briefing
- Auto-generated each morning by Claude + web search
- Categories: AI features & releases, SaaS competitors (Backflip AI, Zoo, etc.), marketing trends, open source CAD news
- Each item: headline, 2-sentence summary, relevance score, suggested action
- "Dismiss" or "Add to tasks" buttons

---

### Page 2: Content Studio

**Where all content gets drafted, reviewed, and approved.**

#### Content Drafts Queue
- Shows all AI-generated drafts awaiting review
- Types: TikTok scripts, YouTube descriptions, blog posts, tweets, Instagram captions, email newsletters
- Each draft shows: content preview, target platform, suggested post time, hashtags, hook analysis
- Actions: **Approve** (moves to schedule) / **Decline** (archived) / **Remix** (Claude regenerates with feedback)

#### Content Repurposer
- Select any high-performing video or post
- Claude auto-generates:
  - **Blog post**: Structured article from the video transcript, with headers, code snippets if technical, SEO keywords
  - **TikTok script**: Condensed hook + body + CTA for a new video on the same topic
  - **Twitter thread**: Key points as a thread
  - **Instagram carousel**: Slide-by-slide text content
  - **Email newsletter section**: Summary for weekly email
- All outputs go into the Drafts Queue for review

#### Hook & Script Generator
- Input: topic or rough idea
- Claude generates 3 hook variations ranked by predicted virality
- Full script with: hook (first 3 sec), body (value delivery), CTA (engagement driver)
- Optimized per platform:
  - **TikTok/Reels**: Pattern interrupt hooks, fast pace, save-worthy tips
  - **YouTube**: Curiosity gap opener, longer value delivery, subscribe CTA
  - **Twitter/X**: Hot take or contrarian angle, quote-tweet bait

#### Content Focus Areas
- Primary: AI automation tools and workflows (open source, educational, build-in-public)
- Primary: mesh2param / mesh-to-CAD technology (thought leadership, waitlist conversion)
- Hooks should emphasize: "I built this", "here's how it works", "you can use this for free", "nobody is talking about this"
- Virality levers: saves/favorites (educational value), shares (surprising insights), comments (ask questions, hot takes)

---

### Page 3: Social Media Analytics

**Performance tracking and algorithm optimization.**

#### Performance Overview
- Cross-platform metrics: views, likes, comments, shares, saves, follower growth
- Time-series charts: daily/weekly/monthly trends
- Engagement rate calculation per platform
- Best performing day/time heatmap

#### Content Scorecard
- Every post ranked by engagement score
- Tags: content type, topic, platform, hook style
- Columns: views, likes, saves, shares, comments, engagement rate
- Color-coded: green (above avg), yellow (avg), red (below avg)
- Filter by: platform, date range, content type, topic

#### What's Working / What's Not
- Claude analyzes all content and generates:
  - "Your AI automation tutorials get 4x more saves than mesh2param content — saves drive algorithmic reach"
  - "Videos under 45 seconds outperform longer ones by 2.3x on TikTok"
  - "Posts with code snippets on screen get more comments"
  - "Your hook style 'Nobody is talking about X' consistently outperforms 'How to X'"

#### Algorithm Optimization Suggestions
- Platform-specific advice based on YOUR data:
  - Optimal post frequency per platform
  - Best posting times (from your audience's activity)
  - Content format recommendations (video length, caption length, hashtag count)
  - Engagement bait techniques that work in your niche
  - Suggested sounds/trends to use on TikTok

#### Competitor Content Tracker
- Monitor 5-10 competitor accounts
- When they post, log: topic, format, engagement metrics
- Claude analysis: "Competitor X's video about reverse engineering got 50K views — they used a before/after format, consider making your own version showing mesh2param's pipeline"
- "Remix it" button → generates a script inspired by their angle but with your unique perspective

---

### Page 4: Social Media Stats

**Deep analytics and trend visualization.**

#### Follower Growth
- Line chart: followers over time per platform
- Annotations: spikes correlated with specific posts
- Growth rate: daily/weekly/monthly

#### Engagement Trends
- Engagement rate over time (likes + comments + saves + shares / views)
- Breakdown by content type
- Breakdown by topic
- Compare: this month vs last month

#### Audience Insights
- Demographics if available from platform APIs
- Active hours (when your audience is online)
- Top commenting users (potential leads or community members)
- Sentiment analysis of comments (positive/negative/questions)

#### Virality Score
- Custom metric: (saves × 3 + shares × 5 + comments × 2 + likes) / views × 100
- Track per post and over time
- Identify what drives saves (the strongest algorithmic signal on TikTok and Instagram)

---

### Page 5: Lead Generation & Outreach

**Turn social media engagement into business opportunities.**

#### Lead Detection
- Scan comments and DMs for buying signals:
  - "How much does this cost?"
  - "Is this available?"
  - "Can I use this for my company?"
  - "Do you offer consulting?"
  - "When does the waitlist open?"
- Claude categorizes: hot lead / warm lead / just curious
- Each lead: username, platform, message, sentiment, suggested action

#### DM Drafter
- For each detected lead, Claude drafts a personalized DM:
  - References their specific comment/question
  - Provides value first (free resource, answer their question)
  - Soft CTA (join waitlist, check out the open-source tools, book a call)
- Actions: **Send** / **Edit** / **Skip**

#### Comment Reply Drafter
- Prioritized queue of comments needing replies
- Claude drafts replies that: answer the question, build community, drive engagement (ask a follow-up question), subtly promote the product
- Batch approve: review all drafts, approve/edit in bulk

#### Waitlist Management (mesh2param)
- Current waitlist count
- Source tracking: which content/platform drove signups
- Conversion funnel: view → profile visit → waitlist signup
- Email draft automation for waitlist updates

#### Feedback Analysis
- Aggregate all comments, DMs, and feedback
- Claude categorizes:
  - **Feature requests**: "Can it handle curved surfaces?" → add to mesh2param roadmap
  - **Bug reports**: "The segmentation fails on thin walls" → create GitHub issue
  - **Content requests**: "Make a video about X" → add to content ideas
  - **Praise**: Track for testimonials and social proof

---

### Page 6: Content Schedule

**Calendar view of the full content + work pipeline.**

#### Calendar View
- Monthly calendar with daily blocks
- Color-coded blocks:
  - **Deep work** (blue): mesh2param development, AI automation coding
  - **Content creation** (purple): filming, editing, writing
  - **Content posting** (green): scheduled posts across platforms
  - **Business ops** (amber): emails, outreach, admin
  - **Research** (gray): market intel, learning, competitor analysis

#### Posting Schedule
- Optimal posting times per platform (calculated from analytics)
- Suggested cadence:
  - TikTok: 1-2x/day
  - YouTube: 2-3x/week
  - Instagram: 1x/day
  - Twitter/X: 3-5x/day
  - Blog: 1x/week
- Each slot shows: assigned content (from drafts queue) or empty (needs content)
- Drag content from drafts into calendar slots

#### Work Blocks
- Claude suggests daily schedule based on:
  - Priority tasks from Command Center
  - Content calendar deadlines
  - Energy patterns (deep work in morning, content in afternoon — configurable)
  - Buffer time for unexpected tasks

#### AI Video Editor Integration
- Calendar shows when raw footage needs to be recorded
- Auto-edit pipeline status: raw → edited → captioned → scheduled → posted
- One-click: select a content slot → opens AI video editor → processes → schedules post

---

### Page 7: Market Intelligence

**Competitive landscape and opportunity detection.**

#### Market Gaps
- Claude + web search scans daily for:
  - Reddit/HackerNews/Twitter complaints about existing CAD tools
  - Forum posts asking "is there a tool that does X?" where X matches mesh2param
  - Gaps in competitor offerings
  - Underserved customer segments
- Each gap: description, source, opportunity score, suggested action

#### Competitor Monitor
- Track: Backflip AI, Zoo/Zookeeper, FreeCAD, CadQuery community, other mesh-to-CAD tools
- New features they launch
- Pricing changes
- Content they publish
- Community sentiment about them
- Claude analysis: "Zoo added STL reverse engineering but reviews say it fails on complex parts — this is your differentiator"

#### Industry News Feed
- AI/ML releases relevant to your stack (new models, new open-source tools)
- CAD industry news (Onshape updates, OCCT releases, new competitors)
- Creator economy updates (platform algorithm changes, new features)
- Marketing/growth tactics trending in your niche

#### Complaints & Pain Points
- Aggregated from Reddit, Twitter, forums, product reviews
- "People hate that Backflip AI requires uploading to their cloud"
- "FreeCAD users want better mesh import"
- "TikTok creators frustrated with CapCut paywall"
- Each complaint mapped to: your product/content opportunity

---

### Page 8: GitHub Progress

**Project tracking across all repos.**

#### Repository Overview
- List all repos: mesh2param, AI video editor, AI automations, operator dashboard
- Per repo: last commit, open issues, open PRs, stars/forks (if public)
- Commit activity chart (GitHub contribution graph style)

#### mesh2param Pipeline Status
- Visual pipeline: Stage 1 ✅ → Stage 2 ✅ → Stage 3 ✅ → Stage 4 🔄 → Stage 5 ⬜ → Stage 6 ⬜
- Per stage: completion %, blockers, test coverage
- Claude suggestions: "Stage 4 edge classification could benefit from the Bevel library for detecting chamfer edges"

#### Issue Tracker Integration
- Pull open issues from GitHub
- Claude prioritizes: "This bug in surface segmentation affects 40% of test models — fix before moving to Stage 5"
- Auto-create issues from feedback analysis (Page 5)

#### Development Suggestions
- Claude reviews recent commits and suggests:
  - Refactoring opportunities
  - Missing test coverage
  - Performance bottlenecks
  - New features based on market intel

---

## n8n Workflows (Always-On Automation)

These run 24/7 on the n8n instance, triggering without manual intervention:

| Workflow | Trigger | Action |
|----------|---------|--------|
| **Morning Briefing** | Cron: 7:00 AM daily | Claude searches news, generates briefing, saves to dashboard DB |
| **Social Media Metrics Pull** | Cron: every 6 hours | Fetch analytics from TikTok/YouTube/Instagram APIs, store in DB |
| **Competitor Monitor** | Cron: daily | Check competitor accounts for new posts, analyze with Claude |
| **Content Auto-Post** | Cron: every 15 min | Check schedule queue, post any content due to the right platform |
| **Lead Detection** | Cron: every 2 hours | Scan new comments/DMs for buying signals, add to leads queue |
| **Waitlist Signup** | Webhook | New signup → welcome email → add to DB → notify dashboard |
| **GitHub Webhook** | Webhook | New commit/issue → update dashboard progress → notify if blocker |
| **Content Repurpose** | On trigger | High-performing post detected → auto-generate blog/thread/carousel drafts |
| **Market Gap Scan** | Cron: weekly | Deep search Reddit/HN/Twitter for complaints and gaps |
| **Weekly Report** | Cron: Sunday 8 PM | Compile weekly metrics, content performance, goals progress |

---

## Claude Reasoning Requirements

The operator agent must reason well, not just template-fill. Key reasoning behaviors:

### Task Prioritization Logic
```
1. What has the highest impact on revenue/growth RIGHT NOW?
   - Waitlist signups → mesh2param development & content about it
   - If engagement is dropping → prioritize content quality
   - If a competitor launched something → respond with differentiation content

2. What is time-sensitive?
   - Trending topic expires → content about it today
   - Scheduled post needs content → draft before posting window
   - Bug report from potential customer → fix immediately

3. What compounds over time?
   - Building in public content → grows audience → generates leads
   - Consistent posting schedule → algorithmic favor → more reach
   - Open source contributions → community trust → mesh2param credibility

4. What can be batched?
   - Film 5 videos in one session → edit throughout the week
   - Draft all social posts for the week on Sunday
   - Review and approve all AI drafts in one 30-min block
```

### Content Strategy Logic
```
Goal: Every piece of content should serve at least one of:
  A) Drive waitlist signups for mesh2param
  B) Build authority in AI automation / CAD reverse engineering
  C) Grow audience on target platforms
  D) Generate leads for consulting/services

Virality optimization:
  - Hook: Pattern interrupt or curiosity gap in first 1-3 seconds
  - Body: Deliver real value (tutorial, insight, result)
  - CTA: Drive saves ("save this for later"), comments ("what do you think?"), shares
  - Format: Short-form video (TikTok/Reels) as primary, repurpose to long-form

Remix strategy:
  - Take competitor's successful FORMAT, apply your own CONTENT
  - Take your best performing TOPIC, try a new FORMAT
  - Never copy — always add your unique technical depth
```

### Market Intel Logic
```
Scan for:
  - Direct competitors: anyone doing mesh-to-parametric CAD
  - Adjacent competitors: text-to-CAD (Zoo, CADAM), AI CAD tools (Leo AI)
  - Content competitors: other AI/automation creators in your niche
  - Customer pain: people complaining about STL editing, mesh cleanup, CAD conversion

Signal priority:
  - "I wish there was..." → highest priority (unmet need)
  - "X tool doesn't work for..." → high priority (competitor weakness)  
  - "I switched from X to Y because..." → medium priority (migration trigger)
  - "X just launched..." → medium priority (competitive move)
```

---

## Tech Stack Summary

```
Frontend:        Next.js 14 + React + Tailwind CSS
Components:      21st.dev + shadcn/ui + custom
Charts:          Recharts or Tremor
Motion:          Framer Motion
Design System:   UI UX Pro Max (Claude skill)

Backend:         FastAPI (Python)
Database:        SQLite → PostgreSQL when scaling
Task Queue:      n8n Community Edition (Docker)
Auth:            Simple token auth (solo user)

AI:              Claude API (Sonnet for speed, Opus for reasoning)
Skills:          coreyhaines31/marketing, GitHub MCP, Google Workspace MCP, n8n MCP
Search:          Claude web search tool for market intel
Video Pipeline:  auto-editor + faster-whisper + ffmpeg + Claude API

Deployment:      Local dev → VPS ($5-10/mo) for 24/7 operation
Version Control: Git + GitHub (private repos for dashboard, public for AI tools)
Secrets:         .env file, never committed
```

---

## File Structure

```
operator-dashboard/
├── .env                          # All secrets (gitignored)
├── .gitignore
├── CLAUDE.md                     # Claude Code project instructions
├── README.md
│
├── frontend/                     # Next.js app
│   ├── app/
│   │   ├── page.tsx              # Command Center (home)
│   │   ├── content/page.tsx      # Content Studio
│   │   ├── analytics/page.tsx    # Social Media Analytics
│   │   ├── stats/page.tsx        # Social Media Stats
│   │   ├── leads/page.tsx        # Lead Generation
│   │   ├── schedule/page.tsx     # Content Schedule
│   │   ├── market/page.tsx       # Market Intelligence
│   │   └── github/page.tsx       # GitHub Progress
│   ├── components/
│   │   ├── ui/                   # 21st.dev + shadcn components
│   │   ├── dashboard/            # Dashboard-specific components
│   │   ├── charts/               # Chart components
│   │   └── layout/               # Sidebar, header, panels
│   └── lib/
│       ├── api.ts                # Backend API client
│       └── utils.ts
│
├── backend/                      # FastAPI server
│   ├── main.py                   # App entrypoint
│   ├── api/
│   │   ├── tasks.py              # Priority tasks endpoints
│   │   ├── content.py            # Content drafting & management
│   │   ├── analytics.py          # Social media metrics
│   │   ├── leads.py              # Lead detection & outreach
│   │   ├── market.py             # Market intelligence
│   │   ├── github_sync.py        # GitHub repo tracking
│   │   ├── schedule.py           # Content calendar
│   │   └── video.py              # AI video editor integration
│   ├── agents/
│   │   ├── reasoning.py          # Core Claude reasoning engine
│   │   ├── content_drafter.py    # Content generation agent
│   │   ├── market_analyst.py     # Market intel agent
│   │   ├── lead_scorer.py        # Lead detection & scoring
│   │   └── task_prioritizer.py   # Task ranking logic
│   ├── services/
│   │   ├── social/
│   │   │   ├── tiktok.py
│   │   │   ├── youtube.py
│   │   │   ├── instagram.py
│   │   │   └── twitter.py
│   │   ├── github_service.py
│   │   ├── n8n_service.py
│   │   └── video_pipeline.py
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   └── db/
│       ├── database.py
│       └── migrations/
│
├── video-pipeline/               # AI Video Editor
│   ├── process.sh                # One-click edit script
│   ├── caption_gen.py
│   ├── assemble.py
│   ├── clip_extractor.py
│   └── upload.py
│
├── n8n/                          # n8n workflow configs
│   ├── workflows/
│   │   ├── morning_briefing.json
│   │   ├── social_metrics.json
│   │   ├── competitor_monitor.json
│   │   ├── content_auto_post.json
│   │   ├── lead_detection.json
│   │   └── weekly_report.json
│   └── docker-compose.yml
│
├── data/                         # Local data (gitignored)
│   ├── operator.db
│   ├── waitlist.db
│   └── analytics_cache/
│
└── scripts/
    ├── setup.sh                  # One-command project setup
    ├── seed_data.py              # Populate with initial goals/config
    └── migrate.py                # DB migrations
```

---

## Build Order

### Phase 1: Foundation (Week 1)
1. FastAPI backend with SQLite
2. Claude reasoning engine (`agents/reasoning.py`)
3. Command Center page with hardcoded goals → then dynamic
4. GitHub integration (track mesh2param progress)
5. `.env` setup with all required keys

### Phase 2: Content Engine (Week 2)
6. Content Studio page (draft/approve/decline/remix flow)
7. Content drafter agent (hooks, scripts, blog posts)
8. AI video editor integration (connect the weekend pipeline)
9. Content schedule calendar

### Phase 3: Analytics & Intel (Week 3)
10. Social media API integrations (TikTok, YouTube, Instagram)
11. Analytics page with charts
12. Market intelligence agent + daily briefing
13. Competitor monitoring

### Phase 4: Growth (Week 4)
14. Lead detection + DM drafter
15. Comment reply automation
16. Waitlist management
17. n8n workflows for all always-on automations

### Phase 5: Polish
18. Full UI/UX pass with 21st.dev + UI UX Pro Max
19. Mobile responsiveness
20. Performance optimization
21. Deploy to VPS for 24/7 operation
