from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.task import TaskType

if TYPE_CHECKING:
    from app.db.models.correspondence import Correspondence


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index(
            "uq_tasks_primary_correspondence_task_type",
            "correspondence_id",
            "task_type",
            unique=True,
            postgresql_where=text("is_primary = true"),
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_type: Mapped[TaskType] = mapped_column(
        Enum(
            TaskType,
            name="task_type",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    correspondence_id: Mapped[int] = mapped_column(ForeignKey("correspondences.id"), nullable=False)
    correspondence: Mapped["Correspondence"] = relationship(back_populates="tasks")
