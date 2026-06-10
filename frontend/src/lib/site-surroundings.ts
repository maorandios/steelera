export const SITE_BUILT_UP = "built_up";
export const SITE_OPEN_INDUSTRIAL = "open_industrial";
export const SITE_PIN = "__pin__";

export type SiteSurroundings =
  | "auto"
  | typeof SITE_BUILT_UP
  | typeof SITE_OPEN_INDUSTRIAL;

export function surroundingsLabel(value: SiteSurroundings): string {
  switch (value) {
    case SITE_BUILT_UP:
      return "Built-up / inside city";
    case SITE_OPEN_INDUSTRIAL:
      return "Open or industrial land";
    default:
      return "Auto from map data";
  }
}
