from enum import StrEnum

from sqlalchemy import Integer, ForeignKey, Enum, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class CaseRelationshipType(StrEnum):
    DIRECT_PARENT = "direct_parent"
    PRIORITY = "priority"

class CaseRelationship(Base):
    __tablename__ = "case_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_case_id",
            "target_case_id",
            "relationship_type",
            name="uq_case_relationship"
        ),
        CheckConstraint(
            "source_case_id <> target_case_id",
            name="ck_case_relationship_not_self"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    target_case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    relationship_type: Mapped[CaseRelationshipType] = mapped_column(
        Enum(
            CaseRelationshipType,
            name="case_relationship_type",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False
    )
