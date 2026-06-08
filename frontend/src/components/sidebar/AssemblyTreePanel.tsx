"use client";

import { ChevronDown, ChevronRight, Layers } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { assemblyEntityIds } from "@/lib/assembly-highlight";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/store/project-store";
import type { StructuralAssembly } from "@/types/ifc-topology";

const TYPE_ORDER: Record<string, number> = {
  BUILDING: 0,
  PORTAL: 1,
  TRUSS: 2,
  ROOF: 3,
  WALL_SIDE: 4,
  WALL_GABLE: 5,
  LONGITUDINAL: 6,
  BRACING: 7,
  MEMBER: 99,
};

/** Hide per-member singleton buckets from the tree. */
function isTreeAssembly(assembly: StructuralAssembly): boolean {
  return assembly.assembly_type !== "MEMBER" && assembly.entity_ids.length > 1;
}

function sortAssemblies(
  assemblies: Record<string, StructuralAssembly>,
): StructuralAssembly[] {
  return Object.values(assemblies).sort((a, b) => {
    const ta = TYPE_ORDER[a.assembly_type] ?? 99;
    const tb = TYPE_ORDER[b.assembly_type] ?? 99;
    if (ta !== tb) return ta - tb;
    return a.label.localeCompare(b.label);
  });
}

function AssemblyTreeNode({
  assembly,
  depth,
  assemblies,
  selectedAssemblyId,
  onSelectAssembly,
}: {
  assembly: StructuralAssembly;
  depth: number;
  assemblies: Record<string, StructuralAssembly>;
  selectedAssemblyId: string | null;
  onSelectAssembly: (assemblyId: string) => void;
}) {
  const [open, setOpen] = useState(depth < 2);
  const children = Object.values(assemblies).filter(
    (a) => a.parent_id === assembly.id && isTreeAssembly(a),
  );
  if (!isTreeAssembly(assembly) && depth > 0) {
    return null;
  }
  const isSelected = selectedAssemblyId === assembly.id;

  return (
    <div>
      <Button
        type="button"
        variant="ghost"
        className={cn(
          "h-7 w-full justify-start gap-1 px-1 font-normal",
          isSelected && "bg-muted",
        )}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
        onClick={() => onSelectAssembly(assembly.id)}
      >
        {children.length > 0 ? (
          <span
            className="inline-flex shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              setOpen((v) => !v);
            }}
            onKeyDown={() => undefined}
            role="presentation"
          >
            {open ? (
              <ChevronDown className="size-3.5 opacity-60" />
            ) : (
              <ChevronRight className="size-3.5 opacity-60" />
            )}
          </span>
        ) : (
          <span className="inline-block w-3.5 shrink-0" />
        )}
        <span className="truncate text-xs">{assembly.label}</span>
        <span className="ml-auto font-mono text-[10px] text-muted-foreground">
          {assembly.entity_ids.length}
        </span>
      </Button>
      {open &&
        children.map((child) => (
          <AssemblyTreeNode
            key={child.id}
            assembly={child}
            depth={depth + 1}
            assemblies={assemblies}
            selectedAssemblyId={selectedAssemblyId}
            onSelectAssembly={onSelectAssembly}
          />
        ))}
    </div>
  );
}

export function AssemblyTreePanel() {
  const topology = useProjectStore((s) => s.structuralTopology);
  const selectedElementId = useProjectStore((s) => s.selectedElementId);
  const selectAssembly = useProjectStore((s) => s.selectAssembly);

  const roots = useMemo(() => {
    if (!topology) return [];
    return sortAssemblies(topology.assemblies).filter(
      (a) => !a.parent_id && isTreeAssembly(a),
    );
  }, [topology]);

  const selectedAssemblyId = useMemo(() => {
    if (!topology || !selectedElementId) return null;
    const entity = topology.entities.find((e) => e.id === selectedElementId);
    return entity?.primary_assembly_id ?? null;
  }, [topology, selectedElementId]);

  if (!topology || roots.length === 0) {
    return null;
  }

  return (
    <section className="rounded-lg border border-border/80 bg-muted/15 p-3">
      <header className="mb-2 flex items-center gap-2">
        <Layers className="size-3.5 text-muted-foreground" />
        <h3 className="text-sm font-semibold tracking-tight">Assemblies</h3>
      </header>
      <p className="mb-2 text-[11px] text-muted-foreground">
        Browse assembly groups. Selection in the viewport highlights one member at
        a time; metadata is kept per element for IFC export.
      </p>
      <div className="max-h-48 overflow-y-auto rounded-md border border-border/50 bg-background/50">
        {roots.map((root) => (
          <AssemblyTreeNode
            key={root.id}
            assembly={root}
            depth={0}
            assemblies={topology.assemblies}
            selectedAssemblyId={selectedAssemblyId}
            onSelectAssembly={(assemblyId) => {
              const ids = assemblyEntityIds(topology, assemblyId);
              selectAssembly(assemblyId, ids[0] ?? null);
            }}
          />
        ))}
      </div>
    </section>
  );
}
