"""I/O helpers for reading and writing programme data.

Provides consistent CSV output with metadata sidecars, directory
management, and versioned dataset handling.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd

logger = logging.getLogger(__name__)


def ensure_dir(path: Path | str) -> Path:
    """Create a directory (and parents) if it does not exist.

    Parameters
    ----------
    path : Path | str
        Directory path to ensure exists.

    Returns
    -------
    Path
        The resolved directory path.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_csv(
    df: pd.DataFrame,
    path: Path | str,
    *,
    index: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write a DataFrame to CSV, optionally with a JSON metadata sidecar.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to write.
    path : Path | str
        Destination CSV path.
    index : bool, optional
        Whether to write the index (default ``False``).
    metadata : Optional[Dict[str, Any]], optional
        Metadata dict written to a ``<name>.meta.json`` sidecar.

    Returns
    -------
    Path
        The path the CSV was written to.
    """
    p = Path(path)
    ensure_dir(p.parent)

    df.to_csv(p, index=index)

    if metadata is not None:
        meta_path = p.with_suffix(p.suffix + ".meta.json")
        meta_path.write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding="utf-8",
        )

    logger.info("Wrote %d rows to %s", len(df), p)
    return p


def read_csv(path: Path | str, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV file into a DataFrame.

    Parameters
    ----------
    path : Path | str
        Path to the CSV file.
    **kwargs
        Additional arguments passed to :func:`pandas.read_csv`.

    Returns
    -------
    pd.DataFrame
        The loaded DataFrame.
    """
    return pd.read_csv(path, **kwargs)


def write_dataset(
    tables: Dict[str, pd.DataFrame],
    output_dir: Path | str,
    *,
    version: str = "v1",
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write a set of tables to a versioned output directory.

    Parameters
    ----------
    tables : Dict[str, pd.DataFrame]
        Mapping of table name → DataFrame.
    output_dir : Path | str
        Base output directory (e.g. ``data/synthetic``).
    version : str, optional
        Version subdirectory name (default ``v1``).
    metadata : Optional[Dict[str, Any]], optional
        Dataset-level metadata written to ``_dataset_meta.json``.

    Returns
    -------
    Path
        The versioned output directory.
    """
    out = ensure_dir(Path(output_dir) / version)

    for name, df in tables.items():
        write_csv(df, out / f"{name}.csv")

    if metadata is not None:
        meta_path = out / "_dataset_meta.json"
        meta_path.write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding="utf-8",
        )

    logger.info("Wrote dataset version %s to %s", version, out)
    return out


def load_dataset(
    version_dir: Path | str,
    table_names: Optional[Sequence[str]] = None,
) -> Dict[str, pd.DataFrame]:
    """Load all (or selected) tables from a versioned dataset directory.

    Parameters
    ----------
    version_dir : Path | str
        Path to the version directory (e.g. ``data/synthetic/v1``).
    table_names : Optional[Sequence[str]], optional
        Subset of table names to load. If ``None``, all ``*.csv`` files
        (excluding metadata) are loaded.

    Returns
    -------
    Dict[str, pd.DataFrame]
        Mapping of table name → DataFrame.
    """
    d = Path(version_dir)
    if not d.exists():
        raise FileNotFoundError(f"Dataset directory not found: {d}")

    tables: Dict[str, pd.DataFrame] = {}
    if table_names is None:
        csv_files = sorted(d.glob("*.csv"))
    else:
        csv_files = [d / f"{name}.csv" for name in table_names]

    for f in csv_files:
        if not f.exists():
            raise FileNotFoundError(f"Table file not found: {f}")
        tables[f.stem] = read_csv(f)

    return tables


def write_manifest(
    output_dir: Path | str,
    *,
    version: str,
    seed: int,
    generated_at: Optional[datetime] = None,
    tables: Optional[Dict[str, int]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write a generation manifest describing a dataset version.

    Parameters
    ----------
    output_dir : Path | str
        Output directory where the manifest will be written. This should
        be the full target directory (including any version subdirectory).
    version : str
        Version identifier.
    seed : int
        Random seed used for generation.
    generated_at : Optional[datetime], optional
        Timestamp of generation (defaults to now).
    tables : Optional[Dict[str, int]], optional
        Mapping of table name → row count.
    extra : Optional[Dict[str, Any]], optional
        Additional metadata to include.

    Returns
    -------
    Path
        Path to the written manifest file.
    """
    out = ensure_dir(Path(output_dir))
    manifest = {
        "version": version,
        "seed": seed,
        "generated_at": (generated_at or datetime.now()).isoformat(),
        "tables": tables or {},
    }
    if extra:
        manifest.update(extra)

    path = out / "_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote manifest to %s", path)
    return path
