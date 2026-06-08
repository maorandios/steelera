import type { StructuralTopology } from "@/types/ifc-topology";
import type { ProjectElementMm } from "@/types/project";

/** Entity ids to highlight when the user selects one member. */
export function highlightedElementIds(
  selectedElementId: string | null,
  topology: StructuralTopology | null,
  elements: ProjectElementMm[],
): Set<string> {
  if (!selectedElementId) {
    return new Set();
  }

  if (topology) {
    const entity = topology.entities.find((e) => e.id === selectedElementId);
    if (entity) {
      const assembly = topology.assemblies[entity.primary_assembly_id];
      if (assembly?.entity_ids.length) {
        return new Set(assembly.entity_ids);
      }
    }
  }

  const selected = elements.find((e) => e.id === selectedElementId);
  if (selected?.primary_assembly_id) {
    if (topology?.assemblies[selected.primary_assembly_id]) {
      return new Set(topology.assemblies[selected.primary_assembly_id].entity_ids);
    }
    const peers = elements.filter(
      (e) => e.primary_assembly_id === selected.primary_assembly_id,
    );
    if (peers.length > 0) {
      return new Set(peers.map((e) => e.id));
    }
  }

  return new Set([selectedElementId]);
}

export function assemblyEntityIds(
  topology: StructuralTopology,
  assemblyId: string,
): string[] {
  return topology.assemblies[assemblyId]?.entity_ids ?? [];
}
