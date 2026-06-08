"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { WizardStep1Data } from "@/types/wizard";

type WizardStep1FormProps = {
  initial: WizardStep1Data;
  disabled?: boolean;
  onSubmit: (data: WizardStep1Data) => void;
};

export function WizardStep1Form({
  initial,
  disabled,
  onSubmit,
}: WizardStep1FormProps) {
  const [form, setForm] = useState(initial);

  return (
    <form
      className="mt-4 space-y-3 rounded-xl border border-white/40 bg-white/30 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
    >
      <div>
        <Label htmlFor="use-case" className="text-xs text-slate-600">
          Use case
        </Label>
        <Input
          id="use-case"
          placeholder="e.g. Industrial warehouse, workshop…"
          value={form.use_case}
          disabled={disabled}
          onChange={(e) => setForm((f) => ({ ...f, use_case: e.target.value }))}
          className="mt-1 bg-white/80"
        />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <Label htmlFor="width" className="text-xs text-slate-600">
            Width (mm)
          </Label>
          <Input
            id="width"
            type="number"
            min={1000}
            value={form.width_mm}
            disabled={disabled}
            onChange={(e) =>
              setForm((f) => ({ ...f, width_mm: Number(e.target.value) }))
            }
            className="mt-1 bg-white/80"
          />
        </div>
        <div>
          <Label htmlFor="length" className="text-xs text-slate-600">
            Length (mm)
          </Label>
          <Input
            id="length"
            type="number"
            min={1000}
            value={form.length_mm}
            disabled={disabled}
            onChange={(e) =>
              setForm((f) => ({ ...f, length_mm: Number(e.target.value) }))
            }
            className="mt-1 bg-white/80"
          />
        </div>
        <div>
          <Label htmlFor="height" className="text-xs text-slate-600">
            Eave (mm)
          </Label>
          <Input
            id="height"
            type="number"
            min={2000}
            value={form.height_mm}
            disabled={disabled}
            onChange={(e) =>
              setForm((f) => ({ ...f, height_mm: Number(e.target.value) }))
            }
            className="mt-1 bg-white/80"
          />
        </div>
      </div>
      <Button type="submit" disabled={disabled} className="w-full">
        Continue → Roof & site
      </Button>
    </form>
  );
}
