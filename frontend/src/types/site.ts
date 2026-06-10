export type TerrainClass = "0" | "II" | "III" | "IV";

export type SiteContext = {
  latitude: number;
  longitude: number;
  location_label: string;
  mean_wind_ms: number;
  design_wind_proxy_ms: number;
  terrain_class: TerrainClass;
  exposure: "open" | "sheltered";
  load_index: number;
  building_count_500m: number;
  near_water: boolean;
  data_sources: string[];
  detected_terrain_class?: TerrainClass | null;
  detected_load_index?: number | null;
  surroundings_applied?: "auto" | "built_up" | "open_industrial";
};

export type GeocodeResult = {
  latitude: number;
  longitude: number;
  display_name: string;
};

export type StructuralRecommendations = {
  bay_spacing_mm: number;
  use_truss: boolean;
  truss_type: string;
  column_profile: string;
  truss_chord_profile: string | null;
  truss_web_profile: string | null;
  x_bracing: boolean;
  roof_bracing: boolean;
  gable_bracing: boolean;
  sag_rods: boolean;
  fly_braces: boolean;
  haunches: boolean;
};
