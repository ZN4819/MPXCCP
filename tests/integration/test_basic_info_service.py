from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

import mpxccp.models as models
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.result import ServiceResult


def _service(tmp_path: Path) -> BasicInfoService:
    engine = create_engine_for_path(tmp_path / "task4.sqlite3")
    init_database(engine)
    return BasicInfoService(engine)


def test_required_basic_info_fields_do_not_create_project_when_missing(tmp_path):
    service = _service(tmp_path)

    result = service.save_basic_info(flow_no="", system_name="System")

    assert isinstance(result, ServiceResult)
    assert result.success is False
    assert result.project_id is None
    assert "flow_no" in result.warnings

    with session_scope(service.engine) as session:
        project_count = session.scalar(select(func.count()).select_from(models.Project))
        basic_info_count = session.scalar(select(func.count()).select_from(models.BasicInfo))

    assert project_count == 0
    assert basic_info_count == 0


def test_none_basic_info_fields_are_treated_as_missing_and_do_not_create_project(tmp_path):
    service = _service(tmp_path)

    result = service.save_basic_info(flow_no=None, system_name=None)

    assert result.success is False
    assert result.project_id is None
    assert result.warnings == ["flow_no", "system_name"]

    with session_scope(service.engine) as session:
        project_count = session.scalar(select(func.count()).select_from(models.Project))
        basic_info_count = session.scalar(select(func.count()).select_from(models.BasicInfo))

    assert project_count == 0
    assert basic_info_count == 0


def test_save_basic_info_for_missing_project_returns_failure_result(tmp_path):
    service = _service(tmp_path)

    result = service.save_basic_info(
        project_id=404,
        flow_no="FLOW-MISSING",
        system_name="Missing System",
    )

    assert result.success is False
    assert result.project_id == 404
    assert result.warnings == ["project_not_found"]


def test_first_basic_info_save_creates_project_and_loads_saved_fields(tmp_path):
    service = _service(tmp_path)

    result = service.save_basic_info(
        flow_no="FLOW-100",
        system_name="Payment System",
        client_name="Client A",
        assessment_org="Org A",
        contact_name="Owner",
        contact_phone="13800000000",
        assessor_name="Assessor",
        assessor_phone="13900000000",
        interview_time="2026-06-24 10:00",
        notes="Interview notes",
    )

    assert result.success is True
    assert result.project_id is not None
    assert result.payload["created"] is True

    loaded = service.load_basic_info(result.project_id)
    assert loaded.success is True
    assert loaded.payload == {
        "project_id": result.project_id,
        "flow_no": "FLOW-100",
        "system_name": "Payment System",
        "client_name": "Client A",
        "assessment_org": "Org A",
        "contact_name": "Owner",
        "contact_phone": "13800000000",
        "assessor_name": "Assessor",
        "assessor_phone": "13900000000",
        "interview_time": "2026-06-24 10:00",
        "notes": "Interview notes",
    }

    with session_scope(service.engine) as session:
        project = session.get(models.Project, result.project_id)
        basic_info = session.scalar(
            select(models.BasicInfo).where(models.BasicInfo.project_id == result.project_id)
        )

    assert project is not None
    assert project.flow_no == "FLOW-100"
    assert project.system_name == "Payment System"
    assert basic_info is not None
    assert basic_info.flow_no == "FLOW-100"
    assert basic_info.system_name == "Payment System"


def test_full_basic_info_rolls_back_first_save_when_later_step_fails(tmp_path):
    service = _service(tmp_path)

    with pytest.raises(TypeError):
        service.save_full_basic_info(
            flow_no="FLOW-ROLLBACK",
            system_name="Rollback System",
            crypto_application_info={"bad": object()},
            subsystems=["Portal"],
        )

    with session_scope(service.engine) as session:
        project_count = session.scalar(select(func.count()).select_from(models.Project))
        basic_info_count = session.scalar(select(func.count()).select_from(models.BasicInfo))
        subsystem_count = session.scalar(select(func.count()).select_from(models.Subsystem))

    assert project_count == 0
    assert basic_info_count == 0
    assert subsystem_count == 0


