#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["polars>=1.5", "click>=8.1.7"]
# ///
import glob
import json
import os
import re
from typing import Dict, List, Optional, Tuple

import click
import polars as pl

# ---------------------------
# Helpers (names are honest)
# ---------------------------


def _common_prefix_suffix(names: List[str]) -> Tuple[str, str]:
    """Return (common_prefix, common_suffix) for a list of basenames."""
    if not names:
        return "", ""
    prefix = os.path.commonprefix(names)
    rev = [n[::-1] for n in names]
    suffix = os.path.commonprefix(rev)[::-1]
    return prefix, suffix


def _derive_output_from_pattern(pattern: str, files: List[str]) -> str:
    """
    Build a default output path by 'removing the pattern':
    i.e., keep common prefix+suffix of matched basenames, strip .csv, add .parquet.
    """
    # Where to drop the result: same directory as the first match (or CWD).
    out_dir = os.path.dirname(files[0]) if files else os.getcwd()
    basenames = [os.path.basename(f) for f in files]
    pre, suf = _common_prefix_suffix(basenames)
    base = (pre + suf) or os.path.basename(re.sub(r"[\*\?\[\]]+", "", pattern))
    # Clean double separators and collapse runs like "__"
    base = re.sub(r"([_\-\.])\1+", r"\1", base)
    # Normalize extension
    base_no_ext = re.sub(r"\.csv(?:\.gz)?$", "", base, flags=re.IGNORECASE)
    out = os.path.join(out_dir, f"{base_no_ext or 'combined'}.parquet")
    return out


def _load_schema(schema_path: Optional[str]) -> Optional[Dict[str, pl.DataType]]:
    if not schema_path:
        return None
    with open(schema_path, "r") as f:
        raw = json.load(f)
    # Map simple strings to Polars dtypes (extend as needed)
    lut = {
        "int8": pl.Int8,
        "int16": pl.Int16,
        "int32": pl.Int32,
        "int64": pl.Int64,
        "uint8": pl.UInt8,
        "uint16": pl.UInt16,
        "uint32": pl.UInt32,
        "uint64": pl.UInt64,
        "float32": pl.Float32,
        "float64": pl.Float64,
        "bool": pl.Boolean,
        "utf8": pl.Utf8,
        "string": pl.Utf8,
        "date": pl.Date,
        "datetime": pl.Datetime,
        "time": pl.Time,
    }
    out: Dict[str, pl.DataType] = {}
    for k, v in raw.items():
        if isinstance(v, str) and v.lower() in lut:
            out[k] = lut[v.lower()]
        else:
            raise click.ClickException(f"Unsupported dtype '{v}' for column '{k}'.")
    return out


def _add_from_filename(lf: pl.LazyFrame, colname: str, regex: str, drop_path: bool) -> pl.LazyFrame:
    lf = lf.with_columns(pl.col("file_path").str.extract(regex).alias(colname))
    if drop_path:
        lf = lf.drop("file_path")
    return lf


# ---------------------------
# CLI
# ---------------------------


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("pattern", metavar="PATTERN")
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False),
    help="Output Parquet path. If omitted, derived from PATTERN by removing the wildcard piece.",
)
@click.option(
    "--relaxed/--strict",
    default=False,
    show_default=True,
    help="Allow missing/extra columns across files (diagonal concat).",
)
@click.option(
    "--schema",
    type=click.Path(exists=True, dir_okay=False),
    help='JSON file mapping column -> dtype (e.g., {"h3":"utf8","value":"float64"}). Locks schema.',
)
@click.option(
    "--infer-length", type=int, default=1000, show_default=True, help="Rows to scan for CSV type inference per file."
)
@click.option(
    "--compression",
    type=click.Choice(["zstd", "snappy", "lz4", "uncompressed"]),
    default="zstd",
    show_default=True,
    help="Parquet compression.",
)
@click.option(
    "--row-group-size", type=int, default=512_000, show_default=True, help="Approx rows per Parquet row group."
)
@click.option(
    "--add-year",
    is_flag=True,
    default=False,
    show_default=True,
    help="Extract a year from filename into a 'year' column.",
)
@click.option(
    "--year-regex",
    default=r"(\d{4})",
    show_default=True,
    help="Regex with one capture group to pull year from file path.",
)
@click.option(
    "--keep-file-path",
    is_flag=True,
    default=False,
    show_default=True,
    help="Keep the source file_path column in the output.",
)
@click.option("--has-header/--no-header", default=True, show_default=True, help="Whether CSV files have header rows.")
def cli(
    pattern: str,
    output: Optional[str],
    relaxed: bool,
    schema: Optional[str],
    infer_length: int,
    compression: str,
    row_group_size: int,
    add_year: bool,
    year_regex: str,
    keep_file_path: bool,
    has_header: bool,
):
    """
    Stream-convert multiple CSVs matched by PATTERN into a single Parquet file.

    PATTERN can include glob wildcards, e.g. 'micro2022_*_h3.csv'.
    By default, the output name is derived by removing the wildcard part from PATTERN.
    """
    files = sorted(glob.glob(pattern))
    if not files:
        raise click.ClickException(f"No files match: {pattern}")

    dtypes = _load_schema(schema)

    # If we're adding year, we need file paths; otherwise we can skip them.
    include_paths = add_year or keep_file_path

    # Preferred fast path: single scan on the glob pattern (streaming friendly).
    if not relaxed:
        lf = pl.scan_csv(
            pattern,
            has_header=has_header,
            dtypes=dtypes,
            infer_schema_length=infer_length,
            include_file_paths=include_paths,
        )
    else:
        # Relaxed path: per-file scans concatenated diagonally to tolerate column drift.
        ldfs = [
            pl.scan_csv(
                f,
                has_header=has_header,
                dtypes=dtypes,
                infer_schema_length=infer_length,
                include_file_paths=include_paths,
            )
            for f in files
        ]
        lf = pl.concat(ldfs, how="diagonal_relaxed")

    if include_paths:
        if add_year:
            lf = _add_from_filename(lf, "year", year_regex, drop_path=(not keep_file_path))
        elif not keep_file_path:
            lf = lf.drop("file_path")

    out_path = output or _derive_output_from_pattern(pattern, files)
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    # Write streaming
    lf.sink_parquet(
        out_path,
        compression=compression,
        statistics=True,
        row_group_size=row_group_size,
        use_pyarrow=False,
    )
    click.echo(f"✚ Wrote {out_path}")


if __name__ == "__main__":
    cli()
