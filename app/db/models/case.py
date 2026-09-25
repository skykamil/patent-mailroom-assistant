from datetime import date
from sqlalchemy import Integer, String, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint(
            "jurisdiction",
            "application_number",
            name="uq_cases_jurisdiction_application_number"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_reference: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    application_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    publication_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    grant_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grant_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    agent_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)