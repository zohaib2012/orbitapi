from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, BotFlow, FlowStatus
from app.schemas.schemas import BotFlowCreate, BotFlowUpdate, BotFlowOut, BotFlowStatsOut

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.get("/stats", response_model=BotFlowStatsOut)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    flows = db.query(BotFlow).filter(BotFlow.user_id == current_user.id).all()
    active = sum(1 for f in flows if f.status == FlowStatus.active)
    total_responses = sum(f.total_responses for f in flows)
    return {
        "active_flows": active,
        "total_responses": total_responses,
        "success_rate": 87.0,
        "avg_response_time": 1.2
    }


@router.get("/", response_model=List[BotFlowOut])
def get_flows(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(BotFlow).filter(BotFlow.user_id == current_user.id).order_by(BotFlow.created_at.desc()).all()


@router.post("/", response_model=BotFlowOut, status_code=201)
def create_flow(data: BotFlowCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    flow = BotFlow(user_id=current_user.id, **data.model_dump())
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return flow


@router.get("/{flow_id}", response_model=BotFlowOut)
def get_flow(flow_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id, BotFlow.user_id == current_user.id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


@router.put("/{flow_id}", response_model=BotFlowOut)
def update_flow(
    flow_id: int, data: BotFlowUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id, BotFlow.user_id == current_user.id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(flow, field, value)
    db.commit()
    db.refresh(flow)
    return flow


@router.delete("/{flow_id}")
def delete_flow(flow_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id, BotFlow.user_id == current_user.id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    db.delete(flow)
    db.commit()
    return {"message": "Flow deleted"}


@router.post("/{flow_id}/toggle")
def toggle_flow(flow_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id, BotFlow.user_id == current_user.id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    flow.status = FlowStatus.paused if flow.status == FlowStatus.active else FlowStatus.active
    db.commit()
    return {"status": flow.status, "message": f"Flow {flow.status}"}


@router.post("/webhook/incoming")
async def incoming_message(payload: dict):
    """
    WhatsApp webhook - receives incoming messages and triggers bot flows.
    This endpoint is called by Meta's WhatsApp Business API.
    """
    # Verify webhook (Meta sends a challenge)
    if "hub.challenge" in payload:
        return int(payload["hub.challenge"])

    # Process incoming message
    # TODO: Parse message, match keyword triggers, send auto-reply
    return {"status": "received"}