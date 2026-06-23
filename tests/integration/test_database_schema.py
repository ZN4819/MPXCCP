from __future__ import annotations

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import mpxccp.models as models
from mpxccp.repositories.session import (
    create_engine_for_path,
    init_database,
    readonly_session_scope,
    session_scope,
)
from mpxccp.services.migration_service import MigrationService

EXPECTED_DETAIL_TABLES = {
    "physical_auth_details",
    "physical_access_integrity_details",
    "physical_video_integrity_details",
    "device_auth_details",
    "device_remote_management_details",
    "device_access_integrity_details",
    "device_log_integrity_details",
    "device_executable_integrity_details",
    "network_auth_details",
    "network_integrity_details",
    "network_confidentiality_details",
    "network_boundary_integrity_details",
    "application_user_auth_details",
    "access_control_objects",
    "access_control_integrity_details",
    "important_data",
    "data_transport_confidentiality_details",
    "data_storage_confidentiality_details",
    "data_transport_integrity_details",
    "data_storage_integrity_details",
    "business_actions",
    "business_action_non_repudiation_details",
}

REMOVED_GENERIC_DETAIL_TABLES = {
    "physical_details",
    "device_details",
    "network_channel_details",
    "application_user_details",
    "application_access_control_details",
    "application_important_data_details",
    "application_business_action_details",
}

REMOVED_GENERIC_DETAIL_EXPORTS = {
    "PhysicalDetail",
    "DeviceDetail",
    "NetworkChannelDetail",
    "ApplicationUserDetail",
    "ApplicationAccessControlDetail",
    "ApplicationImportantDataDetail",
    "ApplicationBusinessActionDetail",
}


def _project(project_id: int) -> models.Project:
    return models.Project(
        id=project_id,
        flow_no=f"LC-{project_id:03d}",
        system_name=f"系统{project_id}",
        client_name="委托方",
        assessment_org="测评机构",
    )


def test_database_schema_creates_core_tables(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)

    init_database(engine)

    names = set(inspect(engine).get_table_names())
    assert {
        "projects",
        "deleted_projects",
        "quantitative_assessments",
        "crypto_products",
        "evidence_images",
        "scoring_indicators",
        "app_settings",
        "data_versions",
    }.issubset(names)


def test_readonly_session_scope_blocks_explicit_commit(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)
    init_database(engine)

    with pytest.raises(InvalidRequestError):
        with readonly_session_scope(engine) as session:
            session.add(_project(1))
            session.commit()

    with session_scope(engine) as session:
        count = session.scalar(select(func.count()).select_from(models.Project))

    assert count == 0


def test_readonly_session_scope_blocks_explicit_flush(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)
    init_database(engine)

    with pytest.raises(InvalidRequestError):
        with readonly_session_scope(engine) as session:
            session.add(_project(1))
            session.flush()

    with session_scope(engine) as session:
        count = session.scalar(select(func.count()).select_from(models.Project))

    assert count == 0


def test_database_schema_uses_one_table_per_measurement_unit(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)

    init_database(engine)

    names = set(inspect(engine).get_table_names())
    assert EXPECTED_DETAIL_TABLES.issubset(names)
    assert REMOVED_GENERIC_DETAIL_TABLES.isdisjoint(names)
    assert REMOVED_GENERIC_DETAIL_EXPORTS.isdisjoint(set(models.__all__))


def test_schema_common_fields_and_project_foreign_keys(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)

    init_database(engine)

    inspector = inspect(engine)
    sort_order_tables = {
        "deleted_projects",
        "basic_infos",
        "system_infos",
        "crypto_application_infos",
        "score_summaries",
    }
    for table_name in sort_order_tables:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "sort_order" in columns

    for table_name in sort_order_tables:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "project_id" in columns
        project_fks = [
            fk
            for fk in inspector.get_foreign_keys(table_name)
            if "project_id" in fk["constrained_columns"]
        ]
        assert project_fks
        assert project_fks[0]["referred_table"] == "projects"


