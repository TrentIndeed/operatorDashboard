#!/usr/bin/env python3
"""
Push a digest of the product repo to the operator dashboard.

The bot runs on the VPS and can't see your local ../meshToParametric folder.
This script reads the repo HERE (where the code actually lives), builds a digest,
and POSTs it to the dashboard API so the cloud bot understands what you're building
and how far along it is.

Run it whenever you want the bot's understanding to catch up (e.g. after a coding
session), or schedule it. Examples:

    # Push to the live VPS
    python scripts/push_codebase_digest.py --api https://api.dragonoperator.com

    # Push to a local backend
    python scripts/push_codebase_digest.py --api http://localhost:8000

    # Point at a different repo
    MESH_REPO_PATH=../meshToParametric python scripts/push_codebase_digest.py

Env vars: DASHBOARD_API_URL (default http://localhost:8000), MESH_REPO_PATH.
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# Make backend/ importable so we reuse the exact same digest logic the server uses.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agents.codebase_digest import generate_digest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Push a codebase digest to the dashboard.")
    parser.add_argument(
        "--api",
        default=os.getenv("DASHBOARD_API_URL", "http://localhost:8000"),
        help="Dashboard API base URL (e.g. https://api.dragonoperator.com)",
    )
    parser.add_argument("--repo", default=os.getenv("MESH_REPO_PATH"), help="Path to the product repo")
    args = parser.parse_args()

    digest = generate_digest(args.repo)
    if not digest:
        print("ERROR: no git repo found. Set MESH_REPO_PATH or pass --repo to point at meshToParametric.")
        return 1

    payload = json.dumps({
        "summary": digest["summary"],
        "detail": digest["detail"],
        "commit_sha": digest["commit_sha"],
        "proposed_stage": digest.get("proposed_stage"),
        "source": "local-push",
    }).encode("utf-8")

    url = args.api.rstrip("/") + "/codebase/snapshot"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
        print(f"Pushed digest (HEAD {digest['commit_sha']}, proposed stage {digest.get('proposed_stage')}) -> {url}")
        print(body)
        return 0
    except Exception as e:
        print(f"ERROR posting to {url}: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
