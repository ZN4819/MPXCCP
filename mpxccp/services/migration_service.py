from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import Engine, inspect, or_, select, text, update
from sqlalchemy.orm import Session

from mpxccp.config.settings import DEFAULT_APP_SETTINGS
from mpxccp.domain.enums import KnowledgeModule, KnowledgeType
from mpxccp.domain.scoring_rules import build_default_indicators, map_indicator_to_units
from mpxccp.models.knowledge import KnowledgeEntry, KnowledgeTaxonomy
from mpxccp.models.scoring import ManagementScore, ScoreDetail, ScoringIndicator
from mpxccp.models.shared import AppSetting, CryptoProduct, DataVersion, QuantitativeAssessment
from mpxccp.models.technical_application import (
    AccessControlIntegrityDetail,
    ApplicationUserAuthDetail,
    BusinessActionNonRepudiationDetail,
    DataStorageConfidentialityDetail,
    DataStorageIntegrityDetail,
    DataTransportConfidentialityDetail,
    DataTransportIntegrityDetail,
)
from mpxccp.models.technical_device import (
    DeviceAccessIntegrityDetail,
    DeviceAuthDetail,
    DeviceExecutableIntegrityDetail,
    DeviceLogIntegrityDetail,
    DeviceRemoteManagementDetail,
)
from mpxccp.models.technical_network import (
    NetworkAuthDetail,
    NetworkBoundaryIntegrityDetail,
    NetworkConfidentialityDetail,
    NetworkIntegrityDetail,
)
from mpxccp.models.technical_physical import (
    PhysicalAccessIntegrityDetail,
    PhysicalAuthDetail,
    PhysicalVideoIntegrityDetail,
)

