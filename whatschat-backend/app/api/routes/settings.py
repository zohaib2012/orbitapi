from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, BusinessSettings

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    business_name:      Optional[str]  = None
    logo_url:           Optional[str]  = None
    website:            Optional[str]  = None
    address:            Optional[str]  = None
    support_email:      Optional[str]  = None
    support_phone:      Optional[str]  = None
    timezone:           Optional[str]  = "Asia/Karachi"
    welcome_message:    Optional[str]  = None
    welcome_media_url:  Optional[str]  = None
    welcome_media_type: Optional[str]  = None
    welcome_enabled:    Optional[bool] = None
    away_message:       Optional[str]  = None
    business_hours:     Optional[dict] = None


@router.get("/")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = db.query(BusinessSettings).filter(BusinessSettings.user_id == current_user.id).first()
    if not s:
        s = BusinessSettings(
            user_id       = current_user.id,
            business_name = current_user.business_name,
            support_email = current_user.email,
            support_phone = current_user.phone,
            timezone      = "Asia/Karachi"
        )
        db.add(s); db.commit(); db.refresh(s)
    return {
        "business_name":      s.business_name,
        "logo_url":           s.logo_url,
        "website":            s.website,
        "address":            s.address,
        "support_email":      s.support_email,
        "support_phone":      s.support_phone,
        "timezone":           s.timezone,
        "welcome_message":    s.welcome_message,
        "welcome_media_url":  getattr(s, "welcome_media_url", None),
        "welcome_media_type": getattr(s, "welcome_media_type", None),
        "welcome_enabled":    getattr(s, "welcome_enabled", True),
        "away_message":       s.away_message,
        "business_hours":     s.business_hours,
    }


@router.put("/")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = db.query(BusinessSettings).filter(BusinessSettings.user_id == current_user.id).first()
    if not s:
        s = BusinessSettings(user_id=current_user.id)
        db.add(s)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value if value != "" else None)
    db.commit()
    return {"message": "Settings updated ✅"}