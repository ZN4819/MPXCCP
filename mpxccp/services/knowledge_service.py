from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine

from mpxccp.domain.enums import KnowledgeModule
from mpxccp.models.knowledge import KnowledgeEntry
from mpxccp.repositories.knowledge_repo import KnowledgeRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.services.result import ServiceResult

DEFAULT_VISIBLE_MODULES = {
    KnowledgeModule.COMMON.value,
    KnowledgeModule.OTHER.value,
}


@dataclass(frozen=True)
class KnowledgeRecord:
    id: int
    entry_type: str
    module: str
    title: str
    content: str
    risk_level: str
    tags: str
    sort_order: int


class KnowledgeService:
    def __init__(
        self,
        engine: Engine,
        knowledge_repo: KnowledgeRepository | None = None,
    ) -> None:
        self.engine = engine
        self.knowledge_repo = knowledge_repo or KnowledgeRepository()

    def list_entries(
        self,
        type: str,
        module: str,
        show_all: bool = False,
        text_filter: str = "",
    ) -> list[KnowledgeRecord]:
        modules = None if show_all else {module, *DEFAULT_VISIBLE_MODULES}
        with readonly_session_scope(self.engine) as session:
            return [
                self._record_payload(item)
                for item in self.knowledge_repo.list_entries(
                    session,
                    entry_type=type,
                    modules=modules,
                    text_filter=text_filter.strip(),
                )
            ]

    def add_entry(self, type: str, module: str, content: str) -> ServiceResult:
        cleaned = self._text(content)
        if not cleaned:
            return ServiceResult(
                success=False,
                message="knowledge content is empty",
                warnings=["empty_content"],
            )
        with session_scope(self.engine) as session:
            entry = self.knowledge_repo.add_entry(
                session,
                entry_type=self._text(type),
                module=self._text(module),
                content=cleaned,
                sort_order=self._next_sort_order(session, type),
            )
            return ServiceResult(
                success=True,
                message="knowledge entry added",
                payload={"entry_id": entry.id},
            )

    def update_entry(self, id: int, content: str, module: str) -> ServiceResult:
        cleaned = self._text(content)
        if not cleaned:
            return ServiceResult(
                success=False,
                message="knowledge content is empty",
                warnings=["empty_content"],
            )
        with session_scope(self.engine) as session:
            entry = session.get(KnowledgeEntry, id)
            if entry is None:
                return ServiceResult(
                    success=False,
                    message="knowledge entry not found",
                    warnings=["entry_not_found"],
                )
            entry.content = cleaned
            entry.title = cleaned[:60]
            entry.module = self._text(module)
            return ServiceResult(success=True, message="knowledge entry updated")

    def delete_entries(self, ids: list[int]) -> ServiceResult:
        with session_scope(self.engine) as session:
            deleted = self.knowledge_repo.delete_entries(session, ids)
            return ServiceResult(
                success=True,
                message="knowledge entries deleted",
                payload={"deleted": deleted},
            )

    def dedupe_append(self, entries: list[dict[str, Any]]) -> ServiceResult:
        added = 0
        skipped = 0
        with session_scope(self.engine) as session:
            for values in entries:
                entry_type = self._text(values.get("type", values.get("entry_type", "")))
                module = self._text(values.get("module", ""))
                content = self._text(values.get("content", ""))
                if not entry_type or not module or not content:
                    skipped += 1
                    continue
                duplicate = self.knowledge_repo.find_duplicate(
                    session,
                    entry_type=entry_type,
                    module=module,
                    content=content,
                )
                if duplicate is not None:
                    skipped += 1
                    continue
                self.knowledge_repo.add_entry(
                    session,
                    entry_type=entry_type,
                    module=module,
                    content=content,
                    sort_order=self._next_sort_order(session, entry_type),
                )
                added += 1
            return ServiceResult(
                success=True,
                message="knowledge entries appended",
                payload={"added": added, "skipped": skipped},
            )

    def replace_all(self, entries: list[dict[str, Any]]) -> ServiceResult:
        cleaned_entries = self._clean_entries(entries)
        if not cleaned_entries:
            return ServiceResult(
                success=False,
                message="no valid knowledge entries to replace",
                warnings=["no_valid_entries"],
                payload={"deleted": 0, "added": 0},
            )
        with session_scope(self.engine) as session:
            deleted = self.knowledge_repo.delete_all(session)
            for sort_order, values in enumerate(cleaned_entries):
                self.knowledge_repo.add_entry(
                    session,
                    entry_type=values["entry_type"],
                    module=values["module"],
                    content=values["content"],
                    sort_order=sort_order,
                )
            return ServiceResult(
                success=True,
                message="knowledge entries replaced",
                payload={"deleted": deleted, "added": len(cleaned_entries)},
            )

    def _clean_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
        cleaned_entries: list[dict[str, str]] = []
        for values in entries:
            entry_type = self._text(values.get("type", values.get("entry_type", "")))
            module = self._text(values.get("module", ""))
            content = self._text(values.get("content", ""))
            if not entry_type or not module or not content:
                continue
            cleaned_entries.append(
                {
                    "entry_type": entry_type,
                    "module": module,
                    "content": content,
                }
            )
        return cleaned_entries

    def _next_sort_order(self, session, entry_type: str) -> int:
        entries = self.knowledge_repo.list_entries(
            session,
            entry_type=entry_type,
            modules=None,
        )
        return len(entries)

    def _text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()

    def _record_payload(self, entry: KnowledgeEntry) -> KnowledgeRecord:
        return KnowledgeRecord(
            id=entry.id,
            entry_type=entry.entry_type,
            module=entry.module,
            title=entry.title,
            content=entry.content,
            risk_level=entry.risk_level,
            tags=entry.tags,
            sort_order=entry.sort_order,
        )