LOGGER = logging.getLogger(__name__)
MigrationFn = Callable[[Session], None]
LEGACY_EMPTY_ENUM_VALUES = ("None", "none", "NULL", "null", "未选择", "请选择")
DETAIL_ENUM_COLUMNS = ("product_compliance", "compliance_status", "risk_level")
ENUM_CLEANUP_COLUMNS: tuple[tuple[type, tuple[str, ...]], ...] = (
    (
        QuantitativeAssessment,
        (
            "d_value",
            "a_value",
            "k_value",
            "ra_value",
            "rk_value",
            "compliance_status",
            "risk_level",
        ),
    ),
    (CryptoProduct, ("product_level",)),
    (ManagementScore, ("compliance_status",)),
    (ScoreDetail, ("compliance_status", "risk_level")),
    (PhysicalAuthDetail, DETAIL_ENUM_COLUMNS),
    (PhysicalAccessIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (PhysicalVideoIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (DeviceAuthDetail, DETAIL_ENUM_COLUMNS),
    (DeviceRemoteManagementDetail, DETAIL_ENUM_COLUMNS),
    (DeviceAccessIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (DeviceLogIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (DeviceExecutableIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (NetworkAuthDetail, DETAIL_ENUM_COLUMNS),
    (NetworkIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (NetworkConfidentialityDetail, DETAIL_ENUM_COLUMNS),
    (
        NetworkBoundaryIntegrityDetail,
        DETAIL_ENUM_COLUMNS + ("boundary_product_level",),
    ),
    (ApplicationUserAuthDetail, DETAIL_ENUM_COLUMNS),
    (AccessControlIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (DataTransportConfidentialityDetail, DETAIL_ENUM_COLUMNS),
    (DataStorageConfidentialityDetail, DETAIL_ENUM_COLUMNS),
    (DataTransportIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (DataStorageIntegrityDetail, DETAIL_ENUM_COLUMNS),
    (BusinessActionNonRepudiationDetail, DETAIL_ENUM_COLUMNS),
)


class MigrationService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def run_all(self) -> None:
        migrations: tuple[tuple[str, str, str, MigrationFn], ...] = (
            (
                "app_settings_defaults",
                "1",
                "Ensure app settings required by local data paths exist.",
                self._ensure_app_settings,
            ),
            (
                "default_scoring_indicators",
                "1",
                "Ensure default scoring indicators exist.",
                self._ensure_default_scoring_indicators,
            ),
            (
                "knowledge_defaults",
                "1",
                "Ensure knowledge type and module defaults exist.",
                self._ensure_knowledge_defaults,
            ),
            (
                "enum_cleanup",
                "1",
                "Clean nullable enum-like values without changing business data.",
                self._run_enum_cleanup,
            ),
            (
                "physical_detail_extra_data",
                "1",
                "Ensure physical detail tables can store requirement-specific extension fields.",
                self._ensure_physical_detail_extra_data_columns,
            ),
            (
                "device_detail_extra_data",
                "1",
                "Ensure device detail tables can store requirement-specific extension fields.",
                self._ensure_device_detail_extra_data_columns,
            ),
            (
                "network_detail_extra_data",
                "1",
                "Ensure network detail tables can store requirement-specific extension fields.",
                self._ensure_network_detail_extra_data_columns,
            ),
            (
                "application_detail_extra_data",
                "1",
                "Ensure application detail tables can store requirement-specific extension fields.",
                self._ensure_application_detail_extra_data_columns,
            ),
            (
                "scoring_summary_detail_columns",
                "1",
                "Ensure scoring tables can store persisted scoring protocol fields.",
                self._ensure_scoring_summary_detail_columns,
            ),
        )
        for name, version, description, migration in migrations:
            self._run_one(name, version, description, migration)

    def _run_one(
        self,
        name: str,
        version: str,
        description: str,
        migration: MigrationFn,
    ) -> None:
        session = Session(self.engine, expire_on_commit=False)
        try:
            migration(session)
            self._record_migration(session, name, version, description)
            session.commit()
        except Exception:
            session.rollback()
            LOGGER.warning(
                "migration %s failed; continuing to keep database open",
                name,
                exc_info=True,
            )
        finally:
            session.close()

    def _record_migration(
        self,
        session: Session,
        name: str,
        version: str,
        description: str,
    ) -> None:
        record = session.execute(
            select(DataVersion).where(DataVersion.migration_name == name)
        ).scalar_one_or_none()
        if record is None:
            session.add(
                DataVersion(
                    migration_name=name,
                    version=version,
                    description=description,
                )
            )
            return
        record.version = version
        record.description = description

    def _ensure_app_settings(self, session: Session) -> None:
        for key, value in DEFAULT_APP_SETTINGS.items():
            setting = session.execute(
                select(AppSetting).where(AppSetting.key == key)
            ).scalar_one_or_none()
            if setting is None:
                session.add(AppSetting(key=key, value=value, description="default setting"))

    def _ensure_default_scoring_indicators(self, session: Session) -> None:
        for indicator in build_default_indicators():
            model = session.execute(
                select(ScoringIndicator).where(
                    ScoringIndicator.indicator_no == indicator.no
                )
            ).scalar_one_or_none()
            values = {
                "name": indicator.name,
                "layer": indicator.layer,
                "weight": indicator.weight,
                "always_not_applicable": indicator.always_not_applicable,
                "unit_types": list(map_indicator_to_units(indicator.no)),
                "sort_order": indicator.no,
            }
            if model is None:
                session.add(ScoringIndicator(indicator_no=indicator.no, **values))
            else:
                for field, value in values.items():
                    setattr(model, field, value)

    def _ensure_knowledge_defaults(self, session: Session) -> None:
        self._upsert_taxonomies(session, "type", [item.value for item in KnowledgeType])
        self._upsert_taxonomies(session, "module", [item.value for item in KnowledgeModule])
        first_type = next(iter(KnowledgeType)).value
        first_module = next(iter(KnowledgeModule)).value
        session.execute(
            update(KnowledgeEntry)
            .where(KnowledgeEntry.entry_type == "")
            .values(entry_type=first_type)
        )
        session.execute(
            update(KnowledgeEntry)
            .where(KnowledgeEntry.module == "")
            .values(module=first_module)
        )

    def _upsert_taxonomies(self, session: Session, category: str, values: list[str]) -> None:
        for sort_order, value in enumerate(values):
            taxonomy = session.execute(
                select(KnowledgeTaxonomy).where(
                    KnowledgeTaxonomy.category == category,
                    KnowledgeTaxonomy.value == value,
                )
            ).scalar_one_or_none()
            if taxonomy is None:
                session.add(
                    KnowledgeTaxonomy(
                        category=category,
                        value=value,
                        sort_order=sort_order,
                    )
                )
            else:
                taxonomy.sort_order = sort_order
                taxonomy.is_enabled = True

    def _run_enum_cleanup(self, session: Session) -> None:
        for model, column_names in ENUM_CLEANUP_COLUMNS:
            for column_name in column_names:
                column = getattr(model, column_name)
                session.execute(
                    update(model)
                    .where(
                        or_(
                            column.is_(None),
                            column.in_(LEGACY_EMPTY_ENUM_VALUES),
                        )
                    )
                    .values({column_name: ""})
                )

    def _ensure_physical_detail_extra_data_columns(self, session: Session) -> None:
        self._ensure_extra_data_columns(
            session,
            (
                "physical_auth_details",
                "physical_access_integrity_details",
                "physical_video_integrity_details",
            ),
        )

    def _ensure_device_detail_extra_data_columns(self, session: Session) -> None:
        self._ensure_extra_data_columns(
            session,
            (
                "device_auth_details",
                "device_remote_management_details",
                "device_access_integrity_details",
                "device_log_integrity_details",
                "device_executable_integrity_details",
            ),
        )

    def _ensure_network_detail_extra_data_columns(self, session: Session) -> None:
        self._ensure_extra_data_columns(
            session,
            (
                "network_auth_details",
                "network_integrity_details",
                "network_confidentiality_details",
                "network_boundary_integrity_details",
            ),
        )

    def _ensure_application_detail_extra_data_columns(self, session: Session) -> None:
        self._ensure_extra_data_columns(
            session,
            (
                "application_user_auth_details",
                "access_control_integrity_details",
                "data_transport_confidentiality_details",
                "data_storage_confidentiality_details",
                "data_transport_integrity_details",
                "data_storage_integrity_details",
                "business_action_non_repudiation_details",
            ),
        )

    def _ensure_scoring_summary_detail_columns(self, session: Session) -> None:
        self._ensure_columns(
            session,
            "score_summaries",
            {
                "total_allocated_score": "FLOAT DEFAULT 100.0 NOT NULL",
                "total_earned_score": "FLOAT DEFAULT 0.0 NOT NULL",
                "total_lost_score": "FLOAT DEFAULT 100.0 NOT NULL",
                "layer_scores": "JSON",
                "dirty": "BOOLEAN DEFAULT 0 NOT NULL",
            },
        )
        self._ensure_columns(
            session,
            "score_details",
            {
                "indicator_name": "VARCHAR(255) DEFAULT '' NOT NULL",
                "indicator_weight": "FLOAT DEFAULT 1.0 NOT NULL",
                "effective_object_count": "INTEGER DEFAULT 0 NOT NULL",
                "allocated_score": "FLOAT",
                "earned_score": "FLOAT",
                "lost_score": "FLOAT",
                "not_applicable": "BOOLEAN DEFAULT 0 NOT NULL",
            },
        )

    def _ensure_extra_data_columns(self, session: Session, table_names: tuple[str, ...]) -> None:
        for table_name in table_names:
            self._ensure_columns(session, table_name, {"extra_data": "JSON"})

    def _ensure_columns(
        self,
        session: Session,
        table_name: str,
        columns: dict[str, str],
    ) -> None:
        inspector = inspect(session.bind)
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, definition in columns.items():
            if column_name in existing_columns:
                continue
            session.execute(text(f"alter table {table_name} add column {column_name} {definition}"))
