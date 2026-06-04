"use client";

import { Loader2 } from "lucide-react";

import type { ShedFormValues, ShedRoofStyle } from "@/lib/shed-assembly";
import { parseBaySpansMm } from "@/lib/shed-assembly";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

export type { ShedFormValues };

const ROOF_STYLE_OPTIONS: { value: ShedRoofStyle; label: string }[] = [
  { value: "duo_pitch", label: "Duo-pitch" },
  { value: "mono_pitch", label: "Mono-pitch" },
  { value: "flat", label: "Flat" },
];

type ShedMacroFieldsProps = {
  values: ShedFormValues;
  onChange: (values: ShedFormValues) => void;
  onSubmit: () => void;
  submitLabel: string;
  loading?: boolean;
  disabled?: boolean;
  error?: string | null;
};

function StructuralToggle({
  id,
  label,
  checked,
  disabled,
  onCheckedChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  disabled?: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/20 px-2.5 py-2">
      <Label htmlFor={id} className="cursor-pointer text-xs font-normal">
        {label}
      </Label>
      <Switch
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
      />
    </div>
  );
}

export function ShedMacroFields({
  values,
  onChange,
  onSubmit,
  submitLabel,
  loading = false,
  disabled = false,
  error = null,
}: ShedMacroFieldsProps) {
  const setField =
    <K extends keyof ShedFormValues>(key: K, value: ShedFormValues[K]) =>
      onChange({ ...values, [key]: value });

  const setInput =
    (key: "xSpans" | "zSpans" | "height" | "pitch" | "purlinSpacing" | "girtSpacing") =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setField(key, e.target.value);

  const pitchDisabled = values.roofStyle === "flat";
  const inputsValid =
    parseBaySpansMm(values.xSpans) != null &&
    parseBaySpansMm(values.zSpans) != null &&
    Number(values.height) > 0 &&
    Number(values.purlinSpacing) > 0 &&
    Number(values.girtSpacing) > 0 &&
    (pitchDisabled ||
      (Number(values.pitch) >= 0 && Number(values.pitch) < 90));

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[10px] text-muted-foreground">
        Spans drive the model and CAD grid. Total width = sum of X spans; total
        depth = sum of Z spans.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2 space-y-1.5">
          <Label htmlFor="shed-field-x-spans">X spans (mm)</Label>
          <Input
            id="shed-field-x-spans"
            type="text"
            placeholder="3000, 7000, 10000, 5000"
            value={values.xSpans}
            onChange={setInput("xSpans")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled}
          />
        </div>
        <div className="col-span-2 space-y-1.5">
          <Label htmlFor="shed-field-z-spans">Z spans (mm)</Label>
          <Input
            id="shed-field-z-spans"
            type="text"
            placeholder="5000, 5000, 5000, 5000, 5000, 5000"
            value={values.zSpans}
            onChange={setInput("zSpans")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="shed-field-height">Height (mm)</Label>
          <Input
            id="shed-field-height"
            type="number"
            min={1}
            step={100}
            value={values.height}
            onChange={setInput("height")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="shed-field-roof-style">Roof style</Label>
          <select
            id="shed-field-roof-style"
            value={values.roofStyle}
            onChange={(e) => {
              const roofStyle = e.target.value as ShedRoofStyle;
              onChange({
                ...values,
                roofStyle,
                pitch: roofStyle === "flat" ? "0" : values.pitch,
              });
            }}
            disabled={loading || disabled}
            className={cn(
              "flex h-9 w-full rounded-md border border-input bg-background px-2.5 text-xs",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              "disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            {ROOF_STYLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="shed-field-pitch">Roof pitch (°)</Label>
          <Input
            id="shed-field-pitch"
            type="number"
            min={0}
            max={89.9}
            step={0.5}
            value={pitchDisabled ? "0" : values.pitch}
            onChange={setInput("pitch")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled || pitchDisabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="shed-field-girt">Girt spacing (mm)</Label>
          <Input
            id="shed-field-girt"
            type="number"
            min={1}
            step={100}
            value={values.girtSpacing}
            onChange={setInput("girtSpacing")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled || !values.generateWallGirts}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="shed-field-purlin">Purlin spacing (mm)</Label>
          <Input
            id="shed-field-purlin"
            type="number"
            min={1}
            step={50}
            value={values.purlinSpacing}
            onChange={setInput("purlinSpacing")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Secondary steel
        </p>
        <div className="grid grid-cols-2 gap-2">
          <StructuralToggle
            id="shed-toggle-truss"
            label="Roof truss"
            checked={values.useTruss}
            disabled={loading || disabled}
            onCheckedChange={(useTruss) => setField("useTruss", useTruss)}
          />
          <StructuralToggle
            id="shed-toggle-bracing"
            label="X-bracing"
            checked={values.useBracing}
            disabled={loading || disabled}
            onCheckedChange={(useBracing) => setField("useBracing", useBracing)}
          />
          <StructuralToggle
            id="shed-toggle-sag"
            label="Sag rods"
            checked={values.useSagRods}
            disabled={loading || disabled}
            onCheckedChange={(useSagRods) => setField("useSagRods", useSagRods)}
          />
          <StructuralToggle
            id="shed-toggle-girts"
            label="Wall girts"
            checked={values.generateWallGirts}
            disabled={loading || disabled}
            onCheckedChange={(generateWallGirts) =>
              setField("generateWallGirts", generateWallGirts)
            }
          />
        </div>
      </div>

      <Button
        type="button"
        size="sm"
        disabled={loading || disabled || !inputsValid}
        onClick={onSubmit}
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Updating…
          </>
        ) : (
          submitLabel
        )}
      </Button>

      {error ? (
        <p className="text-xs text-red-400" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
