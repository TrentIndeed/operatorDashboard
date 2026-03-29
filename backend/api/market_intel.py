from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db, MarketGap, Competitor, CompetitorPost
from models.schemas import MarketGapOut, CompetitorOut, CompetitorPostOut

router = APIRouter(prefix="/market", tags=["market-intel"])


# --- Market Gaps ---

@router.get("/gaps", response_model=List[MarketGapOut])
def get_market_gaps(status: str = None, db: Session = Depends(get_db)):
    q = db.query(MarketGap)
    if status:
        q = q.filter(MarketGap.status == status)
    return q.order_by(MarketGap.opportunity_score.desc()).all()


@router.post("/gaps/{gap_id}/dismiss")
def dismiss_gap(gap_id: int, db: Session = Depends(get_db)):
    gap = db.query(MarketGap).filter(MarketGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=404, detail="Market gap not found")
    gap.status = "dismissed"
    db.commit()
    return {"ok": True}


@router.post("/gaps/{gap_id}/act")
def act_on_gap(gap_id: int, db: Session = Depends(get_db)):
    gap = db.query(MarketGap).filter(MarketGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=404, detail="Market gap not found")
    gap.status = "acted"
    db.commit()
    return {"ok": True}


# --- Competitors ---

@router.get("/competitors", response_model=List[CompetitorOut])
def get_competitors(db: Session = Depends(get_db)):
    return db.query(Competitor).order_by(Competitor.created_at.desc()).all()


@router.get("/competitors/{competitor_id}/posts", response_model=List[CompetitorPostOut])
def get_competitor_posts(competitor_id: int, db: Session = Depends(get_db)):
    competitor = db.query(Competitor).filter(Competitor.id == competitor_id).first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return (
        db.query(CompetitorPost)
        .filter(CompetitorPost.competitor_id == competitor_id)
        .order_by(CompetitorPost.posted_at.desc())
        .all()
    )


# --- Market Scan (AI) ---

def _bg_scan_market():
    """Background wrapper with its own DB session."""
    from db.database import SessionLocal
    from agents.market_intel import scan_market_gaps
    db = SessionLocal()
    try:
        scan_market_gaps(db)
    except Exception as e:
        print(f"[Market] scan_market_gaps failed: {e}")
    finally:
        db.close()


@router.post("/scan")
async def scan_market(background_tasks: BackgroundTasks):
    """Trigger Claude to scan for market gaps and opportunities."""
    background_tasks.add_task(_bg_scan_market)
    return {"status": "scanning", "message": "Claude is scanning for market gaps..."}
