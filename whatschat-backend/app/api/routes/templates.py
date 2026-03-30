from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, WhatsAppTemplate

router = APIRouter(prefix="/templates", tags=["Templates"])


class TemplateCreate(BaseModel):
    name:           str
    language:       str = "en_US"
    category:       str = "MARKETING"
    header_type:    Optional[str] = None
    header_content: Optional[str] = None
    body:           str
    footer:         Optional[str] = None


@router.get("/")
def get_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    templates = db.query(WhatsAppTemplate).filter(WhatsAppTemplate.user_id == current_user.id).all()
    return [{
        "id":             t.id,
        "name":           t.name,
        "language":       t.language,
        "category":       t.category,
        "header_type":    t.header_type,
        "header_content": t.header_content,
        "body":           t.body,
        "footer":         t.footer,
        "status":         t.status,
        "created_at":     t.created_at.isoformat() if t.created_at else None,
    } for t in templates]


@router.post("/", status_code=201)
def create_template(data: TemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    template = WhatsAppTemplate(user_id=current_user.id, **data.model_dump())
    db.add(template); db.commit(); db.refresh(template)
    return {"message": "Template created", "id": template.id}


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    t = db.query(WhatsAppTemplate).filter(WhatsAppTemplate.id == template_id, WhatsAppTemplate.user_id == current_user.id).first()
    if not t: raise HTTPException(404, "Not found")
    db.delete(t); db.commit()
    return {"message": "Deleted"}