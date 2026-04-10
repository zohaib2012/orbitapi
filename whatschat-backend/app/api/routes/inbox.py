# app/api/routes/inbox.py

import os
import uuid
import aiofiles # type: ignore
import subprocess
import tempfile
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, InboxMessage, MessageDirection, FavoriteConversation

router = APIRouter(prefix="/inbox", tags=["Inbox"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── MODELS ───────────────────────────────────────────────────────────────────

class SendReply(BaseModel):
    customer_phone:    str
    message:           str
    message_type:      str           = "text"
    media_url:         Optional[str] = None
    quoted_message_id: Optional[str] = None


# ─── GET: Inbox list ──────────────────────────────────────────────────────────

@router.get("/")
def get_inbox(
    search:       Optional[str] = Query(None),
    unread_only:  bool          = False,
    skip:         int           = 0,
    limit:        int           = 50,
    db:           Session       = Depends(get_db),
    current_user: User          = Depends(get_current_user),
):
    query = db.query(InboxMessage).filter(InboxMessage.user_id == current_user.id)
    if search:
        query = query.filter(InboxMessage.customer_phone.contains(search))
    if unread_only:
        query = query.filter(
            InboxMessage.is_read   == False,
            InboxMessage.direction == MessageDirection.inbound,
        )
    total = query.count()
    msgs  = query.order_by(InboxMessage.received_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "messages": [_msg_dict(m) for m in msgs],
    }


# ─── GET: Conversations list ──────────────────────────────────────────────────

@router.get("/conversations")
def get_conversations(
    skip:         int     = 0,
    limit:        int     = 500,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    from sqlalchemy import func, desc

    subq = db.query(
        InboxMessage.customer_phone,
        func.max(InboxMessage.received_at).label("last_msg_time"),
    ).filter(InboxMessage.user_id == current_user.id)\
     .group_by(InboxMessage.customer_phone).subquery()

    conversations = []
    # Use skip and limit for pagination
    rows = db.query(subq).order_by(desc(subq.c.last_msg_time)).offset(skip).limit(limit).all()
    
    for row in rows:
        last_msg = db.query(InboxMessage).filter(
            InboxMessage.user_id        == current_user.id,
            InboxMessage.customer_phone == row.customer_phone,
        ).order_by(InboxMessage.received_at.desc()).first()

        unread = db.query(InboxMessage).filter(
            InboxMessage.user_id        == current_user.id,
            InboxMessage.customer_phone == row.customer_phone,
            InboxMessage.direction      == MessageDirection.inbound,
            InboxMessage.is_read        == False,
        ).count()

        is_fav = db.query(FavoriteConversation).filter(
            FavoriteConversation.user_id == current_user.id,
            FavoriteConversation.customer_phone == row.customer_phone
        ).first() is not None

        last_content = last_msg.content if last_msg else None
        if last_msg and last_msg.message_type in ("image", "video", "audio"):
            icons        = {"image": "📷 Image", "video": "🎥 Video", "audio": "🎵 Audio"}
            last_content = icons.get(last_msg.message_type, last_content)

        conversations.append({
            "customer_phone":    row.customer_phone,
            "customer_name":     last_msg.customer_name  if last_msg else None,
            "last_message":      last_content,
            "last_message_type": last_msg.message_type   if last_msg else "text",
            "last_time":         last_msg.received_at.isoformat() if last_msg and last_msg.received_at else None,
            "unread_count":      unread,
            "is_favorite":       is_fav,
            "direction":         last_msg.direction       if last_msg else None,
            "duration":          getattr(last_msg, "duration", None),
        })
    return conversations


# ─── GET: Ek customer ki puri conversation ────────────────────────────────────

@router.get("/conversation/{phone}")
def get_conversation_messages(
    phone:        str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    msgs = db.query(InboxMessage).filter(
        InboxMessage.user_id        == current_user.id,
        InboxMessage.customer_phone == phone,
    ).order_by(InboxMessage.received_at.asc()).all()

    db.query(InboxMessage).filter(
        InboxMessage.user_id        == current_user.id,
        InboxMessage.customer_phone == phone,
        InboxMessage.direction      == MessageDirection.inbound,
    ).update({"is_read": True})
    db.commit()

    return [_msg_dict(m) for m in msgs]


# ─── DELETE: Ek customer ki puri conversation delete karo ─────────────────────

@router.delete("/conversation/{phone}")
def delete_conversation_messages(
    phone:        str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    db.query(InboxMessage).filter(
        InboxMessage.user_id        == current_user.id,
        InboxMessage.customer_phone == phone,
    ).delete()
    db.commit()
    return {"message": "Conversation deleted successfully"}


# ─── POST: Toggle Conversation Favorite ──────────────────────────────────────

@router.post("/conversation/{phone}/favorite")
def toggle_conversation_favorite(
    phone:        str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    fav = db.query(FavoriteConversation).filter(
        FavoriteConversation.user_id == current_user.id,
        FavoriteConversation.customer_phone == phone
    ).first()

    if fav:
        db.delete(fav)
        is_favorite = False
    else:
        new_fav = FavoriteConversation(user_id=current_user.id, customer_phone=phone)
        db.add(new_fav)
        is_favorite = True

    db.commit()
    return {"message": "Success", "is_favorite": is_favorite, "customer_phone": phone}


# ─── DELETE: Single message by ID ──────────────────────────────────────

@router.delete("/message/{msg_id}")
def delete_single_message(
    msg_id:       int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    msg = db.query(InboxMessage).filter(
        InboxMessage.id      == msg_id,
        InboxMessage.user_id == current_user.id,
    ).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    db.delete(msg)
    db.commit()
    return {"message": "Message deleted", "id": msg_id}


# ─── GET: Online / Last Seen status ────────────────────────────────────

@router.get("/status/{phone}")
def get_contact_status(
    phone:        str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Return online status based on last message received time.
    'online'  = message within last 2 minutes
    'recent'  = within last 10 minutes
    'offline' = older than 10 minutes"""
    last_msg = db.query(InboxMessage).filter(
        InboxMessage.user_id        == current_user.id,
        InboxMessage.customer_phone == phone,
        InboxMessage.direction      == MessageDirection.inbound,
    ).order_by(InboxMessage.received_at.desc()).first()

    if not last_msg or not last_msg.received_at:
        return {"status": "offline", "last_seen": None}

    now       = datetime.utcnow()
    last_seen = last_msg.received_at.replace(tzinfo=None)
    diff_mins = (now - last_seen).total_seconds() / 60

    if diff_mins < 2:
        status = "online"
    elif diff_mins < 10:
        status = "recent"
    else:
        status = "offline"

    return {
        "status":    status,
        "last_seen": last_msg.received_at.isoformat(),
        "phone":     phone,
    }


# ─── GET: Starred messages for a conversation ────────────────────────────────

@router.get("/starred/{phone}")
def get_starred_messages(
    phone:        str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    msgs = db.query(InboxMessage).filter(
        InboxMessage.user_id        == current_user.id,
        InboxMessage.customer_phone == phone,
        InboxMessage.is_starred     == True,
    ).order_by(InboxMessage.received_at.asc()).all()
    return [_msg_dict(m) for m in msgs]


# ─── POST: Star/unstar toggle ────────────────────────────────────────────────

@router.post("/star/{msg_id}")
def toggle_star(
    msg_id:       int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    msg = db.query(InboxMessage).filter(
        InboxMessage.id      == msg_id,
        InboxMessage.user_id == current_user.id,
    ).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    msg.is_starred = not msg.is_starred
    db.commit()
    return {"is_starred": msg.is_starred, "message_id": msg_id}


# ─── POST: Text reply ─────────────────────────────────────────────────────────

@router.post("/reply")
async def send_reply(
    data:         SendReply,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    from app.services.whatsapp_service import send_whatsapp_message, send_whatsapp_media
    from app.models.user import MessageLog

    if not current_user.whatsapp_connected:
        raise HTTPException(400, "WhatsApp connected nahi hai")

    # ── FIX: WA quoted ID resolve karna ──
    wa_quoted_id = None
    quoted_id = None
    if data.quoted_message_id:
        try:
            quoted_id = int(data.quoted_message_id)
            q_msg = db.query(InboxMessage).filter(InboxMessage.id == quoted_id, InboxMessage.user_id == current_user.id).first()
            if q_msg and q_msg.whatsapp_message_id:
                wa_quoted_id = q_msg.whatsapp_message_id
        except (ValueError, TypeError):
            wa_quoted_id = data.quoted_message_id

    if data.message_type == "text":
        result = await send_whatsapp_message(
            current_user.whatsapp_phone_id,
            current_user.whatsapp_token,
            data.customer_phone,
            data.message,
            wa_quoted_id,
        )
    else:
        result = await send_whatsapp_media(
            current_user.whatsapp_phone_id,
            current_user.whatsapp_token,
            data.customer_phone,
            data.message_type,
            data.media_url,
            data.message,
            wa_quoted_id,
        )

    wa_msg_id = result.get("message_id", "")

    db.add(InboxMessage(
        user_id             = current_user.id,
        customer_phone      = data.customer_phone,
        direction           = MessageDirection.outbound,
        message_type        = data.message_type,
        content             = data.message,
        quoted_message_id   = quoted_id,
        whatsapp_message_id = wa_msg_id,
        whatsapp_status     = "sent",
    ))
    db.add(MessageLog(
        user_id             = current_user.id,
        contact_phone       = data.customer_phone,
        direction           = "outbound",
        message_type        = data.message_type,
        content             = data.message,
        media_url           = data.media_url,
        whatsapp_message_id = wa_msg_id,
    ))
    db.commit()

    return {"message": "Reply bhej diya ✅", "message_id": wa_msg_id}


# ─── POST: Media file upload karke send karo ─────────────────────────────────

@router.post("/send-media")
async def send_media_file(
    to:           str        = Form(...),
    media_type:   str        = Form(...),
    caption:      str        = Form(""),
    quoted_message_id: Optional[str] = Form(None),
    file:         UploadFile = File(...),
    db:           Session    = Depends(get_db),
    current_user: User       = Depends(get_current_user),
):
    from app.services.whatsapp_service import upload_media_to_whatsapp, send_whatsapp_media_by_id
    from app.models.user import MessageLog
    from app.core.config import settings

    if not current_user.whatsapp_connected:
        raise HTTPException(400, "WhatsApp connected nahi hai")

    file_bytes = await file.read()

    ext        = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    filename   = f"{uuid.uuid4()}.{ext}"
    filepath   = os.path.join(UPLOAD_DIR, filename)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(file_bytes)
    public_url = f"{settings.BASE_URL}/uploads/{filename}"

    media_id = await upload_media_to_whatsapp(
        current_user.whatsapp_phone_id,
        current_user.whatsapp_token,
        file_bytes,
        file.content_type,
        file.filename,
    )

    # ── FIX: WA quoted ID resolve karna ──
    wa_quoted_id = None
    quoted_id = None
    if quoted_message_id:
        try:
            quoted_id = int(quoted_message_id)
            q_msg = db.query(InboxMessage).filter(InboxMessage.id == quoted_id, InboxMessage.user_id == current_user.id).first()
            if q_msg and q_msg.whatsapp_message_id:
                wa_quoted_id = q_msg.whatsapp_message_id
        except (ValueError, TypeError):
            wa_quoted_id = quoted_message_id

    result = await send_whatsapp_media_by_id(
        current_user.whatsapp_phone_id,
        current_user.whatsapp_token,
        to,
        media_type,
        media_id,
        caption,
        wa_quoted_id,
    )

    wa_msg_id = result.get("message_id", "")

    db.add(InboxMessage(
        user_id             = current_user.id,
        customer_phone      = to,
        direction           = MessageDirection.outbound,
        message_type        = media_type,
        content             = caption,
        media_url           = public_url,
        quoted_message_id   = quoted_id,
        whatsapp_message_id = wa_msg_id,
        whatsapp_status     = "sent",
    ))
    db.add(MessageLog(
        user_id             = current_user.id,
        contact_phone       = to,
        direction           = "outbound",
        message_type        = media_type,
        content             = caption,
        media_url           = public_url,
        whatsapp_message_id = wa_msg_id,
    ))
    db.commit()

    return {
        "message":    "Media bhej diya ✅",
        "filename":   filename,
        "media_url":  public_url,
        "message_id": wa_msg_id,
    }


# ─── POST: Recorded audio blob send karo ─────────────────────────────────────

@router.post("/send-audio-record")
async def send_audio_record(
    to:                str        = Form(...),
    duration:          Optional[int] = Form(None),
    quoted_message_id: Optional[str] = Form(None),
    file:              UploadFile = File(...),
    db:                Session    = Depends(get_db),
    current_user:      User       = Depends(get_current_user),
):
    from app.services.whatsapp_service import upload_media_to_whatsapp, send_whatsapp_media_by_id
    from app.models.user import MessageLog
    from app.core.config import settings

    if not current_user.whatsapp_connected:
        raise HTTPException(400, "WhatsApp connected nahi hai")

    file_bytes = await file.read()

    # ── AUDIO CONVERSION VIA FFMPEG (IF AVAILABLE) ──
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_in:
            tmp_in.write(file_bytes)
            tmp_in_path = tmp_in.name
        tmp_out_path = tmp_in_path + ".ogg"

        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in_path, "-c:a", "libopus", tmp_out_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if proc.returncode == 0 and os.path.exists(tmp_out_path):
            with open(tmp_out_path, "rb") as f_out:
                final_bytes = f_out.read()
            wa_mime = "audio/ogg; codecs=opus"
            ext = "ogg"
        else:
            final_bytes = file_bytes
            wa_mime = "audio/ogg; codecs=opus"  # Flutter sends OGG
            ext = "ogg"
    except Exception:
        final_bytes = file_bytes
        wa_mime = "audio/ogg; codecs=opus"  # Flutter sends OGG
        ext = "ogg"
    finally:
        if 'tmp_in_path' in locals() and os.path.exists(tmp_in_path): os.remove(tmp_in_path)
        if 'tmp_out_path' in locals() and os.path.exists(tmp_out_path): os.remove(tmp_out_path)

    filename = f"voice_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(final_bytes)
    public_url = f"{settings.BASE_URL}/uploads/{filename}"

    media_id = await upload_media_to_whatsapp(
        current_user.whatsapp_phone_id,
        current_user.whatsapp_token,
        final_bytes,
        wa_mime,
        filename,
    )

    # ── FIX: WA quoted ID resolve karna ──
    wa_quoted_id = None
    quoted_id = None
    if quoted_message_id:
        try:
            quoted_id = int(quoted_message_id)
            q_msg = db.query(InboxMessage).filter(InboxMessage.id == quoted_id, InboxMessage.user_id == current_user.id).first()
            if q_msg and q_msg.whatsapp_message_id:
                wa_quoted_id = q_msg.whatsapp_message_id
        except (ValueError, TypeError):
            wa_quoted_id = quoted_message_id

    result = await send_whatsapp_media_by_id(
        current_user.whatsapp_phone_id,
        current_user.whatsapp_token,
        to,
        "audio",
        media_id,
        "",
        wa_quoted_id,
    )

    wa_msg_id = result.get("message_id", "")

    db.add(InboxMessage(
        user_id             = current_user.id,
        customer_phone      = to,
        direction           = MessageDirection.outbound,
        message_type        = "audio",
        content             = "🎵 Voice message",
        media_url           = public_url,
        quoted_message_id   = quoted_id,
        whatsapp_message_id = wa_msg_id,
        whatsapp_status     = "sent",
        duration            = duration,
    ))
    db.add(MessageLog(
        user_id             = current_user.id,
        contact_phone       = to,
        direction           = "outbound",
        message_type        = "audio",
        content             = "Voice message",
        media_url           = public_url,
        whatsapp_message_id = wa_msg_id,
        duration            = duration,
    ))
    db.commit()

    return {
        "message":    "Voice message bhej diya ✅",
        "filename":   filename,
        "media_url":  public_url,
        "message_id": wa_msg_id,
    }


# ─── GET: Unread count ────────────────────────────────────────────────────────

@router.get("/unread-count")
def get_unread_count(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    count = db.query(InboxMessage).filter(
        InboxMessage.user_id   == current_user.id,
        InboxMessage.direction == MessageDirection.inbound,
        InboxMessage.is_read   == False,
    ).count()
    return {"unread": count}


# ─── HELPER ───────────────────────────────────────────────────────────────────

def _msg_dict(m: InboxMessage) -> dict:
    return {
        "id":                  m.id,
        "customer_phone":      m.customer_phone,
        "customer_name":       getattr(m, "customer_name", None),
        "direction":           m.direction,
        "message_type":        m.message_type,
        "content":             m.content,
        "media_url":           m.media_url,
        "whatsapp_message_id": getattr(m, "whatsapp_message_id", None),
        "is_read":             m.is_read,
        "is_starred":          getattr(m, "is_starred", False),
        "quoted_message_id":   getattr(m, "quoted_message_id", None),
        "whatsapp_status":     getattr(m, "whatsapp_status", "sent"),
        "received_at":         m.received_at.isoformat() if m.received_at else None,
        "duration":            getattr(m, "duration", None),
    }