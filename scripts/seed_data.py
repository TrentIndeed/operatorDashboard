"""
Optional: populate the DB with sample briefing data.
Run from the backend directory: python ../scripts/seed_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from db.database import init_db, SessionLocal, NewsBriefing
from datetime import date

def seed_briefing():
    db = SessionLocal()
    today = date.today().isoformat()

    items = [
        NewsBriefing(
            headline="Claude releases new model family with extended context and tool use",
            summary="Extended context and improved multi-step tool use — useful for complex AI agent workflows.",
            category="ai",
            relevance_score=0.95,
            suggested_action="Evaluate the new model for your AI agent pipelines.",
            briefing_date=today,
        ),
        NewsBriefing(
            headline="Competitor raises Series A, expanding into your market",
            summary="A competitor in your space raised funding and is expanding features. Check their positioning.",
            category="competitor",
            relevance_score=0.9,
            suggested_action="Create a comparison post highlighting your differentiators.",
            briefing_date=today,
        ),
        NewsBriefing(
            headline="TikTok algorithm update: saves now weighted 3x more than likes",
            summary="Educational and reference content (save-worthy) will get significantly more distribution.",
            category="marketing",
            relevance_score=0.85,
            suggested_action="Add 'save this for later' CTAs to all tutorial videos. Frame content as reference material.",
            briefing_date=today,
        ),
        NewsBriefing(
            headline="New open-source tool released in your industry",
            summary="A new open-source project could improve your development pipeline or be a collaboration opportunity.",
            category="industry",
            relevance_score=0.75,
            suggested_action="Test it against your current toolchain before committing.",
            briefing_date=today,
        ),
    ]

    for item in items:
        db.add(item)
    db.commit()
    print(f"Seeded {len(items)} briefing items for {today}")
    db.close()

if __name__ == "__main__":
    init_db()
    seed_briefing()
    print("Done.")
