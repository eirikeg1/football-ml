"""Abstract base class and schema dataclasses for data sources."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

import pandas as pd


@dataclass
class ColumnMeta:
    """Metadata for a single table column."""

    name: str
    data_type: str  # "integer", "real", "text", "blob"
    role: str = "feature"  # "feature", "label", "key", "ignore"


@dataclass
class TableMeta:
    """Metadata for a single table."""

    name: str
    columns: list[ColumnMeta] = field(default_factory=list)


@dataclass
class RelationshipMeta:
    """A foreign key or user-defined relationship between tables."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    rel_type: str = "many_to_one"  # "many_to_one", "one_to_many", "many_to_many"


@dataclass
class DatasetSchema:
    """Full schema for a data source: tables + relationships."""

    tables: list[TableMeta] = field(default_factory=list)
    relationships: list[RelationshipMeta] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> DatasetSchema:
        """Deserialize from JSON string."""
        data = json.loads(text)
        tables = [
            TableMeta(
                name=t["name"],
                columns=[ColumnMeta(**c) for c in t.get("columns", [])],
            )
            for t in data.get("tables", [])
        ]
        relationships = [
            RelationshipMeta(**r) for r in data.get("relationships", [])
        ]
        return cls(tables=tables, relationships=relationships)


class DataSource(ABC):
    """Abstract base class for data sources.

    Subclasses implement schema introspection and table loading for a
    specific storage backend (SQLite, CSV, etc.).
    """

    @abstractmethod
    def introspect(self) -> DatasetSchema:
        """Discover the schema: tables, columns, and relationships."""
        ...

    @abstractmethod
    def load_tables(
        self,
        schema: DatasetSchema | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Load selected tables as DataFrames.

        If *schema* is provided, only included tables/columns are loaded.
        If *schema* is None, all tables and columns are loaded.
        """
        ...