def test_load_basic_info_tolerates_legacy_extra_data_and_damaged_crypto_json(tmp_path):
    service = _service(tmp_path)
    with session_scope(service.engine) as session:
        project = models.Project(
            flow_no="FLOW-LEGACY",
            system_name="Legacy System",
            extra_data="legacy-string",
        )
        session.add(project)
        session.flush()
        session.add_all(
            [
                models.BasicInfo(
                    project_id=project.id,
                    flow_no="FLOW-LEGACY",
                    system_name="Legacy System",
                    contact_name="Legacy Owner",
                    assessment_date="2026-01-01",
                ),
                models.SystemInfo(
                    project_id=project.id,
                    business_description="Legacy business",
                    security_level="二级",
                    extra_data="legacy-system-extra",
                ),
                models.CryptoApplicationInfo(
                    project_id=project.id,
                    application_scope="Legacy scope",
                    algorithm_description="SM2/SM3",
                    key_management_description="Legacy key management",
                    product_description="Legacy products",
                    notes="{damaged json",
                ),
            ]
        )
        project_id = project.id

    loaded_basic = service.load_basic_info(project_id)
    loaded_full = service.load_full_basic_info(project_id)

    assert loaded_basic.success
    assert loaded_basic.payload["assessor_name"] == ""
    assert loaded_basic.payload["interview_time"] == "2026-01-01"
    assert loaded_full.success
    assert loaded_full.payload["system_info"] == {
        "business_description": "Legacy business",
        "security_level": "二级",
    }
    assert loaded_full.payload["crypto_application_info"] == {
        "application_scope": "Legacy scope",
        "algorithm_description": "SM2/SM3",
        "key_management_description": "Legacy key management",
        "product_description": "Legacy products",
        "notes": "{damaged json",
    }


def test_subsystems_preserve_ids_and_list_names_in_saved_order(tmp_path):
    service = _service(tmp_path)
    result = service.save_basic_info(flow_no="FLOW-SUB", system_name="Subsystem System")
    assert result.project_id is not None

    first_sync = service.sync_subsystems(result.project_id, ["Core", "Portal", "Audit"])
    assert first_sync.success
    original = service.list_subsystem_rows(result.project_id)
    original_ids = {item["name"]: item["id"] for item in original}

    second_sync = service.sync_subsystems(result.project_id, ["Audit", "Core", "Risk"])
    assert second_sync.success
    current = service.list_subsystem_rows(result.project_id)

    assert service.list_subsystems(result.project_id) == ["Audit", "Core", "Risk"]
    assert [item["name"] for item in current] == ["Audit", "Core", "Risk"]
    assert current[0]["id"] == original_ids["Audit"]
    assert current[1]["id"] == original_ids["Core"]
    assert current[2]["id"] not in original_ids.values()


