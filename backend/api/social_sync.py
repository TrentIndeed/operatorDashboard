"""Sync real data from connected social media platforms."""
from datetime import datetime, date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db, ContentScore, SocialMetric
from services.youtube import fetch_my_videos, fetch_channel_stats
from services.tiktok import fetch_my_tiktok_videos, fetch_tiktok_profile_stats
from services.twitter import fetch_my_tweets, fetch_twitter_profile_stats

router = APIRouter(prefix="/social", tags=["social-sync"])


def _parse_datetime(val):
    """Parse a datetime string or return None."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _upsert_content_scores(db: Session, items: list[dict], platform: str) -> int:
    """Upsert content scores, handling datetime conversion."""
    count = 0
    for v in items:
        v["posted_at"] = _parse_datetime(v.get("posted_at"))
        existing = db.query(ContentScore).filter(
            ContentScore.external_id == v["external_id"],
            ContentScore.platform == platform,
        ).first()
        if existing:
            for key, val in v.items():
                if key != "external_id":
                    setattr(existing, key, val)
        else:
            db.add(ContentScore(**v))
        count += 1
    return count


@router.post("/sync")
async def sync_all_platforms(db: Session = Depends(get_db)):
    """Pull latest data from all connected social platforms."""
    results = {"synced": [], "errors": []}

    # YouTube
    try:
        yt_videos = await fetch_my_videos(20)
        if yt_videos:
            n = _upsert_content_scores(db, yt_videos, "youtube")
            results["synced"].append(f"youtube: {n} videos")

        yt_stats = await fetch_channel_stats()
        if yt_stats:
            today = date.today().isoformat()
            existing_metric = db.query(SocialMetric).filter(
                SocialMetric.platform == "youtube",
                SocialMetric.date == today
            ).first()
            if existing_metric:
                existing_metric.followers = yt_stats["followers"]
            else:
                db.add(SocialMetric(
                    platform="youtube", date=today,
                    followers=yt_stats["followers"],
                    views=0, likes=0, comments=0, shares=0, saves=0,
                ))
    except Exception as e:
        results["errors"].append(f"youtube: {str(e)}")

    # TikTok
    try:
        tt_videos = await fetch_my_tiktok_videos(20)
        if tt_videos:
            n = _upsert_content_scores(db, tt_videos, "tiktok")
            results["synced"].append(f"tiktok: {n} videos")

        tt_stats = await fetch_tiktok_profile_stats()
        if tt_stats:
            today = date.today().isoformat()
            existing_metric = db.query(SocialMetric).filter(
                SocialMetric.platform == "tiktok",
                SocialMetric.date == today
            ).first()
            if existing_metric:
                existing_metric.followers = tt_stats["followers"]
            else:
                db.add(SocialMetric(
                    platform="tiktok", date=today,
                    followers=tt_stats["followers"],
                    views=0, likes=0, comments=0, shares=0, saves=0,
                ))
    except Exception as e:
        results["errors"].append(f"tiktok: {str(e)}")

    # Twitter
    try:
        tw_tweets = await fetch_my_tweets(20)
        if tw_tweets:
            n = _upsert_content_scores(db, tw_tweets, "twitter")
            results["synced"].append(f"twitter: {n} tweets")

        tw_stats = await fetch_twitter_profile_stats()
        if tw_stats:
            today = date.today().isoformat()
            existing_metric = db.query(SocialMetric).filter(
                SocialMetric.platform == "twitter",
                SocialMetric.date == today
            ).first()
            if existing_metric:
                existing_metric.followers = tw_stats["followers"]
            else:
                db.add(SocialMetric(
                    platform="twitter", date=today,
                    followers=tw_stats["followers"],
                    views=0, likes=0, comments=0, shares=0, saves=0,
                ))
    except Exception as e:
        results["errors"].append(f"twitter: {str(e)}")

    db.commit()
    return results


@router.get("/status")
async def check_connections():
    """Check which platforms have credentials configured."""
    import os
    return {
        "youtube": bool(os.getenv("GOOGLE_REFRESH_TOKEN")),
        "tiktok": bool(os.getenv("TIKTOK_SESSION_ID")),
        "twitter": bool(os.getenv("TWITTER_API_SECRET")),
        "instagram": bool(os.getenv("INSTAGRAM_SESSION_ID")),
    }
