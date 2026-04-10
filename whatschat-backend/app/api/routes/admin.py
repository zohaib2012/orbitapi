from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.core.security import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/auth/admin", tags=["Admin"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.email != "admin@rajacloud.com":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/users")
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.query(User).filter(User.email != "admin@rajacloud.com").order_by(User.created_at.desc()).all()
    return [{
        "id": u.id,
        "email": u.email,
        "business_name": u.business_name,
        "plan": u.plan,
        "is_active": u.is_active,
        "is_approved": u.is_approved,
        "whatsapp_connected": u.whatsapp_connected,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    } for u in users]

@router.post("/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_approved = True
    db.commit()
    return {"message": "User approved!"}

@router.post("/users/{user_id}/decline")
def decline_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_approved = False
    db.commit()
    return {"message": "User declined!"}

class UserEdit(BaseModel):
    business_name: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None

@router.put("/users/{user_id}/edit")
def edit_user(user_id: int, data: UserEdit, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if data.business_name is not None:
        user.business_name = data.business_name
    if data.plan is not None:
        user.plan = data.plan
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_approved is not None:
        user.is_approved = data.is_approved
    db.commit()
    return {"message": "User updated!"}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted!"}
