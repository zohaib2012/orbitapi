from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import csv, io
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Contact, ContactStatus
from app.schemas.schemas import ContactCreate, ContactUpdate, ContactOut, ContactsStatsOut

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("/stats", response_model=ContactsStatsOut)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total = db.query(Contact).filter(Contact.user_id == current_user.id).count()
    active = db.query(Contact).filter(Contact.user_id == current_user.id, Contact.status == ContactStatus.active).count()
    inactive = total - active
    from app.models.user import ContactList
    lists = db.query(ContactList).filter(ContactList.user_id == current_user.id).count()
    return {"total": total, "active": active, "inactive": inactive, "total_lists": lists}


@router.get("/", response_model=List[ContactOut])
def get_contacts(
    search: Optional[str] = Query(None),
    status: Optional[ContactStatus] = Query(None),
    tag: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Contact).filter(Contact.user_id == current_user.id)
    if search:
        query = query.filter(
            (Contact.name.ilike(f"%{search}%")) |
            (Contact.phone.ilike(f"%{search}%")) |
            (Contact.email.ilike(f"%{search}%"))
        )
    if status:
        query = query.filter(Contact.status == status)
    return query.order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ContactOut, status_code=201)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check duplicate phone for this user
    exists = db.query(Contact).filter(Contact.user_id == current_user.id, Contact.phone == data.phone).first()
    if exists:
        raise HTTPException(status_code=400, detail="Contact with this phone already exists")

    contact = Contact(user_id=current_user.id, **data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: int,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return {"message": "Contact deleted"}


@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import contacts from CSV. Required columns: name, phone. Optional: email, tags"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    imported = 0
    skipped = 0
    for row in reader:
        phone = row.get("phone", "").strip()
        name = row.get("name", "").strip()
        if not phone or not name:
            skipped += 1
            continue
        exists = db.query(Contact).filter(Contact.user_id == current_user.id, Contact.phone == phone).first()
        if exists:
            skipped += 1
            continue
        tags_raw = row.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        contact = Contact(
            user_id=current_user.id,
            name=name,
            phone=phone,
            email=row.get("email", None) or None,
            tags=tags,
        )
        db.add(contact)
        imported += 1

    db.commit()
    return {"imported": imported, "skipped": skipped, "message": f"{imported} contacts imported successfully"}