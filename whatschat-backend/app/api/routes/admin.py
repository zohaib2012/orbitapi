# app/api/routes/admin.py
# Yeh file: whatschat-backend/app/api/routes/admin.py mein rakho

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, SubscriptionRequest
from app.core.security import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/auth/admin", tags=["Admin"])

# ── ADMIN CHECK ───────────────────────────────────────────────
def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ── GET ALL USERS ─────────────────────────────────────────────
@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "plan": u.plan or "free",
            "role": u.role or "user",
            "is_active": u.is_active,
            "created_at": u.created_at,
            "phone_number_id": u.phone_number_id,
        }
        for u in users
    ]

# ── UPDATE USER PLAN ──────────────────────────────────────────
class PlanUpdate(BaseModel):
    plan: str

@router.put("/users/{user_id}/plan")
def update_user_plan(
    user_id: int,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nahi mila")
    
    valid_plans = ["free", "starter", "professional", "enterprise"]
    if payload.plan not in valid_plans:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    user.plan = payload.plan
    db.commit()
    return {"message": f"Plan '{payload.plan}' activate ho gaya!", "user_id": user_id}