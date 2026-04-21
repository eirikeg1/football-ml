"""Rolling snapshot graph construction for temporal HeteroGNN training."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import torch
from torch_geometric.data import HeteroData

from football_ml.config import HeteroGNNConfig, SnapshotConfig
from football_ml.datasource.base import RelationshipMeta
from football_ml.datasource.graph_features import (
    aggregate_events,
    encode_event_features,
    encode_match_features,
    encode_match_stat_features,
)
from football_ml.datasource.materialize import to_hetero_graph


@dataclass
class TrainingSample:
    """A single training sample: snapshot graph + match to predict."""

    snapshot: HeteroData
    metadata: tuple
    home_team_idx: int
    away_team_idx: int
    home_score: int
    away_score: int
    match_id: int
    date_key: int = 0


class SnapshotBuilder:
    """Build rolling temporal snapshot graphs from football data.

    For each prediction point (matchday), constructs a HeteroData graph
    containing only historical data (matches, stats, events before that
    date). Teams and competitions are always fully included.
    """

    def __init__(
        self,
        tables: dict[str, pd.DataFrame],
        relationships: list[RelationshipMeta],
        snapshot_config: SnapshotConfig | None = None,
        hetero_config: HeteroGNNConfig | None = None,
    ) -> None:
        self.snapshot_config = snapshot_config or SnapshotConfig()
        self.hetero_config = hetero_config or HeteroGNNConfig()

        # Store raw tables
        self.matches = tables["matches"].copy()
        self.match_stats = tables.get("match_stats", pd.DataFrame()).copy()
        self.match_events = tables.get("match_events", pd.DataFrame()).copy()
        self.teams = tables.get("teams", pd.DataFrame()).copy()
        self.competitions = tables.get("competitions", pd.DataFrame()).copy()

        # Filter to finished matches only
        if "status" in self.matches.columns:
            self.matches = self.matches[self.matches["status"] == "finished"].copy()

        self.matches = self.matches.sort_values("kickoff_time").reset_index(drop=True)

        # Pre-aggregate events if not including event nodes
        if not self.hetero_config.include_events and not self.match_events.empty:
            self.match_stats = aggregate_events(self.match_events, self.match_stats)

        # Store relationships, filtering to relevant tables
        relevant_tables = {"matches", "match_stats", "teams", "competitions"}
        if self.hetero_config.include_events:
            relevant_tables.add("match_events")

        self.relationships = [
            r for r in relationships
            if r.from_table in relevant_tables and r.to_table in relevant_tables
        ]

        # Build team ID → name mapping for reference
        if "id" in self.teams.columns:
            self._team_ids = set(self.teams["id"].values)
        else:
            self._team_ids = set()

        # Build canonical metadata from a full snapshot (all data) so that
        # every snapshot has consistent node/edge type sets
        full_tables = {
            "matches": self.matches,
            "match_stats": self.match_stats,
            "teams": self.teams,
            "competitions": self.competitions,
        }
        if self.hetero_config.include_events and not self.match_events.empty:
            full_tables["match_events"] = self.match_events

        _, self._canonical_metadata, _ = to_hetero_graph(
            full_tables,
            self.relationships,
            add_reverse_edges=True,
        )

    def _filter_tables(
        self, cutoff_time: int
    ) -> dict[str, pd.DataFrame]:
        """Filter tables to only include data before cutoff_time.

        If max_matches_per_team is set, keeps only the most recent N
        matches per team to cap graph size.
        """
        hist_matches = self.matches[self.matches["kickoff_time"] < cutoff_time]

        # Cap matches per team to limit graph size
        cap = self.snapshot_config.max_matches_per_team
        if cap > 0 and len(hist_matches) > cap * 2:
            # Collect the last N match IDs for each team (home + away)
            keep_ids: set = set()
            for col in ("home_team_id", "away_team_id"):
                per_team = (
                    hist_matches.sort_values("kickoff_time", ascending=False)
                    .groupby(col)["id"]
                    .head(cap)
                )
                keep_ids.update(per_team.values)
            hist_matches = hist_matches[hist_matches["id"].isin(keep_ids)]

        hist_match_ids = set(hist_matches["id"].values)

        tables: dict[str, pd.DataFrame] = {
            "matches": hist_matches,
            "teams": self.teams,
            "competitions": self.competitions,
        }

        if not self.match_stats.empty:
            tables["match_stats"] = self.match_stats[
                self.match_stats["match_id"].isin(hist_match_ids)
            ]

        if self.hetero_config.include_events and not self.match_events.empty:
            tables["match_events"] = self.match_events[
                self.match_events["match_id"].isin(hist_match_ids)
            ]

        return tables

    def build_snapshot(
        self, cutoff_time: int
    ) -> tuple[HeteroData, tuple, dict[str, dict]]:
        """Build a HeteroData graph for all data before cutoff_time.

        Returns:
            Tuple of (HeteroData, metadata, id_maps).
        """
        tables = self._filter_tables(cutoff_time)

        # Prepare custom feature tensors
        custom_features: dict[str, torch.Tensor] = {}

        if "matches" in tables and not tables["matches"].empty:
            custom_features["matches"] = encode_match_features(tables["matches"])

        if "match_stats" in tables:
            if not tables["match_stats"].empty:
                custom_features["match_stats"] = encode_match_stat_features(
                    tables["match_stats"]
                )
            else:
                # Empty table — use consistent 11-dim zeros so feature dims
                # don't change between snapshots
                custom_features["match_stats"] = torch.zeros((0, 11), dtype=torch.float32)

        if (
            self.hetero_config.include_events
            and "match_events" in tables
            and not tables["match_events"].empty
        ):
            custom_features["match_events"] = encode_event_features(
                tables["match_events"]
            )

        # Teams and competitions get placeholder features (replaced by
        # learned embeddings in HeteroGNN)
        if "teams" in tables:
            custom_features["teams"] = torch.zeros(
                (len(tables["teams"]), 1), dtype=torch.float32
            )
        if "competitions" in tables:
            custom_features["competitions"] = torch.zeros(
                (len(tables["competitions"]), 1), dtype=torch.float32
            )

        data, _, id_maps = to_hetero_graph(
            tables,
            self.relationships,
            add_reverse_edges=True,
            custom_features=custom_features,
        )

        # Use canonical metadata so all snapshots have consistent types
        canonical_node_types, canonical_edge_types = self._canonical_metadata

        # Ensure all node types exist (even if empty)
        for nt in canonical_node_types:
            if nt not in data.node_types:
                # Use consistent feature dim from custom_features or 1
                feat_dim = custom_features[nt].shape[1] if nt in custom_features else 1
                data[nt].x = torch.zeros((0, feat_dim), dtype=torch.float32)
                data[nt].num_nodes = 0
                data[nt].node_id = torch.zeros(0, dtype=torch.long)

        # Ensure all edge types exist (empty if no edges)
        for et in canonical_edge_types:
            if et not in data.edge_types:
                data[et].edge_index = torch.zeros((2, 0), dtype=torch.long)

        return data, self._canonical_metadata, id_maps

    def build_training_samples(self) -> list[TrainingSample]:
        """Pre-compute all training samples grouped by matchday.

        For each finished match, builds a snapshot of all data before that
        match's kickoff time and creates a TrainingSample.

        Matches on the same matchday/date share the same snapshot.
        """
        samples: list[TrainingSample] = []

        # Group by week to share snapshots (fewer, larger batches)
        self.matches["_date"] = (
            self.matches["kickoff_time"] // (86400 * 7)
        )  # week-level bucket

        snapshot_cache: dict[int, tuple[HeteroData, tuple, dict]] = {}

        for _, match in self.matches.iterrows():
            date_key = match["_date"]
            cutoff = match["kickoff_time"]
            home_team_id = match["home_team_id"]
            away_team_id = match["away_team_id"]

            # Skip if scores are missing
            if pd.isna(match.get("home_score")) or pd.isna(match.get("away_score")):
                continue

            # Build or retrieve cached snapshot
            if date_key not in snapshot_cache:
                snapshot_result = self.build_snapshot(cutoff)
                snapshot_cache[date_key] = snapshot_result

            data, metadata, id_maps = snapshot_cache[date_key]

            # Look up team indices
            team_map = id_maps.get("teams", {})
            home_idx = team_map.get(home_team_id)
            away_idx = team_map.get(away_team_id)

            if home_idx is None or away_idx is None:
                continue

            # Check minimum history requirement
            if self.snapshot_config.min_history_matches > 0:
                match_count = data["matches"].num_nodes if "matches" in data.node_types else 0
                if match_count < self.snapshot_config.min_history_matches:
                    continue

            samples.append(
                TrainingSample(
                    snapshot=data,
                    metadata=metadata,
                    home_team_idx=home_idx,
                    away_team_idx=away_idx,
                    home_score=int(match["home_score"]),
                    away_score=int(match["away_score"]),
                    match_id=int(match["id"]),
                    date_key=int(date_key),
                )
            )

        # Clean up temp column
        self.matches.drop(columns=["_date"], inplace=True, errors="ignore")

        return samples
