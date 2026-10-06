"""add no event selection

Revision ID: dc7e0939d1d6
Revises: 80e1ec4bd229
Create Date: 2026-10-06 17:56:38.964870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc7e0939d1d6'
down_revision: Union[str, Sequence[str], None] = '80e1ec4bd229'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE event_selection ADD VALUE 'no_event'")


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "Downgrade is not supported: removing 'no_event' requires an explicit enum and data migration."
    )
