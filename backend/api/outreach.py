"""
Outreach Command Center API — leads CRUD, signal scanner, stats, drafting.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.database import get_db, Lead, OutreachMessage
from models.schemas import LeadOut, LeadUpdate, LeadCreate, OutreachMessageOut, OutreachStats

router = APIRouter(prefix="/outreach", tags=["outreach"])


def _coerce_str(value) -> Optional[str]:
    """Coerce any Claude response field to a clean string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # Join list items (bullet points) with newlines
        return "\n".join(f"• {str(item).strip()}" if not str(item).strip().startswith(("-", "*", "•")) else str(item).strip() for item in value if item)
    if isinstance(value, dict):
        # Join dict values
        return "\n".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def _apply_drafts_to_lead(lead: Lead, result: dict) -> None:
    """Apply Claude-generated drafts to a Lead, coercing types safely."""
    if result.get("draft_dm"):
        lead.draft_dm = _coerce_str(result["draft_dm"])
    if result.get("draft_public_reply"):
        lead.draft_public_reply = _coerce_str(result["draft_public_reply"])
    if result.get("account_summary"):
        lead.account_summary = _coerce_str(result["account_summary"])
    if result.get("include_demo_video"):
        lead.include_demo_video = _coerce_str(result["include_demo_video"])
    if result.get("tier"):
        try:
            lead.tier = int(result["tier"])
        except (ValueError, TypeError):
            pass
    if result.get("tier_reason"):
        lead.tier_reason = _coerce_str(result["tier_reason"])


# --- Background task wrappers ---

