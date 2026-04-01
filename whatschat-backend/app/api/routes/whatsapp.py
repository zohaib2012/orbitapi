import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import (
    User, InboxMessage, MessageLog, MessageDirection,
    AutoReply, BusinessSettings, InteractiveMenu, Contact
)
from app.schemas.schemas import WhatsAppConnectRequest, SendMessageRequest
from app.services.whatsapp_service import (
    send_whatsapp_message, send_whatsapp_media,
    send_whatsapp_template, send_whatsapp_interactive_list,
    send_whatsapp_interactive_buttons
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp API"])

VERIFY_TOKEN = "whatschat_webhook_token_2024"


class TestMessageRequest(BaseModel):
    to:      str
    message: Optional[str] = "Hello! This is a test message from WhatsChat AI. 👋"


# ── CONNECT / DISCONNECT ──────────────────────────────────────────────────────

@router.post("/connect")
def connect_whatsapp(data: WhatsAppConnectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.whatsapp_phone_id  = data.phone_number_id
    current_user.whatsapp_token     = data.access_token
    current_user.whatsapp_connected = True
    db.commit()
    return {"message": "WhatsApp connected ✅", "connected": True}


@router.post("/disconnect")
def disconnect_whatsapp(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.whatsapp_connected = False
    current_user.whatsapp_phone_id  = None
    current_user.whatsapp_token     = None
    db.commit()
    return {"message": "WhatsApp disconnected", "connected": False}


@router.get("/status")
def whatsapp_status(current_user: User = Depends(get_current_user)):
    return {
        "connected":       current_user.whatsapp_connected,
        "phone_number_id": current_user.whatsapp_phone_id,
    }


# ── TEST MESSAGE ──────────────────────────────────────────────────────────────

@router.post("/test")
async def send_test_message(data: TestMessageRequest, current_user: User = Depends(get_current_user)):
    if not current_user.whatsapp_connected:
        raise HTTPException(400, "WhatsApp connected nahi hai")
    if not current_user.whatsapp_phone_id or not current_user.whatsapp_token:
        raise HTTPException(400, "Phone Number ID ya Token missing hai")

    if data.message and data.message.startswith("TEMPLATE:"):
        template_name = data.message.replace("TEMPLATE:", "").strip()
        return await send_whatsapp_template(
            current_user.whatsapp_phone_id,
            current_user.whatsapp_token,
            data.to, template_name
        )

    return await send_whatsapp_message(
        current_user.whatsapp_phone_id,
        current_user.whatsapp_token,
        data.to, data.message
    )


# ── SEND (single contact) ─────────────────────────────────────────────────────

@router.post("/send")
async def send_message(data: SendMessageRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.whatsapp_connected:
        raise HTTPException(400, "WhatsApp not connected")
    from app.models.user import Contact
    contact = db.query(Contact).filter(Contact.id == data.contact_id, Contact.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    result = await send_whatsapp_message(
        current_user.whatsapp_phone_id,
        current_user.whatsapp_token,
        contact.phone, data.message
    )
    return {**result, "contact": contact.name}


# ── WEBHOOK VERIFY ────────────────────────────────────────────────────────────

@router.get("/webhook")
def webhook_verify(
    hub_mode:         str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge:    str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("✅ Webhook verified!")
        return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "Webhook verification failed")


# ── WEBHOOK RECEIVE ───────────────────────────────────────────────────────────

@router.post("/webhook")
async def webhook_receive(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"}

    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # ── Incoming Messages ─────────────────────────────────────
                for msg in value.get("messages", []):
                    phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
                    from_phone      = msg.get("from", "")
                    msg_id          = msg.get("id", "")
                    timestamp       = msg.get("timestamp", "")
                    msg_type        = msg.get("type", "text")

                    contacts_info = value.get("contacts", [])
                    customer_name = contacts_info[0].get("profile", {}).get("name", "") if contacts_info else ""

                    user = db.query(User).filter(User.whatsapp_phone_id == phone_number_id).first()
                    if not user:
                        logger.warning(f"No user found for phone_number_id: {phone_number_id}")
                        continue

                    # ── Handle interactive reply (user ne menu item select kiya) ──
                    if msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        reply_type  = interactive.get("type", "")
                        reply_id    = ""
                        reply_title = ""

                        if reply_type == "list_reply":
                            reply_id    = interactive.get("list_reply", {}).get("id", "")
                            reply_title = interactive.get("list_reply", {}).get("title", "")
                        elif reply_type == "button_reply":
                            reply_id    = interactive.get("button_reply", {}).get("id", "")
                            reply_title = interactive.get("button_reply", {}).get("title", "")

                        # Save in inbox
                        inbox_msg = InboxMessage(
                            user_id=user.id, customer_phone=from_phone,
                            customer_name=customer_name, direction=MessageDirection.inbound,
                            message_type="text", content=reply_title,
                            whatsapp_message_id=msg_id, is_read=False,
                        )
                        db.add(inbox_msg)
                        db.commit()

                        logger.info(f"📨 Interactive reply from {from_phone}: {reply_id} = {reply_title}")

                        # Follow-up dhundo
                        await _process_interactive_followup(db, user, from_phone, reply_id)
                        continue

                    # ── Extract content ────────────────────────────────────
                    content   = None
                    media_url = None

                    # Quoted message context
                    context_msg_id = msg.get("context", {}).get("id", None)

                    if msg_type == "text":
                        content = msg.get("text", {}).get("body", "")
                    elif msg_type == "image":
                        content  = msg.get("image", {}).get("caption", "")
                        media_id = msg.get("image", {}).get("id", "")
                        if media_id:
                            from app.services.whatsapp_service import download_whatsapp_media
                            med = await download_whatsapp_media(media_id, user.whatsapp_token)
                            media_url = f"{settings.BASE_URL}/uploads/{med['filename']}" if med else None
                    elif msg_type == "video":
                        content  = msg.get("video", {}).get("caption", "")
                        media_id = msg.get("video", {}).get("id", "")
                        if media_id:
                            from app.services.whatsapp_service import download_whatsapp_media
                            med = await download_whatsapp_media(media_id, user.whatsapp_token)
                            media_url = f"{settings.BASE_URL}/uploads/{med['filename']}" if med else None
                    elif msg_type == "audio":
                        media_id = msg.get("audio", {}).get("id", "")
                        if media_id:
                            from app.services.whatsapp_service import download_whatsapp_media
                            med = await download_whatsapp_media(media_id, user.whatsapp_token)
                            media_url = f"{settings.BASE_URL}/uploads/{med['filename']}" if med else None
                    elif msg_type == "document":
                        content  = msg.get("document", {}).get("caption", "")
                        media_id = msg.get("document", {}).get("id", "")
                        if media_id:
                            from app.services.whatsapp_service import download_whatsapp_media
                            med = await download_whatsapp_media(media_id, user.whatsapp_token)
                            media_url = f"{settings.BASE_URL}/uploads/{med['filename']}" if med else None

                    # Inbox mein save karo
                    inbox_msg = InboxMessage(
                        user_id             = user.id,
                        customer_phone      = from_phone,
                        customer_name       = customer_name,
                        direction           = MessageDirection.inbound,
                        message_type        = msg_type,
                        content             = content,
                        media_url           = media_url,
                        whatsapp_message_id = msg_id,
                        is_read             = False,
                    )
                    db.add(inbox_msg)

                    log = MessageLog(
                        user_id             = user.id,
                        contact_phone       = from_phone,
                        contact_name        = customer_name,
                        direction           = MessageDirection.inbound,
                        message_type        = msg_type,
                        content             = content,
                        media_url           = media_url,
                        whatsapp_message_id = msg_id,
                        is_delivered        = True,
                        is_read             = False,
                    )
                    db.add(log)
                    db.commit()

                    # ── Auto-save Contact (with country code) ────────────────
                    try:
                        # Normalise: ensure number starts with +
                        normalised_phone = from_phone if from_phone.startswith("+") else f"+{from_phone}"
                        existing_contact = db.query(Contact).filter(
                            Contact.user_id == user.id,
                            Contact.phone   == normalised_phone,
                        ).first()
                        if not existing_contact:
                            new_contact = Contact(
                                user_id = user.id,
                                name    = customer_name or normalised_phone,
                                phone   = normalised_phone,
                                status  = "active",
                            )
                            db.add(new_contact)
                            db.commit()
                            logger.info(f"💾 Auto-saved contact: {normalised_phone} ({customer_name})")
                        elif customer_name and existing_contact.name == existing_contact.phone:
                            # Update name if it was previously just the phone number
                            existing_contact.name = customer_name
                            db.commit()
                    except Exception as ce:
                        logger.warning(f"Contact auto-save failed: {ce}")

                    logger.info(f"📨 Incoming message from {from_phone}: {content or msg_type}")

                    # ── Welcome Message (first-time user check) ───────────
                    is_first = await _check_first_time_user(db, user, from_phone)
                    if is_first:
                        await _send_welcome_message(db, user, from_phone)

                    # ── Interactive Menu Check (before auto reply) ────────
                    if msg_type == "text" and content:
                        menu_handled = await _process_interactive_menu(db, user, from_phone, content)
                        if not menu_handled:
                            await _process_auto_reply(db, user, from_phone, content)

                # ── Delivery / Read Receipts ──────────────────────────────
                for status in value.get("statuses", []):
                    wamid      = status.get("id", "")
                    status_val = status.get("status", "")

                    if status_val == "delivered":
                        db.query(MessageLog).filter(
                            MessageLog.whatsapp_message_id == wamid
                        ).update({"is_delivered": True, "delivered_at": datetime.utcnow()})
                        # ── FIX: inbox_messages bhi update karo ───────────
                        db.query(InboxMessage).filter(
                            InboxMessage.whatsapp_message_id == wamid
                        ).update({"whatsapp_status": "delivered"})
                        db.commit()

                    elif status_val == "read":
                        db.query(MessageLog).filter(
                            MessageLog.whatsapp_message_id == wamid
                        ).update({"is_read": True, "read_at": datetime.utcnow()})
                        # ── FIX: inbox_messages bhi update karo ───────────
                        db.query(InboxMessage).filter(
                            InboxMessage.whatsapp_message_id == wamid
                        ).update({"whatsapp_status": "read"})
                        db.commit()

                    elif status_val == "sent":
                        db.query(InboxMessage).filter(
                            InboxMessage.whatsapp_message_id == wamid
                        ).update({"whatsapp_status": "sent"})
                        db.commit()

    except Exception as e:
        logger.error(f"Webhook error: {e}")

    return {"status": "ok"}


# ── WELCOME MESSAGE ───────────────────────────────────────────────────────────

async def _check_first_time_user(db: Session, user: User, phone: str) -> bool:
    """Check if this is the first message from this phone number"""
    count = db.query(InboxMessage).filter(
        InboxMessage.user_id        == user.id,
        InboxMessage.customer_phone == phone,
        InboxMessage.direction      == MessageDirection.inbound,
    ).count()
    return count <= 1  # 1 = current message just saved


async def _send_welcome_message(db: Session, user: User, phone: str):
    """Welcome message bhejo first-time user ko"""
    if not user.whatsapp_connected:
        return

    biz_settings = db.query(BusinessSettings).filter(
        BusinessSettings.user_id == user.id
    ).first()

    if not biz_settings:
        return

    welcome_enabled = getattr(biz_settings, "welcome_enabled", True)
    if not welcome_enabled:
        return

    welcome_text      = biz_settings.welcome_message
    welcome_media_url = getattr(biz_settings, "welcome_media_url", None)
    welcome_media_type = getattr(biz_settings, "welcome_media_type", None)

    if not welcome_text and not welcome_media_url:
        return

    logger.info(f"👋 Sending welcome message to {phone}")

    try:
        can_bundle_media = welcome_media_type in ["image", "video", "document"]

        # Bundle text and media if possible
        if welcome_media_url and welcome_media_type and welcome_media_type != "text" and can_bundle_media:
            result = await send_whatsapp_media(
                user.whatsapp_phone_id, user.whatsapp_token,
                phone, welcome_media_type,
                welcome_media_url, welcome_text or ""
            )
            db.add(InboxMessage(
                user_id=user.id, customer_phone=phone,
                direction=MessageDirection.outbound,
                message_type=welcome_media_type,
                content=welcome_text or "", media_url=welcome_media_url,
                whatsapp_message_id=result.get("message_id", ""),
                whatsapp_status="sent",
            ))
        else:
            # Text welcome message (Not bundled)
            if welcome_text:
                result = await send_whatsapp_message(
                    user.whatsapp_phone_id, user.whatsapp_token,
                    phone, welcome_text
                )
                db.add(InboxMessage(
                    user_id=user.id, customer_phone=phone,
                    direction=MessageDirection.outbound,
                    message_type="text", content=welcome_text,
                    whatsapp_message_id=result.get("message_id", ""),
                    whatsapp_status="sent",
                ))

            # Media welcome message (Not bundled)
            if welcome_media_url and welcome_media_type and welcome_media_type != "text":
                result = await send_whatsapp_media(
                    user.whatsapp_phone_id, user.whatsapp_token,
                    phone, welcome_media_type,
                    welcome_media_url, ""
                )
                db.add(InboxMessage(
                    user_id=user.id, customer_phone=phone,
                    direction=MessageDirection.outbound,
                    message_type=welcome_media_type,
                    content="", media_url=welcome_media_url,
                    whatsapp_message_id=result.get("message_id", ""),
                    whatsapp_status="sent",
                ))

        db.commit()

    except Exception as e:
        logger.error(f"Welcome message send failed: {e}")


# ── INTERACTIVE MENU CHECK ────────────────────────────────────────────────────

async def _process_interactive_menu(db: Session, user: User, phone: str, text: str) -> bool:
    """Check if incoming text matches an interactive menu trigger. Returns True if handled."""
    menus = db.query(InteractiveMenu).filter(
        InteractiveMenu.user_id   == user.id,
        InteractiveMenu.is_active == True,
    ).all()

    text_lower = text.lower().strip()
    matched    = None

    for menu in menus:
        kw = menu.trigger_keyword.lower().strip()
        if menu.match_type == "exact"       and text_lower == kw:          matched = menu; break
        if menu.match_type == "contains"    and kw in text_lower:          matched = menu; break
        if menu.match_type == "starts_with" and text_lower.startswith(kw): matched = menu; break

    if not matched:
        return False

    logger.info(f"🤖 Interactive menu triggered: '{matched.trigger_keyword}' → {matched.menu_type}")

    try:
        if matched.menu_type == "buttons":
            result = await send_whatsapp_interactive_buttons(
                user.whatsapp_phone_id, user.whatsapp_token,
                phone,
                matched.body_text,
                matched.items or [],
                matched.header_text,
                matched.footer_text,
            )
        else:  # list
            result = await send_whatsapp_interactive_list(
                user.whatsapp_phone_id, user.whatsapp_token,
                phone,
                matched.body_text,
                matched.button_text or "Menu",
                matched.items or [],
                matched.header_text,
                matched.footer_text,
            )

        matched.total_triggered += 1

        db.add(InboxMessage(
            user_id=user.id, customer_phone=phone,
            direction=MessageDirection.outbound,
            message_type="text", content=f"📋 {matched.name}",
            whatsapp_message_id=result.get("message_id", ""),
            whatsapp_status="sent",
        ))
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Interactive menu send failed: {e}")
        return False


# ── INTERACTIVE FOLLOW-UP ─────────────────────────────────────────────────────

async def _process_interactive_followup(db: Session, user: User, phone: str, reply_id: str):
    """User ne menu item select kiya — follow-up response bhejo"""
    menus = db.query(InteractiveMenu).filter(
        InteractiveMenu.user_id   == user.id,
        InteractiveMenu.is_active == True,
    ).all()

    for menu in menus:
        rules = menu.follow_up_rules or {}
        if reply_id in rules:
            rule = rules[reply_id]
            rule_type = rule.get("type", "text")

            try:
                if rule_type == "text":
                    result = await send_whatsapp_message(
                        user.whatsapp_phone_id, user.whatsapp_token,
                        phone, rule.get("content", "")
                    )
                elif rule_type == "media":
                    result = await send_whatsapp_media(
                        user.whatsapp_phone_id, user.whatsapp_token,
                        phone, rule.get("media_type", "image"),
                        rule.get("media_url", ""),
                        rule.get("caption", "")
                    )
                else:
                    return

                db.add(InboxMessage(
                    user_id=user.id, customer_phone=phone,
                    direction=MessageDirection.outbound,
                    message_type=rule_type if rule_type != "media" else rule.get("media_type", "text"),
                    content=rule.get("content", "") or rule.get("caption", ""),
                    media_url=rule.get("media_url", None),
                    whatsapp_message_id=result.get("message_id", ""),
                    whatsapp_status="sent",
                ))
                db.commit()
                logger.info(f"✅ Follow-up sent for reply_id: {reply_id}")

            except Exception as e:
                logger.error(f"Follow-up send failed: {e}")
            return

    # If no matching follow-up found, check auto replies
    logger.info(f"No follow-up for reply_id: {reply_id}")


# ── AUTO REPLY HELPER ─────────────────────────────────────────────────────────

async def _process_auto_reply(db: Session, user: User, customer_phone: str, incoming_text: str):
    if not user.whatsapp_connected:
        return

    replies = db.query(AutoReply).filter(
        AutoReply.user_id  == user.id,
        AutoReply.is_active == True
    ).all()

    text_lower = incoming_text.lower().strip()
    matched    = None

    for reply in replies:
        kw = reply.trigger_keyword.lower().strip()
        if reply.match_type == "exact"       and text_lower == kw:          matched = reply; break
        if reply.match_type == "contains"    and kw in text_lower:          matched = reply; break
        if reply.match_type == "starts_with" and text_lower.startswith(kw): matched = reply; break

    if not matched:
        return

    logger.info(f"🤖 Auto reply triggered: '{matched.trigger_keyword}' → {matched.reply_type}")

    try:
        if matched.reply_type == "text":
            result = await send_whatsapp_message(
                user.whatsapp_phone_id, user.whatsapp_token,
                customer_phone, matched.reply_text
            )
        else:
            result = await send_whatsapp_media(
                user.whatsapp_phone_id, user.whatsapp_token,
                customer_phone, matched.reply_type,
                matched.media_url, matched.media_caption or ""
            )

        matched.total_triggered += 1
        db.commit()

        out_msg = InboxMessage(
            user_id=user.id, customer_phone=customer_phone,
            direction=MessageDirection.outbound,
            message_type=matched.reply_type,
            content=matched.reply_text,
            media_url=matched.media_url,
            whatsapp_message_id=result.get("message_id", ""),
            whatsapp_status="sent",
        )
        db.add(out_msg)

        out_log = MessageLog(
            user_id=user.id, contact_phone=customer_phone,
            direction=MessageDirection.outbound,
            message_type=matched.reply_type,
            content=matched.reply_text,
            media_url=matched.media_url,
            whatsapp_message_id=result.get("message_id", ""),
        )
        db.add(out_log)
        db.commit()

    except Exception as e:
        logger.error(f"Auto reply send failed: {e}")