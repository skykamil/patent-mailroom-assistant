"""add review agent communication task type

Revision ID: 8861b891f322
Revises: fae90352c4f2
Create Date: 2026-10-07 17:05:34.977152

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8861b891f322'
down_revision: Union[str, Sequence[str], None] = 'fae90352c4f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE task_type ADD VALUE 'review_agent_communication'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
