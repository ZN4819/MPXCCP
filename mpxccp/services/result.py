from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ServiceResult:
    success: bool
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    project_id: int | None = None
    payload: dict[str, object] = field(default_factory=dict)
