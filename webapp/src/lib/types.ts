export type Category =
  | "data_sources"
  | "augmentation"
  | "feature_extractors"
  | "composition"
  | "fusion"
  | "temporal"
  | "heads";

export type PortShape = "flat" | "sequence" | "graph" | "dataset";

export interface PortDef {
  name: string;
  type: "input" | "output";
  dataType: "data" | "embedding" | "tensor" | "graph" | "dataset";
  multi?: boolean; // accepts multiple connections
  // Structural rank of the data flowing through this port. Defaults are inferred
  // from dataType when omitted (dataset→dataset, graph→graph, otherwise flat).
  shape?: PortShape;
  // Name of the node param holding this port's feature-dim width. Used by
  // validation to compare upstream output width to downstream expected width.
  // Leave unset when width isn't meaningful (dataset / graph ports).
  widthParam?: string;
  // Inputs default to required. Set false for genuinely optional inputs.
  required?: boolean;
  // Only meaningful on multi inputs. Defaults to "concat" when multi is true.
  multiSemantics?: "concat" | "stack";
  // Soft-warning hint: expected upstream node categories. Emits category_hint
  // warning when an incoming edge's source category isn't in this list.
  expectedUpstreamCategories?: Category[];
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

export type ValidationSeverity = "error" | "warning";

export type ValidationCode =
  | "dtype_mismatch"
  | "shape_mismatch"
  | "dim_mismatch"
  | "multi_stack_mismatch"
  | "multi_sum_mismatch"
  | "cycle"
  | "required_input_missing"
  | "upstream_unset"
  | "category_hint"
  | "not_implemented";

export interface ValidationIssue {
  severity: ValidationSeverity;
  code: ValidationCode;
  message: string;
  detail?: string;
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
