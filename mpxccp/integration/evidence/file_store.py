from __future__ import annotations

import re
import shutil
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ILLEGAL_WINDOWS_PATH_CHARS = re.compile(r'[\\/:*?"<>|]')
NUMBERED_FILE_PREFIX = re.compile(r"^\d+\.\s*")

MODULE_DIR_BY_UNIT: dict[str, str] = {
    "物理访问身份鉴别": "物理和环境",
    "门禁记录完整性": "物理和环境",
    "视频记录完整性": "物理和环境",
    "设备登录身份鉴别": "设备和计算",
    "远程管理通道": "设备和计算",
    "设备访问控制完整性": "设备和计算",
    "设备日志完整性": "设备和计算",
    "可执行程序完整性": "设备和计算",
    "通信实体身份鉴别": "网络和通信",
    "通信过程数据完整性": "网络和通信",
    "通信过程数据机密性": "网络和通信",
    "网络边界访问控制完整性": "网络和通信",
    "应用用户身份鉴别": "应用和数据",
    "应用访问控制完整性": "应用和数据",
    "重要数据传输机密性": "应用和数据",
    "重要数据存储机密性": "应用和数据",
    "重要数据传输完整性": "应用和数据",
    "重要数据存储完整性": "应用和数据",
    "关键业务行为不可否认性": "应用和数据",
}

DEFAULT_PREFIX_BY_UNIT: dict[str, str] = {
    "物理访问身份鉴别": "物理身份鉴别",
    "门禁记录完整性": "门禁记录完整性",
    "视频记录完整性": "视频记录完整性",
    "设备登录身份鉴别": "设备身份鉴别",
    "远程管理通道": "远程管理",
    "设备访问控制完整性": "访问控制完整性",
    "设备日志完整性": "日志完整性",
    "可执行程序完整性": "可执行程序完整性",
    "通信实体身份鉴别": "通信身份鉴别",
    "通信过程数据完整性": "通信完整性",
    "通信过程数据机密性": "通信机密性",
    "网络边界访问控制完整性": "边界完整性",
    "应用用户身份鉴别": "用户身份鉴别",
    "应用访问控制完整性": "访问控制完整性",
    "重要数据传输机密性": "传输机密性",
    "重要数据存储机密性": "存储机密性",
    "重要数据传输完整性": "传输完整性",
    "重要数据存储完整性": "存储完整性",
    "关键业务行为不可否认性": "不可否认性",
}


@dataclass(frozen=True, slots=True)
class CopiedEvidenceFile:
    source: Path
    destination: Path
    file_name: str
    sort_order: int


