"""Explicit verification, invitation acceptance and selected summary sharing.
No family endpoint exposes original scan text, private URLs, full results or history.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr, field_validator
from sqlalchemy import select, delete, func
from ..database import (
    EmailVerification,
    FamilyGroup,
    FamilyMember,
    FamilyInvitation,
    FamilyAlert,
    UserPreference,
    User,
    Scan,
)
from .mailer import send_email


def digest(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def utcnow():
    return datetime.now(timezone.utc)


def expired(value):
    return value.replace(tzinfo=timezone.utc) < utcnow()


def is_verified(session, user_id):
    record = session.get(EmailVerification, user_id)
    return bool(record and record.verified_at)


class TokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class GroupIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def clean(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("Enter at least two non-space characters.")
        return value.strip()


class InviteIn(BaseModel):
    email: EmailStr


class PreferencesIn(BaseModel):
    language: Literal["en", "hi", "mr"]


class ShareIn(BaseModel):
    scan_id: int
    consent: bool = False


def make_family_router(current, db):
    router = APIRouter()

    def verified(user=Depends(current), session=Depends(db)):
        if not is_verified(session, user.id):
            raise HTTPException(403, "Verify your email before using family sharing.")
        return user

    def member(session, user, group_id):
        group = session.get(FamilyGroup, group_id)
        if not group or not session.get(FamilyMember, (group_id, user.id)):
            raise HTTPException(404, "Family group not found.")
        return group

    def owner(session, user, group_id):
        group = member(session, user, group_id)
        if group.owner_id != user.id:
            raise HTTPException(
                403, "Only the family owner can manage invitations and members."
            )
        return group

    @router.get("/api/profile/preferences")
    def preferences(user=Depends(current), session=Depends(db)):
        item = session.get(UserPreference, user.id)
        return {"language": item.language if item else "en"}

    @router.put("/api/profile/preferences")
    def set_preferences(
        data: PreferencesIn, user=Depends(current), session=Depends(db)
    ):
        item = session.get(UserPreference, user.id)
        if not item:
            item = UserPreference(user_id=user.id)
            session.add(item)
        item.language = data.language
        session.commit()
        return {"language": item.language}

    @router.post("/api/auth/send-verification")
    def send_verification(user=Depends(current), session=Depends(db)):
        row = session.get(EmailVerification, user.id)
        if row and row.verified_at:
            return {"message": "Your email is already verified."}
        # Authenticated callers only. Short cooldown also limits mail-spam retries.
        if (
            row
            and row.expires
            and row.expires.replace(tzinfo=timezone.utc)
            > utcnow() + timedelta(minutes=29)
        ):
            raise HTTPException(
                429, "Wait a minute before requesting another verification email."
            )
        raw = secrets.token_urlsafe(32)
        if not row:
            row = EmailVerification(user_id=user.id)
            session.add(row)
        row.digest = digest(raw)
        row.expires = utcnow() + timedelta(minutes=30)
        link = (
            os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
            + "/verify-email?"
            + urlencode({"token": raw})
        )
        send_email(
            user.email,
            "Verify your ScamShield email",
            f"Confirm your email address:\n{link}\nThis single-use link expires in 30 minutes. If you did not request it, ignore this message.",
        )
        session.commit()
        return {"message": "Verification email sent. Check your inbox."}

    @router.post("/api/auth/verify-email")
    def verify_email(data: TokenIn, session=Depends(db)):
        row = session.scalar(
            select(EmailVerification)
            .where(EmailVerification.digest == digest(data.token))
            .with_for_update()
        )
        if not row or not row.expires or expired(row.expires) or row.verified_at:
            raise HTTPException(400, "Invalid or expired verification link.")
        row.verified_at = utcnow()
        row.digest = None
        row.expires = None
        session.commit()
        return {"message": "Email verified. You can now use family safety."}

    @router.get("/api/families")
    def list_groups(user=Depends(verified), session=Depends(db)):
        groups = session.scalars(
            select(FamilyGroup)
            .join(FamilyMember, FamilyMember.group_id == FamilyGroup.id)
            .where(FamilyMember.user_id == user.id)
            .order_by(FamilyGroup.id)
        ).all()
        return [
            {"id": g.id, "name": g.name, "owner": g.owner_id == user.id} for g in groups
        ]

    @router.post("/api/families", status_code=201)
    def create_group(data: GroupIn, user=Depends(verified), session=Depends(db)):
        if (
            session.scalar(
                select(func.count(FamilyGroup.id)).where(
                    FamilyGroup.owner_id == user.id
                )
            )
            >= 5
        ):
            raise HTTPException(409, "You can own at most five family groups.")
        group = FamilyGroup(owner_id=user.id, name=data.name)
        session.add(group)
        session.flush()
        session.add(FamilyMember(group_id=group.id, user_id=user.id))
        session.commit()
        return {"id": group.id, "name": group.name, "owner": True}

    @router.get("/api/families/{group_id}")
    def group_detail(group_id: int, user=Depends(verified), session=Depends(db)):
        group = member(session, user, group_id)
        # Member consent shares account display names, not email addresses.
        members = session.execute(
            select(User.id, User.name)
            .join(FamilyMember, FamilyMember.user_id == User.id)
            .where(FamilyMember.group_id == group_id)
        ).all()
        alerts = session.scalars(
            select(FamilyAlert)
            .where(FamilyAlert.group_id == group_id)
            .order_by(FamilyAlert.id.desc())
            .limit(50)
        ).all()
        invites = (
            session.scalars(
                select(FamilyInvitation)
                .where(
                    FamilyInvitation.group_id == group_id,
                    FamilyInvitation.status == "pending",
                )
                .order_by(FamilyInvitation.id.desc())
                .limit(50)
            ).all()
            if group.owner_id == user.id
            else []
        )
        return {
            "id": group.id,
            "name": group.name,
            "owner": group.owner_id == user.id,
            "owner_id": group.owner_id,
            "members": [{"id": m.id, "name": m.name} for m in members],
            "invitations": [
                {
                    "id": i.id,
                    "email": i.email,
                    "status": "expired" if expired(i.expires) else i.status,
                }
                for i in invites
            ],
            "alerts": [
                {
                    "id": a.id,
                    "author_id": a.author_id,
                    "kind": a.kind,
                    "score": a.score,
                    "level": a.level,
                    "created_at": a.created_at,
                }
                for a in alerts
            ],
        }

    @router.post("/api/families/{group_id}/invitations", status_code=201)
    def invite(
        group_id: int, data: InviteIn, user=Depends(verified), session=Depends(db)
    ):
        owner(session, user, group_id)
        email = str(data.email).lower()
        if email == user.email:
            raise HTTPException(409, "You are already a member.")
        if (
            session.scalar(
                select(func.count(FamilyMember.user_id)).where(
                    FamilyMember.group_id == group_id
                )
            )
            >= 10
        ):
            raise HTTPException(409, "A family group supports at most ten members.")
        pending = session.scalars(
            select(FamilyInvitation).where(
                FamilyInvitation.group_id == group_id,
                FamilyInvitation.status == "pending",
            )
        ).all()
        if sum(not expired(i.expires) for i in pending) >= 10:
            raise HTTPException(409, "This group has too many pending invitations.")
        for old in pending:
            if old.email == email:
                old.status = "revoked"
                old.digest = None
        raw = secrets.token_urlsafe(32)
        invitation = FamilyInvitation(
            group_id=group_id,
            email=email,
            digest=digest(raw),
            expires=utcnow() + timedelta(days=2),
        )
        session.add(invitation)
        link = (
            os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
            + "/family?"
            + urlencode({"invitation": raw})
        )
        send_email(
            email,
            "ScamShield family invitation",
            f"You were invited to a ScamShield family group.\n{link}\nSign in with this email address, verify your email, then explicitly accept or decline. Acceptance shares your display name, not your private messages or scan history. The link expires in 48 hours. Ignore it to decline.",
        )
        session.commit()
        return {
            "id": invitation.id,
            "message": "Invitation sent. The recipient must explicitly accept.",
        }

    @router.post("/api/families/invitations/preview")
    def preview(data: TokenIn, user=Depends(verified), session=Depends(db)):
        invitation = session.scalar(
            select(FamilyInvitation).where(
                FamilyInvitation.digest == digest(data.token),
                FamilyInvitation.email == user.email,
            )
        )
        if (
            not invitation
            or invitation.status != "pending"
            or expired(invitation.expires)
        ):
            raise HTTPException(404, "Invitation not found or expired.")
        group = session.get(FamilyGroup, invitation.group_id)
        return {
            "group_name": group.name,
            "expires": invitation.expires,
            "consent_notice": "Accepting shares your display name. Your private scans and messages are never automatically shared.",
        }

    @router.post("/api/families/invitations/accept")
    def accept(data: TokenIn, user=Depends(verified), session=Depends(db)):
        invitation = session.scalar(
            select(FamilyInvitation)
            .where(
                FamilyInvitation.digest == digest(data.token),
                FamilyInvitation.email == user.email,
            )
            .with_for_update()
        )
        if (
            not invitation
            or invitation.status != "pending"
            or expired(invitation.expires)
        ):
            raise HTTPException(404, "Invitation not found or expired.")
        # Serialize membership capacity changes on the group in PostgreSQL.
        group = session.scalar(
            select(FamilyGroup)
            .where(FamilyGroup.id == invitation.group_id)
            .with_for_update()
        )
        if not group:
            raise HTTPException(404, "Family group not found.")
        if not session.get(FamilyMember, (group.id, user.id)):
            if (
                session.scalar(
                    select(func.count(FamilyMember.user_id)).where(
                        FamilyMember.group_id == group.id
                    )
                )
                >= 10
            ):
                raise HTTPException(409, "The family group is full.")
            session.add(FamilyMember(group_id=group.id, user_id=user.id))
        invitation.status = "accepted"
        invitation.digest = None
        session.commit()
        return {"message": "Family invitation accepted.", "group_id": group.id}

    @router.delete("/api/families/{group_id}/invitations/{invitation_id}")
    def revoke(
        group_id: int, invitation_id: int, user=Depends(verified), session=Depends(db)
    ):
        owner(session, user, group_id)
        item = session.get(FamilyInvitation, invitation_id)
        if not item or item.group_id != group_id:
            raise HTTPException(404, "Invitation not found.")
        item.status = "revoked"
        item.digest = None
        session.commit()
        return {"message": "Invitation revoked."}

    @router.delete("/api/families/{group_id}/members/{user_id}")
    def remove(
        group_id: int, user_id: int, user=Depends(verified), session=Depends(db)
    ):
        group = member(session, user, group_id)
        if user_id == group.owner_id:
            raise HTTPException(
                409, "The owner must delete the group instead of leaving."
            )
        if user.id != user_id and group.owner_id != user.id:
            raise HTTPException(403, "You cannot remove another member.")
        item = session.get(FamilyMember, (group_id, user_id))
        if not item:
            raise HTTPException(404, "Member not found.")
        session.delete(item)
        session.execute(
            delete(FamilyAlert).where(
                FamilyAlert.group_id == group_id, FamilyAlert.author_id == user_id
            )
        )
        session.commit()
        return {"message": "Membership and that member's shared summaries removed."}

    @router.post("/api/families/{group_id}/alerts", status_code=201)
    def share(
        group_id: int, data: ShareIn, user=Depends(verified), session=Depends(db)
    ):
        member(session, user, group_id)
        if not data.consent:
            raise HTTPException(
                422, "Explicit consent is required for each shared summary."
            )
        scan = session.get(Scan, data.scan_id)
        if not scan or scan.user_id != user.id:
            raise HTTPException(404, "Scan not found.")
        if (
            session.scalar(
                select(func.count(FamilyAlert.id)).where(
                    FamilyAlert.group_id == group_id
                )
            )
            >= 200
        ):
            raise HTTPException(409, "Remove old shared summaries before adding more.")
        alert = FamilyAlert(
            group_id=group_id,
            author_id=user.id,
            kind=scan.kind,
            score=scan.score,
            level=scan.result["level"],
        )
        session.add(alert)
        session.commit()
        return {
            "id": alert.id,
            "message": "Only scan type, score, risk level and sharing time were shared.",
        }

    @router.delete("/api/families/{group_id}/alerts/{alert_id}")
    def unshare(
        group_id: int, alert_id: int, user=Depends(verified), session=Depends(db)
    ):
        group = member(session, user, group_id)
        alert = session.get(FamilyAlert, alert_id)
        if not alert or alert.group_id != group_id:
            raise HTTPException(404, "Shared summary not found.")
        if alert.author_id != user.id and group.owner_id != user.id:
            raise HTTPException(
                403, "Only the author or owner can remove this summary."
            )
        session.delete(alert)
        session.commit()
        return {"message": "Shared summary removed."}

    @router.delete("/api/families/{group_id}")
    def delete_group(group_id: int, user=Depends(verified), session=Depends(db)):
        group = owner(session, user, group_id)
        for model in (FamilyAlert, FamilyInvitation, FamilyMember):
            session.execute(delete(model).where(model.group_id == group_id))
        session.delete(group)
        session.commit()
        return {"message": "Family group and all shared summaries deleted."}

    return router
