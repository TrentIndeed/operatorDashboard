"""
User settings API — change password, delete account, manage config.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import (
    get_db, User, Task, Project, Goal, AISuggestion, NewsBriefing,
    ContentDraft, ContentScheduleItem, SocialMetric, ContentScore,
    MarketGap, GithubRepo,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.post("/change-password")
def change_password(body: dict, db: Session = Depends(get_db)):
    """Change user password."""
    username = body.get("username", "")
    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")

    if not username or not current_password or not new_password:
        raise HTTPException(status_code=400, detail="All fields required")
    if len(new_password) < 3:
        raise HTTPException(status_code=400, detail="Password must be at least 3 characters")

    import hashlib
    auth_secret = os.getenv("AUTH_SECRET", "")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_hash = hashlib.sha256(f"{auth_secret}:{current_password}".encode()).hexdigest()
    if user.password_hash != current_hash:
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    user.password_hash = hashlib.sha256(f"{auth_secret}:{new_password}".encode()).hexdigest()
    db.commit()
    return {"status": "ok", "message": "Password changed"}


@router.post("/delete-account")
def delete_account(body: dict, db: Session = Depends(get_db)):
    """Delete user account and all their data."""
    username = body.get("username", "")
    password = body.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    import hashlib
    auth_secret = os.getenv("AUTH_SECRET", "")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    pw_hash = hashlib.sha256(f"{auth_secret}:{password}".encode()).hexdigest()
    if user.password_hash != pw_hash:
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Delete all user data
    db.query(Task).delete()
    db.query(Project).delete()
    db.query(Goal).delete()
    db.query(AISuggestion).delete()
    db.query(NewsBriefing).delete()
    db.query(ContentDraft).delete()
    db.query(ContentScheduleItem).delete()
    db.query(SocialMetric).delete()
    db.query(ContentScore).delete()
    db.query(MarketGap).delete()
    db.query(GithubRepo).delete()
    db.delete(user)
    db.commit()

    return {"status": "ok", "message": "Account and all data deleted"}


@router.get("/config")
def get_config():
    """Get current configuration (non-sensitive values only)."""
    return {
        "github_owner": os.getenv("GITHUB_OWNER", ""),
        "github_connected": bool(os.getenv("GITHUB_TOKEN")),
        "youtube_connected": bool(os.getenv("GOOGLE_REFRESH_TOKEN")),
        "tiktok_connected": bool(os.getenv("TIKTOK_SESSION_ID")),
        "twitter_connected": bool(os.getenv("TWITTER_CONSUMER_KEY")),
        "email_to": os.getenv("EMAIL_TO", ""),
        "display_name": os.getenv("NEXT_PUBLIC_DISPLAY_NAME", ""),
        "n8n_configured": bool(os.getenv("N8N_WEBHOOK_URL")),
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY")),
    }
