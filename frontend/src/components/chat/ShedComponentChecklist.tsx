"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";

import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { formatChecklistDimensions } from "@/lib/shed-checklist";
import { useProjectStore } from "@/store/project-store";
import type { ShedChecklistPayload, ShedChecklistSelections } from "@/types/chat";
import { TRUSS_TYPE_OPTIONS, type TrussType } from "@/types/shed-config";

const DEFAULT_SELECTIONS: ShedChecklistSelections = {
  use_bracing: false,
  use_gable_bracing: false,
  use_roof_bracing: false,
  use_truss: false,
  truss_type: "pratt",
  use_sag_rods: false,
  use_haunches: false,
  use_fly_braces: false,
  use_base_plates: false,
  use_bottom_chord_restraint: false,
  generate_wall_girts: true,
  generate_tie_beams: true,
};

type BooleanSelectionKey = {
  [K in keyof ShedChecklistSelections]: ShedChecklistSelections[K] extends boolean
    ? K
    : never;
}[keyof ShedChecklistSelections];

type ChecklistOption = {
  id: BooleanSelectionKey;
  label: string;
  description: string;
};

const OPTIONS: ChecklistOption[] = [
  {
    id: "use_bracing",
    label: "Side Wall X-Bracing",
    description: "Diagonal cross bracing on the two long side walls.",
  },
  {
    id: "use_gable_bracing",
    label: "End Wall X-Bracing",
    description: "Diagonal cross bracing on the two gable end walls.",
  },
  {
    id: "use_roof_bracing",
    label: "Roof Plane X-Bracing",
    description: "Diagonal bracing across the roof slopes (end bays).",
  },
  {
    id: "generate_wall_girts",
    label: "Wall Cladding Framework (Girts)",
    description: "Horizontal members for cladding support along the walls.",
  },
  {
    id: "generate_tie_beams",
    label: "Longitudinal Tie Struts",
    description: "Ties portal frames together along the building length.",
  },
  {
    id: "use_sag_rods",
    label: "Anti-Sag Tension Rods",
    description: "Mid-bay ties to stabilize purlins against sag.",
  },
  {
    id: "use_haunches",
    label: "Eave & Apex Haunches",
    description: "Tapered knee/apex haunches on rafter (portal) frames.",
  },
  {
    id: "use_fly_braces",
    label: "Fly / Flange Braces",
    description: "Small stays restraining the rafter inner flange.",
  },
  {
    id: "use_base_plates",
    label: "Column Base Plates",
    description: "Steel base plates under every column foot (clean IFC).",
  },
  {
    id: "use_bottom_chord_restraint",
    label: "Truss Bottom-Chord Restraint",
    description: "Longitudinal runners tying truss bottom chords (trusses only).",
  },
  {
    id: "use_truss",
    label: "Heavy-Duty Roof Truss",
    description: "Trussed roof frames instead of solid IPE rafters.",
  },
];

type ShedComponentChecklistProps = {
  payload: ShedChecklistPayload;
};

export function ShedComponentChecklist({ payload }: ShedComponentChecklistProps) {
  const confirmShedChecklist = useProjectStore((s) => s.confirmShedChecklist);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const [selections, setSelections] =
    useState<ShedChecklistSelections>(DEFAULT_SELECTIONS);
  const [error, setError] = useState<string | null>(null);

  const setOption =
    (key: BooleanSelectionKey) => (checked: boolean) =>
      setSelections((prev) => ({ ...prev, [key]: checked }));

  const handleConfirm = async () => {
    setError(null);
    try {
      await confirmShedChecklist(payload, selections);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate structure.",
      );
    }
  };

  return (
    <div className="mt-3 w-full max-w-md rounded-xl border border-border/80 bg-muted/30 p-4 shadow-sm">
      <div className="mb-3 border-b border-border/60 pb-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-primary">
          Portal frame configuration
        </p>
        <p className="mt-1 font-mono text-[11px] text-muted-foreground">
          {formatChecklistDimensions(payload)}
        </p>
      </div>

      <p className="mb-2 text-xs text-muted-foreground">
        Select secondary steel to include in your structural system:
      </p>

      <ul className="flex flex-col gap-2">
        {OPTIONS.map((opt) => (
          <li
            key={opt.id}
            className="flex items-start justify-between gap-3 rounded-lg border border-border/50 bg-background/60 px-3 py-2.5"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium leading-snug text-foreground">
                {opt.label}
              </p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                {opt.description}
              </p>
            </div>
            <Switch
              id={`checklist-${opt.id}`}
              checked={Boolean(selections[opt.id])}
              disabled={isMacroLoading}
              onCheckedChange={setOption(opt.id)}
              className="mt-0.5 shrink-0"
            />
          </li>
        ))}
      </ul>

      {selections.use_truss ? (
        <div className="mt-2 flex items-center justify-between gap-3 rounded-lg border border-border/50 bg-background/60 px-3 py-2.5">
          <label
            htmlFor="checklist-truss-type"
            className="text-sm font-medium text-foreground"
          >
            Truss Pattern
          </label>
          <select
            id="checklist-truss-type"
            value={selections.truss_type}
            disabled={isMacroLoading}
            onChange={(e) =>
              setSelections((prev) => ({
                ...prev,
                truss_type: e.target.value as Exclude<TrussType, "none">,
              }))
            }
            className="h-8 rounded-md border border-border/60 bg-background px-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {TRUSS_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <Button
        type="button"
        className="mt-4 w-full bg-blue-600 font-medium text-white hover:bg-blue-700"
        disabled={isMacroLoading}
        onClick={() => void handleConfirm()}
      >
        {isMacroLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating structure…
          </>
        ) : (
          "Confirm & Generate Structure"
        )}
      </Button>

      {error ? (
        <p className="mt-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
