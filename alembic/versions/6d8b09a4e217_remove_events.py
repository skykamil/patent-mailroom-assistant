"""Remove events; link tasks directly to correspondence.

Revision ID: 6d8b09a4e217
Revises: 8861b891f322
"""
from alembic import op
import sqlalchemy as sa

revision = "6d8b09a4e217"
down_revision = "8861b891f322"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve Office Action classification used to create tasks after approval.
    op.execute("UPDATE analyses SET office_action_type = 'Office Action' WHERE event_type = 'office_action' AND office_action_type IS NULL")
    op.drop_index("uq_tasks_primary_event_task_type", table_name="tasks")
    op.drop_constraint("tasks_event_id_fkey", "tasks", type_="foreignkey")
    op.drop_constraint("fk_analyses_event_id_events", "analyses", type_="foreignkey")
    op.drop_column("tasks", "event_id")
    op.drop_column("analyses", "event_id")
    op.drop_column("analyses", "event_selection")
    op.drop_column("analyses", "event_type")
    op.drop_table("events")
    sa.Enum(name="event_selection").drop(op.get_bind())
    sa.Enum(name="event_type").drop(op.get_bind())
    op.create_index(
        "uq_tasks_primary_correspondence_task_type", "tasks",
        ["correspondence_id", "task_type"], unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )


def downgrade() -> None:
    raise NotImplementedError("Removed event records and links cannot be restored; restore a database backup.")
