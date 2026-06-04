"use client";

import { useEffect, useState } from "react";

import { ShedMacroFields, type ShedFormValues } from "@/components/sidebar/ShedMacroFields";
import {
  DEFAULT_SHED_PARAMS,
  SHED_ASSEMBLY_ID,
  SHED_ASSEMBLY_LABEL,
  parseShedFormValues,
  shedParamsToFormStrings,
} from "@/lib/shed-assembly";
import { useProjectStore } from "@/store/project-store";

export function AssemblyShedInspector() {
  const shedAssemblyParams = useProjectStore((s) => s.shedAssemblyParams);
  const generateShedMacro = useProjectStore((s) => s.generateShedMacro);
  const isMacroLoading = useProjectStore((s) => s.isMacroLoading);

  const [form, setForm] = useState<ShedFormValues>(
    shedParamsToFormStrings(shedAssemblyParams ?? DEFAULT_SHED_PARAMS),
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (shedAssemblyParams) {
      setForm(shedParamsToFormStrings(shedAssemblyParams));
    }
  }, [shedAssemblyParams]);

  const handleUpdate = async () => {
    const parsed = parseShedFormValues(form);
    if ("error" in parsed) {
      setError(parsed.error);
      return;
    }
    setError(null);
    try {
      await generateShedMacro(parsed.params);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update assembly.",
      );
    }
  };

  return (
    <section className="rounded-lg border border-border/80 bg-muted/15 p-3">
      <header className="mb-3 space-y-0.5">
        <h3 className="text-sm font-semibold tracking-tight text-foreground">
          Assembly Inspector: {SHED_ASSEMBLY_LABEL}
        </h3>
        <p className="font-mono text-[11px] text-muted-foreground">
          ({SHED_ASSEMBLY_ID})
        </p>
        <p className="text-xs text-muted-foreground">
          Edit parameters and regenerate the full shed from any member.
        </p>
      </header>

      <ShedMacroFields
        values={form}
        onChange={setForm}
        onSubmit={() => void handleUpdate()}
        submitLabel="Update Assembly"
        loading={isMacroLoading}
        error={error}
      />
    </section>
  );
}
