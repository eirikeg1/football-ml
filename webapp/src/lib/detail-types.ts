/** Typed interfaces for detail panel configurations. */

export interface ColumnSelection {
  name: string;
  dataType: string; // "integer" | "real" | "text" | "blob"
  included: boolean;
  role: "feature" | "label" | "key" | "ignore";
}

export interface TableSelection {
  name: string;
  included: boolean;
  columns: ColumnSelection[];
}

export interface Relationship {
  id: string;
  fromTable: string;
  fromColumn: string;
  toTable: string;
  toColumn: string;
  type: "one_to_many" | "many_to_one" | "many_to_many";
  autoDetected: boolean;
}

export interface SqliteSourceConfig {
  dbPath: string;
  tables: TableSelection[];
  relationships: Relationship[];
}

export interface CsvFileEntry {
  filename: string;
  included: boolean;
  columns: ColumnSelection[];
  delimiter: string;
  hasHeader: boolean;
}

export interface CsvSourceConfig {
  directoryPath: string;
  files: CsvFileEntry[];
  relationships: Relationship[];
}

export interface TableSelectorConfig {
  selectedTable: string;
  columns: string[];
}

export interface FlattenOptions {
  joinOrder: string[];
  joinType: "inner" | "left" | "outer";
}

export interface GraphNodeType {
  table: string;
  features: string[];
}

export interface GraphEdgeType {
  relationship: string;
  directed: boolean;
}

export interface GraphOptions {
  nodeTypes: GraphNodeType[];
  edgeTypes: GraphEdgeType[];
}

export interface MaterializationConfig {
  strategy: "flatten" | "aligned" | "heterogeneous_graph";
  flattenOptions?: FlattenOptions;
  graphOptions?: GraphOptions;
}
