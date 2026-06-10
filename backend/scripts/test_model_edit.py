"""Smoke tests for surgical model edits."""

from core.geometry_engine import macro_members_to_project_elements
from core.member_resolver import member_from_grid_nodes
from core.model_edit import (
    collect_snap_nodes,
    delete_members,
    place_brace_leg,
    update_member_profiles,
)
from schemas.spatial_grid import GridNodeReference, StructuralMember


def _brace_macro(eid: str, start, end):
    dummy = GridNodeReference(x_axis="A", z_axis="1", elevation="ground")
    member = StructuralMember(
        id=eid,
        element_type="bracing",
        profile="L70x70x7",
        start_node=dummy,
        end_node=dummy,
    )
    macro = member_from_grid_nodes(
        member,
        assembly_id="shed_1",
        start=start,
        end=end,
        grid=None,
    )
    assert macro is not None
    return macro


def test_update_profile_and_place():
    macros = [
        _brace_macro("shed_1-brace-roof-b1-a", (0, 8000, 0), (6000, 8000, 5714)),
        _brace_macro("shed_1-brace-roof-b1-b", (0, 8000, 5714), (6000, 8000, 0)),
    ]
    elements = macro_members_to_project_elements(macros)
    updated, changed = update_member_profiles(
        elements,
        profile="L100x100x10",
        reference_element_id="shed_1-brace-roof-b1-a",
        scope="group",
    )
    assert len(changed) == 2
    assert all(e.profile_name == "L100x100x10" for e in updated if e.id in changed)

    with_new, created = place_brace_leg(
        updated,
        start_mm=(12000, 6000, 5714),
        end_mm=(12000, 6000, 11428),
        profile="L70x70x7",
    )
    assert len(created) == 1
    assert len(with_new) == len(updated) + 1

    nodes = collect_snap_nodes(with_new)
    assert len(nodes) >= 4

    remaining, deleted = delete_members(
        with_new,
        reference_element_id="shed_1-brace-roof-b1-a",
        scope="pair",
    )
    assert len(deleted) == 2
    assert len(remaining) == len(with_new) - 2
    print("test_model_edit OK")


if __name__ == "__main__":
    test_update_profile_and_place()
