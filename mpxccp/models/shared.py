from __future__ import annotations

from sqlalchemy import Float, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mpxccp.models.base import (
    Base,
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
)


class QuantitativeAssessment(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "quantitative_assessments"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "unit_type",
            "related_id",
            name="uq_quantitative_assessments_related",
        ),
        Index("ix_quantitative_assessments_related", "project_id", "unit_type", "related_id"),
    )

    unit_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    related_id: Mapped[int] = mapped_column(index=True, nullable=False)
    d_value: Mapped[str | None] = mapped_column(String(16), default="", nullable=True)
    a_value: Mapped[str | None] = mapped_column(String(16), default="", nullable=True)
    k_value: Mapped[str | None] = mapped_column(String(16), default="", nullable=True)
    ra_value: Mapped[str | None] = mapped_column(String(16), default="", nullable=True)
    rk_value: Mapped[str | None] = mapped_column(String(16), default="", nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_status: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class CryptoProduct(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "crypto_products"
    __table_args__ = (
        Index("ix_crypto_products_related", "project_id", "unit_type", "related_id"),
    )

    unit_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    related_id: Mapped[int] = mapped_column(index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    product_model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    certificate_no: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    product_level: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    vendor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    usage: Mapped[str] = mapped_column(Text, default="", nullable=False)


class EvidenceImage(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "evidence_images"
    __table_args__ = (
        Index("ix_evidence_images_related", "project_id", "unit_type", "related_id"),
    )

    unit_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    related_id: Mapped[int] = mapped_column(index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    caption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), default="", nullable=False)


class AppSetting(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_app_settings_key"),)

    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    value_type: Mapped[str] = mapped_column(String(64), default="str", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class DataVersion(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_versions"
    __table_args__ = (UniqueConstraint("migration_name", name="uq_data_versions_migration_name"),)

    migration_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
