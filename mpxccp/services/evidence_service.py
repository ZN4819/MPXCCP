from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mpxccp.config.paths import evidence_root_from_settings
from mpxccp.domain.enums import MeasureUnit
from mpxccp.integration.evidence.file_store import EvidenceFileStore
from mpxccp.integration.evidence.thumbnails import ThumbnailGenerator
from mpxccp.models.shared import EvidenceImage
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.repositories.shared_repo import SharedRepository

PHYSICAL_UNITS = {
    MeasureUnit.PHYSICAL_AUTH.value,
    MeasureUnit.PHYSICAL_ACCESS_INTEGRITY.value,
    MeasureUnit.PHYSICAL_VIDEO_INTEGRITY.value,
}
DEVICE_UNITS = {
    MeasureUnit.DEVICE_AUTH.value,
    MeasureUnit.DEVICE_REMOTE.value,
    MeasureUnit.DEVICE_ACCESS_INTEGRITY.value,
    MeasureUnit.DEVICE_LOG_INTEGRITY.value,
    MeasureUnit.DEVICE_EXECUTABLE_INTEGRITY.value,
}
NETWORK_UNITS = {
    MeasureUnit.NETWORK_AUTH.value,
    MeasureUnit.NETWORK_INTEGRITY.value,
    MeasureUnit.NETWORK_CONFIDENTIALITY.value,
    MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value,
}
APPLICATION_UNITS = {
    MeasureUnit.APP_USER_AUTH.value,
    MeasureUnit.APP_ACCESS_INTEGRITY.value,
    MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value,
    MeasureUnit.DATA_STORAGE_CONFIDENTIALITY.value,
    MeasureUnit.DATA_TRANSPORT_INTEGRITY.value,
    MeasureUnit.DATA_STORAGE_INTEGRITY.value,
    MeasureUnit.BUSINESS_ACTION_NON_REPUDIATION.value,
}
PREFIXES = {
    MeasureUnit.PHYSICAL_AUTH.value: "物理身份鉴别",
    MeasureUnit.PHYSICAL_ACCESS_INTEGRITY.value: "门禁记录完整性",
    MeasureUnit.PHYSICAL_VIDEO_INTEGRITY.value: "视频记录完整性",
    MeasureUnit.DEVICE_AUTH.value: "设备身份鉴别",
    MeasureUnit.DEVICE_REMOTE.value: "远程管理",
    MeasureUnit.DEVICE_ACCESS_INTEGRITY.value: "访问控制完整性",
    MeasureUnit.DEVICE_LOG_INTEGRITY.value: "日志完整性",
    MeasureUnit.DEVICE_EXECUTABLE_INTEGRITY.value: "可执行程序完整性",
    MeasureUnit.NETWORK_AUTH.value: "通信身份鉴别",
    MeasureUnit.NETWORK_INTEGRITY.value: "通信完整性",
    MeasureUnit.NETWORK_CONFIDENTIALITY.value: "通信机密性",
    MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value: "边界完整性",
    MeasureUnit.APP_USER_AUTH.value: "用户身份鉴别",
    MeasureUnit.APP_ACCESS_INTEGRITY.value: "访问控制完整性",
    MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value: "传输机密性",
    MeasureUnit.DATA_STORAGE_CONFIDENTIALITY.value: "存储机密性",
    MeasureUnit.DATA_TRANSPORT_INTEGRITY.value: "传输完整性",
    MeasureUnit.DATA_STORAGE_INTEGRITY.value: "存储完整性",
    MeasureUnit.BUSINESS_ACTION_NON_REPUDIATION.value: "不可否认性",
}


@dataclass(frozen=True)
class EvidenceRecord:
    id: int
    project_id: int
    unit_type: str
    related_id: int
    file_name: str
    original_name: str
    caption: str
    checksum: str
    sort_order: int
    exists_on_disk: bool = False
    thumbnail_path: Path | None = None


@dataclass(frozen=True)
class EvidenceResult:
    success: bool
    message: str = ""
    warnings: list[str] | None = None
    records: list[EvidenceRecord] | None = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            object.__setattr__(self, "warnings", [])
        if self.records is None:
            object.__setattr__(self, "records", [])


