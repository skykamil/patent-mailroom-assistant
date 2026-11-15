from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.doc_type import DocType

if TYPE_CHECKING:
    from app.db.models.case import Case



class File(Base):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[str] = mapped_column(String(36), nullable=False)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", name="fk_files_case_id_cases"), nullable=False)
    doc_type: Mapped[DocType] = mapped_column(
        Enum(
            DocType,
            name="doc_type",
            values_callable=lambda enum_class: [item.value for item in enum_class]
        ),
        nullable=False,
        server_default=DocType.OTHER.value
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    client_file_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    case: Mapped["Case"] = relationship(back_populates="files")
