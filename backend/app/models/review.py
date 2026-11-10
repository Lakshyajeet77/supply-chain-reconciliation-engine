"""ORM models for human review workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.session import Base


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_REVIEW")
    original_extraction: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    corrections: Mapped[list[Correction]] = relationship("Correction", back_populates="review_request", cascade="all, delete-orphan")
    actions: Mapped[list[ReviewAction]] = relationship("ReviewAction", back_populates="review_request", cascade="all, delete-orphan")


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    review_request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("review_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    field_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_value: Mapped[dict | list | str | int | float | None] = mapped_column(JSON, nullable=True)
    corrected_value: Mapped[dict | list | str | int | float | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    corrected_by: Mapped[str] = mapped_column(String(255), nullable=False)
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    review_request: Mapped[ReviewRequest] = relationship("ReviewRequest", back_populates="corrections")


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    review_request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("review_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # APPROVE, REJECT, REQUEST_CHANGES
    reviewer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    review_request: Mapped[ReviewRequest] = relationship("ReviewRequest", back_populates="actions")