class EvidenceService:
    def __init__(
        self,
        engine: Engine,
        *,
        shared_repo: SharedRepository | None = None,
        file_store: EvidenceFileStore | None = None,
        thumbnail_generator: ThumbnailGenerator | None = None,
    ) -> None:
        self.engine = engine
        self.shared_repo = shared_repo or SharedRepository()
        self.file_store = file_store or EvidenceFileStore()
        self.thumbnail_generator = thumbnail_generator or ThumbnailGenerator()

    def import_files(
        self,
        *,
        project_id: int,
        system_name: str,
        unit_type: str,
        related_id: int,
        object_name: str,
        files: list[Path],
        suffixes: list[str],
        prefix: str | None = None,
    ) -> EvidenceResult:
        warnings: list[str] = []
        records: list[EvidenceRecord] = []
        with session_scope(self.engine) as session:
            root = evidence_root_from_settings(session)
            directory = self._directory(
                root=root,
                project_id=project_id,
                system_name=system_name,
                unit_type=unit_type,
                object_name=object_name,
            )
            current_number = len([path for path in directory.iterdir() if path.is_file()]) + 1
            for index, raw_source in enumerate(files):
                source = Path(raw_source)
                if not source.is_file():
                    warnings.append(f"file_not_found:{source.name}")
                    continue
                suffix = suffixes[index] if index < len(suffixes) else ""
                target_name, current_number = self.file_store.next_available_file_name(
                    directory,
                    sequence=current_number,
                    unit_type=unit_type,
                    suffix=suffix,
                    extension=source.suffix,
                    prefix=prefix,
                )
                target = directory / target_name
                try:
                    self.file_store.copy_file(source, target)
                except OSError as exc:
                    warnings.append(f"copy_failed:{source.name}:{exc.__class__.__name__}")
                    continue
                model = self.shared_repo.add_evidence(
                    session,
                    project_id=project_id,
                    unit_type=unit_type,
                    related_id=related_id,
                    file_name=target_name,
                    original_name=source.name,
                    caption=str(suffix or ""),
                    checksum=self._checksum(target),
                    sort_order=current_number,
                )
                records.append(self._record_payload(model, directory))
                current_number += 1
        return EvidenceResult(
            success=bool(records),
            message="evidence files imported" if records else "no evidence files imported",
            warnings=warnings,
            records=records,
        )

    def list_records(
        self,
        *,
        project_id: int,
        system_name: str,
        unit_type: str,
        related_id: int,
        object_name: str,
    ) -> EvidenceResult:
        with readonly_session_scope(self.engine) as session:
            root = evidence_root_from_settings(session)
            directory = self._directory(
                root=root,
                project_id=project_id,
                system_name=system_name,
                unit_type=unit_type,
                object_name=object_name,
            )
            records = [
                self._record_payload(item, directory)
                for item in self.shared_repo.list_evidence(
                    session,
                    project_id,
                    unit_type,
                    related_id,
                )
            ]
        return EvidenceResult(success=True, message="evidence records loaded", records=records)

    def delete_records(
        self,
        *,
        project_id: int,
        system_name: str,
        unit_type: str,
        related_id: int,
        object_name: str,
        record_ids: list[int],
    ) -> EvidenceResult:
        if not record_ids:
            return EvidenceResult(
                success=False,
                message="no evidence records selected",
                warnings=["no_selection"],
            )

        warnings: list[str] = []
        staged_deletes: list[tuple[Path, str]] = []
        renumber_mapping: dict[str, str] = {}
        records: list[EvidenceRecord] = []
        session = Session(self.engine, expire_on_commit=False)
        try:
            root = evidence_root_from_settings(session)
            directory = self._directory(
                root=root,
                project_id=project_id,
                system_name=system_name,
                unit_type=unit_type,
                object_name=object_name,
            )
            selected = self.shared_repo.list_evidence_by_ids(
                session,
                project_id,
                unit_type,
                related_id,
                record_ids,
            )
            for record in selected:
                staged = self.file_store.stage_delete_file(directory, record.file_name)
                if staged is None:
                    warnings.append(f"missing_file:{record.file_name}")
                else:
                    staged_deletes.append((staged, record.file_name))
                session.delete(record)
            session.flush()
            remaining = self.shared_repo.list_evidence(
                session,
                project_id,
                unit_type,
                related_id,
            )
            renumber_mapping = self.file_store.renumber_named_files(
                directory,
                [record.file_name for record in remaining],
            )
            for record in remaining:
                if record.file_name in renumber_mapping:
                    record.file_name = renumber_mapping[record.file_name]
                record.sort_order = self._leading_number(record.file_name)
            records = [self._record_payload(item, directory) for item in remaining]
            session.commit()
        except Exception:
            session.rollback()
            self.file_store.restore_renumbered_files(directory, renumber_mapping)
            for staged, file_name in reversed(staged_deletes):
                self.file_store.restore_staged_file(staged, directory, file_name)
            raise
        else:
            for staged, _file_name in staged_deletes:
                try:
                    self.file_store.finalize_staged_delete(staged)
                except OSError:
                    warnings.append(f"staged_delete_not_finalized:{staged.name}")
            return EvidenceResult(
                success=True,
                message="evidence records deleted",
                warnings=warnings,
                records=records,
            )
        finally:
            session.close()

    def _directory(
        self,
        *,
        root: Path,
        project_id: int,
        system_name: str,
        unit_type: str,
        object_name: str,
    ) -> Path:
        return self.file_store.evidence_directory(
            root=root,
            system_name=system_name,
            module_dir=self._module_dir(unit_type),
            object_name=object_name,
            project_id=project_id,
        )

    def _module_dir(self, unit_type: str) -> str:
        if unit_type in PHYSICAL_UNITS:
            return "物理和环境"
        if unit_type in DEVICE_UNITS:
            return "设备和计算"
        if unit_type in NETWORK_UNITS:
            return "网络和通信"
        if unit_type in APPLICATION_UNITS:
            return "应用和数据"
        return "其他"

    def _target_name(
        self,
        number: int,
        unit_type: str,
        extension: str,
        suffix: str,
        prefix: str | None,
    ) -> str:
        base = str(prefix or PREFIXES.get(unit_type, unit_type)).strip()
        suffix_text = str(suffix or "").strip()
        name = f"{base}_{suffix_text}" if suffix_text else base
        return f"{number}. {name}{extension}"

    def _record_payload(self, record: EvidenceImage, directory: Path) -> EvidenceRecord:
        path = directory / record.file_name
        thumbnail = self.thumbnail_generator.create_thumbnail(path) if path.exists() else None
        return EvidenceRecord(
            id=record.id,
            project_id=record.project_id,
            unit_type=record.unit_type,
            related_id=record.related_id,
            file_name=record.file_name,
            original_name=record.original_name,
            caption=record.caption,
            checksum=record.checksum,
            sort_order=record.sort_order,
            exists_on_disk=path.exists(),
            thumbnail_path=thumbnail,
        )

    def _checksum(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _leading_number(self, file_name: str) -> int:
        head = file_name.split(".", 1)[0]
        try:
            return int(head)
        except ValueError:
            return 0
