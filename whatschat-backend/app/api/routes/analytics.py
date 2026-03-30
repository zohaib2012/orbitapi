from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Message, Campaign
from app.schemas.schemas import AnalyticsOverview, DailyMetric, DeviceBreakdown

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_date_range(period: str):
    now = datetime.utcnow()
    if period == "7days":
        return now - timedelta(days=7)
    elif period == "30days":
        return now - timedelta(days=30)
    elif period == "90days":
        return now - timedelta(days=90)
    return now - timedelta(days=7)


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(
    period: str = Query("7days", enum=["7days", "30days", "90days"]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    since = get_date_range(period)

    # Get all campaigns for this user
    campaign_ids = [c.id for c in db.query(Campaign.id).filter(Campaign.user_id == current_user.id).all()]

    msgs = db.query(Message).filter(
        Message.campaign_id.in_(campaign_ids),
        Message.sent_at >= since
    )

    total = msgs.count()
    delivered = msgs.filter(Message.is_delivered == True).count()
    read = msgs.filter(Message.is_read == True).count()
    clicked = msgs.filter(Message.is_clicked == True).count()

    return {
        "total_sent": total,
        "delivery_rate": round((delivered / total * 100) if total else 0, 1),
        "read_rate": round((read / total * 100) if total else 0, 1),
        "click_rate": round((clicked / total * 100) if total else 0, 1),
        "avg_response_time": 1.8,
        "total_delivered": delivered,
        "total_read": read,
        "total_clicked": clicked,
    }


@router.get("/daily", response_model=List[DailyMetric])
def get_daily_metrics(
    period: str = Query("7days", enum=["7days", "30days"]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns per-day message metrics for charting"""
    days = 7 if period == "7days" else 30
    since = datetime.utcnow() - timedelta(days=days)
    campaign_ids = [c.id for c in db.query(Campaign.id).filter(Campaign.user_id == current_user.id).all()]

    results = []
    for i in range(days):
        day = since + timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0)
        day_end = day.replace(hour=23, minute=59, second=59)

        msgs = db.query(Message).filter(
            Message.campaign_id.in_(campaign_ids),
            Message.sent_at >= day_start,
            Message.sent_at <= day_end
        )
        sent = msgs.count()
        results.append({
            "date": day.strftime("%b %d"),
            "sent": sent,
            "delivered": msgs.filter(Message.is_delivered == True).count(),
            "read": msgs.filter(Message.is_read == True).count(),
            "clicked": msgs.filter(Message.is_clicked == True).count(),
        })

    return results


@router.get("/devices", response_model=DeviceBreakdown)
def get_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Device breakdown — placeholder until real device tracking is added"""
    total_contacts = len(current_user.contacts)
    return {
        "android": int(total_contacts * 0.65),
        "ios": int(total_contacts * 0.31),
        "web": int(total_contacts * 0.04),
    }


@router.get("/campaigns")
def get_campaign_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Per-campaign read rate performance"""
    campaigns = db.query(Campaign).filter(
        Campaign.user_id == current_user.id,
        Campaign.total_sent > 0
    ).order_by(Campaign.created_at.desc()).limit(10).all()

    return [
        {
            "name": c.name,
            "sent": c.total_sent,
            "read_rate": round((c.total_read / c.total_sent * 100) if c.total_sent else 0, 1),
            "status": c.status,
        }
        for c in campaigns
    ]