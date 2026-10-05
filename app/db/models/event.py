from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.analysis import EventType

if TYPE_CHECKING:
    from app.db.models.analysis import Analysis
    from app.db.models.case import Case
    from app.db.models.task import Task


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(
            EventType,
            name="event_type",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    case: Mapped["Case"] = relationship(back_populates="events")
    tasks: Mapped[list["Task"]] = relationship(back_populates="event")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="event")
