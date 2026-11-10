"""Add review tables and relationships.

Revision ID: 20261110_0003
Revises: 20261024_0002
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0003"
down_revision: Union[str, None] = "20261024_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("original_extraction", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_request_id", sa.Uuid(), sa.ForeignKey("review_requests.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field_path", sa.String(512), nullable=False),
        sa.Column("original_value", sa.JSON(), nullable=True),
        sa.Column("corrected_value", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("corrected_by", sa.String(255), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "review_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_request_id", sa.Uuid(), sa.ForeignKey("review_requests.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reviewer_id", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("review_actions")
    op.drop_table("corrections")
    op.drop_table("review_requests")
