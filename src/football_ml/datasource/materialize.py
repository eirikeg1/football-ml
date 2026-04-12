"""Materialization strategies: convert multi-table data to model-ready formats."""

from __future__ import annotations

from functools import reduce

import pandas as pd
import torch

from football_ml.datasource.base import RelationshipMeta


def flatten(
    tables: dict[str, pd.DataFrame],
    relationships: list[RelationshipMeta],
    join_order: list[str] | None = None,
    join_type: str = "inner",
) -> pd.DataFrame:
    """Join all tables into one wide DataFrame.

    Args:
        tables: mapping of table name to DataFrame.
        relationships: list of FK relationships used to determine join keys.
        join_order: order in which to join tables. If None, uses dict order.
        join_type: pandas merge how parameter ("inner", "left", "outer").

    Returns:
        A single merged DataFrame.
    """
    if not tables:
        return pd.DataFrame()

    order = join_order if join_order else list(tables.keys())
    order = [t for t in order if t in tables]

    if len(order) == 0:
        return pd.DataFrame()
    if len(order) == 1:
        return tables[order[0]].copy()

    # Build a lookup: (left_table, right_table) -> (left_col, right_col)
    rel_lookup: dict[tuple[str, str], tuple[str, str]] = {}
    for rel in relationships:
        rel_lookup[(rel.from_table, rel.to_table)] = (
            rel.from_column,
            rel.to_column,
        )
        # Also store the reverse direction
        rel_lookup[(rel.to_table, rel.from_table)] = (
            rel.to_column,
            rel.from_column,
        )

    def merge_pair(left: pd.DataFrame, right_name: str) -> pd.DataFrame:
        right = tables[right_name]
        # Find the relationship between the accumulated result and this table
        # Try all tables already merged
        for prev_name in merged_names:
            key = (prev_name, right_name)
            if key in rel_lookup:
                left_col, right_col = rel_lookup[key]
                if left_col in left.columns and right_col in right.columns:
                    return left.merge(
                        right,
                        left_on=left_col,
                        right_on=right_col,
                        how=join_type,
                        suffixes=("", f"_{right_name}"),
                    )
        # Fallback: try to find any shared column name
        shared = set(left.columns) & set(right.columns)
        if shared:
            return left.merge(
                right,
                on=list(shared),
                how=join_type,
                suffixes=("", f"_{right_name}"),
            )
        raise ValueError(
            f"No join key found between accumulated tables and '{right_name}'. "
            f"Define a relationship or ensure shared column names."
        )

    result = tables[order[0]].copy()
    merged_names = [order[0]]

    for name in order[1:]:
        result = merge_pair(result, name)
        merged_names.append(name)

    return result


def to_aligned_tensors(
    tables: dict[str, pd.DataFrame],
    key_column: str = "id",
) -> dict[str, torch.Tensor]:
    """Convert each table to a float tensor, aligned by a shared key column.

    Numeric columns are converted to tensors. Non-numeric columns and the
    key column itself are excluded from the tensor.

    Args:
        tables: mapping of table name to DataFrame.
        key_column: column present in each table used for alignment.

    Returns:
        Mapping of table name to 2D float tensor.
    """
    result: dict[str, torch.Tensor] = {}
    for name, df in tables.items():
        numeric = df.select_dtypes(include=["number"])
        # Drop the key column from features if present
        if key_column in numeric.columns:
            numeric = numeric.drop(columns=[key_column])
        if numeric.empty:
            continue
        result[name] = torch.tensor(
            numeric.fillna(0).values, dtype=torch.float32
        )
    return result


