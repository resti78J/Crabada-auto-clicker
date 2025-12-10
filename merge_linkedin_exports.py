#!/usr/bin/env python3
"""Utility for merging multiple LinkedIn CSV/XLSX exports without overwriting past runs."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

import pandas as pd

CSV_EXTENSIONS = {".csv", ".tsv"}
EXCEL_EXTENSIONS = {".xlsx"}
SUPPORTED_EXTENSIONS = CSV_EXTENSIONS | EXCEL_EXTENSIONS


@dataclass
class LoadedFrame:
    path: Path
    rows: int
    columns: List[str]
    dataframe: pd.DataFrame


class MergeError(RuntimeError):
    """Raised when the merge process can not continue."""


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge multiple CSV/XLSX exports locally. "
            "Each run produces a timestamped output so older merges remain untouched."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Paths to CSV/XLSX files or directories that contain them.",
    )
    parser.add_argument(
        "--output-dir",
        default="merged_runs",
        help="Directory that will receive the merged file (default: merged_runs).",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Optional label added to the output filename so you can keep runs separated.",
    )
    parser.add_argument(
        "--output-format",
        choices=("csv", "xlsx"),
        default="xlsx",
        help="Format for the merged file (default: xlsx).",
    )
    parser.add_argument(
        "--sheet-name",
        default="merged",
        help="Sheet name used when writing XLSX files (default: merged).",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding assumed for CSV files (default: utf-8).",
    )
    parser.add_argument(
        "--delimiter",
        default=None,
        help="Override the delimiter for CSV/TSV files. Leave empty for auto-detection.",
    )
    parser.add_argument(
        "--dedupe-on",
        nargs="+",
        default=None,
        help="Optional column names to deduplicate on after concatenation.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When a directory is passed, crawl it recursively for supported files.",
    )
    return parser.parse_args(argv)


def normalize_tag(tag: str | None) -> str:
    if not tag:
        return "run"
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", tag.strip())
    return cleaned or "run"


def discover_files(inputs: Iterable[str], recursive: bool) -> List[Path]:
    discovered: List[Path] = []
    for raw_path in inputs:
        path = Path(raw_path).expanduser().resolve()
        if path.is_file():
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise MergeError(f"Unsupported file type: {path.name}")
            discovered.append(path)
        elif path.is_dir():
            glob_pattern = "**/*" if recursive else "*"
            files = sorted(
                p for p in path.glob(glob_pattern) if p.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            if not files:
                raise MergeError(f"No supported files found in directory: {path}")
            discovered.extend(files)
        else:
            raise MergeError(f"Path does not exist: {path}")
    if not discovered:
        raise MergeError("No input files provided after filtering.")
    return discovered


def sniff_delimiter(path: Path, encoding: str) -> str:
    with path.open("r", newline="", encoding=encoding) as handle:
        sample = handle.read(4096)
    try:
        return csv.Sniffer().sniff(sample).delimiter
    except csv.Error:
        return ","


def load_frame(path: Path, encoding: str, delimiter: str | None, sheet_name: str) -> LoadedFrame:
    suffix = path.suffix.lower()
    if suffix in CSV_EXTENSIONS:
        sep = delimiter or sniff_delimiter(path, encoding)
        df = pd.read_csv(path, dtype=str, encoding=encoding, sep=sep)
    elif suffix in EXCEL_EXTENSIONS:
        df = pd.read_excel(path, dtype=str, sheet_name=sheet_name)
    else:
        raise MergeError(f"Unsupported extension: {path.suffix}")

    df = df.fillna("")
    df["_source_file"] = path.name
    return LoadedFrame(path=path, rows=len(df), columns=list(df.columns), dataframe=df)


def concat_frames(frames: List[LoadedFrame]) -> pd.DataFrame:
    if not frames:
        raise MergeError("Nothing to merge.")
    ordered_columns: List[str] = []
    for frame in frames:
        for column in frame.dataframe.columns:
            if column not in ordered_columns:
                ordered_columns.append(column)
    concatenated = pd.concat([frame.dataframe for frame in frames], ignore_index=True)
    return concatenated.reindex(columns=ordered_columns)


def dedupe_if_needed(df: pd.DataFrame, columns: Sequence[str] | None) -> pd.DataFrame:
    if not columns:
        return df
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise MergeError(f"Columns not found for dedupe: {', '.join(missing)}")
    return df.drop_duplicates(subset=list(columns))


def write_outputs(
    df: pd.DataFrame,
    metadata: dict,
    output_dir: Path,
    filename_stub: str,
    output_format: str,
    sheet_name: str,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = output_dir / f"{filename_stub}.{output_format}"
    if output_format == "csv":
        df.to_csv(data_path, index=False)
    else:
        df.to_excel(data_path, index=False, sheet_name=sheet_name)
    metadata_path = output_dir / f"{filename_stub}.json"
    metadata["output_file"] = str(data_path)
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
    return data_path, metadata_path


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        files = discover_files(args.inputs, recursive=args.recursive)
        loaded_frames = [
            load_frame(path, encoding=args.encoding, delimiter=args.delimiter, sheet_name=args.sheet_name)
            for path in files
        ]
        merged = concat_frames(loaded_frames)
        merged = dedupe_if_needed(merged, args.dedupe_on)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename_stub = f"{timestamp}_{normalize_tag(args.tag)}"
        metadata = {
            "created_at": timestamp,
            "tag": args.tag,
            "inputs": [
                {"path": str(frame.path), "rows": frame.rows, "columns": frame.columns}
                for frame in loaded_frames
            ],
            "total_rows": len(merged),
            "dedupe_on": args.dedupe_on or [],
        }
        data_path, metadata_path = write_outputs(
            merged,
            metadata,
            Path(args.output_dir),
            filename_stub,
            args.output_format,
            args.sheet_name,
        )
    except MergeError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - surface unexpected issues
        print(f"[unexpected] {exc}", file=sys.stderr)
        return 1

    print("Merge completed!")
    print(f"- Rows merged: {metadata['total_rows']}")
    print(f"- Output file: {data_path}")
    print(f"- Metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
