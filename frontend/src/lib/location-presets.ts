export type LocationPreset = {
  label: string;
  latitude: number;
  longitude: number;
};

export const LOCATION_PRESETS: LocationPreset[] = [
  { label: "Tel Aviv, Israel", latitude: 32.0853, longitude: 34.7818 },
  { label: "Dubai, UAE", latitude: 25.2048, longitude: 55.2708 },
  { label: "Riyadh, Saudi Arabia", latitude: 24.7136, longitude: 46.6753 },
  { label: "New York, USA", latitude: 40.7128, longitude: -74.006 },
  { label: "Houston, USA", latitude: 29.7604, longitude: -95.3698 },
  { label: "London, UK", latitude: 51.5074, longitude: -0.1278 },
  { label: "Sydney, Australia", latitude: -33.8688, longitude: 151.2093 },
];
