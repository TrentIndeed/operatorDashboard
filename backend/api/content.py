"""
Content Engine API routes — drafts, schedule, hook generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from db.database import get_db, ContentDraft, ContentScheduleItem
from models.schemas import (
    ContentDraftOut, ContentDraftCreate, ContentDraftUpdate,
    ScheduleItemOut, ScheduleItemCreate, ScheduleItemUpdate,
    HookRequest, HookResponse,
)

router = APIRouter(prefix="/content", tags=["content"])


# --- Content Drafts ---

@router.get("/drafts/", response_model=List[ContentDraftOut])
def list_drafts(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    project_tag: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ContentDraft)
    if status:
        q = q.filter(ContentDraft.status == status)
    if platform:
        q = q.filter(ContentDraft.platform == platform)
    if project_tag:
        q = q.filter(ContentDraft.project_tag == project_tag)
    return q.order_by(ContentDraft.created_at.desc()).all()


@router.post("/drafts/", response_model=ContentDraftOut)
def create_draft(draft: ContentDraftCreate, db: Session = Depends(get_db)):
    db_draft = ContentDraft(**draft.model_dump())
    db.add(db_draft)
    db.commit()
    db.refresh(db_draft)
    return db_draft


@router.patch("/drafts/{draft_id}", response_model=ContentDraftOut)
def update_draft(draft_id: int, update: ContentDraftUpdate, db: Session = Depends(get_db)):
    db_draft = db.query(ContentDraft).filter(ContentDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(db_draft, field, value)
    db_draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_draft)
    return db_draft


@router.post("/drafts/{draft_id}/approve", response_model=ContentDraftOut)
def approve_draft(
    draft_id: int,
    scheduled_at: Optional[str] = Query(None, description="ISO datetime to schedule, e.g. 2026-03-29T10:00"),
    db: Session = Depends(get_db),
):
    db_draft = db.query(ContentDraft).filter(ContentDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    db_draft.status = "approved"
    db_draft.updated_at = datetime.utcnow()

    # Optionally create a schedule item
    if scheduled_at:
        db_draft.status = "scheduled"
        db_draft.suggested_post_time = scheduled_at
        schedule_item = ContentScheduleItem(
            draft_id=db_draft.id,
            title=db_draft.title,
            platform=db_draft.platform,
            scheduled_at=datetime.fromisoformat(scheduled_at),
            status="scheduled",
            block_type="content",
        )
        db.add(schedule_item)

    db.commit()
    db.refresh(db_draft)
    return db_draft


@router.post("/drafts/{draft_id}/decline", response_model=ContentDraftOut)
def decline_draft(
    draft_id: int,
    feedback: Optional[str] = Query(None, description="Feedback for why the draft was declined"),
    db: Session = Depends(get_db),
):
    db_draft = db.query(ContentDraft).filter(ContentDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    db_draft.status = "declined"
    if feedback:
        db_draft.feedback = feedback
    db_draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_draft)
    return db_draft


@router.post("/drafts/{draft_id}/remix", response_model=ContentDraftOut)
def remix_draft(
    draft_id: int,
    feedback: str = Query(..., description="Feedback/instructions for the remix"),
    db: Session = Depends(get_db),
):
    db_draft = db.query(ContentDraft).filter(ContentDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    from agents.content_drafter import remix_content
    result = remix_content(db_draft.body, feedback, db_draft.platform)

    new_draft = ContentDraft(
        title=result.get("title", f"Remix: {db_draft.title}"),
        body=result.get("body", ""),
        platform=db_draft.platform,
        content_type=db_draft.content_type,
        hook=result.get("hook"),
        cta=result.get("cta"),
        hashtags=result.get("hashtags"),
        status="draft",
        ai_generated=True,
        remix_of_id=db_draft.id,
        feedback=feedback,
        project_tag=db_draft.project_tag,
        hook_score=result.get("hook_score"),
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)
    return new_draft


@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: int, db: Session = Depends(get_db)):
    db_draft = db.query(ContentDraft).filter(ContentDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    db.delete(db_draft)
    db.commit()
    return {"ok": True}


# --- Content Schedule ---

@router.get("/schedule/", response_model=List[ScheduleItemOut])
def list_schedule(
    start: Optional[str] = Query(None, description="Start date ISO, e.g. 2026-03-28"),
    end: Optional[str] = Query(None, description="End date ISO, e.g. 2026-04-04"),
    db: Session = Depends(get_db),
):
    q = db.query(ContentScheduleItem)
    if start:
        q = q.filter(ContentScheduleItem.scheduled_at >= datetime.fromisoformat(start))
    if end:
        q = q.filter(ContentScheduleItem.scheduled_at <= datetime.fromisoformat(end))
    return q.order_by(ContentScheduleItem.scheduled_at.asc()).all()


@router.post("/schedule/", response_model=ScheduleItemOut)
def create_schedule_item(item: ScheduleItemCreate, db: Session = Depends(get_db)):
    db_item = ContentScheduleItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/schedule/{item_id}", response_model=ScheduleItemOut)
def update_schedule_item(item_id: int, update: ScheduleItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(ContentScheduleItem).filter(ContentScheduleItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/schedule/{item_id}")
def delete_schedule_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(ContentScheduleItem).filter(ContentScheduleItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    db.delete(db_item)
    db.commit()
    return {"ok": True}


# --- Hook Generation ---

@router.post("/generate-hooks", response_model=HookResponse)
def generate_hooks_endpoint(req: HookRequest, db: Session = Depends(get_db)):
    from agents.content_drafter import generate_hooks
    variations = generate_hooks(req.topic, req.platform, req.project_tag)
    return HookResponse(variations=variations)
