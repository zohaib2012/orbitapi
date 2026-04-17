import os, uuid, logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["Media Upload"])

UPLOAD_DIR   = "uploads"
ALLOWED_TYPES = {
    "image":    ["image/jpeg", "image/png", "image/webp", "image/gif"],
    "video":    ["video/mp4", "video/3gpp"],
    "audio":    ["audio/mpeg", "audio/ogg", "audio/wav", "audio/mp4", "audio/aac"],
    "document": ["application/pdf", "application/msword",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
}
MAX_SIZE = {
    "image":    5  * 1024 * 1024,   # 5MB
    "video":    16 * 1024 * 1024,   # 16MB
    "audio":    16 * 1024 * 1024,   # 16MB
    "document": 100* 1024 * 1024,   # 100MB
}


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Image/Video/Audio/Document upload karo — public URL milega"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Media type detect karo
    media_type = None
    for mtype, mime_list in ALLOWED_TYPES.items():
        if file.content_type in mime_list:
            media_type = mtype
            break

    if not media_type:
        raise HTTPException(400, f"File type '{file.content_type}' allowed nahi hai")

    # Size check
    contents = await file.read()
    if len(contents) > MAX_SIZE[media_type]:
        max_mb = MAX_SIZE[media_type] // (1024*1024)
        raise HTTPException(400, f"{media_type} ka max size {max_mb}MB hai")

    # Unique filename
    ext      = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    # URL (production mein yeh CDN URL hoga)
    file_url = f"/uploads/{filename}"

    logger.info(f"📎 Media uploaded: {filename} ({media_type}, {len(contents)//1024}KB)")

    return {
        "url":        file_url,
        "filename":   filename,
        "media_type": media_type,
        "size_kb":    len(contents) // 1024
    }