"use client";

import { Loader2, MapPin } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  clickToLatLon,
  formatCoord,
  MAP_ZOOM,
  pinPositionOnMap,
  tileUrl,
  tilesForViewport,
} from "@/lib/map-pin";
import { useProjectStore } from "@/store/project-store";

const MAP_WIDTH = 400;
const MAP_HEIGHT = 220;

type SiteMapPinPickerProps = {
  initialLat: number;
  initialLon: number;
  active: boolean;
  onComplete?: () => void;
};

export function SiteMapPinPicker({
  initialLat,
  initialLon,
  active,
  onComplete,
}: SiteMapPinPickerProps) {
  const confirmSiteMapPin = useProjectStore((s) => s.confirmSiteMapPin);
  const isProposing = useProjectStore((s) => s.isProposing);
  const [pinLat, setPinLat] = useState(initialLat);
  const [pinLon, setPinLon] = useState(initialLon);
  const [loading, setLoading] = useState(false);

  const disabled = !active || loading || isProposing;

  const tiles = useMemo(
    () => tilesForViewport(initialLat, initialLon, MAP_WIDTH, MAP_HEIGHT),
    [initialLat, initialLon],
  );

  const pinPos = useMemo(
    () =>
      pinPositionOnMap(
        pinLat,
        pinLon,
        initialLat,
        initialLon,
        MAP_WIDTH,
        MAP_HEIGHT,
      ),
    [pinLat, pinLon, initialLat, initialLon],
  );

  const handleMapClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (disabled) return;
      const rect = event.currentTarget.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;
      const next = clickToLatLon(
        clickX,
        clickY,
        initialLat,
        initialLon,
        MAP_WIDTH,
        MAP_HEIGHT,
      );
      setPinLat(next.lat);
      setPinLon(next.lon);
    },
    [disabled, initialLat, initialLon],
  );

  return (
    <div className="mt-3 space-y-2">
      <div
        role="presentation"
        onClick={handleMapClick}
        className="relative cursor-crosshair overflow-hidden rounded-2xl border border-white/80 bg-white/50 shadow-sm"
        style={{ width: MAP_WIDTH, height: MAP_HEIGHT, maxWidth: "100%" }}
      >
        {tiles.map((tile) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={`${tile.x}-${tile.y}`}
            src={tileUrl(tile.x, tile.y, MAP_ZOOM)}
            alt=""
            draggable={false}
            className="absolute pointer-events-none"
            style={{
              left: tile.left,
              top: tile.top,
              width: 256,
              height: 256,
            }}
          />
        ))}
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full text-primary drop-shadow"
          style={{ left: pinPos.left, top: pinPos.top }}
        >
          <MapPin className="h-7 w-7 fill-primary stroke-primary-foreground" />
        </div>
        <p className="pointer-events-none absolute bottom-1 right-1 rounded bg-background/80 px-1 text-[9px] text-muted-foreground">
          © OpenStreetMap
        </p>
      </div>
      <p className="font-mono text-[10px] text-muted-foreground">
        Pin: {formatCoord(pinLat)}, {formatCoord(pinLon)}
      </p>
      <Button
        type="button"
        disabled={disabled}
        className="w-full rounded-full"
        onClick={async () => {
          setLoading(true);
          try {
            await confirmSiteMapPin(pinLat, pinLon);
            onComplete?.();
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Updating site data…
          </>
        ) : (
          "Confirm pin & continue"
        )}
      </Button>
    </div>
  );
}
