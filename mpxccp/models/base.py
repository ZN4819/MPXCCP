from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    pass


class IntegerPrimaryKeyMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SortOrderMixin:
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ProjectScopedMixin:
    @declared_attr
    def project_id(cls) -> Mapped[int]:
        return mapped_column(ForeignKey("projects.id"), index=True, nullable=False)


class EvaluationDetailMixin:
    requirement: Mapped[str] = mapped_column(Text, default="", nullable=False)
    implementation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evaluation_result: Mapped[str] = mapped_column(Text, default="", nullable=False)
    crypto_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)
    algorithm: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    product_compliance: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    compliance_status: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    risk_analysis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    remediation: Mapped[str] = mapped_column(Text, default="", nullable=False)
