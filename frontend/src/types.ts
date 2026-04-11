export interface Tile {
  series_name: string;
  product_name?: string;
  color: string;
  surface: string;
  size_cm: string;
  application: string;
  suitable_for: string;
  sku: string;
  page_number?: string;
  image_path: string;
  base_score: number;
  final_score: number;
  why_recommended?: string;
}

export interface SearchResponse {
  query: string;
  preferences: any;
  count: number;
  ai_response: {
    ai_summary: string;
    recommended_tiles: Partial<Tile>[];
  };
  results: Tile[];
}

export interface Message {
  role: "user" | "model";
  text: string;
  tiles?: Tile[];
}

export interface NavItem {
  label: string;
  icon: string;
  active?: boolean;
}
