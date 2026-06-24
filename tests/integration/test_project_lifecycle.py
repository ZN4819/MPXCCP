from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

import mpxccp.models as models
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.project_service import ProjectService


def _init_services(tmp_path: Path) -> tuple[BasicInfoService, ProjectService]:
    engine = create_engine_for_path(tmp_path / "task4.sqlite3")
    init_database(engine)
    return BasicInfoService(engine), ProjectService(engine)


def _create_project(
    basic_service: BasicInfoService,
    flow_no: str,
    system_name: str,
) -> int:
    result = basic_service.save_basic_info(
        flow_no=flow_no,
        system_name=system_name,
        client_name="Client",
        assessment_org="Assessment Org",
    )
    assert result.success, result.message
    assert result.project_id is not None
    return result.project_id


def test_openable_projects_hide_soft_deleted_and_restore_reenables(tmp_path):
    basic_service, project_service = _init_services(tmp_path)
    first_id = _create_project(basic_service, "FLOW-001", "First System")
    second_id = _create_project(basic_service, "FLOW-002", "Second System")

    openable = project_service.list_openable()
    assert [item["id"] for item in openable] == [second_id, first_id]

    delete_result = project_service.soft_delete(second_id, deleted_by="tester", reason="cleanup")
    assert delete_result.success
    assert delete_result.project_id == second_id
    assert [item["id"] for item in project_service.list_openable()] == [first_id]

    second_delete = project_service.soft_delete(second_id, deleted_by="tester")
    assert second_delete.success

    with session_scope(project_service.engine) as session:
        deleted_count = session.scalar(
            select(func.count()).select_from(models.DeletedProject).where(
                models.DeletedProject.project_id == second_id
            )
        )
        basic_info_count = session.scalar(
            select(func.count()).select_from(models.BasicInfo).where(
                models.BasicInfo.project_id == second_id
            )
        )

    assert deleted_count == 1
    assert basic_info_count == 1

    restore_result = project_service.restore([second_id])
    assert restore_result.success
    assert [item["id"] for item in project_service.list_openable()] == [second_id, first_id]

    with session_scope(project_service.engine) as session:
        deleted_count = session.scalar(
            select(func.count()).select_from(models.DeletedProject).where(
                models.DeletedProject.project_id == second_id
            )
        )
        restored_project = session.get(models.Project, second_id)

    assert deleted_count == 0
    assert restored_project is not None
    assert restored_project.is_deleted is False


