from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.analysis import Analysis
    from app.db.models.file import File
    from app.db.models.task import Task


class Correspondence(Base):
    __tablename__ = "correspondences"
    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            name="uq_correspondences_submission_id"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    submission_id: Mapped[str] = mapped_column(String(36), nullable=False)
    files: Mapped[list["File"]] = relationship(back_populates="correspondence")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="correspondence")
    tasks: Mapped[list["Task"]] = relationship(back_populates="correspondence")
