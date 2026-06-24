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


class PhysicalObject(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "physical_objects"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_physical_objects_id_project"),
    )

    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    access_control_system: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    video_system: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    interview_record: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PhysicalAuthDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "physical_auth_details"
    __table_args__ = (
        UniqueConstraint("physical_object_id", name="uq_physical_auth_detail_object"),
        ForeignKeyConstraint(
            ["physical_object_id", "project_id"],
            ["physical_objects.id", "physical_objects.project_id"],
            name="fk_physical_auth_details_object_project",
        ),
        Index("ix_physical_auth_details_project", "project_id"),
    )

    physical_object_id: Mapped[int] = mapped_column(
        ForeignKey("physical_objects.id"),
        index=True,
        nullable=False,
    )
    auth_methods: Mapped[str] = mapped_column(Text, default="", nullable=False)
    access_control_device: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PhysicalAccessIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "physical_access_integrity_details"
    __table_args__ = (
        UniqueConstraint("physical_object_id", name="uq_physical_access_integrity_object"),
        ForeignKeyConstraint(
            ["physical_object_id", "project_id"],
            ["physical_objects.id", "physical_objects.project_id"],
            name="fk_physical_access_integrity_details_object_project",
        ),
        Index("ix_physical_access_integrity_details_project", "project_id"),
    )

    physical_object_id: Mapped[int] = mapped_column(
        ForeignKey("physical_objects.id"),
        index=True,
        nullable=False,
    )
    record_source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PhysicalVideoIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "physical_video_integrity_details"
    __table_args__ = (
        UniqueConstraint("physical_object_id", name="uq_physical_video_integrity_object"),
        ForeignKeyConstraint(
            ["physical_object_id", "project_id"],
            ["physical_objects.id", "physical_objects.project_id"],
            name="fk_physical_video_integrity_details_object_project",
        ),
        Index("ix_physical_video_integrity_details_project", "project_id"),
    )

    physical_object_id: Mapped[int] = mapped_column(
        ForeignKey("physical_objects.id"),
        index=True,
        nullable=False,
    )
    video_record_source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
