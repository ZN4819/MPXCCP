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


class ApplicationSubsystem(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "application_subsystems"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_application_subsystem_name"),
        UniqueConstraint("id", "project_id", name="uq_application_subsystems_id_project"),
        ForeignKeyConstraint(
            ["basic_subsystem_id", "project_id"],
            ["subsystems.id", "subsystems.project_id"],
            name="fk_application_subsystems_basic_subsystem_project",
        ),
    )

    basic_subsystem_id: Mapped[int | None] = mapped_column(
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ApplicationUser(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "application_users"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_application_users_id_project"),
        ForeignKeyConstraint(
            ["application_subsystem_id", "project_id"],
            ["application_subsystems.id", "application_subsystems.project_id"],
            name="fk_application_users_subsystem_project",
        ),
    )

    application_subsystem_id: Mapped[int] = mapped_column(
        ForeignKey("application_subsystems.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ApplicationUserAuthDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "application_user_auth_details"
    __table_args__ = (
        UniqueConstraint("application_user_id", name="uq_application_user_auth_detail_user"),
        ForeignKeyConstraint(
            ["application_user_id", "project_id"],
            ["application_users.id", "application_users.project_id"],
            name="fk_application_user_auth_details_user_project",
        ),
        Index("ix_application_user_auth_details_project", "project_id"),
    )

    application_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id"),
        index=True,
        nullable=False,
    )
    auth_methods: Mapped[str] = mapped_column(Text, default="", nullable=False)
    certificate_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AccessControlObject(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "access_control_objects"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_access_control_objects_id_project"),
        ForeignKeyConstraint(
            ["application_subsystem_id", "project_id"],
            ["application_subsystems.id", "application_subsystems.project_id"],
            name="fk_access_control_objects_subsystem_project",
        ),
    )

    application_subsystem_id: Mapped[int] = mapped_column(
        ForeignKey("application_subsystems.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    policy_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AccessControlIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "access_control_integrity_details"
    __table_args__ = (
        UniqueConstraint("access_control_object_id", name="uq_access_control_integrity_object"),
        ForeignKeyConstraint(
            ["access_control_object_id", "project_id"],
            ["access_control_objects.id", "access_control_objects.project_id"],
            name="fk_access_control_integrity_details_object_project",
        ),
        Index("ix_access_control_integrity_details_project", "project_id"),
    )

    access_control_object_id: Mapped[int] = mapped_column(
        ForeignKey("access_control_objects.id"),
        index=True,
        nullable=False,
    )
    access_control_policy: Mapped[str] = mapped_column(Text, default="", nullable=False)
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ImportantData(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "important_data"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_important_data_id_project"),
        ForeignKeyConstraint(
            ["application_subsystem_id", "project_id"],
            ["application_subsystems.id", "application_subsystems.project_id"],
            name="fk_important_data_subsystem_project",
        ),
        ForeignKeyConstraint(
            ["related_channel_id", "project_id"],
            ["network_channels.id", "network_channels.project_id"],
            name="fk_important_data_related_channel_project",
        ),
    )

    application_subsystem_id: Mapped[int] = mapped_column(
        ForeignKey("application_subsystems.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    data_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    related_channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_channels.id"),
        index=True,
        nullable=True,
    )
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DataTransportConfidentialityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "data_transport_confidentiality_details"
    __table_args__ = (
        UniqueConstraint(
            "important_data_id",
            name="uq_data_transport_confidentiality_important_data",
        ),
        ForeignKeyConstraint(
            ["important_data_id", "project_id"],
            ["important_data.id", "important_data.project_id"],
            name="fk_data_transport_confidentiality_details_data_project",
        ),
        ForeignKeyConstraint(
            ["network_channel_id", "project_id"],
            ["network_channels.id", "network_channels.project_id"],
            name="fk_data_transport_confidentiality_details_channel_project",
        ),
        Index("ix_data_transport_confidentiality_details_project", "project_id"),
    )

    important_data_id: Mapped[int] = mapped_column(
        ForeignKey("important_data.id"),
        index=True,
        nullable=False,
    )
    network_channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_channels.id"),
        index=True,
        nullable=True,
    )
    encryption_method: Mapped[str] = mapped_column(Text, default="", nullable=False)


class DataStorageConfidentialityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "data_storage_confidentiality_details"
    __table_args__ = (
        UniqueConstraint("important_data_id", name="uq_data_storage_confidentiality_data"),
        ForeignKeyConstraint(
            ["important_data_id", "project_id"],
            ["important_data.id", "important_data.project_id"],
            name="fk_data_storage_confidentiality_details_data_project",
        ),
        Index("ix_data_storage_confidentiality_details_project", "project_id"),
    )

    important_data_id: Mapped[int] = mapped_column(
        ForeignKey("important_data.id"),
        index=True,
        nullable=False,
    )
    storage_location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    encryption_method: Mapped[str] = mapped_column(Text, default="", nullable=False)


class DataTransportIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "data_transport_integrity_details"
    __table_args__ = (
        UniqueConstraint("important_data_id", name="uq_data_transport_integrity_data"),
        ForeignKeyConstraint(
            ["important_data_id", "project_id"],
            ["important_data.id", "important_data.project_id"],
            name="fk_data_transport_integrity_details_data_project",
        ),
        ForeignKeyConstraint(
            ["network_channel_id", "project_id"],
            ["network_channels.id", "network_channels.project_id"],
            name="fk_data_transport_integrity_details_channel_project",
        ),
        Index("ix_data_transport_integrity_details_project", "project_id"),
    )

    important_data_id: Mapped[int] = mapped_column(
        ForeignKey("important_data.id"),
        index=True,
        nullable=False,
    )
    network_channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_channels.id"),
        index=True,
        nullable=True,
    )
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)


class DataStorageIntegrityDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "data_storage_integrity_details"
    __table_args__ = (
        UniqueConstraint("important_data_id", name="uq_data_storage_integrity_data"),
        ForeignKeyConstraint(
            ["important_data_id", "project_id"],
            ["important_data.id", "important_data.project_id"],
            name="fk_data_storage_integrity_details_data_project",
        ),
        Index("ix_data_storage_integrity_details_project", "project_id"),
    )

    important_data_id: Mapped[int] = mapped_column(
        ForeignKey("important_data.id"),
        index=True,
        nullable=False,
    )
    storage_location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    integrity_method: Mapped[str] = mapped_column(Text, default="", nullable=False)


class BusinessAction(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "business_actions"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_business_actions_id_project"),
        ForeignKeyConstraint(
            ["application_subsystem_id", "project_id"],
            ["application_subsystems.id", "application_subsystems.project_id"],
            name="fk_business_actions_subsystem_project",
        ),
    )

    application_subsystem_id: Mapped[int] = mapped_column(
        ForeignKey("application_subsystems.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class BusinessActionNonRepudiationDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    EvaluationDetailMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "business_action_non_repudiation_details"
    __table_args__ = (
        UniqueConstraint("business_action_id", name="uq_business_action_non_repudiation"),
        ForeignKeyConstraint(
            ["business_action_id", "project_id"],
            ["business_actions.id", "business_actions.project_id"],
            name="fk_business_action_non_repudiation_details_action_project",
        ),
        Index("ix_business_action_non_repudiation_details_project", "project_id"),
    )

    business_action_id: Mapped[int] = mapped_column(
        ForeignKey("business_actions.id"),
        index=True,
        nullable=False,
    )
    signature_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timestamp_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    certificate_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)
