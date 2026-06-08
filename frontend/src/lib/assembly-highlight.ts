import type { StructuralTopology } from "@/types/ifc-topology";

/** Reserved for phase-2 bulk edit: all entity ids sharing a profile/role. */
export function assemblyEntityIds(
  topology: StructuralTopology,
  assemblyId: string,
): string[] {
  return topology.assemblies[assemblyId]?.entity_ids ?? [];
}
