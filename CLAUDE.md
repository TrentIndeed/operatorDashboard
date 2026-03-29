# Operator Dashboard — Claude Code Instructions

See `CLAUDE_INSTRUCTIONS.md` for the full project spec, architecture, and feature details.

## Quick Reference

- **Frontend**: `frontend/` — Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **Backend**: `backend/` — FastAPI + SQLite + Claude API
- **Automations**: `n8n/` — n8n workflow JSON configs

## Running Locally

```bash
# Backend (from repo root)
cd backend && uvicorn main:app --reload --port 8000

# Frontend (from repo root)
cd frontend && npm run dev
```

## Key Conventions

- All secrets in `.env` (never commit)
- Backend API at `http://localhost:8000`
- Frontend at `http://localhost:3000`
- Claude model: `claude-sonnet-4-6` for speed, `claude-opus-4-6` for deep reasoning
- Database: SQLite at `data/operator.db` (gitignored)

## Design System

Dark theme: `#0A0A0B` base, electric blue accents, Geist/JetBrains Mono fonts.
Reference: Linear meets Bloomberg Terminal meets Vercel Dashboard.
