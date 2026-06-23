from __future__ import annotations

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mpxccp.models.base import Base, IntegerPrimaryKeyMixin, SortOrderMixin, TimestampMixin


class KnowledgeEntry(IntegerPrimaryKeyMixin, SortOrderMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_entries"
    __table_args__ = (
        Index("ix_knowledge_entries_type_module", "entry_type", "module"),
    )

    entry_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    module: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)


class KnowledgeTaxonomy(IntegerPrimaryKeyMixin, SortOrderMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_taxonomies"
    __table_args__ = (
        UniqueConstraint("category", "value", name="uq_knowledge_taxonomies_category_value"),
    )

    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(128), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
