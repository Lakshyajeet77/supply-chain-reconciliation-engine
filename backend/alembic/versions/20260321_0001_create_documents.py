"""create documents table

Revision ID: 20260321_0001
Revises:
Create Date: 2026-03-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260321_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("stored_path", sa.String(length=1024), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extraction_fixture_id", sa.String(length=255), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256", name="uq_documents_sha256"),
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_table("documents")
