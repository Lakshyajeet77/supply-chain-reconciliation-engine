"""Add reconciliation snapshot table for immutable audit trail.

Records the exact approved document data used in a reconciliation run.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0004"
down_revision: Union[str, None] = "20261110_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("po_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("delivery_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("review_request_ids", sa.JSON(), nullable=False),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reconciliation_result", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reconciliation_snapshots")