def test_full_basic_info_round_trips_system_crypto_and_subsystems(tmp_path):
    service = _service(tmp_path)
    system_info = {
        "business_description": "Handles payment orders.",
        "subsystem_description": "Portal and management backend.",
        "online_date": "2025-01-15",
        "classified_status": "classified",
        "security_level": "三级",
        "s_value": "S3",
        "a_value": "A2",
        "level_consistency": "consistent",
        "assessment_status": "passed",
        "assessment_org": "Assessment Org",
        "assessment_date": "2026-06-24",
        "assessment_result": "符合",
        "pass_rate": "95%",
        "upstream_systems": "CRM",
        "downstream_systems": "ERP",
        "other_systems": "BI",
    }
    crypto_application_info = {
        "last_assessment_status": "passed",
        "last_assessment_org": "Prior Org",
        "last_assessment_date": "2025-06-01",
        "last_assessment_result": "基本符合",
        "last_assessment_score": "82",
        "has_scheme": "yes",
        "scheme_description": "Uses approved commercial crypto scheme.",
        "is_reviewed": "yes",
        "review_method": "专家评审",
        "review_org": "Review Org",
        "review_date": "2026-01-10",
    }

    saved = service.save_full_basic_info(
        flow_no="FLOW-FULL",
        system_name="Full System",
        client_name="Client Full",
        assessment_org="Org Full",
        contact_name="Owner Full",
        contact_phone="13800000001",
        assessor_name="Assessor Full",
        assessor_phone="13900000001",
        interview_time="2026-06-24 11:00",
        notes="Full notes",
        system_info=system_info,
        crypto_application_info=crypto_application_info,
        subsystems=["门户", "管理端"],
    )
    assert saved.success
    assert saved.project_id is not None

    loaded = service.load_full_basic_info(saved.project_id)

    assert loaded.success
    assert loaded.payload["basic_info"]["flow_no"] == "FLOW-FULL"
    assert loaded.payload["basic_info"]["system_name"] == "Full System"
    assert loaded.payload["system_info"] == system_info
    assert loaded.payload["crypto_application_info"] == crypto_application_info
    assert loaded.payload["subsystems"] == ["门户", "管理端"]


def test_subsystem_sync_creates_network_application_entries_without_clearing_module_data(
    tmp_path,
):
    service = _service(tmp_path)
    result = service.save_basic_info(flow_no="FLOW-SYNC", system_name="Sync System")
    assert result.project_id is not None
    project_id = result.project_id

    service.sync_subsystems(project_id, ["Core", "Portal"])
    with session_scope(service.engine) as session:
        core_network = session.scalar(
            select(models.NetworkSubsystem).where(
                models.NetworkSubsystem.project_id == project_id,
                models.NetworkSubsystem.name == "Core",
            )
        )
        core_application = session.scalar(
            select(models.ApplicationSubsystem).where(
                models.ApplicationSubsystem.project_id == project_id,
                models.ApplicationSubsystem.name == "Core",
            )
        )
        assert core_network is not None
        assert core_application is not None
        core_network.description = "Existing network description"
        core_application.description = "Existing application description"
        session.add_all(
            [
                models.NetworkChannel(
                    project_id=project_id,
                    network_subsystem_id=core_network.id,
                    name="Core Channel",
                ),
                models.ApplicationUser(
                    project_id=project_id,
                    application_subsystem_id=core_application.id,
                    name="Core User",
                ),
            ]
        )

    sync_result = service.sync_subsystems(project_id, ["Portal", "Risk"])
    assert sync_result.success
    assert sync_result.payload["disabled"] == ["Core"]
    assert sync_result.payload["disabled_policy"] == "soft_disable_basic_subsystem"
    assert sync_result.payload["network_created"] == ["Risk"]
    assert sync_result.payload["application_created"] == ["Risk"]

    with session_scope(service.engine) as session:
        core_basic = session.scalar(
            select(models.Subsystem).where(
                models.Subsystem.project_id == project_id,
                models.Subsystem.name == "Core",
            )
        )
        network_channel_count = session.scalar(
            select(func.count()).select_from(models.NetworkChannel).where(
                models.NetworkChannel.project_id == project_id
            )
        )
        application_user_count = session.scalar(
            select(func.count()).select_from(models.ApplicationUser).where(
                models.ApplicationUser.project_id == project_id
            )
        )
        network_description = session.scalar(
            select(models.NetworkSubsystem.description).where(
                models.NetworkSubsystem.project_id == project_id,
                models.NetworkSubsystem.name == "Core",
            )
        )
        application_description = session.scalar(
            select(models.ApplicationSubsystem.description).where(
                models.ApplicationSubsystem.project_id == project_id,
                models.ApplicationSubsystem.name == "Core",
            )
        )

    assert core_basic is not None
    assert core_basic.is_enabled is False
    assert network_channel_count == 1
    assert application_user_count == 1
    assert network_description == "Existing network description"
    assert application_description == "Existing application description"