def test_hard_delete_removes_only_target_project_database_records_and_keeps_files(tmp_path):
    basic_service, project_service = _init_services(tmp_path)
    target_id = _create_project(basic_service, "FLOW-DEL", "Delete Me")
    survivor_id = _create_project(basic_service, "FLOW-KEEP", "Keep Me")
    target_evidence_file = tmp_path / "target-evidence.png"
    target_evidence_file.write_bytes(b"not really an image")

    basic_service.sync_subsystems(target_id, ["Trading"])
    basic_service.sync_subsystems(survivor_id, ["Survivor"])

    with session_scope(project_service.engine) as session:
        target_network = session.scalar(
            select(models.NetworkSubsystem).where(models.NetworkSubsystem.project_id == target_id)
        )
        survivor_network = session.scalar(
            select(models.NetworkSubsystem).where(models.NetworkSubsystem.project_id == survivor_id)
        )
        target_application = session.scalar(
            select(models.ApplicationSubsystem).where(
                models.ApplicationSubsystem.project_id == target_id
            )
        )
        survivor_application = session.scalar(
            select(models.ApplicationSubsystem).where(
                models.ApplicationSubsystem.project_id == survivor_id
            )
        )
        assert target_network is not None
        assert survivor_network is not None
        assert target_application is not None
        assert survivor_application is not None

        session.add_all(
            [
                models.NetworkChannel(
                    project_id=target_id,
                    network_subsystem_id=target_network.id,
                    name="Target Channel",
                ),
                models.NetworkChannel(
                    project_id=survivor_id,
                    network_subsystem_id=survivor_network.id,
                    name="Survivor Channel",
                ),
                models.ApplicationUser(
                    project_id=target_id,
                    application_subsystem_id=target_application.id,
                    name="Target User",
                ),
                models.ApplicationUser(
                    project_id=survivor_id,
                    application_subsystem_id=survivor_application.id,
                    name="Survivor User",
                ),
                models.EvidenceImage(
                    project_id=target_id,
                    unit_type="network",
                    related_id=1,
                    file_name=target_evidence_file.name,
                    original_name="target.png",
                    checksum="abc",
                ),
                models.EvidenceImage(
                    project_id=survivor_id,
                    unit_type="network",
                    related_id=1,
                    file_name="survivor.png",
                    original_name="survivor.png",
                    checksum="def",
                ),
                models.QuantitativeAssessment(
                    project_id=target_id,
                    unit_type="network",
                    related_id=1,
                    d_value="1",
                ),
                models.QuantitativeAssessment(
                    project_id=survivor_id,
                    unit_type="network",
                    related_id=1,
                    d_value="1",
                ),
                models.CryptoProduct(
                    project_id=target_id,
                    unit_type="network",
                    related_id=1,
                    product_name="Target Product",
                ),
                models.CryptoProduct(
                    project_id=survivor_id,
                    unit_type="network",
                    related_id=1,
                    product_name="Survivor Product",
                ),
                models.ManagementScore(
                    project_id=target_id,
                    indicator_no=23,
                    layer="management",
                ),
                models.ManagementScore(
                    project_id=survivor_id,
                    indicator_no=23,
                    layer="management",
                ),
                models.ScoreSummary(project_id=target_id, total_score=0),
                models.ScoreSummary(project_id=survivor_id, total_score=0),
            ]
        )
        session.flush()
        target_summary = session.scalar(
            select(models.ScoreSummary).where(models.ScoreSummary.project_id == target_id)
        )
        survivor_summary = session.scalar(
            select(models.ScoreSummary).where(models.ScoreSummary.project_id == survivor_id)
        )
        assert target_summary is not None
        assert survivor_summary is not None
        session.add_all(
            [
                models.ScoreDetail(
                    project_id=target_id,
                    summary_id=target_summary.id,
                    indicator_no=1,
                    layer="physical",
                    unit_type="network",
                ),
                models.ScoreDetail(
                    project_id=survivor_id,
                    summary_id=survivor_summary.id,
                    indicator_no=1,
                    layer="physical",
                    unit_type="network",
                ),
                models.DeletedProject(
                    project_id=target_id,
                    flow_no="FLOW-DEL",
                    system_name="Delete Me",
                ),
                models.DeletedProject(
                    project_id=survivor_id,
                    flow_no="FLOW-KEEP",
                    system_name="Keep Me",
                ),
            ]
        )

    result = project_service.hard_delete(target_id)
    assert result.success
    assert result.project_id == target_id
    assert target_evidence_file.exists()

    with session_scope(project_service.engine) as session:
        assert session.get(models.Project, target_id) is None
        assert session.get(models.Project, survivor_id) is not None
        for model in (
            models.BasicInfo,
            models.Subsystem,
            models.NetworkSubsystem,
            models.ApplicationSubsystem,
            models.NetworkChannel,
            models.ApplicationUser,
            models.EvidenceImage,
            models.QuantitativeAssessment,
            models.CryptoProduct,
            models.ManagementScore,
            models.ScoreSummary,
            models.ScoreDetail,
            models.DeletedProject,
        ):
            target_count = session.scalar(
                select(func.count()).select_from(model).where(model.project_id == target_id)
            )
            survivor_count = session.scalar(
                select(func.count()).select_from(model).where(model.project_id == survivor_id)
            )
            assert target_count == 0
            assert survivor_count == 1