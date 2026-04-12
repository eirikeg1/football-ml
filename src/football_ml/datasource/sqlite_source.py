"""SQLite data source adapter."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from football_ml.datasource.base import (
    ColumnMeta,
    DatasetSchema,
    DataSource,
    RelationshipMeta,
    TableMeta,
)

# Tables that are internal bookkeeping, not user data
_INTERNAL_TABLES = frozenset({
    "sqlite_sequence",
    "sqlite_stat1",
})


class SqliteSource(DataSource):
    """Load data from a SQLite database file."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def introspect(self) -> DatasetSchema:
        """Read table/column metadata and foreign keys from SQLite PRAGMAs."""
        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Get all user tables
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
            table_names = [
                row[0]
                for row in cursor.fetchall()
                if row[0] not in _INTERNAL_TABLES
            ]

            tables: list[TableMeta] = []
            relationships: list[RelationshipMeta] = []

            for table_name in table_names:
                # Column info
                cursor.execute(f"PRAGMA table_info('{table_name}')")
                columns = [
                    ColumnMeta(
                        name=row[1],
                        data_type=row[2].lower() if row[2] else "text",
                        role="key" if row[1] == "id" or row[1].endswith("_id") else "feature",
                    )
                    for row in cursor.fetchall()
                ]
                tables.append(TableMeta(name=table_name, columns=columns))

                # Foreign key info
                cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
                for fk_row in cursor.fetchall():
                    # fk_row: (id, seq, table, from, to, on_update, on_delete, match)
                    relationships.append(
                        RelationshipMeta(
                            from_table=table_name,
                            from_column=fk_row[3],
                            to_table=fk_row[2],
                            to_column=fk_row[4],
                            rel_type="many_to_one",
                        )
                    )

            return DatasetSchema(tables=tables, relationships=relationships)
        finally:
            conn.close()

    def load_tables(
        self,
        schema: DatasetSchema | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Load tables as DataFrames, optionally filtered by schema selection."""
        if schema is None:
            schema = self.introspect()

        conn = self._connect()
        try:
            result: dict[str, pd.DataFrame] = {}
            for table in schema.tables:
                # Select only included columns (non-ignored)
                cols = [c.name for c in table.columns if c.role != "ignore"]
                if not cols:
                    continue
                col_list = ", ".join(f'"{c}"' for c in cols)
                query = f'SELECT {col_list} FROM "{table.name}"'
                result[table.name] = pd.read_sql_query(query, conn)
            return result
        finally:
            conn.close()
