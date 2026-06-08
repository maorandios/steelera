"use client";

import { ArrowUpDown, Building2, Layers } from "lucide-react";
import { useEffect, useState } from "react";

import { AssemblyTreePanel } from "@/components/sidebar/AssemblyTreePanel";
import { ShedMacroFields, type ShedFormValues } from "@/components/sidebar/ShedMacroFields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  DEFAULT_SHED_PARAMS,
  mergeShedParams,
  parseBaySpansMm,
  parseShedFormValues,
  shedParamsToFormStrings,
  totalFromSpans,
} from "@/lib/shed-assembly";
import { assemblyParamsToShedConfig } from "@/lib/shed-config";
import { buildStructuralGridState } from "@/lib/structural-grid";
import { useProjectStore } from "@/store/project-store";

const OTHER_MACROS = [
  { id: "mezzanine", label: "Generate Mezzanine Floor", icon: Layers },
  { id: "staircase", label: "Generate Staircase", icon: ArrowUpDown },
] as const;

export function ProjectPresetsPanel() {
  const [shedForm, setShedForm] = useState<ShedFormValues>(
    shedParamsToFormStrings(DEFAULT_SHED_PARAMS),
  );
  const [shedError, setShedError] = useState<string | null>(null);

  const generateShedMacro = useProjectStore((s) => s.generateShedMacro);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);
  const shedAssemblyParams = useProjectStore((s) => s.shedAssemblyParams);
  const structuralGrid = useProjectStore((s) => s.structuralGrid);
  const setStructuralGrid = useProjectStore((s) => s.setStructuralGridFromSpans);

  useEffect(() => {
    if (shedAssemblyParams) {
      setShedForm(shedParamsToFormStrings(shedAssemblyParams));
    }
  }, [shedAssemblyParams]);

  useEffect(() => {
    const x = parseBaySpansMm(shedForm.xSpans);
    const z = parseBaySpansMm(shedForm.zSpans);
    if (x && z) {
      setStructuralGrid(shedForm.xSpans, shedForm.zSpans);
    }
  }, [shedForm.xSpans, shedForm.zSpans, setStructuralGrid]);

  const handleGenerateShed = async () => {
    const parsed = parseShedFormValues(shedForm);
    if ("error" in parsed) {
      setShedError(parsed.error);
      return;
    }
    setShedError(null);
    try {
      const merged = mergeShedParams(
        shedAssemblyParams ?? DEFAULT_SHED_PARAMS,
        parsed.params,
      );
      await generateShedMacro(assemblyParamsToShedConfig(merged));
    } catch (err) {
      setShedError(
        err instanceof Error ? err.message : "Shed generation failed.",
      );
    }
  };

  const xSpans = parseBaySpansMm(shedForm.xSpans);
  const zSpans = parseBaySpansMm(shedForm.zSpans);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-sm font-semibold tracking-tight">
          Portal frame shed
        </h3>
        <p className="mt-1 text-xs text-muted-foreground">
          X and Z spans define portal frames, columns, and the CAD grid.
        </p>
      </div>

      <ShedMacroFields
        values={shedForm}
        onChange={setShedForm}
        onSubmit={() => void handleGenerateShed()}
        submitLabel="Generate Portal Frame Shed"
        loading={isMacroLoading}
        error={shedError}
      />

      <AssemblyTreePanel />

      {xSpans && zSpans ? (
        <p className="font-mono text-[10px] text-muted-foreground">
          Total width {totalFromSpans(xSpans).toLocaleString()} mm · depth{" "}
          {totalFromSpans(zSpans).toLocaleString()} mm
        </p>
      ) : null}

      <Separator />

      <div>
        <h3 className="text-sm font-semibold tracking-tight">Grid configuration</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Mirrors X and Z spans (read-only). Letters on X lines, numbers on Z
          lines.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="grid-x-spacing">X spacing (mm)</Label>
          <Input
            id="grid-x-spacing"
            type="text"
            readOnly
            tabIndex={-1}
            value={shedForm.xSpans}
            className="h-9 cursor-default font-mono text-xs opacity-90"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="grid-z-spacing">Z spacing (mm)</Label>
          <Input
            id="grid-z-spacing"
            type="text"
            readOnly
            tabIndex={-1}
            value={shedForm.zSpans}
            className="h-9 cursor-default font-mono text-xs opacity-90"
          />
        </div>
        <p className="font-mono text-[10px] text-muted-foreground">
          X: [{structuralGrid.xCoordsMm.join(", ")}] mm · Z: [
          {structuralGrid.zCoordsMm.join(", ")}] mm
        </p>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold tracking-tight">Other macros</h3>
        <p className="mt-1 text-xs text-muted-foreground">Coming soon.</p>
      </div>

      <div className="flex flex-col gap-2">
        {OTHER_MACROS.map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            type="button"
            variant="outline"
            className="h-auto min-h-10 justify-start gap-2 px-3 py-2.5 text-left text-xs leading-snug"
            disabled
          >
            <Icon className="h-4 w-4 shrink-0 opacity-70" />
            <span>{label}</span>
          </Button>
        ))}
      </div>
    </div>
  );
}
