import { SHED_ASSEMBLY_ID } from "@/lib/shed-assembly";
import type { GridDefinition, StructuralGridLayout } from "@/types/spatial-grid";

export function gridDefinitionToLayout(
  gridDefinition: GridDefinition,
): StructuralGridLayout {
  return {
    assembly_id: SHED_ASSEMBLY_ID,
    replace_existing: true,
    grid_definition: gridDefinition,
    structural_members: [],
  };
}
