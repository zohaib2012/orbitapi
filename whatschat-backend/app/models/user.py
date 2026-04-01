from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Enum, BigInteger, Float, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class PlanType(str, enum.Enum):
    starter = "starter"
    professional = "professional"
    enterprise = "enterprise"


class TeamRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    manager = "manager"
    agent = "agent"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    scheduled = "scheduled"
    completed = "completed"
    paused = "paused"


class ContactStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class FlowStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    draft = "draft"


class MemberStatus(str, enum.Enum):
    active = "active"
    invited = "invited"
    inactive = "inactive"


# ─── MODELS ───────────────────────────────────────────────────────────────────

class User(Base):
    """Main vendor/business account"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    plan = Column(Enum(PlanType), default=PlanType.starter)
    whatsapp_connected = Column(Boolean, default=False)
    whatsapp_phone_id = Column(String(100), nullable=True)
    whatsapp_token = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    team_members = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    bot_flows = relationship("BotFlow", back_populates="user", cascade="all, delete-orphan")
    contact_lists = relationship("ContactList", back_populates="user", cascade="all, delete-orphan")


class Contact(Base):
    """WhatsApp contacts"""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    phone = Column(String(30), nullable=False)
    email = Column(String(255), nullable=True)
    tags = Column(JSON, default=list)  # ["VIP", "Active"]
    status = Column(Enum(ContactStatus), default=ContactStatus.active)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="contacts")
    messages = relationship("Message", back_populates="contact")


class ContactList(Base):
    """Groups of contacts for targeting campaigns"""
    __tablename__ = "contact_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    contact_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="contact_lists")


class Campaign(Base):
    """WhatsApp marketing campaigns"""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    message_template = Column(Text, nullable=False)
    target_audience = Column(String(200), nullable=True)  # "VIP Customers"
    status = Column(Enum(CampaignStatus), default=CampaignStatus.draft)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Stats
    total_sent = Column(Integer, default=0)
    total_delivered = Column(Integer, default=0)
    total_read = Column(Integer, default=0)
    total_clicked = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="campaigns")
    messages = relationship("Message", back_populates="campaign")


class Message(Base):
    """Individual messages sent to contacts"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_delivered = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    is_clicked = Column(Boolean, default=False)
    whatsapp_message_id = Column(String(200), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    campaign = relationship("Campaign", back_populates="messages")
    contact = relationship("Contact", back_populates="messages")


class BotFlow(Base):
    """Chatbot automation flows"""
    __tablename__ = "bot_flows"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)  # "keyword", "new_contact", "business_hours"
    trigger_value = Column(String(200), nullable=True)  # keyword value e.g. "track"
    response_message = Column(Text, nullable=False)
    status = Column(Enum(FlowStatus), default=FlowStatus.active)
    total_responses = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="bot_flows")


class TeamMember(Base):
    """Team members with roles and permissions"""
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(Enum(TeamRole), default=TeamRole.agent)
    permissions = Column(JSON, default=list)  # ["campaigns", "contacts", "analytics"]
    status = Column(Enum(MemberStatus), default=MemberStatus.invited)
    last_active = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="team_members")


# ─── NEW MODELS ───────────────────────────────────────────────────────────────

class MediaType(str, enum.Enum):
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"

class AutoReplyType(str, enum.Enum):
    text = "text"
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"

class TemplateStatus(str, enum.Enum):
    approved = "approved"
    pending = "pending"
    rejected = "rejected"

class SubscriptionRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    denied = "denied"

class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class MessageLog(Base):
    """Detailed log of all messages sent/received"""
    __tablename__ = "message_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_phone       = Column(String(30), nullable=False)
    contact_name        = Column(String(200), nullable=True)
    direction           = Column(Enum(MessageDirection), default=MessageDirection.outbound)
    message_type        = Column(String(20), default="text")  # text/image/video/audio
    content             = Column(Text, nullable=True)
    media_url           = Column(String(500), nullable=True)
    whatsapp_message_id = Column(String(200), nullable=True)
    is_delivered        = Column(Boolean, default=False)
    is_read             = Column(Boolean, default=False)
    campaign_id         = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    sent_at             = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at        = Column(DateTime(timezone=True), nullable=True)
    read_at             = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class WhatsAppTemplate(Base):
    """WhatsApp approved message templates"""
    __tablename__ = "whatsapp_templates"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    name          = Column(String(200), nullable=False)
    language      = Column(String(10), default="en_US")
    category      = Column(String(50), default="MARKETING")  # MARKETING/UTILITY/AUTHENTICATION
    header_type   = Column(String(20), nullable=True)   # TEXT/IMAGE/VIDEO/DOCUMENT
    header_content= Column(Text, nullable=True)
    body          = Column(Text, nullable=False)
    footer        = Column(Text, nullable=True)
    status        = Column(Enum(TemplateStatus), default=TemplateStatus.pending)
    meta_template_id = Column(String(200), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])


