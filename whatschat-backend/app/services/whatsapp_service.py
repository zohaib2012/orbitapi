# whatsapp_service.py — Meta WhatsApp Business API actual calls

import os
import uuid
import httpx
import aiofiles # type: ignore
import logging
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"
UPLOAD_DIR       = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── PHONE NUMBER CLEANER ─────────────────────────────────────────────────────

def clean_phone(num: str) -> str:
    n = str(num).strip().replace(" ", "").replace("-", "")
    if n.startswith("+"):    n = n[1:]
    if n.startswith("00"):   n = n[2:]
    if n.startswith("0"):    n = "92" + n[1:]
    if n.startswith("9292"): n = n[2:]
    return n


# ─── WHATSAPP MEDIA UPLOAD — file → media_id ─────────────────────────────────
# WhatsApp URL se media accept nahi karta reliably
# Pehle file upload karo, media_id lo, phir send karo

async def upload_media_to_whatsapp(
    phone_number_id: str,
    access_token:    str,
    file_bytes:      bytes,
    mime_type:       str,
    filename:        str,
) -> str:
    """
    File bytes WhatsApp pe upload karo.
    Returns: media_id (string)
    """
    url     = f"{WHATSAPP_API_URL}/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {access_token}"}

    files = {
        "file":              (filename, file_bytes, mime_type),
        "messaging_product": (None, "whatsapp"),
        "type":              (None, mime_type),
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, files=files)
    except httpx.ConnectTimeout:
        raise HTTPException(503, "WhatsApp media upload timeout")
    except httpx.ConnectError:
        raise HTTPException(503, "Connection error during media upload")

    logger.info(f"WA Media Upload: {resp.status_code} | {resp.text[:200]}")

    if resp.status_code == 200:
        data     = resp.json()
        media_id = data.get("id", "")
        if not media_id:
            raise HTTPException(500, "WhatsApp ne media_id nahi diya")
        logger.info(f"✅ Media uploaded to WA: {media_id}")
        return media_id
    else:
        try:
            err    = resp.json()
            detail = err.get("error", {}).get("message", "Unknown")
        except Exception:
            detail = resp.text
        raise HTTPException(resp.status_code, f"WA Media Upload Error: {detail}")


# ─── TEXT MESSAGE SEND ────────────────────────────────────────────────────────

async def send_whatsapp_message(
    phone_number_id:   str,
    access_token:      str,
    to:                str,
    message:           str,
    quoted_message_id: Optional[str] = None,
) -> dict:

    if not access_token or access_token.startswith("EAAxxxxxxx") or len(access_token) < 20:
        raise HTTPException(400, "Access Token invalid hai. Reconnect karo.")
    if not phone_number_id or len(phone_number_id) < 5:
        raise HTTPException(400, "Phone Number ID missing hai.")

    url        = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    headers    = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    cleaned_to = clean_phone(to)

    if message.startswith("TEMPLATE:"):
        template_name = message.replace("TEMPLATE:", "").strip()
        payload = {
            "messaging_product": "whatsapp",
            "to":   cleaned_to,
            "type": "template",
            "template": {"name": template_name, "language": {"code": "en_US"}},
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type":    "individual",
            "to":                cleaned_to,
            "type":              "text",
            "text":              {"body": message},
        }

    if quoted_message_id:
        payload["context"] = {"message_id": quoted_message_id}

    logger.info("=" * 60)
    logger.info(f"WHATSAPP TEXT | To: {cleaned_to} | Quoted: {quoted_message_id}")
    logger.info(f"Message: {message[:60]}")
    logger.info("=" * 60)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.ConnectTimeout:
        raise HTTPException(503, "TIMEOUT: graph.facebook.com reachable nahi.")
    except httpx.ConnectError:
        raise HTTPException(503, "CONNECTION ERROR: Internet check karo.")

    logger.info(f"RESPONSE: {resp.status_code} | {resp.text}")

    if resp.status_code == 200:
        data   = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "")
        logger.info(f"✅ Sent! ID: {msg_id}")
        return {"success": True, "message_id": msg_id, "to": to}

    elif resp.status_code == 401:
        raise HTTPException(401, "Token expire ho gaya. Meta se naya token lo.")

    else:
        try:
            err     = resp.json()
            detail  = err.get("error", {}).get("message", "Unknown")
            fbtrace = err.get("error", {}).get("fbtrace_id", "")
            logger.error(f"❌ Meta Error: {detail} | Trace: {fbtrace}")
        except Exception:
            detail = resp.text
        raise HTTPException(resp.status_code, f"WhatsApp API Error: {detail}")


