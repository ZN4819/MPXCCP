from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mpxccp.models.knowledge import KnowledgeEntry


class KnowledgeRepository:
    def list_entries(
        self,
        session: Session,
        *,
        entry_type: str,
        modules: Iterable[str] | None = None,
        text_filter: str = "",
    ) -> list[KnowledgeEntry]:
        statement = select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == entry_type,
            KnowledgeEntry.is_enabled.is_(True),
        )
        module_values = list(modules or [])
        if module_values:
            statement = statement.where(KnowledgeEntry.module.in_(module_values))
        if text_filter:
            statement = statement.where(KnowledgeEntry.content.contains(text_filter))
        return list(
            session.scalars(statement.order_by(KnowledgeEntry.sort_order, KnowledgeEntry.id))
        )

    def list_all_entries(self, session: Session) -> list[KnowledgeEntry]:
        return list(
            session.scalars(
                select(KnowledgeEntry)
                .where(KnowledgeEntry.is_enabled.is_(True))
                .order_by(
                    KnowledgeEntry.entry_type,
                    KnowledgeEntry.module,
                    KnowledgeEntry.sort_order,
                    KnowledgeEntry.id,
                )
            )
        )

    def find_duplicate(
        self,
        session: Session,
        *,
        entry_type: str,
        module: str,
        content: str,
    ) -> KnowledgeEntry | None:
        return session.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.entry_type == entry_type,
                KnowledgeEntry.module == module,
                KnowledgeEntry.content == content,
                KnowledgeEntry.is_enabled.is_(True),
            )
        )

    def add_entry(
        self,
        session: Session,
        *,
        entry_type: str,
        module: str,
        content: str,
        title: str = "",
        risk_level: str = "",
        tags: str = "",
        sort_order: int = 0,
    ) -> KnowledgeEntry:
        entry = KnowledgeEntry(
            entry_type=entry_type,
            module=module,
            title=title or content[:60],
            content=content,
            risk_level=risk_level,
            tags=tags,
            sort_order=sort_order,
        )
        session.add(entry)
        session.flush()
        return entry

    def delete_entries(self, session: Session, ids: Iterable[int]) -> int:
        id_list = list(ids)
        if not id_list:
            return 0
        result = session.execute(delete(KnowledgeEntry).where(KnowledgeEntry.id.in_(id_list)))
        return int(result.rowcount or 0)

    def delete_all(self, session: Session) -> int:
        result = session.execute(delete(KnowledgeEntry))
        return int(result.rowcount or 0)
