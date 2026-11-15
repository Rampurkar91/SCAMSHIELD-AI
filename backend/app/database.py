import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, ForeignKey, JSON, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

URL = os.getenv("DATABASE_URL", "sqlite:///./scamshield.db")
if URL.startswith("postgres://"):
    URL = URL.replace("postgres://", "postgresql+psycopg://", 1)
if URL.startswith("postgresql://"):
    URL = URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(
    URL, connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(default=0)
    role: Mapped[str] = mapped_column(default="user")


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    content: Mapped[str] = mapped_column(String(12000))
    score: Mapped[int] = mapped_column(Integer, index=True)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(4000))
    status: Mapped[str] = mapped_column(default="Submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ResetToken(Base):
    __tablename__ = "reset_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(String(500))
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class IntegrationEvent(Base):
    __tablename__ = "security_api_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quiz_id: Mapped[str] = mapped_column(String(40))
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    digest: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FamilyGroup(Base):
    __tablename__ = "family_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FamilyMember(Base):
    __tablename__ = "family_members"
    group_id: Mapped[int] = mapped_column(
        ForeignKey("family_groups.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("family_groups.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(254), index=True)
    digest: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FamilyAlert(Base):
    __tablename__ = "family_alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("family_groups.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Consent creates a snapshot without original content, URLs, IDs or explanations.
    kind: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
