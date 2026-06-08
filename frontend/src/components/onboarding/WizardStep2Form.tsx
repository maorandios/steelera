"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { WizardStep2Data } from "@/types/wizard";

type WizardStep2FormProps = {
  initial: WizardStep2Data;
  disabled?: boolean;
  loading?: boolean;
  onBack: () => void;
  onSubmit: (data: WizardStep2Data) => void;
};

export function WizardStep2Form({
  initial,
  disabled,
  loading,
  onBack,
  onSubmit,
}: WizardStep2FormProps) {
  const [form, setForm] = useState(initial);

  return (
    <form
      className="mt-4 space-y-3 rounded-xl border border-white/40 bg-white/30 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
    >
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="roof-style" className="text-xs text-slate-600">
            Roof type
          </Label>
          <select
            id="roof-style"
            disabled={disabled}
            value={form.roof_style}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                roof_style: e.target.value as WizardStep2Data["roof_style"],
                roof_pitch_deg:
                  e.target.value === "flat" ? 0 : f.roof_pitch_deg || 10,
              }))
            }
            className="mt-1 w-full rounded-md border border-input bg-white/80 px-3 py-2 text-sm"
          >
            <option value="duo_pitch">Duo-pitch</option>
            <option value="mono_pitch">Mono-pitch</option>
            <option value="flat">Flat</option>
          </select>
        </div>
        <div>
          <Label htmlFor="exposure" className="text-xs text-slate-600">
            Site exposure
          </Label>
          <select
            id="exposure"
            disabled={disabled}
            value={form.exposure}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                exposure: e.target.value as WizardStep2Data["exposure"],
              }))
            }
            className="mt-1 w-full rounded-md border border-input bg-white/80 px-3 py-2 text-sm"
          >
            <option value="open">Open terrain / high wind</option>
            <option value="sheltered">Sheltered / urban</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="pitch" className="text-xs text-slate-600">
            Roof pitch (°)
          </Label>
          <Input
            id="pitch"
            type="number"
            min={0}
            max={45}
            disabled={disabled || form.roof_style === "flat"}
            value={form.roof_pitch_deg}
            onChange={(e) =>
              setForm((f) => ({ ...f, roof_pitch_deg: Number(e.target.value) }))
            }
            className="mt-1 bg-white/80"
          />
        </div>
        <div>
          <Label htmlFor="bay-spacing" className="text-xs text-slate-600">
            Frame spacing (mm)
          </Label>
          <Input
            id="bay-spacing"
            type="number"
            min={3000}
            step={500}
            placeholder="6000 default"
            disabled={disabled}
            value={form.bay_spacing_mm ?? ""}
            onChange={(e) => {
              const v = e.target.value.trim();
              setForm((f) => ({
                ...f,
                bay_spacing_mm: v ? Number(v) : null,
              }));
            }}
            className="mt-1 bg-white/80"
          />
        </div>
      </div>
      <div className="flex gap-2">
        <Button type="button" variant="outline" disabled={disabled} onClick={onBack}>
          Back
        </Button>
        <Button type="submit" disabled={disabled || loading} className="flex-1">
          {loading ? "Computing proposal…" : "Generate engineering proposal →"}
        </Button>
      </div>
    </form>
  );
}
