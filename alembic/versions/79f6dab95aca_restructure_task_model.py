
"""restructure task model

Revision ID: 79f6dab95aca
Revises: 58f786ebcde7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "79f6dab95aca"
down_revision: Union[str, Sequence[str], None] = "58f786ebcde7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_TASK_TYPES = (
    "office_action",
    "review_office_action",
    "review_agent_communication",
)

NEW_TASK_TYPES = (
    "office_action",
    "office_action_1mo",
    "office_action_2mo",
    "office_action_3mo",
    "office_action_4mo",
    "office_action_5mo",
    "office_action_6mo",
)


def upgrade() -> None:
    connection = op.get_bind()

    if connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM tasks)")
    ):
        raise RuntimeError(
            "Cannot restructure tasks: table contains data."
        )

    op.create_unique_constraint(
        "uq_correspondences_id_case_id",
        "correspondences",
        ["id", "case_id"],
    )

    op.add_column(
        "tasks", sa.Column("case_id", sa.Integer(), nullable=False)
    )
    op.add_column(
        "tasks", sa.Column("start_date", sa.Date(), nullable=False)
    )
    op.add_column(
        "tasks",
        sa.Column("dates_manually_adjusted", sa.Boolean(), nullable=False),
    )
    op.add_column(
        "tasks",
        sa.Column("proposal_id", sa.String(length=50), nullable=True),
    )

    op.drop_index(
        "uq_tasks_primary_correspondence_task_type",
        table_name="tasks",
    )

    op.drop_constraint(
        "fk_tasks_correspondence_id_correspondences",
        "tasks",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_tasks_correspondence_case",
        "tasks",
        "correspondences",
        ["correspondence_id", "case_id"],
        ["id", "case_id"],
    )

    op.create_foreign_key(
        "fk_tasks_case_id_cases",
        "tasks",
        "cases",
        ["case_id"],
        ["id"],
    )

    op.drop_column("tasks", "name")
    op.drop_column("tasks", "is_primary")

    # Replace the old PostgreSQL ENUM with the new OA-only catalog.
    op.execute("ALTER TYPE task_type RENAME TO task_type_previous")

    postgresql.ENUM(
        *NEW_TASK_TYPES, name="task_type"
    ).create(connection, checkfirst=False)

    op.execute(
        "ALTER TABLE tasks "
        "ALTER COLUMN task_type TYPE task_type "
        "USING task_type::text::task_type"
    )

    postgresql.ENUM(
        name="task_type_previous"
    ).drop(connection, checkfirst=False)


def downgrade() -> None:
    connection = op.get_bind()

    if connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM tasks)")
    ):
        raise RuntimeError(
            "Cannot safely downgrade: tasks contains data."
        )

    # Restore the original PostgreSQL ENUM.
    op.execute("ALTER TYPE task_type RENAME TO task_type_current")

    postgresql.ENUM(
        *OLD_TASK_TYPES, name="task_type"
    ).create(connection, checkfirst=False)

    op.execute(
        "ALTER TABLE tasks "
        "ALTER COLUMN task_type TYPE task_type "
        "USING task_type::text::task_type"
    )

    postgresql.ENUM(
        name="task_type_current"
    ).drop(connection, checkfirst=False)

    op.add_column(
        "tasks", sa.Column("is_primary", sa.Boolean(), nullable=False)
    )
    op.add_column(
        "tasks", sa.Column("name", sa.String(100), nullable=False)
    )

    op.drop_constraint(
        "fk_tasks_case_id_cases",
        "tasks",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_tasks_correspondence_case",
        "tasks",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_tasks_correspondence_id_correspondences",
        "tasks",
        "correspondences",
        ["correspondence_id"],
        ["id"],
    )

    op.create_index(
        "uq_tasks_primary_correspondence_task_type",
        "tasks",
        ["correspondence_id", "task_type"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )

    op.drop_column("tasks", "proposal_id")
    op.drop_column("tasks", "dates_manually_adjusted")
    op.drop_column("tasks", "start_date")
    op.drop_column("tasks", "case_id")

    op.drop_constraint(
        "uq_correspondences_id_case_id",
        "correspondences",
        type_="unique",
    )
