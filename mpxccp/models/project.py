from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from mpxccp.models.base import Base, IntegerPrimaryKeyMixin, SortOrderMixin, TimestampMixin


class Project(IntegerPrimaryKeyMixin, SortOrderMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    flow_no: Mapped[str] = mapped_column(String(128), default="", nullable=False, index=True)
    system_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    assessment_org: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeletedProject(IntegerPrimaryKeyMixin, SortOrderMixin, TimestampMixin, Base):
    __tablename__ = "deleted_projects"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True, nullable=False)
    flow_no: Mapped[str] = mapped_column(String(128), default="", nullable=False, index=True)
    system_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    deleted_by: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    project_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