class AutoReply(Base):
    """Auto reply rules — keyword triggers with text/media responses"""
    __tablename__ = "auto_replies"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    name            = Column(String(200), nullable=False)
    trigger_keyword = Column(String(200), nullable=False)  # "hello", "price", "hi"
    match_type      = Column(String(20), default="contains")  # exact/contains/starts_with
    reply_type      = Column(Enum(AutoReplyType), default=AutoReplyType.text)
    reply_text      = Column(Text, nullable=True)
    media_url       = Column(String(500), nullable=True)   # for image/video/audio
    media_caption   = Column(Text, nullable=True)
    is_active       = Column(Boolean, default=True)
    total_triggered = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])


class SubscriptionRequest(Base):
    """Manual payment requests via WhatsApp screenshot"""
    __tablename__ = "subscription_requests"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan           = Column(String(50), nullable=False)   # starter/professional/enterprise
    amount         = Column(Float, nullable=False)
    payment_method = Column(String(100), nullable=True)   # "JazzCash", "Easypaisa", etc
    screenshot_url = Column(String(500), nullable=True)   # payment proof
    status         = Column(Enum(SubscriptionRequestStatus), default=SubscriptionRequestStatus.pending)
    admin_note     = Column(Text, nullable=True)
    requested_at   = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at    = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class BusinessSettings(Base):
    """Business profile and general settings per user"""
    __tablename__ = "business_settings"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    business_name    = Column(String(200), nullable=True)
    logo_url         = Column(String(500), nullable=True)
    website          = Column(String(300), nullable=True)
    address          = Column(Text, nullable=True)
    support_email    = Column(String(255), nullable=True)
    support_phone    = Column(String(30), nullable=True)
    timezone         = Column(String(50), default="Asia/Karachi")
    welcome_message  = Column(Text, nullable=True)
    welcome_media_url  = Column(String(500), nullable=True)
    welcome_media_type = Column(String(20), nullable=True)  # text/image/video/audio/mixed
    welcome_enabled    = Column(Boolean, default=True)
    away_message     = Column(Text, nullable=True)
    business_hours   = Column(JSON, nullable=True)  # {"mon": "9-5", "tue": "9-5"}
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])


class InteractiveMenu(Base):
    """WhatsApp Interactive List/Button menus with follow-up responses"""
    __tablename__ = "interactive_menus"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    name            = Column(String(200), nullable=False)
    trigger_keyword = Column(String(200), nullable=False)
    match_type      = Column(String(20), default="contains")  # exact/contains/starts_with
    menu_type       = Column(String(20), default="list")  # list / buttons
    header_text     = Column(String(60), nullable=True)
    body_text       = Column(Text, nullable=False)
    footer_text     = Column(String(60), nullable=True)
    button_text     = Column(String(20), nullable=True)  # List button label
    items           = Column(JSON, default=list)
    # List items: [{"id":"1","title":"Service Info","description":"Details"}]
    # Button items: [{"id":"btn_1","title":"Yes"},{"id":"btn_2","title":"No"}]
    follow_up_rules = Column(JSON, nullable=True)
    # {"1": {"type":"text","content":"Details..."},
    #  "2": {"type":"media","media_type":"image","media_url":"...","caption":"..."}}
    is_active       = Column(Boolean, default=True)
    total_triggered = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])


class InboxMessage(Base):
    """Live chat inbox — incoming messages from customers"""
    __tablename__ = "inbox_messages"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_phone      = Column(String(30), nullable=False)
    customer_name       = Column(String(200), nullable=True)
    direction           = Column(Enum(MessageDirection), default=MessageDirection.inbound)
    message_type        = Column(String(20), default="text")
    content             = Column(Text, nullable=True)
    media_url           = Column(String(500), nullable=True)
    whatsapp_message_id = Column(String(200), nullable=True)
    is_read             = Column(Boolean, default=False)
    is_starred          = Column(Boolean, default=False)
    quoted_message_id   = Column(Integer, nullable=True)
    whatsapp_status     = Column(String(20), default="sent")  # sent/delivered/read
    received_at         = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])


class FavoriteConversation(Base):
    """Conversations marked as favorite by the user"""
    __tablename__ = "favorite_conversations"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_phone  = Column(String(30), nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])