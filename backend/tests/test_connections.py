"""
Test: All dashboard connections work correctly — auth, data persistence, API endpoints.

Tests that everything saves correctly and survives across requests.

Run:
    cd backend
    pytest tests/test_connections.py -v -s

Does NOT require Claude CLI (no AI calls). Fast to run.
"""
import os
import sys
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

# Isolate test DB
_test_db_dir = tempfile.mkdtemp(prefix="optest_conn_")
_test_db_path = os.path.join(_test_db_dir, "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["AUTH_SECRET"] = "test_secret_fixed"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from db.database import init_db


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c
    shutil.rmtree(_test_db_dir, ignore_errors=True)


# ── Auth ────────────────────────────────────────────────────────────

class TestAuth:
    def test_signup_creates_account(self, client):
        resp = client.post("/auth/signup", json={
            "username": "testuser",
            "password": "testpass",
            "plan": "local",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["username"] == "testuser"
        assert "token" in data

    def test_signup_duplicate_fails(self, client):
        resp = client.post("/auth/signup", json={
            "username": "testuser",
            "password": "testpass",
        })
        assert resp.status_code == 409

    def test_login_works(self, client):
        resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["token"]

    def test_login_wrong_password(self, client):
        resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/auth/login", json={
            "username": "nobody",
            "password": "pass",
        })
        assert resp.status_code == 401

    def test_login_persists_across_requests(self, client):
        """Login token is consistent (same secret = same hash)."""
        r1 = client.post("/auth/login", json={"username": "testuser", "password": "testpass"})
        r2 = client.post("/auth/login", json={"username": "testuser", "password": "testpass"})
        assert r1.json()["token"] == r2.json()["token"]

    def test_verify_token(self, client):
        login = client.post("/auth/login", json={"username": "testuser", "password": "testpass"})
        token = login.json()["token"]
        resp = client.get(f"/auth/verify?token={token}")
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_verify_invalid_token(self, client):
        resp = client.get("/auth/verify?token=invalidtoken123")
        assert resp.status_code == 401


# ── Projects ────────────────────────────────────────────────────────

class TestProjects:
    def test_create_project(self, client):
        resp = client.post("/projects/", json={
            "name": "Test Project",
            "slug": "test-project",
            "description": "A test project",
            "current_stage": 1,
            "total_stages": 5,
            "stage_label": "Stage 1",
            "color": "#3b82f6",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Project"
        assert resp.json()["id"] > 0

    def test_project_persists(self, client):
        resp = client.get("/projects/")
        assert resp.status_code == 200
        projects = resp.json()
        assert any(p["slug"] == "test-project" for p in projects)

    def test_update_project(self, client):
        projects = client.get("/projects/").json()
        pid = next(p["id"] for p in projects if p["slug"] == "test-project")
        resp = client.patch(f"/projects/{pid}", json={
            "current_stage": 3,
            "stage_label": "Updated stage",
        })
        assert resp.status_code == 200
        assert resp.json()["current_stage"] == 3


# ── Goals ───────────────────────────────────────────────────────────

class TestGoals:
    def test_create_goal(self, client):
        resp = client.post("/goals/", json={
            "title": "Reach 1000 signups",
            "timeframe": "month",
            "progress": 0.0,
            "project_slug": "test-project",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Reach 1000 signups"

    def test_goal_persists(self, client):
        resp = client.get("/goals/")
        assert resp.status_code == 200
        goals = resp.json()
        assert any(g["title"] == "Reach 1000 signups" for g in goals)

    def test_update_goal_progress(self, client):
        goals = client.get("/goals/").json()
        gid = goals[0]["id"]
        resp = client.patch(f"/goals/{gid}", json={"progress": 0.5})
        assert resp.status_code == 200
        assert resp.json()["progress"] == 0.5


# ── Tasks ───────────────────────────────────────────────────────────

class TestTasks:
    def test_create_task(self, client):
        resp = client.post("/tasks/", json={
            "title": "Reply to 10 Reddit comments",
            "why": "Growth outreach",
            "estimated_minutes": 30,
            "project_tag": "test-project",
            "priority_score": 8.0,
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Reply to 10 Reddit comments"

    def test_task_persists(self, client):
        resp = client.get("/tasks/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_complete_task(self, client):
        tasks = client.get("/tasks/").json()
        tid = tasks[0]["id"]
        resp = client.patch(f"/tasks/{tid}", json={"status": "done"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

    def test_completed_task_filtered(self, client):
        resp = client.get("/tasks/?status=pending")
        tasks = resp.json()
        assert not any(t["status"] == "done" for t in tasks)


# ── Content Drafts ──────────────────────────────────────────────────

class TestContentDrafts:
    def test_create_draft(self, client):
        resp = client.post("/content/drafts/", json={
            "title": "Test TikTok Draft",
            "body": "Hook: This changed everything...",
            "platform": "tiktok",
            "content_type": "short-form",
            "status": "draft",
        })
        assert resp.status_code == 200
        assert resp.json()["platform"] == "tiktok"

    def test_draft_persists(self, client):
        resp = client.get("/content/drafts/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_approve_draft(self, client):
        drafts = client.get("/content/drafts/").json()
        did = drafts[0]["id"]
        resp = client.post(f"/content/drafts/{did}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


# ── Schedule ────────────────────────────────────────────────────────

class TestSchedule:
    def test_create_schedule_item(self, client):
        resp = client.post("/content/schedule/", json={
            "title": "Post TikTok video",
            "platform": "tiktok",
            "scheduled_at": "2026-04-01T10:00:00",
            "status": "scheduled",
            "block_type": "content",
            "color": "#A855F7",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Post TikTok video"

    def test_schedule_persists(self, client):
        resp = client.get("/content/schedule/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ── Suggestions ─────────────────────────────────────────────────────

class TestSuggestions:
    def test_suggestions_endpoint(self, client):
        resp = client.get("/suggestions/")
        assert resp.status_code == 200


# ── Market Gaps ─────────────────────────────────────────────────────

class TestMarketGaps:
    def test_gaps_endpoint(self, client):
        resp = client.get("/market/gaps")
        assert resp.status_code == 200


# ── Command Center Aggregation ──────────────────────────────────────

class TestCommandCenter:
    def test_command_center_returns_all_data(self, client):
        resp = client.get("/command-center/")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "projects" in data
        assert "goals_week" in data
        assert "goals_month" in data
        assert "goals_quarter" in data
        assert "suggestions" in data
        assert "briefing" in data

    def test_command_center_has_project(self, client):
        data = client.get("/command-center/").json()
        assert len(data["projects"]) >= 1
        assert data["projects"][0]["name"] == "Test Project"


# ── GitHub ──────────────────────────────────────────────────────────

class TestGitHub:
    def test_repos_endpoint(self, client):
        resp = client.get("/github/repos")
        assert resp.status_code == 200


# ── Analytics ───────────────────────────────────────────────────────

class TestAnalytics:
    def test_metrics_endpoint(self, client):
        resp = client.get("/analytics/metrics")
        assert resp.status_code == 200

    def test_content_scores_endpoint(self, client):
        resp = client.get("/analytics/content-scores")
        assert resp.status_code == 200


# ── Billing ─────────────────────────────────────────────────────────

class TestBilling:
    def test_plans_endpoint(self, client):
        resp = client.get("/billing/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert "local" in plans
        assert "starter" in plans
        assert "pro" in plans


# ── Health ──────────────────────────────────────────────────────────

class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Data Persistence Flow ──────────────────────────────────────────

class TestPersistenceFlow:
    """End-to-end: create data → read it back → verify it survived."""

    def test_full_flow(self, client):
        # Create a second project
        client.post("/projects/", json={
            "name": "Growth Project",
            "slug": "growth",
            "description": "Testing persistence",
            "current_stage": 0,
            "total_stages": 3,
            "color": "#10b981",
        })

        # Create goals for it
        client.post("/goals/", json={
            "title": "Get 50 beta users",
            "timeframe": "week",
            "progress": 0.0,
            "project_slug": "growth",
        })
        client.post("/goals/", json={
            "title": "Post 10 videos",
            "timeframe": "month",
            "progress": 0.0,
            "project_slug": "growth",
        })

        # Create a task
        client.post("/tasks/", json={
            "title": "DM 5 people on Twitter about growth project",
            "priority_score": 9.0,
            "estimated_minutes": 20,
            "project_tag": "growth",
            "status": "pending",
        })

        # Read everything back through command center
        data = client.get("/command-center/").json()

        # Verify it all came back
        assert any(p["slug"] == "growth" for p in data["projects"])
        assert any(g["title"] == "Get 50 beta users" for g in data["goals_week"])
        assert any(g["title"] == "Post 10 videos" for g in data["goals_month"])
        assert any(t["title"] == "DM 5 people on Twitter about growth project" for t in data["tasks"])
