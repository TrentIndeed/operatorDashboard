"""
Optional: populate the DB with richer seed data.
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
            headline="Anthropic releases Claude 4 with extended context and improved tool use",
            summary="Claude 4 adds 1M token context and significantly better multi-step tool use — directly useful for the mesh2param analysis pipeline.",
            category="ai",
            relevance_score=0.95,
            suggested_action="Evaluate Claude 4 for the surface segmentation reasoning step in mesh2param Stage 4.",
            briefing_date=today,
        ),
        NewsBriefing(
            headline="Backflip AI announces $12M Series A, expanding mesh conversion coverage",
            summary="Backflip AI raised $12M and plans to expand STL-to-CAD features. They're adding Fusion 360 export. Reviews note it still struggles with organic shapes.",
            category="competitor",
            relevance_score=0.9,
            suggested_action="Post a comparison video: 'I tried Backflip AI vs mesh2param on this organic part — here's the difference.'",
            briefing_date=today,
        ),
        NewsBriefing(
            headline="TikTok algorithm change: saves now weighted 3x more than likes for algorithmic reach",
            summary="TikTok reportedly updated ranking to weight saves much more heavily. Educational and reference content (save-worthy) will get more distribution.",
            category="marketing",
            relevance_score=0.85,
            suggested_action="Add 'save this for later' CTAs to all technical tutorial videos. Frame content as reference material.",
            briefing_date=today,
        ),
        NewsBriefing(
            headline="OpenCASCADE 7.9 released with improved mesh healing algorithms",
            summary="OCCT 7.9 ships with better BRep healing from mesh input. Could improve mesh2param's preprocessing pipeline quality.",
            category="cad",
            relevance_score=0.75,
            suggested_action="Test OCCT 7.9 mesh healing on the Stage 3 test suite before upgrading.",
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
