"""CSV directory data source adapter."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_ml.datasource.base import (
    ColumnMeta,
    DatasetSchema,
    DataSource,
    TableMeta,
)

# Map pandas dtypes to simple type strings
_DTYPE_MAP = {
    "int64": "integer",
    "int32": "integer",
    "float64": "real",
    "float32": "real",
    "object": "text",
    "bool": "integer",
    "datetime64[ns]": "text",
}


class CsvSource(DataSource):
    """Load data from a directory of CSV files.

    Each CSV file is treated as a separate table (using the filename
    without extension as the table name).
    """

    def __init__(
        self,
        directory: str | Path,
        delimiter: str = ",",
        sample_rows: int = 100,
    ) -> None:
        self.directory = Path(directory).expanduser().resolve()
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.directory}")
        self.delimiter = delimiter
        self.sample_rows = sample_rows

    def _csv_files(self) -> list[Path]:
        return sorted(self.directory.glob("*.csv"))

    def introspect(self) -> DatasetSchema:
        """Read CSV headers and infer column types from a sample of rows."""
        tables: list[TableMeta] = []

        for csv_path in self._csv_files():
            table_name = csv_path.stem
            # Read a small sample to infer types
            sample = pd.read_csv(
                csv_path,
                delimiter=self.delimiter,
                nrows=self.sample_rows,
            )
            columns = [
                ColumnMeta(
                    name=col,
                    data_type=_DTYPE_MAP.get(str(sample[col].dtype), "text"),
                    role="key" if col == "id" or col.endswith("_id") else "feature",
                )
                for col in sample.columns
            ]
            tables.append(TableMeta(name=table_name, columns=columns))

        # CSVs have no FK metadata — relationships must be defined manually
        return DatasetSchema(tables=tables, relationships=[])

    def load_tables(
        self,
        schema: DatasetSchema | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Load CSV files as DataFrames."""
        if schema is None:
            schema = self.introspect()

        # Build a set of table names we should load
        schema_tables = {t.name: t for t in schema.tables}

        result: dict[str, pd.DataFrame] = {}
        for csv_path in self._csv_files():
            table_name = csv_path.stem
            table_meta = schema_tables.get(table_name)
            if table_meta is None:
                continue

            cols = [c.name for c in table_meta.columns if c.role != "ignore"]
            if not cols:
                continue

            df = pd.read_csv(csv_path, delimiter=self.delimiter, usecols=cols)
            result[table_name] = df

        return result
