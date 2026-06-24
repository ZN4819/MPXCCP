from __future__ import annotations

from pathlib import Path

from sqlalchemy import event, select

import mpxccp.models as models
from mpxccp.config.settings import EVIDENCE_ROOT_SETTING_KEY
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.evidence_service import EvidenceService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "task5-evidence.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="EVID-001",
        system_name="证据/系统:*?",
        client_name="Client",
        assessment_org="Org",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def _set_evidence_root(engine, root: Path) -> None:
    with session_scope(engine) as session:
        setting = session.scalar(
            select(models.AppSetting).where(models.AppSetting.key == EVIDENCE_ROOT_SETTING_KEY)
        )
        assert setting is not None
        setting.value = str(root)


def test_evidence_import_copies_file_and_records_relative_name(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    source = tmp_path / "source.png"
    source.write_bytes(b"fake image")
    service = EvidenceService(engine)

    result = service.import_files(
        project_id=project_id,
        system_name="证据/系统:*?",
        unit_type="物理访问身份鉴别",
        related_id=101,
        object_name='机房/A:*?"',
        files=[source],
        suffixes=["现场"],
    )

    assert result.success
    assert len(result.records) == 1
    assert result.records[0].file_name == "1. 物理身份鉴别_现场.png"
    assert Path(result.records[0].file_name).is_absolute() is False

    evidence_dir = root / "证据系统项目测评证据" / "物理和环境" / "机房A"
    assert (evidence_dir / "1. 物理身份鉴别_现场.png").exists()

    listed = service.list_records(
        project_id=project_id,
        system_name="证据/系统:*?",
        unit_type="物理访问身份鉴别",
        related_id=101,
        object_name='机房/A:*?"',
    )
    assert listed.records[0].thumbnail_path is None
    assert listed.records[0].exists_on_disk is True


def test_evidence_import_skips_missing_files_and_uses_prefix_override(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    source = tmp_path / "source.jpg"
    source.write_bytes(b"fake image")
    service = EvidenceService(engine)

    result = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="通信过程数据机密性",
        related_id=11,
        object_name="信道1",
        files=[tmp_path / "missing.png", source],
        suffixes=["缺失", ""],
        prefix="信道A",
    )

    assert result.success
    assert result.records[0].file_name == "1. 信道A.jpg"
    assert result.warnings == ["file_not_found:missing.png"]


def test_evidence_delete_removes_records_even_when_disk_file_missing_and_renumbers(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    third = tmp_path / "third.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    third.write_bytes(b"third")
    service = EvidenceService(engine)
    imported = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        files=[first, second, third],
        suffixes=["一", "二", "三"],
    )
    assert [record.file_name for record in imported.records] == [
        "1. 设备身份鉴别_一.png",
        "2. 设备身份鉴别_二.png",
        "3. 设备身份鉴别_三.png",
    ]
    evidence_dir = root / "系统项目测评证据" / "设备和计算" / "设备A"
    (evidence_dir / "2. 设备身份鉴别_二.png").unlink()

    delete = service.delete_records(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        record_ids=[imported.records[1].id],
    )

    assert delete.success
    assert delete.warnings == ["missing_file:2. 设备身份鉴别_二.png"]
    assert sorted(path.name for path in evidence_dir.iterdir()) == [
        "1. 设备身份鉴别_一.png",
        "2. 设备身份鉴别_三.png",
    ]

    listed = service.list_records(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
    )
    assert [record.file_name for record in listed.records] == [
        "1. 设备身份鉴别_一.png",
        "2. 设备身份鉴别_三.png",
    ]
    assert [record.sort_order for record in listed.records] == [1, 2]

def test_evidence_delete_renumbers_only_current_related_records(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    remote = tmp_path / "remote.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    remote.write_bytes(b"remote")
    service = EvidenceService(engine)
    auth = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        files=[first, second],
        suffixes=["一", "二"],
    )
    remote_result = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="远程管理通道",
        related_id=303,
        object_name="设备A",
        files=[remote],
        suffixes=["远程"],
    )
    assert remote_result.records[0].file_name == "3. 远程管理_远程.png"

    delete = service.delete_records(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        record_ids=[auth.records[0].id],
    )

    assert delete.success
    evidence_dir = root / "系统项目测评证据" / "设备和计算" / "设备A"
    assert (evidence_dir / "1. 设备身份鉴别_二.png").exists()
    assert (evidence_dir / "3. 远程管理_远程.png").exists()

    remote_list = service.list_records(
        project_id=project_id,
        system_name="系统",
        unit_type="远程管理通道",
        related_id=303,
        object_name="设备A",
    )
    assert remote_list.records[0].file_name == "3. 远程管理_远程.png"
    assert remote_list.records[0].exists_on_disk is True


