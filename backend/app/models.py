from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    """Staff account: Guild President, delegate (cabinet member) or admin."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20))          # president | delegate | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    delegate: Mapped["Delegate"] = relationship(back_populates="user", uselist=False)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    base_severity: Mapped[float] = mapped_column(Float, default=0.5)    # 0..1
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)  # always private


class Delegate(Base):
    __tablename__ = "delegates"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    portfolio: Mapped[str] = mapped_column(String(120))
    categories_handled: Mapped[str] = mapped_column(String(300), default="")  # comma separated names
    max_open_load: Mapped[int] = mapped_column(Integer, default=5)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    show_public: Mapped[bool] = mapped_column(Boolean, default=True)   # listed on the public Cabinet page
    user: Mapped[User] = relationship(back_populates="delegate")


class RelatedGroup(Base):
    __tablename__ = "related_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    master_concern_id: Mapped[int] = mapped_column(Integer)
    reports_count: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Concern(Base):
    __tablename__ = "concerns"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    access_code_hash: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    campus: Mapped[str] = mapped_column(String(60), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    urgency: Mapped[int] = mapped_column(Integer, default=2)          # 1..4
    safety_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    students_affected: Mapped[int] = mapped_column(Integer, default=1)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="new")    # new|assigned|in_progress|resolved|closed
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_score: Mapped[float] = mapped_column(Float, default=0)
    priority_level: Mapped[str] = mapped_column(String(10), default="Low")
    group_id: Mapped[int | None] = mapped_column(ForeignKey("related_groups.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reopened_count: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[Category] = relationship()
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="concern")
    updates: Mapped[list["ConcernUpdate"]] = relationship(back_populates="concern", order_by="ConcernUpdate.id")


class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    concern_id: Mapped[int] = mapped_column(ForeignKey("concerns.id"))
    delegate_id: Mapped[int] = mapped_column(ForeignKey("delegates.id"))
    recommended_score: Mapped[float] = mapped_column(Float, default=0)
    was_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    status: Mapped[str] = mapped_column(String(20), default="active")   # active | completed | reassigned
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    concern: Mapped[Concern] = relationship(back_populates="assignments")
    delegate: Mapped[Delegate] = relationship()


class ConcernUpdate(Base):
    """Replies and notes. visibility: public | private (student sees) | internal (staff only)."""
    __tablename__ = "concern_updates"
    id: Mapped[int] = mapped_column(primary_key=True)
    concern_id: Mapped[int] = mapped_column(ForeignKey("concerns.id"))
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    author_label: Mapped[str] = mapped_column(String(60), default="Student")
    visibility: Mapped[str] = mapped_column(String(10), default="private")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    concern: Mapped[Concern] = relationship(back_populates="updates")


class EscalationEvent(Base):
    __tablename__ = "escalation_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    concern_id: Mapped[int] = mapped_column(ForeignKey("concerns.id"))
    type: Mapped[str] = mapped_column(String(15))              # reminder | escalation
    reason: Mapped[str] = mapped_column(String(200))
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class HandoverRecord(Base):
    __tablename__ = "handover_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    term_label: Mapped[str] = mapped_column(String(60))
    snapshot: Mapped[str] = mapped_column(Text)               # JSON text
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
