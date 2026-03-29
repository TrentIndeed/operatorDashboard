"""
Test: AI Generate button fills out data for all dashboard tabs.

This is an integration test that calls /ai/generate-all against a live backend
with a real Claude CLI, then verifies every tab's endpoints return the expected
data. It uses a temporary SQLite database so it doesn't pollute production data.

Run:
    cd backend
    pytest tests/test_ai_generate.py -v -s

Requires:
    - Claude Code CLI installed and authenticated (`claude --version`)
    - Takes ~2-3 minutes (real Claude API calls)
"""
import os
import sys
import time
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

# ── Isolate the test DB so we don't touch production data ───────────────
_test_db_dir = tempfile.mkdtemp(prefix="optest_")
_test_db_path = os.path.join(_test_db_dir, "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app  # noqa: E402
from db.database import init_db, SessionLocal  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Shared test client for the whole module."""
    init_db()
    # Seed runs automatically in lifespan, but TestClient may not trigger it.
    # Force seed if needed.
    from main import _seed_initial_data
    _seed_initial_data()
    with TestClient(app) as c:
        yield c
    # Cleanup temp DB
    try:
        shutil.rmtree(_test_db_dir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(scope="module")
def claude_available():
    """Check if Claude CLI is installed and accessible."""
    path = shutil.which("claude") or os.path.join(
        os.environ.get("APPDATA", ""), "npm", "claude.cmd"
    )
    if not path or not os.path.isfile(path):
        pytest.skip("Claude CLI not found — skipping AI integration tests")
    return True


# ── Helpers ─────────────────────────────────────────────────────────────

def wait_for_background_tasks(client, max_wait=180, poll_interval=10):
    """Poll /tasks/ until AI-generated tasks appear, or timeout."""
    start = time.time()
    while time.time() - start < max_wait:
        resp = client.get("/tasks/")
        tasks = resp.json()
        ai_tasks = [t for t in tasks if t.get("ai_generated")]
        if ai_tasks:
            return True
        print(f"  ... waiting for AI tasks ({int(time.time() - start)}s elapsed)")
        time.sleep(poll_interval)
    return False


# ── Tests ───────────────────────────────────────────────────────────────

class TestAIGenerateAll:
    """
    Test that the AI Generate button (/ai/generate-all) populates data
    required by every dashboard tab.
    """

    def test_health(self, client):
        """Sanity: backend is alive."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_seed_data_exists(self, client):
        """Pre-condition: seed data (projects, goals) is present."""
        resp = client.get("/command-center/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) >= 4, "Expected 4 seeded projects"
        assert len(data["goals_week"]) >= 1, "Expected seeded weekly goals"
        assert len(data["goals_month"]) >= 1, "Expected seeded monthly goals"
        assert len(data["goals_quarter"]) >= 1, "Expected seeded quarterly goals"

    def test_generate_all_returns_ok(self, client, claude_available):
        """POST /ai/generate-all returns 200 with queued tasks."""
        resp = client.post("/ai/generate-all")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "generating"
        assert "queued" in body
        assert "generate_tasks" in body["queued"]
        assert "generate_suggestions" in body["queued"]
        assert "scan_market" in body["queued"]
        assert "sync_github" in body["queued"]

    def test_wait_for_completion(self, client, claude_available):
        """Wait for background tasks to finish (up to 3 min)."""
        completed = wait_for_background_tasks(client, max_wait=180)
        assert completed, (
            "AI-generated tasks did not appear within 3 minutes. "
            "Check backend logs for [Claude] or [AI] errors."
        )

    # ── Command Center tab ──────────────────────────────────────────

    def test_command_center_has_tasks(self, client, claude_available):
        """Command Center: AI-generated priority tasks exist."""
        resp = client.get("/tasks/")
        tasks = resp.json()
        ai_tasks = [t for t in tasks if t.get("ai_generated")]
        assert len(ai_tasks) >= 1, "Expected AI-generated tasks"

        # Each task must have required fields
        for t in ai_tasks:
            assert t["title"], f"Task {t['id']} missing title"
            assert t["priority_score"] > 0, f"Task {t['id']} has no priority score"
            assert t["status"] == "pending"

    def test_command_center_has_suggestions(self, client, claude_available):
        """Command Center: AI suggestions were generated."""
        resp = client.get("/suggestions/")
        suggestions = resp.json()
        # Should have more than the 4 seeded ones
        assert len(suggestions) >= 5, (
            f"Expected >=5 suggestions (4 seed + AI), got {len(suggestions)}"
        )

    def test_command_center_has_projects(self, client):
        """Command Center: projects exist from seed data."""
        resp = client.get("/projects/")
        assert len(resp.json()) >= 4

    def test_command_center_has_goals(self, client):
        """Command Center: goals exist from seed data."""
        resp = client.get("/goals/")
        goals = resp.json()
        assert len(goals) >= 9, f"Expected 9 seeded goals, got {len(goals)}"

    # ── Content Studio tab ──────────────────────────────────────────

    def test_content_studio_has_drafts(self, client, claude_available):
        """Content Studio: AI-generated content drafts exist."""
        resp = client.get("/content/drafts/")
        drafts = resp.json()
        ai_drafts = [d for d in drafts if d.get("ai_generated")]
        assert len(ai_drafts) >= 1, "Expected at least 1 AI-generated draft"

        for d in ai_drafts:
            assert d["title"], f"Draft {d['id']} missing title"
            assert d["body"], f"Draft {d['id']} missing body"
            assert d["platform"], f"Draft {d['id']} missing platform"
            assert d["status"] == "draft"

    def test_content_studio_drafts_have_hooks(self, client, claude_available):
        """Content Studio: drafts have hook and hook_score."""
        resp = client.get("/content/drafts/")
        drafts = [d for d in resp.json() if d.get("ai_generated")]
        for d in drafts:
            assert d.get("hook"), f"Draft '{d['title'][:40]}' missing hook"
            # hook_score may be null for some — just check at least one has it
        has_score = any(d.get("hook_score") is not None for d in drafts)
        assert has_score, "No drafts have a hook_score"

    # ── Schedule tab ────────────────────────────────────────────────

    def test_schedule_has_items(self, client, claude_available):
        """Schedule: AI-generated drafts were auto-scheduled."""
        resp = client.get("/content/schedule/")
        items = resp.json()
        assert len(items) >= 1, (
            "Expected at least 1 scheduled item from AI draft generation"
        )
        for item in items:
            assert item["title"], f"Schedule item {item['id']} missing title"
            assert item["scheduled_at"], f"Schedule item {item['id']} missing scheduled_at"
            assert item["platform"], f"Schedule item {item['id']} missing platform"
            assert item["block_type"] == "content"

    def test_schedule_items_linked_to_drafts(self, client, claude_available):
        """Schedule: scheduled items reference a draft_id."""
        resp = client.get("/content/schedule/")
        items = resp.json()
        linked = [i for i in items if i.get("draft_id")]
        assert len(linked) >= 1, "Expected schedule items linked to drafts"

    # ── Market Intelligence tab ─────────────────────────────────────

    def test_market_has_gaps(self, client, claude_available):
        """Market Intel: AI-scanned market gaps exist."""
        # Market scan may take longer — poll briefly
        gaps = []
        for _ in range(12):
            resp = client.get("/market/gaps")
            gaps = resp.json()
            if gaps:
                break
            time.sleep(10)

        assert len(gaps) >= 1, "Expected at least 1 market gap from AI scan"

        for g in gaps:
            assert g["description"], f"Gap {g['id']} missing description"
            assert 0 <= g["opportunity_score"] <= 1, (
                f"Gap {g['id']} score out of range: {g['opportunity_score']}"
            )
            assert g["status"] in ("new", "active"), (
                f"Gap {g['id']} unexpected status: {g['status']}"
            )

    def test_market_gaps_have_actions(self, client, claude_available):
        """Market Intel: gaps have suggested actions."""
        resp = client.get("/market/gaps")
        gaps = resp.json()
        with_actions = [g for g in gaps if g.get("suggested_action")]
        assert len(with_actions) >= 1, "Expected gaps with suggested_action"

    # ── Analytics tab ───────────────────────────────────────────────

    def test_analytics_endpoints_respond(self, client):
        """Analytics: all analytics endpoints return 200."""
        for path in [
            "/analytics/metrics",
            "/analytics/content-scores",
            "/analytics/engagement-trend",
        ]:
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} returned {resp.status_code}"

    # ── Stats tab ───────────────────────────────────────────────────

    def test_stats_endpoints_respond(self, client):
        """Stats: metrics and content-scores endpoints return 200."""
        resp = client.get("/analytics/metrics")
        assert resp.status_code == 200

        resp = client.get("/analytics/content-scores")
        assert resp.status_code == 200

    # ── GitHub tab ──────────────────────────────────────────────────

    def test_github_repos_synced(self, client, claude_available):
        """GitHub: at least one repo was synced."""
        # GitHub sync may take a few seconds — poll briefly
        repos = []
        for _ in range(6):
            resp = client.get("/github/repos")
            repos = resp.json()
            if repos:
                break
            time.sleep(5)

        assert len(repos) >= 1, "Expected at least 1 synced GitHub repo"

        for r in repos:
            assert r["owner"], f"Repo {r['id']} missing owner"
            assert r["name"], f"Repo {r['id']} missing name"
            assert r["synced_at"], f"Repo {r['id']} missing synced_at"

    def test_github_repo_has_commit_data(self, client, claude_available):
        """GitHub: synced repo has commit info."""
        resp = client.get("/github/repos")
        repos = resp.json()
        with_commits = [r for r in repos if r.get("last_commit_sha")]
        assert len(with_commits) >= 1, "Expected repos with commit data"

    # ── Leads tab ───────────────────────────────────────────────────

    def test_leads_endpoints_respond(self, client):
        """Leads: all leads endpoints return 200."""
        for path in [
            "/leads/",
            "/leads/comment-replies",
            "/leads/waitlist",
            "/leads/waitlist/stats",
        ]:
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} returned {resp.status_code}"

    # ── Cross-tab: Command Center aggregation ───────────────────────

    def test_command_center_aggregates_all(self, client, claude_available):
        """Command Center /command-center/ returns data from all sources."""
        resp = client.get("/command-center/")
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["tasks"]) >= 1, "Command center has no tasks"
        assert len(data["projects"]) >= 4, "Command center missing projects"
        assert len(data["goals_week"]) >= 1, "Command center missing weekly goals"
        assert len(data["suggestions"]) >= 1, "Command center missing suggestions"