def test_evidence_import_sanitizes_prefix_and_suffix_components(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    source = tmp_path / "source.jpg"
    source.write_bytes(b"fake image")
    service = EvidenceService(engine)

    result = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="通信过程数据机密性",
        related_id=11,
        object_name="信道1",
        files=[source],
        suffixes=['现场/1:*?"'],
        prefix='信/道:*A',
    )

    assert result.success
    assert result.records[0].file_name == "1. 信道A_现场1.jpg"
    evidence_dir = root / "系统项目测评证据" / "网络和通信" / "信道1"
    assert (evidence_dir / "1. 信道A_现场1.jpg").exists()

class FailingRenumberStore:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.deleted: list[Path] = []

    def evidence_directory(self, *args, **kwargs):
        return self.wrapped.evidence_directory(*args, **kwargs)

    def build_file_name(self, *args, **kwargs):
        return self.wrapped.build_file_name(*args, **kwargs)

    def copy_file(self, *args, **kwargs):
        return self.wrapped.copy_file(*args, **kwargs)

    def next_available_file_name(self, *args, **kwargs):
        return self.wrapped.next_available_file_name(*args, **kwargs)

    def stage_delete_file(self, *args, **kwargs):
        return self.wrapped.stage_delete_file(*args, **kwargs)

    def restore_staged_file(self, *args, **kwargs):
        return self.wrapped.restore_staged_file(*args, **kwargs)

    def restore_renumbered_files(self, *args, **kwargs):
        return self.wrapped.restore_renumbered_files(*args, **kwargs)

    def finalize_staged_delete(self, *args, **kwargs):
        return self.wrapped.finalize_staged_delete(*args, **kwargs)

    def delete_file_if_exists(self, path: Path) -> bool:
        if path.exists():
            self.deleted.append(path)
            path.unlink()
            return True
        return False

    def renumber_named_files(self, directory: Path, file_names):
        raise RuntimeError("renumber failed")


def test_evidence_import_avoids_overwriting_existing_file_name(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    remote = tmp_path / "remote.png"
    new_remote = tmp_path / "new-remote.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    remote.write_bytes(b"remote-original")
    new_remote.write_bytes(b"remote-new")
    service = EvidenceService(engine)
    auth = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        files=[first, second],
        suffixes=["一", "二"],
    )
    remote_result = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="远程管理通道",
        related_id=303,
        object_name="设备A",
        files=[remote],
        suffixes=["远程"],
    )
    service.delete_records(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        record_ids=[auth.records[0].id],
    )

    second_remote = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="远程管理通道",
        related_id=303,
        object_name="设备A",
        files=[new_remote],
        suffixes=["远程"],
    )

    evidence_dir = root / "系统项目测评证据" / "设备和计算" / "设备A"
    assert (evidence_dir / remote_result.records[0].file_name).read_bytes() == b"remote-original"
    assert second_remote.records[0].file_name != remote_result.records[0].file_name
    assert (evidence_dir / second_remote.records[0].file_name).read_bytes() == b"remote-new"


def test_evidence_delete_rolls_back_file_delete_when_renumber_fails(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    wrapped = EvidenceService(engine).file_store
    file_store = FailingRenumberStore(wrapped)
    service = EvidenceService(engine, file_store=file_store)
    imported = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        files=[first, second],
        suffixes=["一", "二"],
    )

    try:
        service.delete_records(
            project_id=project_id,
            system_name="系统",
            unit_type="设备登录身份鉴别",
            related_id=202,
            object_name="设备A",
            record_ids=[imported.records[0].id],
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("delete_records should propagate renumber failure")

    evidence_dir = root / "系统项目测评证据" / "设备和计算" / "设备A"
    assert (evidence_dir / "1. 设备身份鉴别_一.png").exists()
    listed = service.list_records(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
    )
    assert [record.file_name for record in listed.records] == [
        "1. 设备身份鉴别_一.png",
        "2. 设备身份鉴别_二.png",
    ]

def test_evidence_delete_restores_staged_file_when_database_commit_fails(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    root = tmp_path / "evidence-root"
    root.mkdir()
    _set_evidence_root(engine, root)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    service = EvidenceService(engine)
    imported = service.import_files(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
        files=[first, second],
        suffixes=["一", "二"],
    )

    def fail_commit(conn):
        event.remove(engine, "commit", fail_commit)
        raise RuntimeError("commit failed")

    event.listen(engine, "commit", fail_commit)
    try:
        service.delete_records(
            project_id=project_id,
            system_name="系统",
            unit_type="设备登录身份鉴别",
            related_id=202,
            object_name="设备A",
            record_ids=[imported.records[0].id],
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("delete_records should propagate commit failure")

    evidence_dir = root / "系统项目测评证据" / "设备和计算" / "设备A"
    assert (evidence_dir / "1. 设备身份鉴别_一.png").exists()
    listed = service.list_records(
        project_id=project_id,
        system_name="系统",
        unit_type="设备登录身份鉴别",
        related_id=202,
        object_name="设备A",
    )
    assert [record.file_name for record in listed.records] == [
        "1. 设备身份鉴别_一.png",
        "2. 设备身份鉴别_二.png",
    ]
