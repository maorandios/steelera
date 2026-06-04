"use client";

import { Loader2 } from "lucide-react";

import { parseBaySpansMm } from "@/lib/shed-assembly";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export type ShedFormValues = {
  xSpans: string;
  zSpans: string;
  height: string;
  pitch: string;
  purlinSpacing: string;
};

type ShedMacroFieldsProps = {
  values: ShedFormValues;
  onChange: (values: ShedFormValues) => void;
  onSubmit: () => void;
  submitLabel: string;
  loading?: boolean;
  disabled?: boolean;
  error?: string | null;
};

export function ShedMacroFields({
  values,
  onChange,
  onSubmit,
  submitLabel,
  loading = false,
  disabled = false,
  error = null,
}: ShedMacroFieldsProps) {
  const set =
    (key: keyof ShedFormValues) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...values, [key]: e.target.value });

  const inputsValid =
    parseBaySpansMm(values.xSpans) != null &&
    parseBaySpansMm(values.zSpans) != null &&
    Number(values.height) > 0 &&
    Number(values.purlinSpacing) > 0 &&
    Number(values.pitch) >= 0 &&
    Number(values.pitch) < 90;

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
            onChange={set("xSpans")}
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
            onChange={set("zSpans")}
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
            onChange={set("height")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="shed-field-pitch">Roof pitch (°)</Label>
          <Input
            id="shed-field-pitch"
            type="number"
            min={0}
            max={89.9}
            step={0.5}
            value={values.pitch}
            onChange={set("pitch")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled}
          />
        </div>
        <div className="col-span-2 space-y-1.5">
          <Label htmlFor="shed-field-purlin">Purlin spacing (mm)</Label>
          <Input
            id="shed-field-purlin"
            type="number"
            min={1}
            step={50}
            value={values.purlinSpacing}
            onChange={set("purlinSpacing")}
            className="h-9 font-mono text-xs"
            disabled={loading || disabled}
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
