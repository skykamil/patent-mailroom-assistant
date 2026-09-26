from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document

class ImportType(StrEnum):
    EMAIL = "email"
    DIRECT_UPLOAD = "direct_upload"

class Correspondence(Base):
    __tablename__ = "correspondences"
    __table_args__ = (
        UniqueConstraint("source_sha256",
        name="uq_correspondences_source_sha256"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    import_type: Mapped[ImportType] = mapped_column(
        Enum(
            ImportType,
            name="correspondence_import_type",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    documents: Mapped[list["Document"]] = relationship(back_populates="correspondence")