# ─── MEDIA MESSAGE SEND — media_id se (recommended) ──────────────────────────

async def send_whatsapp_media_by_id(
    phone_number_id:   str,
    access_token:      str,
    to:                str,
    media_type:        str,       # "image" / "video" / "audio" / "document"
    media_id:          str,       # WhatsApp media_id (upload se mila)
    caption:           str = "",
    quoted_message_id: Optional[str] = None,
) -> dict:
    """media_id se bhejo — yeh most reliable tarika hai"""

    url        = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    headers    = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    cleaned_to = clean_phone(to)

    media_obj: dict = {"id": media_id}
    if caption and media_type in ("image", "video", "document"):
        media_obj["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                cleaned_to,
        "type":              media_type,
        media_type:          media_obj,
    }

    if quoted_message_id:
        payload["context"] = {"message_id": quoted_message_id}

    logger.info(f"WHATSAPP MEDIA (id) | {media_type} | To: {cleaned_to} | media_id: {media_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.ConnectTimeout:
        raise HTTPException(503, "Timeout — internet check karo")
    except httpx.ConnectError:
        raise HTTPException(503, "Connection error")

    logger.info(f"MEDIA SEND RESPONSE: {resp.status_code} | {resp.text[:200]}")

    if resp.status_code == 200:
        data   = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "")
        return {"success": True, "message_id": msg_id, "to": cleaned_to}
    else:
        try:
            err    = resp.json()
            detail = err.get("error", {}).get("message", "Unknown error")
        except Exception:
            detail = resp.text
        raise HTTPException(resp.status_code, f"WhatsApp Media Error: {detail}")


# ─── MEDIA MESSAGE SEND — URL se (auto reply / template use karta hai) ────────

async def send_whatsapp_media(
    phone_number_id:   str,
    access_token:      str,
    to:                str,
    media_type:        str,
    media_url:         str,
    caption:           str = "",
    quoted_message_id: Optional[str] = None,
) -> dict:
    """URL se bhejo — auto reply wagera ke liye"""

    url        = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    headers    = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    cleaned_to = clean_phone(to)

    media_obj: dict = {"link": media_url}
    if caption and media_type in ("image", "video", "document"):
        media_obj["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                cleaned_to,
        "type":              media_type,
        media_type:          media_obj,
    }

    if quoted_message_id:
        payload["context"] = {"message_id": quoted_message_id}

    logger.info(f"WHATSAPP MEDIA (url) | {media_type} | To: {cleaned_to} | URL: {media_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.ConnectTimeout:
        raise HTTPException(503, "Timeout — internet check karo")
    except httpx.ConnectError:
        raise HTTPException(503, "Connection error")

    if resp.status_code == 200:
        data   = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "")
        return {"success": True, "message_id": msg_id, "to": cleaned_to}
    else:
        try:
            err    = resp.json()
            detail = err.get("error", {}).get("message", "Unknown error")
        except Exception:
            detail = resp.text
        raise HTTPException(resp.status_code, f"WhatsApp Media Error: {detail}")


# ─── MEDIA DOWNLOAD — Webhook media_id → VPS pe save ─────────────────────────

