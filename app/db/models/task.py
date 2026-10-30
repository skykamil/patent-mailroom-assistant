from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Boolean, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.task import TaskType

if TYPE_CHECKING:
    from app.db.models.case import Case
    from app.db.models.correspondence import Correspondence


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    case: Mapped["Case"] = relationship(back_populates="tasks")
    correspondence_id: Mapped[int] = mapped_column(ForeignKey("correspondences.id"), nullable=False)
    correspondence: Mapped["Correspondence"] = relationship(back_populates="tasks")
    task_type: Mapped[TaskType] = mapped_column(
        Enum(
            TaskType,
            name="task_type",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    dates_manually_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    proposal_id: Mapped[str | None] = mapped_column(String, nullable=True)
