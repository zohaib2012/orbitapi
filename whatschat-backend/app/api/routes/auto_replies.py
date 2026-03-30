from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, AutoReply, AutoReplyType

router = APIRouter(prefix="/auto-replies", tags=["Auto Replies"])


class AutoReplyCreate(BaseModel):
    name:            str
    trigger_keyword: str
    match_type:      str = "contains"   # exact/contains/starts_with
    reply_type:      str = "text"       # text/image/video/audio/document
    reply_text:      Optional[str] = None
    media_url:       Optional[str] = None
    media_caption:   Optional[str] = None
    is_active:       bool = True

class AutoReplyUpdate(AutoReplyCreate):
    pass


@router.get("/")
def get_auto_replies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    replies = db.query(AutoReply).filter(AutoReply.user_id == current_user.id).order_by(AutoReply.created_at.desc()).all()
    return [{
        "id":              r.id,
        "name":            r.name,
        "trigger_keyword": r.trigger_keyword,
        "match_type":      r.match_type,
        "reply_type":      r.reply_type,
        "reply_text":      r.reply_text,
        "media_url":       r.media_url,
        "media_caption":   r.media_caption,
        "is_active":       r.is_active,
        "total_triggered": r.total_triggered,
        "created_at":      r.created_at.isoformat() if r.created_at else None,
    } for r in replies]


@router.post("/", status_code=201)
def create_auto_reply(data: AutoReplyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.reply_type == "text" and not data.reply_text:
        raise HTTPException(400, "Text reply ke liye reply_text zaroori hai")
    if data.reply_type in ["image","video","audio","document"] and not data.media_url:
        raise HTTPException(400, "Media reply ke liye media_url zaroori hai")
    reply = AutoReply(user_id=current_user.id, **data.model_dump())
    db.add(reply); db.commit(); db.refresh(reply)
    return {"message": "Auto reply created", "id": reply.id}


@router.put("/{reply_id}")
def update_auto_reply(reply_id: int, data: AutoReplyUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reply = db.query(AutoReply).filter(AutoReply.id == reply_id, AutoReply.user_id == current_user.id).first()
    if not reply: raise HTTPException(404, "Auto reply not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reply, field, value)
    db.commit()
    return {"message": "Updated"}


@router.delete("/{reply_id}")
def delete_auto_reply(reply_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reply = db.query(AutoReply).filter(AutoReply.id == reply_id, AutoReply.user_id == current_user.id).first()
    if not reply: raise HTTPException(404, "Not found")
    db.delete(reply); db.commit()
    return {"message": "Deleted"}


@router.post("/{reply_id}/toggle")
def toggle_auto_reply(reply_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reply = db.query(AutoReply).filter(AutoReply.id == reply_id, AutoReply.user_id == current_user.id).first()
    if not reply: raise HTTPException(404, "Not found")
    reply.is_active = not reply.is_active
    db.commit()
    return {"is_active": reply.is_active}


def find_matching_reply(db: Session, user_id: int, incoming_text: str) -> Optional[AutoReply]:
    """Incoming message ke liye matching auto reply dhundo"""
    replies = db.query(AutoReply).filter(
        AutoReply.user_id == user_id,
        AutoReply.is_active == True
    ).all()
    text_lower = incoming_text.lower().strip()
    for reply in replies:
        kw = reply.trigger_keyword.lower().strip()
        if reply.match_type == "exact"       and text_lower == kw:          return reply
        if reply.match_type == "contains"    and kw in text_lower:          return reply
        if reply.match_type == "starts_with" and text_lower.startswith(kw): return reply
    return None