/** OSM tile math for the site pin picker (no static-map API). */

export const MAP_ZOOM = 13;
const TILE_SIZE = 256;

export type MapTile = {
  x: number;
  y: number;
  left: number;
  top: number;
};

export function latLonToWorldPixel(lat: number, lon: number, zoom: number) {
  const scale = TILE_SIZE * 2 ** zoom;
  const x = ((lon + 180) / 360) * scale;
  const sinLat = Math.sin((lat * Math.PI) / 180);
  const y =
    (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale;
  return { x, y };
}

export function worldPixelToLatLon(x: number, y: number, zoom: number) {
  const scale = TILE_SIZE * 2 ** zoom;
  const lon = (x / scale) * 360 - 180;
  const n = Math.PI - (2 * Math.PI * y) / scale;
  const lat = (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  return {
    lat: Math.max(-85, Math.min(85, lat)),
    lon: ((lon + 180) % 360) - 180,
  };
}

export function tileUrl(x: number, y: number, zoom: number): string {
  return `https://tile.openstreetmap.org/${zoom}/${x}/${y}.png`;
}

export function tilesForViewport(
  centerLat: number,
  centerLon: number,
  width: number,
  height: number,
  zoom = MAP_ZOOM,
): MapTile[] {
  const center = latLonToWorldPixel(centerLat, centerLon, zoom);
  const left = center.x - width / 2;
  const top = center.y - height / 2;
  const x0 = Math.floor(left / TILE_SIZE);
  const y0 = Math.floor(top / TILE_SIZE);
  const x1 = Math.floor((left + width - 1) / TILE_SIZE);
  const y1 = Math.floor((top + height - 1) / TILE_SIZE);
  const tiles: MapTile[] = [];
  for (let ty = y0; ty <= y1; ty += 1) {
    for (let tx = x0; tx <= x1; tx += 1) {
      tiles.push({
        x: tx,
        y: ty,
        left: tx * TILE_SIZE - left,
        top: ty * TILE_SIZE - top,
      });
    }
  }
  return tiles;
}

export function clickToLatLon(
  clickX: number,
  clickY: number,
  centerLat: number,
  centerLon: number,
  width: number,
  height: number,
  zoom = MAP_ZOOM,
) {
  const center = latLonToWorldPixel(centerLat, centerLon, zoom);
  return worldPixelToLatLon(
    center.x - width / 2 + clickX,
    center.y - height / 2 + clickY,
    zoom,
  );
}

export function pinPositionOnMap(
  pinLat: number,
  pinLon: number,
  centerLat: number,
  centerLon: number,
  width: number,
  height: number,
  zoom = MAP_ZOOM,
) {
  const center = latLonToWorldPixel(centerLat, centerLon, zoom);
  const pin = latLonToWorldPixel(pinLat, pinLon, zoom);
  return {
    left: pin.x - center.x + width / 2,
    top: pin.y - center.y + height / 2,
  };
}

export function formatCoord(value: number, decimals = 4): string {
  return value.toFixed(decimals);
}
