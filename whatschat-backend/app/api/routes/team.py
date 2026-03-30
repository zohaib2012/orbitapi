from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, TeamMember, MemberStatus, TeamRole
from app.schemas.schemas import TeamMemberInvite, TeamMemberUpdate, TeamMemberOut, TeamStatsOut

router = APIRouter(prefix="/team", tags=["Team"])

PLAN_SEATS = {"starter": 2, "professional": 10, "enterprise": 999}


@router.get("/stats", response_model=TeamStatsOut)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    members = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).all()
    total = len(members)
    active = sum(1 for m in members if m.status == MemberStatus.active)
    pending = sum(1 for m in members if m.status == MemberStatus.invited)
    seats_total = PLAN_SEATS.get(current_user.plan, 2)
    return {
        "total_members": total,
        "active": active,
        "pending_invites": pending,
        "seats_used": total,
        "seats_total": seats_total,
    }


@router.get("/", response_model=List[TeamMemberOut])
def get_members(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(TeamMember).filter(TeamMember.user_id == current_user.id).order_by(TeamMember.created_at).all()


@router.post("/invite", response_model=TeamMemberOut, status_code=201)
def invite_member(
    data: TeamMemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check seat limit
    current_count = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).count()
    max_seats = PLAN_SEATS.get(current_user.plan, 2)
    if current_count >= max_seats:
        raise HTTPException(status_code=400, detail=f"Seat limit reached ({max_seats}). Upgrade your plan.")

    # Check if already invited
    exists = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.email == data.email
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="This email is already in your team")

    member = TeamMember(
        user_id=current_user.id,
        name=data.name,
        email=data.email,
        role=data.role,
        permissions=data.permissions,
        status=MemberStatus.invited
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    # TODO: Send invite email
    return member


@router.put("/{member_id}", response_model=TeamMemberOut)
def update_member(
    member_id: int, data: TeamMemberUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    member = db.query(TeamMember).filter(TeamMember.id == member_id, TeamMember.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == TeamRole.owner:
        raise HTTPException(status_code=403, detail="Cannot modify owner role")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}")
def remove_member(member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    member = db.query(TeamMember).filter(TeamMember.id == member_id, TeamMember.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == TeamRole.owner:
        raise HTTPException(status_code=403, detail="Cannot remove owner")
    db.delete(member)
    db.commit()
    return {"message": "Member removed"}