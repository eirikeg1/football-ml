"""CLI for data source introspection.

Usage:
    python -m football_ml.datasource introspect <path> [--type sqlite|csv] [--output FILE]

Outputs a JSON schema description that can be imported into the webapp's
detail panel to configure table/column selection and relationships.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from football_ml.datasource.base import DatasetSchema
from football_ml.datasource.csv_source import CsvSource
from football_ml.datasource.sqlite_source import SqliteSource


def detect_source_type(path: Path) -> str:
    """Guess the source type from the path."""
    if path.is_dir():
        return "csv"
    if path.suffix in (".db", ".sqlite", ".sqlite3"):
        return "sqlite"
    return "sqlite"


def introspect(path: Path, source_type: str | None = None) -> DatasetSchema:
    """Run introspection on the given path."""
    if source_type is None:
        source_type = detect_source_type(path)

    if source_type == "sqlite":
        source = SqliteSource(path)
    elif source_type == "csv":
        source = CsvSource(path)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    return source.introspect()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Data source schema introspection tool"
    )
    subparsers = parser.add_subparsers(dest="command")

    intro_parser = subparsers.add_parser(
        "introspect",
        help="Discover schema (tables, columns, FK relationships) from a data source",
    )
    intro_parser.add_argument("path", type=Path, help="Path to database file or CSV directory")
    intro_parser.add_argument(
        "--type",
        choices=["sqlite", "csv"],
        default=None,
        help="Source type (auto-detected if not specified)",
    )
    intro_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args(argv)

    if args.command == "introspect":
        schema = introspect(args.path, args.type)
        json_str = schema.to_json()

        if args.output:
            args.output.write_text(json_str)
            print(f"Schema written to {args.output}", file=sys.stderr)
        else:
            print(json_str)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
