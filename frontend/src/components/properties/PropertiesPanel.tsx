"use client";

import { RotateCw, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  useProjectStore,
  useSelectedElement,
} from "@/store/project-store";
import type { ElementAlignment, ElementRotation } from "@/types/project";

const ROTATIONS: ElementRotation[] = [0, 90, 180, 270];
const ALIGNMENTS: ElementAlignment[] = ["top", "center", "bottom"];

export function PropertiesPanel() {
  const selected = useSelectedElement();
  const clearSelection = useProjectStore((state) => state.clearSelection);
  const updateElementRotation = useProjectStore(
    (state) => state.updateElementRotation,
  );
  const updateElementAlignment = useProjectStore(
    (state) => state.updateElementAlignment,
  );

  if (!selected) return null;

  return (
    <aside className="pointer-events-auto absolute right-3 top-12 z-20 w-[min(100%,18rem)]">
      <Card className="border-border/80 bg-background/95 shadow-lg backdrop-blur-md">
        <div className="flex items-start justify-between gap-2 p-4 pb-2">
          <div className="min-w-0 space-y-1">
            <h2 className="text-sm font-semibold tracking-tight">Properties</h2>
            <p className="truncate font-mono text-xs text-muted-foreground">
              {selected.id}
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={clearSelection}
            aria-label="Close properties panel"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <CardContent className="space-y-4 pb-4">
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="secondary">{selected.shape_type}</Badge>
            {selected.profile_name && (
              <Badge variant="outline">{selected.profile_name}</Badge>
            )}
            <Badge variant="outline">axis {selected.axis ?? "y"}</Badge>
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
              Shifts the profile mesh relative to its structural axis line.
              The axis path stays fixed — only the cross-section placement
              changes. No AI call.
            </p>
          </div>
        </CardContent>
      </Card>
    </aside>
  );
}
