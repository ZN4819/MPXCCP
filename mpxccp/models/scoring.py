from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from mpxccp.models.base import (
    Base,
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
)


class ScoringIndicator(IntegerPrimaryKeyMixin, SortOrderMixin, TimestampMixin, Base):
    __tablename__ = "scoring_indicators"
    __table_args__ = (UniqueConstraint("indicator_no", name="uq_scoring_indicators_no"),)

    indicator_no: Mapped[int] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    layer: Mapped[str] = mapped_column(String(128), default="", nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    always_not_applicable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unit_types: Mapped[list | None] = mapped_column(JSON, nullable=True)


class ManagementScore(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "management_scores"
    __table_args__ = (
        UniqueConstraint("project_id", "indicator_no", name="uq_management_scores_indicator"),
    )

    indicator_no: Mapped[int] = mapped_column(index=True, nullable=False)
    layer: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_status: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ScoreSummary(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "score_summaries"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_score_summaries_project"),
        UniqueConstraint("id", "project_id", name="uq_score_summaries_id_project"),
    )

    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    management_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_allocated_score: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        server_default=text("100.0"),
        nullable=False,
    )
    total_earned_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default=text("0.0"),
        nullable=False,
    )
    total_lost_score: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        server_default=text("100.0"),
        nullable=False,
    )
    compliant_count: Mapped[int] = mapped_column(default=0, nullable=False)
    partial_count: Mapped[int] = mapped_column(default=0, nullable=False)
    non_compliant_count: Mapped[int] = mapped_column(default=0, nullable=False)
    not_applicable_count: Mapped[int] = mapped_column(default=0, nullable=False)
    layer_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dirty: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class ScoreDetail(
    IntegerPrimaryKeyMixin,
    ProjectScopedMixin,
    SortOrderMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "score_details"
    __table_args__ = (
        ForeignKeyConstraint(
            ["summary_id", "project_id"],
            ["score_summaries.id", "score_summaries.project_id"],
            name="fk_score_details_summary_project",
        ),
        Index("ix_score_details_related", "project_id", "unit_type", "related_id"),
    )

    summary_id: Mapped[int] = mapped_column(
        ForeignKey("score_summaries.id"),
        index=True,
        nullable=False,
    )
    indicator_no: Mapped[int] = mapped_column(index=True, nullable=False)
    indicator_name: Mapped[str] = mapped_column(
        String(255),
        default="",
        server_default="",
        nullable=False,
    )
    layer: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    unit_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    related_id: Mapped[int | None] = mapped_column(index=True, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    indicator_weight: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        server_default=text("1.0"),
        nullable=False,
    )
    effective_object_count: Mapped[int] = mapped_column(
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    allocated_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    earned_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    lost_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_status: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(64), default="", nullable=True)
    not_applicable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
