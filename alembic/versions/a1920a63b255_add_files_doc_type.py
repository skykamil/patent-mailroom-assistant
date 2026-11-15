"""add files doc_type

Revision ID: a1920a63b255
Revises: d3ee694937d8
Create Date: 2026-11-15 14:58:08.961254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1920a63b255'
down_revision: Union[str, Sequence[str], None] = 'd3ee694937d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

doc_type_enum = postgresql.ENUM(
    "office_action",
    "agent_letter",
    "search_report",
    "claims",
    "specification",
    "submission",
    "invoice",
    "official_letter",
    "reference",
    "other",
    "eml_communication_agent",
    "eml_review_communication_agent",
    "eml_review_office_action",
    "eml_reminder",
    name="doc_type",
    create_type=False,
)

def upgrade() -> None:
    """Upgrade schema."""
    doc_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "files",
        sa.Column("doc_type", doc_type_enum, server_default="other", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("files", "doc_type")
    doc_type_enum.drop(op.get_bind(), checkfirst=True)
