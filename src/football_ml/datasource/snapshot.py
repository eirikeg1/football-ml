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

    def _filter_tables(
        self, cutoff_time: int
    ) -> dict[str, pd.DataFrame]:
        """Filter tables to only include data before cutoff_time."""
        hist_matches = self.matches[self.matches["kickoff_time"] < cutoff_time]
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

        if "match_stats" in tables and not tables["match_stats"].empty:
            custom_features["match_stats"] = encode_match_stat_features(
                tables["match_stats"]
            )

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

        data, metadata, id_maps = to_hetero_graph(
            tables,
            self.relationships,
            add_reverse_edges=True,
            custom_features=custom_features,
        )

        return data, metadata, id_maps

    def build_training_samples(self) -> list[TrainingSample]:
        """Pre-compute all training samples grouped by matchday.

        For each finished match, builds a snapshot of all data before that
        match's kickoff time and creates a TrainingSample.

        Matches on the same matchday/date share the same snapshot.
        """
        samples: list[TrainingSample] = []

        # Group by kickoff date (day-level) to share snapshots
        self.matches["_date"] = (
            self.matches["kickoff_time"] // 86400
        )  # day-level bucket

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
                )
            )

        # Clean up temp column
        self.matches.drop(columns=["_date"], inplace=True, errors="ignore")

        return samples
