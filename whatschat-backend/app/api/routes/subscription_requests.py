from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionRequest, SubscriptionRequestStatus, PlanType

router = APIRouter(prefix="/subscription-requests", tags=["Subscription Requests"])

PLAN_PRICES = {
    "starter":      29,
    "professional": 79,
    "enterprise":   199
}

class CreateRequest(BaseModel):
    plan:           str
    payment_method: Optional[str] = "JazzCash"
    screenshot_url: Optional[str] = None

class ReviewRequest(BaseModel):
    status:     str   # approved / denied
    admin_note: Optional[str] = None


@router.post("/", status_code=201)
def create_subscription_request(
    data: CreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if data.plan not in PLAN_PRICES:
        raise HTTPException(400, "Invalid plan")
    # Pending request already hai?
    existing = db.query(SubscriptionRequest).filter(
        SubscriptionRequest.user_id == current_user.id,
        SubscriptionRequest.status == SubscriptionRequestStatus.pending
    ).first()
    if existing:
        raise HTTPException(400, "Aapki ek request already pending hai")

    req = SubscriptionRequest(
        user_id        = current_user.id,
        plan           = data.plan,
        amount         = PLAN_PRICES[data.plan],
        payment_method = data.payment_method,
        screenshot_url = data.screenshot_url,
        status         = SubscriptionRequestStatus.pending
    )
    db.add(req); db.commit(); db.refresh(req)
    return {"message": "Request submit ho gayi. Admin review karega.", "id": req.id}


@router.get("/my")
def get_my_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reqs = db.query(SubscriptionRequest).filter(
        SubscriptionRequest.user_id == current_user.id
    ).order_by(SubscriptionRequest.requested_at.desc()).all()
    return [{
        "id":             r.id,
        "plan":           r.plan,
        "amount":         r.amount,
        "payment_method": r.payment_method,
        "status":         r.status,
        "admin_note":     r.admin_note,
        "requested_at":   r.requested_at.isoformat() if r.requested_at else None,
        "reviewed_at":    r.reviewed_at.isoformat() if r.reviewed_at else None,
    } for r in reqs]


# ── ADMIN ENDPOINTS ───────────────────────────────────────────────────────────

@router.get("/admin/all")
def admin_get_all_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # TODO: Admin check add karo
    query = db.query(SubscriptionRequest)
    if status: query = query.filter(SubscriptionRequest.status == status)
    reqs = query.order_by(SubscriptionRequest.requested_at.desc()).all()
    return [{
        "id":             r.id,
        "user_id":        r.user_id,
        "user_email":     r.user.email if r.user else None,
        "user_name":      r.user.business_name if r.user else None,
        "plan":           r.plan,
        "amount":         r.amount,
        "payment_method": r.payment_method,
        "screenshot_url": r.screenshot_url,
        "status":         r.status,
        "admin_note":     r.admin_note,
        "requested_at":   r.requested_at.isoformat() if r.requested_at else None,
    } for r in reqs]


@router.post("/admin/{request_id}/review")
def admin_review_request(
    request_id: int,
    data: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(SubscriptionRequest).filter(SubscriptionRequest.id == request_id).first()
    if not req: raise HTTPException(404, "Request not found")
    if req.status != SubscriptionRequestStatus.pending:
        raise HTTPException(400, "Request already reviewed hai")

    req.status      = data.status
    req.admin_note  = data.admin_note
    req.reviewed_at = datetime.utcnow()

    # Agar approved → user ka plan update karo
    if data.status == "approved":
        user = db.query(User).filter(User.id == req.user_id).first()
        if user:
            user.plan = req.plan
            db.add(user)

    db.commit()
    return {"message": f"Request {data.status}"}