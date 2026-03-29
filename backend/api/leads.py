from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from db.database import get_db, Lead, CommentReply, WaitlistSignup
from models.schemas import (
    LeadOut,
    LeadUpdate,
    CommentReplyOut,
    CommentReplyUpdate,
    WaitlistSignupOut,
    WaitlistSignupCreate,
)

router = APIRouter(prefix="/leads", tags=["leads"])


# --- Leads ---

@router.get("/", response_model=List[LeadOut])
def get_leads(
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Lead)
    if category:
        q = q.filter(Lead.category == category)
    if status:
        q = q.filter(Lead.status == status)
    return q.order_by(Lead.created_at.desc()).all()


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, update: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/generate-dm")
def generate_dm(lead_id: int, db: Session = Depends(get_db)):
    """Generate a personalized DM draft for a lead via Claude."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    from agents.lead_agent import generate_dm_draft
    dm = generate_dm_draft(lead)
    lead.dm_draft = dm
    db.commit()
    db.refresh(lead)
    return {"ok": True, "dm_draft": dm}


# --- Comment Replies ---

@router.get("/comment-replies", response_model=List[CommentReplyOut])
def get_comment_replies(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(CommentReply)
    if status:
        q = q.filter(CommentReply.status == status)
    return q.order_by(CommentReply.created_at.desc()).all()


@router.patch("/comment-replies/{reply_id}", response_model=CommentReplyOut)
def update_comment_reply(
    reply_id: int,
    update: CommentReplyUpdate,
    db: Session = Depends(get_db),
):
    reply = db.query(CommentReply).filter(CommentReply.id == reply_id).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Comment reply not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(reply, field, value)
    db.commit()
    db.refresh(reply)
    return reply


@router.post("/comment-replies/{reply_id}/generate")
def generate_reply(reply_id: int, db: Session = Depends(get_db)):
    """Generate a reply for a comment via Claude."""
    reply = db.query(CommentReply).filter(CommentReply.id == reply_id).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Comment reply not found")
    from agents.lead_agent import generate_comment_reply
    draft = generate_comment_reply(reply.original_comment, reply.platform)
    reply.reply_draft = draft
    db.commit()
    db.refresh(reply)
    return {"ok": True, "reply_draft": draft}


# --- Waitlist ---

@router.get("/waitlist", response_model=List[WaitlistSignupOut])
def get_waitlist(db: Session = Depends(get_db)):
    return db.query(WaitlistSignup).order_by(WaitlistSignup.signed_up_at.desc()).all()


@router.post("/waitlist", response_model=WaitlistSignupOut)
def add_waitlist_signup(signup: WaitlistSignupCreate, db: Session = Depends(get_db)):
    existing = db.query(WaitlistSignup).filter(WaitlistSignup.email == signup.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already on waitlist")
    db_signup = WaitlistSignup(**signup.model_dump())
    db.add(db_signup)
    db.commit()
    db.refresh(db_signup)
    return db_signup


@router.get("/waitlist/stats")
def get_waitlist_stats(db: Session = Depends(get_db)):
    """Waitlist stats: total, by source, growth."""
    total = db.query(WaitlistSignup).filter(WaitlistSignup.status == "active").count()
    by_source = (
        db.query(WaitlistSignup.source, func.count(WaitlistSignup.id))
        .filter(WaitlistSignup.status == "active")
        .group_by(WaitlistSignup.source)
        .all()
    )
    converted = db.query(WaitlistSignup).filter(WaitlistSignup.status == "converted").count()

    return {
        "total": total,
        "converted": converted,
        "by_source": {source or "unknown": count for source, count in by_source},
    }
