from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mpxccp.models.base import (
    Base,
    EvaluationDetailMixin,
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
)


class NetworkSubsystem(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "network_subsystems"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_network_subsystem_name"),
        UniqueConstraint("id", "project_id", name="uq_network_subsystems_id_project"),
        ForeignKeyConstraint(
            ["basic_subsystem_id", "project_id"],
            ["subsystems.id", "subsystems.project_id"],
            name="fk_network_subsystems_basic_subsystem_project",
        ),
    )

    basic_subsystem_id: Mapped[int | None] = mapped_column(
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class NetworkChannel(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "network_channels"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_network_channels_id_project"),
        ForeignKeyConstraint(
            ["network_subsystem_id", "project_id"],
            ["network_subsystems.id", "network_subsystems.project_id"],
            name="fk_network_channels_subsystem_project",
        ),
    )

    network_subsystem_id: Mapped[int] = mapped_column(
        ForeignKey("network_subsystems.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    target: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    protocol: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class NetworkAuthDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "network_auth_details"
    __table_args__ = (
        UniqueConstraint("network_channel_id", name="uq_network_auth_detail_channel"),
        ForeignKeyConstraint(
            ["network_channel_id", "project_id"],
            ["network_channels.id", "network_channels.project_id"],
            name="fk_network_auth_details_channel_project",
        ),
        Index("ix_network_auth_details_project", "project_id"),
    )

    network_channel_id: Mapped[int] = mapped_column(
        ForeignKey("network_channels.id"),
        index=True,
        nullable=False,
    )
    auth_methods: Mapped[str] = mapped_column(Text, default="", nullable=False)
    certificate_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)


class NetworkIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "network_integrity_details"
    __table_args__ = (
        UniqueConstraint("network_channel_id", name="uq_network_integrity_detail_channel"),
        ForeignKeyConstraint(
            ["network_channel_id", "project_id"],
            ["network_channels.id", "network_channels.project_id"],
            name="fk_network_integrity_details_channel_project",
        ),
        Index("ix_network_integrity_details_project", "project_id"),
    )

    network_channel_id: Mapped[int] = mapped_column(
        ForeignKey("network_channels.id"),
        index=True,
        nullable=False,
    )
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    certificate_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)


class NetworkConfidentialityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "network_confidentiality_details"
    __table_args__ = (
        UniqueConstraint("network_channel_id", name="uq_network_confidentiality_detail_channel"),
        ForeignKeyConstraint(
            ["network_channel_id", "project_id"],
            ["network_channels.id", "network_channels.project_id"],
            name="fk_network_confidentiality_details_channel_project",
        ),
        Index("ix_network_confidentiality_details_project", "project_id"),
    )

    network_channel_id: Mapped[int] = mapped_column(
        ForeignKey("network_channels.id"),
        index=True,
        nullable=False,
    )
    encryption_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    certificate_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)


class NetworkBoundaryIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "network_boundary_integrity_details"
    __table_args__ = (
        UniqueConstraint("network_channel_id", name="uq_network_boundary_integrity_channel"),
        ForeignKeyConstraint(
            ["network_channel_id", "project_id"],
            ["network_channels.id", "network_channels.project_id"],
            name="fk_network_boundary_integrity_details_channel_project",
        ),
        Index("ix_network_boundary_integrity_details_project", "project_id"),
    )

    network_channel_id: Mapped[int] = mapped_column(
        ForeignKey("network_channels.id"),
        index=True,
        nullable=False,
    )
    boundary_device: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    boundary_product_level: Mapped[str | None] = mapped_column(
        String(64),
        default="",
        nullable=True,
    )
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
