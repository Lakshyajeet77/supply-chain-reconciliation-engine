"""Add extracted document data.

Revision ID: 20261024_0002
Revises: 20260321_0001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261024_0002"
down_revision: Union[str, None] = "20260321_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("extracted_data", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "extracted_data")