from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, func, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.correspondence import Correspondence


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correspondence_id: Mapped[int] = mapped_column(ForeignKey("correspondences.id"), nullable=False, unique=True)
    correspondence: Mapped["Correspondence"] = relationship(back_populates="analysis")
    proposed_tasks: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    review_decisions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