def _bg_scan_signals():
    """Background: scan all sources (Reddit, HN, Onshape Forum) for new leads."""
    from db.database import SessionLocal
    from services.signal_scanner import scan_all
    db = SessionLocal()
    try:
        new_leads = scan_all(db)
        # Auto-draft messages for new leads
        if new_leads:
            _bg_draft_batch(new_leads, db)
    except Exception as e:
        print(f"[Outreach] scan failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def _bg_draft_batch(leads, db):
    """Draft messages for a batch of leads."""
    from services.message_drafter import draft_all_for_lead
    drafted = 0
    for lead in leads[:20]:  # Cap at 20 to avoid rate limits
        try:
            data = {
                "username": lead.username,
                "platform": lead.platform,
                "post_text": lead.post_text or lead.message or "",
                "post_url": lead.post_url or lead.source_url or "",
            }
            result = draft_all_for_lead(data)
            if result:
                _apply_drafts_to_lead(lead, result)
                db.commit()
                drafted += 1
        except Exception as e:
            print(f"[Outreach] Draft failed for lead {lead.id}: {e}")
    print(f"[Outreach] Drafted messages for {drafted}/{len(leads)} leads")


def _bg_draft_single(lead_id: int):
    """Background: draft messages for a single lead."""
    from db.database import SessionLocal
    from services.message_drafter import draft_all_for_lead
    db = SessionLocal()
    try:
        lead = db.query(Lead).get(lead_id)
        if not lead:
            return
        data = {
            "username": lead.username,
            "platform": lead.platform,
            "post_text": lead.post_text or lead.message or "",
            "post_url": lead.post_url or lead.source_url or "",
        }
        result = draft_all_for_lead(data)
        if result:
            _apply_drafts_to_lead(lead, result)
            db.commit()
            print(f"[Outreach] Drafted for lead {lead_id}: {lead.username}")
    except Exception as e:
        print(f"[Outreach] Draft single failed: {e}")
    finally:
        db.close()


# --- Endpoints ---

@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    tier: Optional[int] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List leads with optional filters."""
    q = db.query(Lead).order_by(Lead.tier.asc().nullslast(), Lead.created_at.desc())
    if tier:
        q = q.filter(Lead.tier == tier)
    if status:
        q = q.filter(Lead.status == status)
    if platform:
        q = q.filter(Lead.platform.contains(platform))
    if search:
        q = q.filter(
            Lead.username.contains(search) |
            Lead.post_text.contains(search) |
            Lead.message.contains(search)
        )
    return q.offset(offset).limit(limit).all()


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a single lead by ID."""
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/leads", response_model=LeadOut)
def create_lead(body: LeadCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually add a lead (for LinkedIn, Fiverr, Upwork, etc.)."""
    lead = Lead(
        username=body.username,
        platform=body.platform,
        post_url=body.post_url,
        post_text=body.post_text,
        profile_url=body.profile_url,
        source_url=body.source_url or body.post_url,
        message=body.post_text[:200] if body.post_text else None,
        notes=body.notes,
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    # Auto-draft in background
    background_tasks.add_task(_bg_draft_single, lead.id)
    return lead


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, body: LeadUpdate, db: Session = Depends(get_db)):
    """Update a lead's status, drafts, notes, etc."""
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = body.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    # Auto-set timestamps based on status changes
    if body.status == "contacted" and not lead.contacted_at:
        lead.contacted_at = datetime.utcnow()
    elif body.status == "responded" and not lead.responded_at:
        lead.responded_at = datetime.utcnow()

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/leads/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """Delete a lead."""
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"ok": True}


@router.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger the signal scanner to find new leads from Reddit."""
    background_tasks.add_task(_bg_scan_signals)
    return {"status": "scanning", "message": "Scanning Reddit for new leads..."}


@router.post("/leads/{lead_id}/draft")
async def draft_messages(lead_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Generate/regenerate AI drafts for a specific lead."""
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    background_tasks.add_task(_bg_draft_single, lead_id)
    return {"status": "drafting", "message": f"Generating drafts for {lead.username}..."}


@router.post("/leads/{lead_id}/contacted")
def mark_contacted(lead_id: int, db: Session = Depends(get_db)):
    """Mark a lead as contacted. Saves the current draft_dm to messages."""
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = "contacted"
    lead.contacted_at = datetime.utcnow()
    # Save the message to history
    if lead.draft_dm:
        msg = OutreachMessage(
            lead_id=lead.id,
            direction="outbound",
            message_type="dm",
            message_text=lead.draft_dm,
        )
        db.add(msg)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/leads/{lead_id}/follow-up")
def mark_follow_up(lead_id: int, db: Session = Depends(get_db)):
    """Mark that a follow-up was sent."""
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.follow_up_sent = True
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/stats", response_model=OutreachStats)
def get_stats(db: Session = Depends(get_db)):
    """Get outreach pipeline stats."""
    total = db.query(Lead).count()
    tier1 = db.query(Lead).filter(Lead.tier == 1).count()
    tier2 = db.query(Lead).filter(Lead.tier == 2).count()
    tier3 = db.query(Lead).filter(Lead.tier == 3).count()
    new = db.query(Lead).filter(Lead.status == "new").count()
    contacted = db.query(Lead).filter(Lead.status == "contacted").count()
    responded = db.query(Lead).filter(Lead.status == "responded").count()
    interested = db.query(Lead).filter(Lead.status == "interested").count()
    beta = db.query(Lead).filter(Lead.status == "beta_user").count()
    paying = db.query(Lead).filter(Lead.status == "paying").count()

    # Follow-ups due: contacted 4+ days ago, no response, no follow-up sent
    cutoff = datetime.utcnow() - timedelta(days=4)
    follow_ups = db.query(Lead).filter(
        Lead.status == "contacted",
        Lead.contacted_at != None,
        Lead.contacted_at < cutoff,
        Lead.follow_up_sent == False,
    ).count()

    return OutreachStats(
        total_leads=total,
        tier1_count=tier1,
        tier2_count=tier2,
        tier3_count=tier3,
        new_count=new,
        contacted_count=contacted,
        responded_count=responded,
        interested_count=interested,
        beta_count=beta,
        paying_count=paying,
        follow_ups_due=follow_ups,
    )


@router.get("/follow-ups", response_model=list[LeadOut])
def get_follow_ups(db: Session = Depends(get_db)):
    """Get leads that need follow-up (contacted 4+ days ago, no response)."""
    cutoff = datetime.utcnow() - timedelta(days=4)
    return db.query(Lead).filter(
        Lead.status == "contacted",
        Lead.contacted_at != None,
        Lead.contacted_at < cutoff,
        Lead.follow_up_sent == False,
    ).order_by(Lead.contacted_at.asc()).all()


@router.get("/leads/{lead_id}/messages", response_model=list[OutreachMessageOut])
def get_lead_messages(lead_id: int, db: Session = Depends(get_db)):
    """Get message history for a lead."""
    return db.query(OutreachMessage).filter(
        OutreachMessage.lead_id == lead_id
    ).order_by(OutreachMessage.created_at.asc()).all()


@router.post("/parse-reply")
def parse_email_reply(body: dict, db: Session = Depends(get_db)):
    """
    Parse an email body for lead status codes (#L142 contacted) and update.
    Called by n8n when it receives a reply to a digest email.

    Body: {"text": "the full email body"}
    """
    from services.reply_parser import parse_reply
    text = body.get("text", "") or body.get("body", "")
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text' in body")
    return parse_reply(text, db)