def test_project_scoped_children_reject_cross_project_parent_links(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)
    init_database(engine)

    with session_scope(engine) as session:
        session.add_all([_project(1), _project(2)])
    with session_scope(engine) as session:
        session.add_all(
            [
                models.PhysicalObject(id=1, project_id=1, name="机房A"),
                models.DeviceObject(id=1, project_id=1, name="服务器A"),
                models.NetworkSubsystem(id=1, project_id=1, name="网络子系统A"),
                models.ApplicationSubsystem(id=1, project_id=1, name="应用子系统A"),
            ]
        )
    with session_scope(engine) as session:
        session.add_all(
            [
                models.NetworkChannel(
                    id=1,
                    project_id=1,
                    network_subsystem_id=1,
                    name="业务通信",
                ),
                models.ApplicationUser(
                    id=1,
                    project_id=1,
                    application_subsystem_id=1,
                    name="管理员",
                ),
                models.AccessControlObject(
                    id=1,
                    project_id=1,
                    application_subsystem_id=1,
                    name="权限矩阵",
                ),
                models.ImportantData(
                    id=1,
                    project_id=1,
                    application_subsystem_id=1,
                    name="交易记录",
                    data_type="业务数据",
                ),
                models.BusinessAction(
                    id=1,
                    project_id=1,
                    application_subsystem_id=1,
                    name="交易提交",
                ),
            ]
        )

    cross_project_children = [
        models.PhysicalAuthDetail(project_id=2, physical_object_id=1),
        models.PhysicalAccessIntegrityDetail(project_id=2, physical_object_id=1),
        models.PhysicalVideoIntegrityDetail(project_id=2, physical_object_id=1),
        models.DeviceAuthDetail(project_id=2, device_object_id=1),
        models.DeviceRemoteManagementDetail(project_id=2, device_object_id=1),
        models.DeviceAccessIntegrityDetail(project_id=2, device_object_id=1),
        models.DeviceLogIntegrityDetail(project_id=2, device_object_id=1),
        models.DeviceExecutableIntegrityDetail(project_id=2, device_object_id=1),
        models.NetworkChannel(project_id=2, network_subsystem_id=1, name="跨项目通信"),
        models.NetworkAuthDetail(project_id=2, network_channel_id=1),
        models.NetworkIntegrityDetail(project_id=2, network_channel_id=1),
        models.NetworkConfidentialityDetail(project_id=2, network_channel_id=1),
        models.NetworkBoundaryIntegrityDetail(project_id=2, network_channel_id=1),
        models.ApplicationUser(
            project_id=2,
            application_subsystem_id=1,
            name="跨项目用户",
        ),
        models.AccessControlObject(
            project_id=2,
            application_subsystem_id=1,
            name="跨项目权限",
        ),
        models.ImportantData(
            project_id=2,
            application_subsystem_id=1,
            name="跨项目数据",
            data_type="业务数据",
        ),
        models.BusinessAction(
            project_id=2,
            application_subsystem_id=1,
            name="跨项目行为",
        ),
        models.ApplicationUserAuthDetail(project_id=2, application_user_id=1),
        models.AccessControlIntegrityDetail(project_id=2, access_control_object_id=1),
        models.DataTransportConfidentialityDetail(project_id=2, important_data_id=1),
        models.DataStorageConfidentialityDetail(project_id=2, important_data_id=1),
        models.DataTransportIntegrityDetail(project_id=2, important_data_id=1),
        models.DataStorageIntegrityDetail(project_id=2, important_data_id=1),
        models.BusinessActionNonRepudiationDetail(project_id=2, business_action_id=1),
    ]
    for child in cross_project_children:
        with pytest.raises(IntegrityError), session_scope(engine) as session:
            session.add(child)


def test_network_and_application_subsystems_reject_cross_project_basic_subsystem(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)
    init_database(engine)

    with session_scope(engine) as session:
        session.add_all([_project(1), _project(2)])
    with session_scope(engine) as session:
        session.add(models.Subsystem(id=1, project_id=1, name="基础子系统A"))

    cross_project_subsystems = [
        models.NetworkSubsystem(
            project_id=2,
            basic_subsystem_id=1,
            name="网络子系统跨项目",
        ),
        models.ApplicationSubsystem(
            project_id=2,
            basic_subsystem_id=1,
            name="应用子系统跨项目",
        ),
    ]
    for subsystem in cross_project_subsystems:
        with pytest.raises(IntegrityError), session_scope(engine) as session:
            session.add(subsystem)


