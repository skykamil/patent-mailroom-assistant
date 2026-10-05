from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, func, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.analysis import AnalysisStatus, EventSelection, EventType, OfficeActionType

if TYPE_CHECKING:
    from app.db.models.correspondence import Correspondence
    from app.db.models.event import Event


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correspondence_id: Mapped[int] = mapped_column(
        ForeignKey("correspondences.id"),
        nullable=False,
        unique=True,
    )
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    correspondence: Mapped["Correspondence"] = relationship(back_populates="analysis")
    event: Mapped["Event | None"] = relationship(back_populates="analyses")
    internal_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(2), nullable=True)
    application_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_type: Mapped[EventType | None] = mapped_column(
        Enum(
            EventType,
            name="event_type",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=True
    )
    office_action_type: Mapped[OfficeActionType | None] = mapped_column(
        Enum(
            OfficeActionType,
            name="office_action_type",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=True
    )
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    agent_notification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    agent_reported_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    calculated_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    event_selection: Mapped[EventSelection] = mapped_column(
        Enum(
            EventSelection,
            name="event_selection",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        default=EventSelection.UNRESOLVED,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(
            AnalysisStatus,
            name="analysis_status",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False,
        default=AnalysisStatus.PENDING_REVIEW,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
