"use client";

import { Loader2, MapPin, Navigation } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LOCATION_PRESETS } from "@/lib/location-presets";
import { useProjectStore } from "@/store/project-store";

type LocationPickerProps = {
  active: boolean;
};

export function LocationPicker({ active }: LocationPickerProps) {
  const [loading, setLoading] = useState(false);
  const setOnboardingLocation = useProjectStore((s) => s.setOnboardingLocation);
  const requestLocationCustom = useProjectStore((s) => s.requestLocationCustom);
  const isProposing = useProjectStore((s) => s.isProposing);

  const disabled = !active || loading || isProposing;

  const pickPreset = async (label: string, lat: number, lon: number) => {
    if (disabled) return;
    setLoading(true);
    try {
      await setOnboardingLocation(lat, lon, label);
    } finally {
      setLoading(false);
    }
  };

  const useGeolocation = () => {
    if (disabled || !navigator.geolocation) return;
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          await setOnboardingLocation(
            pos.coords.latitude,
            pos.coords.longitude,
            "My current location",
          );
        } finally {
          setLoading(false);
        }
      },
      () => {
        setLoading(false);
      },
      { enableHighAccuracy: false, timeout: 12_000, maximumAge: 60_000 },
    );
  };

  return (
    <div className="mt-3 space-y-2">
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={disabled}
        className={cn(
          "h-auto min-h-9 w-full justify-start gap-2 rounded-full px-4 py-2 text-sm font-normal",
          !disabled && "hover:bg-primary/10 hover:text-primary",
        )}
        onClick={useGeolocation}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
        ) : (
          <Navigation className="h-4 w-4 shrink-0" />
        )}
        Use my location
      </Button>
      <div className="flex flex-wrap gap-2">
        {LOCATION_PRESETS.map((preset) => (
          <Button
            key={preset.label}
            type="button"
            variant="secondary"
            size="sm"
            disabled={disabled}
            className={cn(
              "h-auto min-h-9 whitespace-normal rounded-full px-4 py-2 text-left text-sm font-normal",
              !disabled && "hover:bg-primary/10 hover:text-primary",
            )}
            onClick={() => pickPreset(preset.label, preset.latitude, preset.longitude)}
          >
            {preset.label}
          </Button>
        ))}
      </div>
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={disabled}
        className="h-auto min-h-9 w-full justify-start gap-2 rounded-full px-4 py-2 text-sm font-normal"
        onClick={() => requestLocationCustom()}
      >
        <MapPin className="h-4 w-4 shrink-0" />
        Enter address or city…
      </Button>
    </div>
  );
}
