from __future__ import annotations

from sqlalchemy import JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mpxccp.models.base import (
    Base,
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
)


class BasicInfo(IntegerPrimaryKeyMixin, ProjectScopedMixin, SortOrderMixin, TimestampMixin, Base):
    __tablename__ = "basic_infos"
    __table_args__ = (UniqueConstraint("project_id", name="uq_basic_infos_project"),)

    flow_no: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    system_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    assessment_org: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    contact_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    assessment_date: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class SystemInfo(IntegerPrimaryKeyMixin, ProjectScopedMixin, SortOrderMixin, TimestampMixin, Base):
    __tablename__ = "system_infos"
    __table_args__ = (UniqueConstraint("project_id", name="uq_system_infos_project"),)

    system_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    security_level: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    deployment_mode: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    network_environment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    business_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CryptoApplicationInfo(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "crypto_application_infos"
    __table_args__ = (UniqueConstraint("project_id", name="uq_crypto_application_infos_project"),)

    application_scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    algorithm_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    key_management_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    product_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Subsystem(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "subsystems"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_subsystems_project_name"),
        UniqueConstraint("id", "project_id", name="uq_subsystems_id_project"),
    )

    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
