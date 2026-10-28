from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_reference: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    application_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    publication_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grant_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
