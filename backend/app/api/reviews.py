"""API router for human review workflow."""

from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.review import ReviewService
from app.schemas.review import (
    ReviewRequestResponse,
    CorrectionCreate,
    CorrectionResponse,
    ReviewActionCreate,
    ReviewActionResponse,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewRequestResponse])
def list_review_queue(status: str | None = None, db: Session = Depends(get_db)):
    service = ReviewService(db)
    return service.list_queue(status=status)


@router.get("/{review_id}", response_model=ReviewRequestResponse)
def get_review_request(review_id: UUID, db: Session = Depends(get_db)):
    service = ReviewService(db)
    req = service.get_review_request(review_id)
    if not req:
        raise HTTPException(status_code=404, detail="Review request not found")
    return req


@router.post("/{review_id}/corrections", response_model=CorrectionResponse, status_code=status.HTTP_201_CREATED)
def add_correction(review_id: UUID, payload: CorrectionCreate, db: Session = Depends(get_db)):
    service = ReviewService(db)
    try:
        correction = service.add_correction(
            review_request_id=review_id,
            field_path=payload.field_path,
            original_value=payload.original_value,
            corrected_value=payload.corrected_value,
            reviewer_id=payload.reviewer_id,
        )
        return correction
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{review_id}/actions", response_model=ReviewRequestResponse, status_code=status.HTTP_200_OK)
def perform_review_action(review_id: UUID, payload: ReviewActionCreate, db: Session = Depends(get_db)):
    service = ReviewService(db)
    try:
        updated = service.perform_action(
            review_request_id=review_id,
            action=payload.action,
            reviewer_id=payload.reviewer_id,
            notes=payload.notes,
        )
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
