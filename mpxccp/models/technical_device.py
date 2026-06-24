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


class DeviceObject(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "device_objects"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_device_objects_id_project"),
    )

    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    device_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    management_address: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    interview_record: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceAuthDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "device_auth_details"
    __table_args__ = (
        UniqueConstraint("device_object_id", name="uq_device_auth_detail_object"),
        ForeignKeyConstraint(
            ["device_object_id", "project_id"],
            ["device_objects.id", "device_objects.project_id"],
            name="fk_device_auth_details_object_project",
        ),
        Index("ix_device_auth_details_project", "project_id"),
    )

    device_object_id: Mapped[int] = mapped_column(
        ForeignKey("device_objects.id"),
        index=True,
        nullable=False,
    )
    auth_methods: Mapped[str] = mapped_column(Text, default="", nullable=False)
    login_channel: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceRemoteManagementDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "device_remote_management_details"
    __table_args__ = (
        UniqueConstraint("device_object_id", name="uq_device_remote_management_object"),
        ForeignKeyConstraint(
            ["device_object_id", "project_id"],
            ["device_objects.id", "device_objects.project_id"],
            name="fk_device_remote_management_details_object_project",
        ),
        Index("ix_device_remote_management_details_project", "project_id"),
    )

    device_object_id: Mapped[int] = mapped_column(
        ForeignKey("device_objects.id"),
        index=True,
        nullable=False,
    )
    remote_protocol: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    certificate_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)
    channel_protection: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceAccessIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "device_access_integrity_details"
    __table_args__ = (
        UniqueConstraint("device_object_id", name="uq_device_access_integrity_object"),
        ForeignKeyConstraint(
            ["device_object_id", "project_id"],
            ["device_objects.id", "device_objects.project_id"],
            name="fk_device_access_integrity_details_object_project",
        ),
        Index("ix_device_access_integrity_details_project", "project_id"),
    )

    device_object_id: Mapped[int] = mapped_column(
        ForeignKey("device_objects.id"),
        index=True,
        nullable=False,
    )
    access_control_policy: Mapped[str] = mapped_column(Text, default="", nullable=False)
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceLogIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "device_log_integrity_details"
    __table_args__ = (
        UniqueConstraint("device_object_id", name="uq_device_log_integrity_object"),
        ForeignKeyConstraint(
            ["device_object_id", "project_id"],
            ["device_objects.id", "device_objects.project_id"],
            name="fk_device_log_integrity_details_object_project",
        ),
        Index("ix_device_log_integrity_details_project", "project_id"),
    )

    device_object_id: Mapped[int] = mapped_column(
        ForeignKey("device_objects.id"),
        index=True,
        nullable=False,
    )
    log_source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceExecutableIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "device_executable_integrity_details"
    __table_args__ = (
        UniqueConstraint("device_object_id", name="uq_device_executable_integrity_object"),
        ForeignKeyConstraint(
            ["device_object_id", "project_id"],
            ["device_objects.id", "device_objects.project_id"],
            name="fk_device_executable_integrity_details_object_project",
        ),
        Index("ix_device_executable_integrity_details_project", "project_id"),
    )

    device_object_id: Mapped[int] = mapped_column(
        ForeignKey("device_objects.id"),
        index=True,
        nullable=False,
    )
    executable_scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
