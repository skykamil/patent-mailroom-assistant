from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.correspondence import ImportType

if TYPE_CHECKING:
    from app.db.models.document import Document


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
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_sender: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    documents: Mapped[list["Document"]] = relationship(back_populates="correspondence")