def test_init_database_runs_foundation_migrations_idempotently(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)

    init_database(engine)
    init_database(engine)

    with engine.connect() as connection:
        indicator_count = connection.execute(
            text("select count(*) from scoring_indicators")
        ).scalar_one()
        distinct_indicator_count = connection.execute(
            text("select count(distinct indicator_no) from scoring_indicators")
        ).scalar_one()
        migration_names = set(
            connection.execute(text("select migration_name from data_versions")).scalars()
        )

    assert indicator_count == 41
    assert distinct_indicator_count == 41
    assert {
        "default_scoring_indicators",
        "knowledge_defaults",
        "enum_cleanup",
    }.issubset(migration_names)


def test_enum_cleanup_covers_old_values_across_schema(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)
    init_database(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                insert into projects (
                    id, flow_no, system_name, client_name, assessment_org,
                    status, is_deleted, sort_order
                )
                values (1, 'LC-001', '业务系统', '委托方', '测评机构', 'active', 0, 0)
                """
            )
        )
        connection.execute(
            text(
                """
                insert into physical_objects (
                    id, project_id, sort_order, name, location,
                    access_control_system, video_system, interview_record, description
                )
                values (1, 1, 0, '机房A', '一层', '', '', '', '')
                """
            )
        )
        connection.execute(
            text(
                """
                insert into physical_auth_details (
                    id, project_id, physical_object_id, sort_order,
                    requirement, implementation, evaluation_result,
                    auth_methods, access_control_device, crypto_usage, algorithm,
                    product_compliance, compliance_status, risk_level,
                    risk_analysis, remediation
                )
                values (1, 1, 1, 0, '', '', '', '', '', '', '', '未选择', null, 'None', '', '')
                """
            )
        )
        connection.execute(
            text(
                """
                insert into quantitative_assessments (
                    id, project_id, unit_type, related_id, sort_order,
                    d_value, a_value, k_value, ra_value, rk_value,
                    compliance_status, risk_level, notes
                )
                values (
                    1, 1, '物理访问身份鉴别', 1, 0,
                    'None', 'null', '未选择', null, '请选择',
                    'None', 'null', ''
                )
                """
            )
        )
        connection.execute(
            text(
                """
                insert into crypto_products (
                    id, project_id, unit_type, related_id, sort_order,
                    product_name, product_model, certificate_no,
                    product_level, vendor, usage
                )
                values (1, 1, '物理访问身份鉴别', 1, 0, '产品A', '', '', 'null', '', '')
                """
            )
        )
        connection.execute(
            text(
                """
                insert into management_scores (
                    id, project_id, sort_order, indicator_no, layer,
                    compliance_status, notes
                )
                values (1, 1, 0, 23, '管理制度', '未选择', '')
                """
            )
        )
        connection.execute(
            text(
                """
                insert into score_summaries (
                    id, project_id, sort_order, total_score,
                    compliant_count, partial_count, non_compliant_count,
                    not_applicable_count
                )
                values (1, 1, 0, 0, 0, 0, 0, 0)
                """
            )
        )
        connection.execute(
            text(
                """
                insert into score_details (
                    id, project_id, summary_id, sort_order, indicator_no,
                    layer, unit_type, related_id, compliance_status, risk_level, notes
                )
                values (
                    1, 1, 1, 0, 1, '物理和环境安全',
                    '物理访问身份鉴别', 1, '请选择', 'None', ''
                )
                """
            )
        )

    MigrationService(engine).run_all()
    MigrationService(engine).run_all()

    with engine.connect() as connection:
        physical_values = connection.execute(
            text(
                """
                select compliance_status, risk_level, product_compliance
                from physical_auth_details
                """
            )
        ).one()
        quant_values = connection.execute(
            text(
                """
                select d_value, a_value, k_value, ra_value, rk_value,
                       compliance_status, risk_level
                from quantitative_assessments
                """
            )
        ).one()
        product_level = connection.execute(
            text("select product_level from crypto_products")
        ).scalar_one()
        management_status = connection.execute(
            text("select compliance_status from management_scores")
        ).scalar_one()
        score_values = connection.execute(
            text("select compliance_status, risk_level from score_details")
        ).one()

    assert tuple(physical_values) == ("", "", "")
    assert tuple(quant_values) == ("", "", "", "", "", "", "")
    assert product_level == ""
    assert management_status == ""
    assert tuple(score_values) == ("", "")
