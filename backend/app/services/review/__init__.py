"""Review workflow service and business logic."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from app.models.review import ReviewRequest, Correction, ReviewAction
from app.models.document import Document


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_review_request_if_needed(self, document: Document) -> ReviewRequest | None:
        """Create a review request when a document is extracted."""
        if not document.extracted_data:
            return None

        # Check if review request already exists
        existing = self.db.query(ReviewRequest).filter_by(document_id=document.id).first()
        if existing:
            return existing

        review_req = ReviewRequest(
            id=uuid4(),
            document_id=document.id,
            status="PENDING_REVIEW",
            original_extraction=document.extracted_data,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(review_req)
        self.db.commit()
        self.db.refresh(review_req)
        return review_req

    def get_review_request(self, review_id: UUID) -> ReviewRequest | None:
        return self.db.query(ReviewRequest).filter_by(id=review_id).first()

    def get_by_document(self, document_id: UUID) -> ReviewRequest | None:
        return self.db.query(ReviewRequest).filter_by(document_id=document_id).first()

    def list_queue(self, status: str | None = None) -> list[ReviewRequest]:
        query = self.db.query(ReviewRequest)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(ReviewRequest.created_at.desc()).all()

    def add_correction(
        self,
        *,
        review_request_id: UUID,
        field_path: str,
        original_value: Any,
        corrected_value: Any,
        reviewer_id: str,
    ) -> Correction:
        review_req = self.get_review_request(review_request_id)
        if not review_req:
            raise ValueError("Review request not found")

        # Determine version
        existing_corrections = self.db.query(Correction).filter_by(
            review_request_id=review_request_id, field_path=field_path
        ).order_by(Correction.version.desc()).all()

        next_version = (existing_corrections[0].version + 1) if existing_corrections else 1

        # If status was APPROVED, reset to IN_REVIEW because approval is invalidated by new/changed corrections
        if review_req.status == "APPROVED":
            review_req.status = "IN_REVIEW"

        correction = Correction(
            id=uuid4(),
            review_request_id=review_request_id,
            field_path=field_path,
            original_value=original_value,
            corrected_value=corrected_value,
            version=next_version,
            corrected_by=reviewer_id,
            corrected_at=datetime.now(timezone.utc),
        )
        self.db.add(correction)
        review_req.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(correction)
        return correction

    def perform_action(
        self,
        *,
        review_request_id: UUID,
        action: str,  # APPROVED, REJECTED, IN_REVIEW
        reviewer_id: str,
        notes: str | None = None,
    ) -> ReviewRequest:
        review_req = self.get_review_request(review_request_id)
        if not review_req:
            raise ValueError("Review request not found")

        if action not in ["APPROVED", "REJECTED", "IN_REVIEW"]:
            raise ValueError(f"Invalid review action: {action}")

        review_req.status = action
        review_req.updated_at = datetime.now(timezone.utc)

        rev_action = ReviewAction(
            id=uuid4(),
            review_request_id=review_request_id,
            action=action,
            reviewer_id=reviewer_id,
            notes=notes,
            performed_at=datetime.now(timezone.utc),
        )
        self.db.add(rev_action)
        self.db.commit()
        self.db.refresh(review_req)
        return review_req

    def get_effective_extracted_data(self, review_request_id: UUID) -> dict | None:
        """Returns the extracted data combined with latest approved corrections.
        If not approved, returns original extraction (or raises if strict enforcement needed).
        """
        review_req = self.get_review_request(review_request_id)
        if not review_req:
            return None

        # Rule: Only approved document data may enter final matching/reconciliation
        if review_req.status != "APPROVED":
            return None

        # Start with original extraction
        import copy
        data = copy.deepcopy(review_req.original_extraction)

        # Apply latest version of each correction
        # Group corrections by field_path, pick highest version
        corrections_map: dict[str, Correction] = {}
        for c in review_req.corrections:
            if c.field_path not in corrections_map or c.version > corrections_map[c.field_path].version:
                corrections_map[c.field_path] = c

        for field_path, correction in corrections_map.items():
            # field_path format e.g. "po_number" or "line_items.0.quantity"
            parts = field_path.split(".")
            curr = data
            for part in parts[:-1]:
                if part.isdigit():
                    curr = curr[int(part)]
                else:
                    curr = curr[part]
            last_part = parts[-1]
            if last_part.isdigit():
                curr[int(last_part)] = correction.corrected_value
            else:
                curr[last_part] = correction.corrected_value

        return data