async def download_whatsapp_media(media_id: str, access_token: str) -> dict:
    """
    Webhook se aaya media_id lo, WhatsApp se file download karo,
    VPS ke uploads/ mein save karo.
    Returns: { filename, mime_type, media_type, filepath }
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        meta_r    = await client.get(f"{WHATSAPP_API_URL}/{media_id}", headers=headers)
        meta      = meta_r.json()
        media_url = meta["url"]
        mime_type = meta.get("mime_type", "application/octet-stream")
        file_r    = await client.get(media_url, headers=headers)

    ext_map = {
        "image/jpeg":             "jpg",
        "image/png":              "png",
        "image/webp":             "webp",
        "video/mp4":              "mp4",
        "video/3gpp":             "3gp",
        "audio/ogg":              "ogg",
        "audio/mpeg":             "mp3",
        "audio/opus":             "ogg",
        "audio/ogg; codecs=opus": "ogg",
        "application/pdf":        "pdf",
    }
    ext      = ext_map.get(mime_type, "bin")
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(file_r.content)

    logger.info(f"✅ Media saved: {filename} ({mime_type})")

    return {
        "filename":   filename,
        "filepath":   filepath,
        "mime_type":  mime_type,
        "media_type": mime_type.split("/")[0],
    }


# ─── TEMPLATE SEND ────────────────────────────────────────────────────────────

async def send_whatsapp_template(
    phone_number_id: str,
    access_token:    str,
    to:              str,
    template_name:   str,
    language:        str = "en_US",
) -> dict:
    url     = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to":   clean_phone(to),
        "type": "template",
        "template": {"name": template_name, "language": {"code": language}},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        data   = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "")
        return {"success": True, "message_id": msg_id}
    else:
        try:
            err    = resp.json()
            detail = err.get("error", {}).get("message", "Unknown")
        except Exception:
            detail = resp.text
        raise HTTPException(resp.status_code, f"Template Error: {detail}")


# ─── INTERACTIVE LIST MESSAGE ─────────────────────────────────────────────────

async def send_whatsapp_interactive_list(
    phone_number_id: str,
    access_token:    str,
    to:              str,
    body_text:       str,
    button_text:     str,
    items:           list,
    header_text:     str = None,
    footer_text:     str = None,
) -> dict:
    """WhatsApp Interactive List Message bhejo — menu style"""

    url        = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    headers    = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    cleaned_to = clean_phone(to)

    rows = []
    for item in items[:10]:  # max 10 items
        row = {"id": str(item.get("id", "")), "title": str(item.get("title", ""))[:24]}
        desc = item.get("description", "")
        if desc:
            row["description"] = str(desc)[:72]
        rows.append(row)

    interactive = {
        "type": "list",
        "body": {"text": body_text},
        "action": {
            "button": button_text[:20],
            "sections": [{"title": "Options", "rows": rows}],
        },
    }

    if header_text:
        interactive["header"] = {"type": "text", "text": header_text[:60]}
    if footer_text:
        interactive["footer"] = {"text": footer_text[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                cleaned_to,
        "type":              "interactive",
        "interactive":       interactive,
    }

    logger.info(f"WHATSAPP INTERACTIVE LIST | To: {cleaned_to} | {len(rows)} items")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.ConnectTimeout:
        raise HTTPException(503, "Timeout — internet check karo")
    except httpx.ConnectError:
        raise HTTPException(503, "Connection error")

    logger.info(f"INTERACTIVE LIST RESPONSE: {resp.status_code} | {resp.text[:200]}")

    if resp.status_code == 200:
        data   = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "")
        return {"success": True, "message_id": msg_id}
    else:
        try:
            err    = resp.json()
            detail = err.get("error", {}).get("message", "Unknown")
        except Exception:
            detail = resp.text
        raise HTTPException(resp.status_code, f"Interactive List Error: {detail}")


# ─── INTERACTIVE BUTTON MESSAGE ───────────────────────────────────────────────

async def send_whatsapp_interactive_buttons(
    phone_number_id: str,
    access_token:    str,
    to:              str,
    body_text:       str,
    buttons:         list,
    header_text:     str = None,
    footer_text:     str = None,
) -> dict:
    """WhatsApp Interactive Reply Buttons bhejo — max 3 buttons"""

    url        = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"
    headers    = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    cleaned_to = clean_phone(to)

    btn_list = []
    for btn in buttons[:3]:  # max 3 buttons
        btn_list.append({
            "type": "reply",
            "reply": {
                "id":    str(btn.get("id", "")),
                "title": str(btn.get("title", ""))[:20],
            },
        })

    interactive = {
        "type": "button",
        "body": {"text": body_text},
        "action": {"buttons": btn_list},
    }

    if header_text:
        interactive["header"] = {"type": "text", "text": header_text[:60]}
    if footer_text:
        interactive["footer"] = {"text": footer_text[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                cleaned_to,
        "type":              "interactive",
        "interactive":       interactive,
    }

    logger.info(f"WHATSAPP INTERACTIVE BUTTONS | To: {cleaned_to} | {len(btn_list)} buttons")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.ConnectTimeout:
        raise HTTPException(503, "Timeout")
    except httpx.ConnectError:
        raise HTTPException(503, "Connection error")

    if resp.status_code == 200:
        data   = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "")
        return {"success": True, "message_id": msg_id}
    else:
        try:
            err    = resp.json()
            detail = err.get("error", {}).get("message", "Unknown")
        except Exception:
            detail = resp.text
        raise HTTPException(resp.status_code, f"Interactive Button Error: {detail}")