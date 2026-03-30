# app/api/routes/interactive_menus.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, InteractiveMenu

router = APIRouter(prefix="/interactive-menus", tags=["Interactive Menus"])


class MenuItemSchema(BaseModel):
    id:          str
    title:       str
    description: Optional[str] = None


class FollowUpRule(BaseModel):
    type:       str                 # "text" / "media"
    content:    Optional[str] = None
    media_type: Optional[str] = None
    media_url:  Optional[str] = None
    caption:    Optional[str] = None


class InteractiveMenuCreate(BaseModel):
    name:            str
    trigger_keyword: str
    match_type:      str  = "contains"
    menu_type:       str  = "list"     # list / buttons
    header_text:     Optional[str] = None
    body_text:       str
    footer_text:     Optional[str] = None
    button_text:     Optional[str] = "Menu"
    items:           list = []
    follow_up_rules: Optional[dict] = None
    is_active:       bool = True


class InteractiveMenuUpdate(InteractiveMenuCreate):
    pass


@router.get("/")
def get_menus(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    menus = db.query(InteractiveMenu).filter(
        InteractiveMenu.user_id == current_user.id
    ).order_by(InteractiveMenu.created_at.desc()).all()
    return [{
        "id":              m.id,
        "name":            m.name,
        "trigger_keyword": m.trigger_keyword,
        "match_type":      m.match_type,
        "menu_type":       m.menu_type,
        "header_text":     m.header_text,
        "body_text":       m.body_text,
        "footer_text":     m.footer_text,
        "button_text":     m.button_text,
        "items":           m.items or [],
        "follow_up_rules": m.follow_up_rules or {},
        "is_active":       m.is_active,
        "total_triggered": m.total_triggered,
        "created_at":      m.created_at.isoformat() if m.created_at else None,
    } for m in menus]


@router.post("/", status_code=201)
def create_menu(data: InteractiveMenuCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not data.body_text:
        raise HTTPException(400, "Body text zaroori hai")
    if not data.items or len(data.items) == 0:
        raise HTTPException(400, "Kam az kam 1 item zaroori hai")
    if data.menu_type == "buttons" and len(data.items) > 3:
        raise HTTPException(400, "Buttons max 3 ho sakte hain")
    if data.menu_type == "list" and len(data.items) > 10:
        raise HTTPException(400, "List items max 10 ho sakte hain")

    menu = InteractiveMenu(user_id=current_user.id, **data.model_dump())
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return {"message": "Interactive menu created ✅", "id": menu.id}


@router.put("/{menu_id}")
def update_menu(menu_id: int, data: InteractiveMenuUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    menu = db.query(InteractiveMenu).filter(
        InteractiveMenu.id == menu_id,
        InteractiveMenu.user_id == current_user.id
    ).first()
    if not menu:
        raise HTTPException(404, "Menu not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(menu, field, value)
    db.commit()
    return {"message": "Menu updated ✅"}


@router.delete("/{menu_id}")
def delete_menu(menu_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    menu = db.query(InteractiveMenu).filter(
        InteractiveMenu.id == menu_id,
        InteractiveMenu.user_id == current_user.id
    ).first()
    if not menu:
        raise HTTPException(404, "Menu not found")
    db.delete(menu)
    db.commit()
    return {"message": "Menu deleted ✅"}


@router.post("/{menu_id}/toggle")
def toggle_menu(menu_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    menu = db.query(InteractiveMenu).filter(
        InteractiveMenu.id == menu_id,
        InteractiveMenu.user_id == current_user.id
    ).first()
    if not menu:
        raise HTTPException(404, "Menu not found")
    menu.is_active = not menu.is_active
    db.commit()
    return {"is_active": menu.is_active}