class EvidenceFileStore:
    def sanitize_path_part(self, value: str, *, fallback: str) -> str:
        cleaned = ILLEGAL_WINDOWS_PATH_CHARS.sub("", value).strip()
        cleaned = cleaned.rstrip(". ")
        return cleaned or fallback

    def sanitize_segment(self, value: str, fallback: str) -> str:
        return self.sanitize_path_part(value, fallback=fallback)

    def module_dir_for_unit(self, unit_type: str) -> str:
        return MODULE_DIR_BY_UNIT.get(unit_type, "其他")

    def default_prefix_for_unit(self, unit_type: str) -> str:
        return DEFAULT_PREFIX_BY_UNIT.get(unit_type, unit_type or "证据")

    def evidence_directory(
        self,
        evidence_root: Path | None = None,
        *,
        root: Path | None = None,
        project_id: int,
        system_name: str,
        unit_type: str | None = None,
        module_dir: str | None = None,
        object_name: str,
        create: bool = True,
    ) -> Path:
        base_root = evidence_root or root
        if base_root is None:
            raise ValueError("evidence root is required")

        system_part = self.sanitize_path_part(system_name, fallback=f"项目{project_id}")
        object_part = self.sanitize_path_part(object_name, fallback="未命名对象")
        directory = (
            base_root
            / f"{system_part}项目测评证据"
            / (module_dir or self.module_dir_for_unit(unit_type or ""))
            / object_part
        )
        if create:
            directory.mkdir(parents=True, exist_ok=True)
        return directory

    def build_file_name(
        self,
        *,
        sequence: int,
        unit_type: str,
        suffix: str,
        extension: str,
        prefix: str | None = None,
    ) -> str:
        clean_prefix = self._sanitize_file_component(
            prefix if prefix is not None else self.default_prefix_for_unit(unit_type),
            fallback="证据",
        )
        clean_suffix = self._sanitize_file_component(suffix, fallback="")
        if clean_suffix:
            return f"{sequence}. {clean_prefix}_{clean_suffix}{extension}"
        return f"{sequence}. {clean_prefix}{extension}"

    def copy_file(
        self,
        source: Path,
        target_or_directory: Path,
        *,
        unit_type: str | None = None,
        suffix: str = "",
        prefix: str | None = None,
    ) -> CopiedEvidenceFile | None:
        if unit_type is None:
            target_or_directory.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target_or_directory)
            return None

        directory = target_or_directory
        sequence = self.next_sequence(directory)
        file_name = self.build_file_name(
            sequence=sequence,
            unit_type=unit_type,
            suffix=suffix,
            extension=source.suffix,
            prefix=prefix,
        )
        destination = directory / file_name
        while destination.exists():
            sequence += 1
            file_name = self.build_file_name(
                sequence=sequence,
                unit_type=unit_type,
                suffix=suffix,
                extension=source.suffix,
                prefix=prefix,
            )
            destination = directory / file_name

        shutil.copy2(source, destination)
        return CopiedEvidenceFile(
            source=source,
            destination=destination,
            file_name=file_name,
            sort_order=sequence,
        )

    def next_available_file_name(
        self,
        directory: Path,
        *,
        sequence: int,
        unit_type: str,
        suffix: str,
        extension: str,
        prefix: str | None = None,
    ) -> tuple[str, int]:
        current_sequence = sequence
        while True:
            file_name = self.build_file_name(
                sequence=current_sequence,
                unit_type=unit_type,
                suffix=suffix,
                extension=extension,
                prefix=prefix,
            )
            if not (directory / file_name).exists():
                return file_name, current_sequence
            current_sequence += 1

    def stage_delete_file(self, directory: Path, file_name: str) -> Path | None:
        source = directory / file_name
        if not source.exists():
            return None
        trash_dir = directory / ".mpxccp-delete-staging"
        trash_dir.mkdir(exist_ok=True)
        staged = trash_dir / f"{uuid.uuid4().hex}-{file_name}"
        source.rename(staged)
        return staged

    def restore_staged_file(self, staged: Path, directory: Path, file_name: str) -> None:
        target = directory / file_name
        if staged.exists() and not target.exists():
            staged.rename(target)

    def finalize_staged_delete(self, staged: Path) -> None:
        if staged.exists():
            staged.unlink()
        try:
            staged.parent.rmdir()
        except OSError:
            pass

    def delete_file(self, directory: Path, file_name: str) -> bool:
        return self.delete_file_if_exists(directory / file_name)

    def delete_file_if_exists(self, path: Path) -> bool:
        if not path.exists():
            return False
        path.unlink()
        return True

    def renumber_files(self, directory: Path) -> dict[str, str]:
        if not directory.exists():
            return {}

        files = sorted(
            (path for path in directory.iterdir() if path.is_file()),
            key=lambda path: path.name,
        )
        if not files:
            return {}

        token = uuid.uuid4().hex
        temporary_paths: list[tuple[Path, Path, str]] = []
        for index, path in enumerate(files):
            temporary = directory / f".mpxccp-renumber-{token}-{index}.tmp"
            path.rename(temporary)
            temporary_paths.append((path, temporary, self._strip_number_prefix(path.name)))

        mapping: dict[str, str] = {}
        for index, (original, temporary, base_name) in enumerate(temporary_paths, start=1):
            final_name = f"{index}. {base_name}"
            temporary.rename(directory / final_name)
            mapping[original.name] = final_name

        return mapping

    def renumber_named_files(self, directory: Path, file_names: Iterable[str]) -> dict[str, str]:
        if not directory.exists():
            return {}

        selected_paths = [directory / name for name in file_names]
        selected_paths = [path for path in selected_paths if path.is_file()]
        if not selected_paths:
            return {}

        token = uuid.uuid4().hex
        temporary_paths: list[tuple[str, Path, str]] = []
        mapping: dict[str, str] = {}
        try:
            for index, path in enumerate(selected_paths):
                temporary = directory / f".mpxccp-renumber-selected-{token}-{index}.tmp"
                path.rename(temporary)
                temporary_paths.append((path.name, temporary, self._strip_number_prefix(path.name)))

            used_names = {path.name for path in directory.iterdir() if path.is_file()}
            for index, (original_name, temporary, base_name) in enumerate(
                temporary_paths,
                start=1,
            ):
                sequence = index
                final_name = f"{sequence}. {base_name}"
                while final_name in used_names:
                    sequence += 1
                    final_name = f"{sequence}. {base_name}"
                temporary.rename(directory / final_name)
                used_names.add(final_name)
                mapping[original_name] = final_name
        except Exception:
            self.restore_renumbered_files(directory, mapping)
            for original_name, temporary, _base_name in reversed(temporary_paths):
                original = directory / original_name
                if temporary.exists() and not original.exists():
                    temporary.rename(original)
            raise
        return mapping

    def restore_renumbered_files(self, directory: Path, mapping: dict[str, str]) -> None:
        for original_name, current_name in reversed(list(mapping.items())):
            current = directory / current_name
            original = directory / original_name
            if current.exists() and not original.exists():
                current.rename(original)

    def renumber_directory(self, directory: Path) -> dict[str, str]:
        return self.renumber_files(directory)

    def next_sequence(self, directory: Path) -> int:
        if not directory.exists():
            return 1
        return sum(1 for path in directory.iterdir() if path.is_file()) + 1

    def _sanitize_file_component(self, value: str, *, fallback: str) -> str:
        cleaned = ILLEGAL_WINDOWS_PATH_CHARS.sub("", value).strip().rstrip(". ")
        return cleaned or fallback

    def _strip_number_prefix(self, file_name: str) -> str:
        stripped = NUMBERED_FILE_PREFIX.sub("", file_name, count=1)
        return stripped or file_name