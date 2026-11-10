"""Add document relationships table for transaction grouping.

Allows explicit association of PO, Invoice and optional Delivery documents.
Supports multiple invoices per PO. Uses RESTRICT deletion to preserve audit history.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0005"
down_revision: Union[str, None] = "20261110_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("po_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="SUGGESTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("po_id", "invoice_id", name="uq_relationship_po_invoice"),
    )


def downgrade() -> None:
    op.drop_table("document_relationships")