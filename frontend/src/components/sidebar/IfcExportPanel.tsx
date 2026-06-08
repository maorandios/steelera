"use client";

import { Download, Loader2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  downloadBlob,
  postExportIfc,
  type IfcSchemaVersion,
} from "@/lib/api";
import { SHED_ASSEMBLY_ID } from "@/lib/shed-assembly";
import { useProjectStore } from "@/store/project-store";

const SCHEMA_OPTIONS: { value: IfcSchemaVersion; label: string }[] = [
  { value: "IFC4", label: "IFC4 (recommended)" },
  { value: "IFC2X3", label: "IFC2X3" },
];

export function IfcExportPanel() {
  const structuralTopology = useProjectStore((s) => s.structuralTopology);
  const projectElements = useProjectStore((s) => s.projectElements);

  const [schema, setSchema] = useState<IfcSchemaVersion>("IFC4");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasTopology =
    structuralTopology != null &&
    (structuralTopology.entities?.length ?? 0) > 0;
  const hasModel = projectElements.length > 0;

  const handleDownload = async () => {
    if (!structuralTopology) {
      setError("No structural topology. Generate a shed first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const buildingId = structuralTopology.building_id || SHED_ASSEMBLY_ID;
      const filename = `${buildingId}.ifc`;
      const blob = await postExportIfc(structuralTopology, schema, filename);
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "IFC export failed.");
    } finally {
      setLoading(false);
    }
  };

  if (!hasModel) {
    return null;
  }

  return (
    <section className="rounded-lg border border-border/80 bg-muted/15 p-3">
      <header className="mb-2 flex items-center gap-2">
        <Download className="size-3.5 text-muted-foreground" />
        <h3 className="text-sm font-semibold tracking-tight">Export IFC</h3>
      </header>
      <p className="mb-3 text-[11px] text-muted-foreground">
        Download a BIM-ready IFC file from the current structural topology
        (nodes, members, profiles, assemblies).
      </p>

      <div className="mb-3 space-y-1.5">
        <Label htmlFor="ifc-schema" className="text-xs">
          Schema
        </Label>
        <select
          id="ifc-schema"
          className="flex h-9 w-full rounded-md border border-input bg-background px-2.5 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={schema}
          disabled={loading}
          onChange={(e) => setSchema(e.target.value as IfcSchemaVersion)}
        >
          {SCHEMA_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <Button
        type="button"
        variant="outline"
        className="w-full gap-2 text-xs"
        disabled={!hasTopology || loading}
        onClick={() => void handleDownload()}
      >
        {loading ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <Download className="size-3.5" />
        )}
        {loading ? "Exporting…" : "Download IFC"}
      </Button>

      {!hasTopology ? (
        <p className="mt-2 text-[11px] text-amber-600 dark:text-amber-500">
          Regenerate the shed to refresh topology data before exporting.
        </p>
      ) : null}

      {error ? (
        <p className="mt-2 text-[11px] text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
