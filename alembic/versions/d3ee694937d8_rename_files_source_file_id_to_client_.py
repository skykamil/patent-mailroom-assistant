"""rename files source_file_id to client_file_id

Revision ID: d3ee694937d8
Revises: 0151a742c218
Create Date: 2026-11-15 13:21:48.962482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3ee694937d8'
down_revision: Union[str, Sequence[str], None] = '0151a742c218'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("files", "source_file_id", new_column_name="client_file_id")
    op.execute(
        "ALTER TABLE files RENAME CONSTRAINT files_source_file_id_key TO files_client_file_id_key"
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE files RENAME CONSTRAINT files_client_file_id_key TO files_source_file_id_key"
    )
    op.alter_column("files", "client_file_id", new_column_name="source_file_id")