def to_hetero_graph(
    tables: dict[str, pd.DataFrame],
    relationships: list[RelationshipMeta],
    node_types: list[dict] | None = None,
    edge_types: list[dict] | None = None,
    add_reverse_edges: bool = False,
    custom_features: dict[str, torch.Tensor] | None = None,
) -> tuple:
    """Build a PyTorch Geometric HeteroData object.

    Each selected table becomes a node type. Each relationship becomes
    an edge type. Node features are the numeric columns of that table.

    Args:
        tables: mapping of table name to DataFrame.
        relationships: FK relationships for creating edges.
        node_types: list of dicts with "table" and optional "features" keys.
            If None, all tables become node types.
        edge_types: list of dicts with "relationship" index and "directed" flag.
            If None, all relationships become edge types.
        add_reverse_edges: if True, add reverse edges for bidirectional
            message passing (required for HGTConv).
        custom_features: optional pre-computed feature tensors per node type.
            If provided for a node type, these are used instead of auto-extracting
            numeric columns from the DataFrame.

    Returns:
        Tuple of (HeteroData, metadata, id_maps) where:
        - HeteroData: the graph object
        - metadata: (node_types_list, edge_types_list) tuple for HGTConv
        - id_maps: dict mapping table_name -> {original_id -> node_index}
    """
    from torch_geometric.data import HeteroData

    data = HeteroData()
    custom_features = custom_features or {}

    # Determine which tables to use as node types
    if node_types:
        selected_tables = {nt["table"]: nt.get("features") for nt in node_types}
    else:
        selected_tables = {name: None for name in tables}

    # Build node features and ID mappings
    id_maps: dict[str, dict] = {}  # table_name -> {row_id -> index}

    for table_name, feature_cols in selected_tables.items():
        if table_name not in tables:
            continue
        df = tables[table_name]

        # Build ID mapping (assumes "id" column exists)
        if "id" in df.columns:
            id_maps[table_name] = {
                val: idx for idx, val in enumerate(df["id"].values)
            }
            data[table_name].node_id = torch.tensor(
                df["id"].values, dtype=torch.long
            )
        else:
            id_maps[table_name] = {idx: idx for idx in range(len(df))}
            data[table_name].node_id = torch.arange(len(df), dtype=torch.long)

        # Use custom features if provided, otherwise auto-extract
        if table_name in custom_features:
            data[table_name].x = custom_features[table_name]
        else:
            if feature_cols:
                numeric = df[
                    [c for c in feature_cols if c in df.columns]
                ].select_dtypes(include=["number"])
            else:
                numeric = df.select_dtypes(include=["number"])
                id_cols = [c for c in numeric.columns if c == "id" or c.endswith("_id")]
                numeric = numeric.drop(columns=id_cols, errors="ignore")

            if not numeric.empty:
                data[table_name].x = torch.tensor(
                    numeric.fillna(0).values, dtype=torch.float32
                )
            else:
                data[table_name].x = torch.zeros((len(df), 1), dtype=torch.float32)

        data[table_name].num_nodes = len(df)

    # Build edges from relationships
    all_edge_types: list[tuple[str, str, str]] = []

    for rel in relationships:
        if rel.from_table not in id_maps or rel.to_table not in id_maps:
            continue
        if rel.from_table not in tables or rel.to_table not in tables:
            continue

        from_df = tables[rel.from_table]
        from_map = id_maps[rel.to_table]  # map target IDs to indices

        if rel.from_column not in from_df.columns:
            continue

        src_indices = []
        dst_indices = []
        for row_idx, fk_val in enumerate(from_df[rel.from_column].values):
            if fk_val in from_map:
                src_indices.append(row_idx)
                dst_indices.append(from_map[fk_val])

        if src_indices:
            edge_type = (rel.from_table, f"{rel.from_column}_to_{rel.to_column}", rel.to_table)
            edge_tensor = torch.tensor(
                [src_indices, dst_indices], dtype=torch.long
            )
            data[edge_type].edge_index = edge_tensor
            all_edge_types.append(edge_type)

            # Add reverse edge for bidirectional message passing
            if add_reverse_edges:
                rev_edge_type = (rel.to_table, f"rev_{rel.from_column}_to_{rel.to_column}", rel.from_table)
                data[rev_edge_type].edge_index = torch.tensor(
                    [dst_indices, src_indices], dtype=torch.long
                )
                all_edge_types.append(rev_edge_type)

    node_types_list = list(selected_tables.keys())
    metadata = (node_types_list, all_edge_types)

    return data, metadata, id_maps
