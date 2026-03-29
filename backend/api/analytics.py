from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta

from db.database import get_db, SocialMetric, ContentScore
from models.schemas import (
    SocialMetricOut,
    ContentScoreOut,
    AnalyticsOverview,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(db: Session = Depends(get_db)):
    """Aggregated analytics overview across all platforms."""
    today = date.today()
    thirty_days_ago = (today - timedelta(days=30)).isoformat()

    # Latest metric per platform
    platforms = ["tiktok", "youtube", "instagram", "twitter"]
    metrics_by_platform = {}
    total_followers = 0
    engagement_rates = []

    for p in platforms:
        latest = (
            db.query(SocialMetric)
            .filter(SocialMetric.platform == p)
            .order_by(SocialMetric.date.desc())
            .first()
        )
        if latest:
            metrics_by_platform[p] = {
                "followers": latest.followers,
                "views": latest.views,
                "likes": latest.likes,
                "engagement_rate": latest.engagement_rate,
                "date": latest.date,
            }
            total_followers += latest.followers
            engagement_rates.append(latest.engagement_rate)

    # Total views last 30 days
    total_views_30d = (
        db.query(func.sum(SocialMetric.views))
        .filter(SocialMetric.date >= thirty_days_ago)
        .scalar()
    ) or 0

    avg_engagement = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0.0

    # Top content by virality score
    top_content = (
        db.query(ContentScore)
        .order_by(ContentScore.virality_score.desc())
        .limit(5)
        .all()
    )

    # Growth trend — daily metrics for all platforms over last 30 days
    growth_trend = (
        db.query(SocialMetric)
        .filter(SocialMetric.date >= thirty_days_ago)
        .order_by(SocialMetric.date.asc())
        .all()
    )

    return AnalyticsOverview(
        metrics_by_platform=metrics_by_platform,
        total_followers=total_followers,
        total_views_30d=total_views_30d,
        avg_engagement_rate=round(avg_engagement, 4),
        top_content=top_content,
        growth_trend=growth_trend,
    )


@router.get("/metrics", response_model=List[SocialMetricOut])
def get_metrics(
    platform: Optional[str] = None,
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """List social metrics, optionally filtered by platform and date range."""
    q = db.query(SocialMetric)
    if platform:
        q = q.filter(SocialMetric.platform == platform)
    if start_date:
        q = q.filter(SocialMetric.date >= start_date)
    if end_date:
        q = q.filter(SocialMetric.date <= end_date)
    return q.order_by(SocialMetric.date.desc()).all()


@router.get("/content-scores", response_model=List[ContentScoreOut])
def get_content_scores(
    sort_by: str = Query("virality_score", description="Sort field"),
    db: Session = Depends(get_db),
):
    """List content scores, sortable by various fields."""
    sort_col = getattr(ContentScore, sort_by, ContentScore.virality_score)
    return db.query(ContentScore).order_by(sort_col.desc()).all()


@router.get("/engagement-trend", response_model=List[SocialMetricOut])
def get_engagement_trend(
    platform: Optional[str] = None,
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db),
):
    """Time series engagement data for charts."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    q = db.query(SocialMetric).filter(SocialMetric.date >= cutoff)
    if platform:
        q = q.filter(SocialMetric.platform == platform)
    return q.order_by(SocialMetric.date.asc()).all()
