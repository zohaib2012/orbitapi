from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Campaign, CampaignStatus, Contact, ContactStatus, Message
from app.schemas.schemas import CampaignCreate, CampaignUpdate, CampaignOut, CampaignStatsOut
from app.services.whatsapp_service import send_whatsapp_message

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


# ── STATS ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=CampaignStatsOut)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    base = db.query(Campaign).filter(Campaign.user_id == current_user.id)
    return {
        "total":     base.count(),
        "active":    db.query(Campaign).filter(Campaign.user_id == current_user.id, Campaign.status == CampaignStatus.active).count(),
        "scheduled": db.query(Campaign).filter(Campaign.user_id == current_user.id, Campaign.status == CampaignStatus.scheduled).count(),
        "completed": db.query(Campaign).filter(Campaign.user_id == current_user.id, Campaign.status == CampaignStatus.completed).count(),
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[CampaignOut])
def get_campaigns(
    status: Optional[CampaignStatus] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Campaign).filter(Campaign.user_id == current_user.id)
    if status: query = query.filter(Campaign.status == status)
    if search: query = query.filter(Campaign.name.ilike(f"%{search}%"))
    return query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=CampaignOut, status_code=201)
def create_campaign(data: CampaignCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    campaign = Campaign(user_id=current_user.id, **data.model_dump())
    db.add(campaign); db.commit(); db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == current_user.id).first()
    if not c: raise HTTPException(404, "Campaign not found")
    return c


@router.put("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, data: CampaignUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == current_user.id).first()
    if not c: raise HTTPException(404, "Campaign not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit(); db.refresh(c)
    return c


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == current_user.id).first()
    if not c: raise HTTPException(404, "Campaign not found")
    db.delete(c); db.commit()
    return {"message": "Campaign deleted"}


# ── SEND CAMPAIGN ─────────────────────────────────────────────────────────────

async def _do_send_campaign(campaign_id: int, user_id: int, db: Session):
    """
    Background mein chalti hai:
    1. Sare active contacts lo
    2. Har contact ko WhatsApp message bhejo
    3. Har message DB mein save karo
    4. Campaign stats update karo
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    user     = db.query(User).filter(User.id == user_id).first()
    if not campaign or not user: return

    # Target contacts find karo
    contacts_query = db.query(Contact).filter(
        Contact.user_id == user_id,
        Contact.status == ContactStatus.active
    )

    # Agar target_audience set hai toh tags se filter karo
    if campaign.target_audience and campaign.target_audience.strip():
        tag = campaign.target_audience.strip()
        # JSON array mein tag dhundo
        contacts_query = contacts_query.filter(
            Contact.tags.contains([tag])
        )

    contacts = contacts_query.all()

    if not contacts:
        # Koi contact nahi mila — campaign complete mark karo
        campaign.status = CampaignStatus.completed
        campaign.total_sent = 0
        db.commit()
        return

    sent_count = 0
    failed_count = 0

    for contact in contacts:
        try:
            # WhatsApp pe message bhejo
            result = await send_whatsapp_message(
                phone_number_id = user.whatsapp_phone_id,
                access_token    = user.whatsapp_token,
                to              = contact.phone,
                message         = campaign.message_template
            )

            # Message DB mein save karo
            msg = Message(
                campaign_id         = campaign.id,
                contact_id          = contact.id,
                content             = campaign.message_template,
                whatsapp_message_id = result.get("message_id", ""),
                is_delivered        = False,
                is_read             = False,
                sent_at             = datetime.utcnow()
            )
            db.add(msg)
            sent_count += 1

        except Exception as e:
            failed_count += 1
            print(f"Failed to send to {contact.phone}: {e}")
            # Failed message bhi record karo
            msg = Message(
                campaign_id         = campaign.id,
                contact_id          = contact.id,
                content             = campaign.message_template,
                whatsapp_message_id = None,
                is_delivered        = False,
                sent_at             = datetime.utcnow()
            )
            db.add(msg)

    # Campaign stats update karo
    campaign.total_sent      = sent_count
    campaign.total_delivered = 0   # Webhook se update hoga
    campaign.total_read      = 0   # Webhook se update hoga
    campaign.status          = CampaignStatus.completed
    campaign.sent_at         = datetime.utcnow()
    db.commit()

    print(f"Campaign {campaign_id}: {sent_count} sent, {failed_count} failed")


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Campaign ke sare active contacts ko WhatsApp message bhejo"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign: raise HTTPException(404, "Campaign not found")
    if campaign.status == CampaignStatus.completed:
        raise HTTPException(400, "Yeh campaign pehle se complete ho chuki hai")
    if not current_user.whatsapp_connected:
        raise HTTPException(400, "WhatsApp connected nahi hai. Pehle connect karo.")
    if not current_user.whatsapp_phone_id or not current_user.whatsapp_token:
        raise HTTPException(400, "WhatsApp credentials missing hain. Dobara connect karo.")

    # Count karo kitne contacts milenge
    contacts_count = db.query(Contact).filter(
        Contact.user_id == current_user.id,
        Contact.status == ContactStatus.active
    ).count()

    if contacts_count == 0:
        raise HTTPException(400, "Koi active contact nahi hai. Pehle contacts add karo.")

    # Status active karo
    campaign.status  = CampaignStatus.active
    campaign.sent_at = datetime.utcnow()
    db.commit()

    # Background mein bhejo
    background_tasks.add_task(_do_send_campaign, campaign_id, current_user.id, db)

    return {
        "message":       f"Campaign send ho rahi hai — {contacts_count} contacts ko",
        "campaign_id":   campaign_id,
        "contacts_count": contacts_count
    }


@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == current_user.id).first()
    if not c: raise HTTPException(404, "Campaign not found")
    c.status = CampaignStatus.paused
    db.commit()
    return {"message": "Campaign paused"}