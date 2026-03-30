from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, MessageLog, MessageDirection

router = APIRouter(prefix="/message-log", tags=["Message Log"])


@router.get("/")
def get_message_log(
    direction: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(MessageLog).filter(MessageLog.user_id == current_user.id)
    if direction: query = query.filter(MessageLog.direction == direction)
    if search:    query = query.filter(MessageLog.contact_phone.contains(search) | MessageLog.contact_name.contains(search))
    total = query.count()
    logs  = query.order_by(MessageLog.sent_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "logs": [{
            "id":            l.id,
            "contact_phone": l.contact_phone,
            "contact_name":  l.contact_name,
            "direction":     l.direction,
            "message_type":  l.message_type,
            "content":       l.content,
            "media_url":     l.media_url,
            "is_delivered":  l.is_delivered,
            "is_read":       l.is_read,
            "sent_at":       l.sent_at.isoformat() if l.sent_at else None,
            "delivered_at":  l.delivered_at.isoformat() if l.delivered_at else None,
            "read_at":       l.read_at.isoformat() if l.read_at else None,
        } for l in logs]
    }


@router.get("/stats")
def get_log_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    base = db.query(MessageLog).filter(MessageLog.user_id == current_user.id)
    return {
        "total_sent":      base.filter(MessageLog.direction == MessageDirection.outbound).count(),
        "total_received":  base.filter(MessageLog.direction == MessageDirection.inbound).count(),
        "total_delivered": base.filter(MessageLog.is_delivered == True).count(),
        "total_read":      base.filter(MessageLog.is_read == True).count(),
    }