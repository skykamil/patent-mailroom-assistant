from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.correspondence import Correspondence
    from app.db.models.task import Task


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_reference: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    application_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    publication_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grant_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    correspondences: Mapped[list["Correspondence"]] = relationship(back_populates="case")
    tasks: Mapped[list["Task"]] = relationship(back_populates="case")
