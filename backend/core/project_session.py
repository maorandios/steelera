"""In-memory project element store for macro endpoints (single-process dev session)."""

from schemas.elements import ProjectElementMm
from schemas.project import ProjectState

_session = ProjectState()
_shed_params_by_assembly: dict[str, dict[str, float]] = {}


def get_state() -> ProjectState:
    return _session.model_copy(deep=True)


def get_elements() -> list[ProjectElementMm]:
    return list(_session.projectElements)


def set_elements(elements: list[ProjectElementMm]) -> None:
    global _session
    _session = ProjectState(projectElements=list(elements))


def merge_assembly(
    assembly_id: str,
    new_members: list[ProjectElementMm],
    *,
    replace_existing: bool,
) -> list[ProjectElementMm]:
    """Append macro members; optionally drop prior members in the same assembly."""
    global _session
    kept = list(_session.projectElements)
    if replace_existing:
        kept = [element for element in kept if element.assembly_id != assembly_id]
    merged = kept + new_members
    _session = ProjectState(projectElements=merged)
    return list(_session.projectElements)


def get_shed_params(assembly_id: str) -> dict[str, float] | None:
    stored = _shed_params_by_assembly.get(assembly_id)
    return dict(stored) if stored else None


def set_shed_params(assembly_id: str, params: dict[str, float]) -> None:
    _shed_params_by_assembly[assembly_id] = dict(params)
