"use client";

import { MousePointerClick, RotateCw } from "lucide-react";

import { AssemblyShedInspector } from "@/components/sidebar/AssemblyShedInspector";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { isShedAssemblyMember } from "@/lib/shed-assembly";
import {
  useProjectStore,
  useSelectedElement,
} from "@/store/project-store";
import type { ElementAlignment, ElementRotation } from "@/types/project";

const ROTATIONS: ElementRotation[] = [0, 90, 180, 270];
const ALIGNMENTS: ElementAlignment[] = ["top", "center", "bottom"];

const PROFILE_OPTIONS = [
  "UB 305×165×40",
  "UB 254×146×31",
  "UC 203×203×46",
  "PFC 200×75×23",
  "RHS 150×100×6",
] as const;

export function ElementPropertiesPanel() {
  const selected = useSelectedElement();
  const updateElementRotation = useProjectStore(
    (state) => state.updateElementRotation,
  );
  const updateElementAlignment = useProjectStore(
    (state) => state.updateElementAlignment,
  );

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border/80 bg-muted/20 px-4 py-10 text-center">
        <MousePointerClick className="h-8 w-8 text-muted-foreground/60" />
        <p className="text-sm text-muted-foreground">
          Click an element in the viewport to inspect.
        </p>
      </div>
    );
  }

  const showShedInspector = isShedAssemblyMember(selected);

  return (
    <div className="flex flex-col gap-4">
      {showShedInspector ? <AssemblyShedInspector /> : null}

      {showShedInspector ? <Separator /> : null}

      <div className="space-y-1">
        <p className="truncate font-mono text-xs text-muted-foreground">
          {selected.id}
        </p>
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="secondary">{selected.shape_type}</Badge>
          {selected.assembly_id ? (
            <Badge variant="outline">{selected.assembly_id}</Badge>
          ) : null}
          {selected.primary_assembly_id ? (
            <Badge variant="outline">{selected.primary_assembly_id}</Badge>
          ) : null}
          <Badge variant="outline">axis {selected.axis ?? "y"}</Badge>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="element-profile">Profile</Label>
        <select
          id="element-profile"
          className="flex h-9 w-full rounded-md border border-input bg-background px-2.5 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={selected.profile_name ?? ""}
          onChange={() => {}}
          disabled
          aria-label="Steel profile (placeholder)"
        >
          <option value="">
            {selected.profile_name ?? "Select profile…"}
          </option>
          {PROFILE_OPTIONS.map((profile) => (
            <option key={profile} value={profile}>
              {profile}
            </option>
          ))}
        </select>
        <p className="text-[11px] text-muted-foreground">
          Catalog assignment via AI chat for now.
        </p>
      </div>

      <Separator />

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <RotateCw className="h-3.5 w-3.5" />
          Rotation (axis)
        </div>
        <div className="grid grid-cols-4 gap-1.5">
          {ROTATIONS.map((rotation) => (
            <Button
              key={rotation}
              type="button"
              size="sm"
              variant={
                (selected.rotation ?? 0) === rotation ? "default" : "outline"
              }
              onClick={() => updateElementRotation(selected.id, rotation)}
            >
              {rotation}°
            </Button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Alignment
        </p>
        <div className="grid grid-cols-3 gap-1.5">
          {ALIGNMENTS.map((alignment) => (
            <Button
              key={alignment}
              type="button"
              size="sm"
              variant={
                (selected.alignment ?? "center") === alignment
                  ? "default"
                  : "outline"
              }
              className="capitalize"
              onClick={() => updateElementAlignment(selected.id, alignment)}
            >
              {alignment}
            </Button>
          ))}
        </div>
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          Shifts the profile mesh on its local axis. No AI call.
        </p>
      </div>
    </div>
  );
}
