"""Generic data source abstraction for loading and materializing tabular data."""

from football_ml.datasource.base import (
    ColumnMeta,
    DatasetSchema,
    DataSource,
    RelationshipMeta,
    TableMeta,
)
from football_ml.datasource.csv_source import CsvSource
from football_ml.datasource.sqlite_source import SqliteSource

__all__ = [
    "ColumnMeta",
    "CsvSource",
    "DatasetSchema",
    "DataSource",
    "RelationshipMeta",
    "SqliteSource",
    "TableMeta",
]
