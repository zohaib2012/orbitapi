from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.user import PlanType, TeamRole, CampaignStatus, ContactStatus, FlowStatus, MemberStatus


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    business_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ─── USER ─────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    business_name: str
    email: str
    phone: Optional[str]
    plan: PlanType
    whatsapp_connected: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    business_name: Optional[str] = None
    phone: Optional[str] = None


# ─── CONTACT ──────────────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    tags: Optional[List[str]] = []
    status: Optional[ContactStatus] = ContactStatus.active
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[ContactStatus] = None
    notes: Optional[str] = None


class ContactOut(BaseModel):
    id: int
    user_id: int
    name: str
    phone: str
    email: Optional[str]
    tags: List[str]
    status: ContactStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ContactsStatsOut(BaseModel):
    total: int
    active: int
    inactive: int
    total_lists: int


# ─── CAMPAIGN ─────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str
    message_template: str
    target_audience: Optional[str] = None
    status: Optional[CampaignStatus] = CampaignStatus.draft
    scheduled_at: Optional[datetime] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    message_template: Optional[str] = None
    target_audience: Optional[str] = None
    status: Optional[CampaignStatus] = None
    scheduled_at: Optional[datetime] = None


class CampaignOut(BaseModel):
    id: int
    user_id: int
    name: str
    message_template: str
    target_audience: Optional[str]
    status: CampaignStatus
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    total_sent: int
    total_delivered: int
    total_read: int
    total_clicked: int
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignStatsOut(BaseModel):
    total: int
    active: int
    scheduled: int
    completed: int


# ─── BOT FLOW ─────────────────────────────────────────────────────────────────

class BotFlowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str  # "keyword" | "new_contact" | "business_hours"
    trigger_value: Optional[str] = None
    response_message: str
    status: Optional[FlowStatus] = FlowStatus.active


class BotFlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    response_message: Optional[str] = None
    status: Optional[FlowStatus] = None


class BotFlowOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_value: Optional[str]
    response_message: str
    status: FlowStatus
    total_responses: int
    created_at: datetime

    class Config:
        from_attributes = True


class BotFlowStatsOut(BaseModel):
    active_flows: int
    total_responses: int
    success_rate: float
    avg_response_time: float


# ─── TEAM ─────────────────────────────────────────────────────────────────────

class TeamMemberInvite(BaseModel):
    name: str
    email: EmailStr
    role: TeamRole
    permissions: List[str] = []


class TeamMemberUpdate(BaseModel):
    role: Optional[TeamRole] = None
    permissions: Optional[List[str]] = None
    status: Optional[MemberStatus] = None


class TeamMemberOut(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    role: TeamRole
    permissions: List[str]
    status: MemberStatus
    last_active: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class TeamStatsOut(BaseModel):
    total_members: int
    active: int
    pending_invites: int
    seats_used: int
    seats_total: int


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

class AnalyticsOverview(BaseModel):
    total_sent: int
    delivery_rate: float
    read_rate: float
    click_rate: float
    avg_response_time: float
    total_delivered: int
    total_read: int
    total_clicked: int


class DailyMetric(BaseModel):
    date: str
    sent: int
    delivered: int
    read: int
    clicked: int


class DeviceBreakdown(BaseModel):
    android: int
    ios: int
    web: int


# ─── WHATSAPP ─────────────────────────────────────────────────────────────────

class WhatsAppConnectRequest(BaseModel):
    phone_number_id: str
    access_token: str


class SendMessageRequest(BaseModel):
    contact_id: int
    message: str