class TestAIGenerateIndividual:
    """Test individual AI generation endpoints work independently."""

    def test_generate_tasks_endpoint(self, client, claude_available):
        """POST /ai/generate-tasks returns 200."""
        resp = client.post("/ai/generate-tasks")
        assert resp.status_code == 200
        assert resp.json()["status"] == "generating"

    def test_generate_suggestions_endpoint(self, client, claude_available):
        """POST /ai/generate-suggestions returns 200."""
        resp = client.post("/ai/generate-suggestions")
        assert resp.status_code == 200
        assert resp.json()["status"] == "generating"

    def test_market_scan_endpoint(self, client, claude_available):
        """POST /market/scan returns 200."""
        resp = client.post("/market/scan")
        assert resp.status_code == 200
        assert resp.json()["status"] == "scanning"

    def test_github_sync_all_endpoint(self, client):
        """POST /github/sync-all returns 200."""
        resp = client.post("/github/sync-all")
        assert resp.status_code == 200

    def test_generate_draft_endpoint(self, client, claude_available):
        """POST /ai/generate-draft creates a draft synchronously."""
        resp = client.post(
            "/ai/generate-draft",
            params={
                "topic": "Quick test: why AI automation matters",
                "platform": "twitter",
                "content_type": "thread",
                "project_tag": "ai-automation",
            },
        )
        assert resp.status_code == 200
        draft = resp.json()
        assert draft["title"], "Draft missing title"
        assert draft["body"], "Draft missing body"
        assert draft["platform"] == "twitter"
        assert draft["ai_generated"] is True
        assert draft["status"] == "draft"
