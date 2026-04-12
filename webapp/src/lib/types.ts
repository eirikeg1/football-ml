export type Category =
  | "data_sources"
  | "augmentation"
  | "feature_extractors"
  | "composition"
  | "fusion"
  | "temporal"
  | "heads";

export interface PortDef {
  name: string;
  type: "input" | "output";
  dataType: "data" | "embedding" | "tensor" | "graph" | "dataset";
  multi?: boolean; // accepts multiple connections
}

export interface ParamDef {
  name: string;
  type: "number" | "string" | "select";
  default: number | string;
  options?: string[];
}

export type DetailPanelType =
  | "datasource_sqlite"
  | "datasource_csv"
  | "table_selector"
  | "materialization";

export interface NodeDef {
  id: string;
  label: string;
  category: Category;
  description: string;
  ports: PortDef[];
  params: ParamDef[];
  detailPanel?: DetailPanelType;
  implemented?: boolean; // defaults to true; false shows "Coming soon" indicator
}

export interface NodeInstance {
  instanceId: string;
  defId: string;
  x: number;
  y: number;
  params: Record<string, number | string>;
  detailConfig?: Record<string, unknown>;
}

export interface Connection {
  id: string;
  fromNode: string; // instanceId
  fromPort: string; // port name
  toNode: string;
  toPort: string;
}

export interface PendingConnection {
  fromNode: string;
  fromPort: string;
  fromX: number;
  fromY: number;
  mouseX: number;
  mouseY: number;
}

export const CATEGORY_COLORS: Record<Category, string> = {
  data_sources: "var(--color-data-sources)",
  augmentation: "var(--color-augmentation)",
  feature_extractors: "var(--color-feature-extractors)",
  composition: "var(--color-composition)",
  fusion: "var(--color-fusion)",
  temporal: "var(--color-temporal)",
  heads: "var(--color-heads)",
};

export const CATEGORY_LABELS: Record<Category, string> = {
  data_sources: "Data Sources",
  augmentation: "Augmentation",
  feature_extractors: "Feature Extractors",
  composition: "Composition",
  fusion: "Fusion",
  temporal: "Temporal",
  heads: "Prediction Heads",
};
