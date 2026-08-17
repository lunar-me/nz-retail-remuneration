"""Store / location generator.

Creates a realistic set of NZ retail store locations with region, format,
size band, and trading-hour patterns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.synthetic_data.schemas import STORES_SCHEMA
from src.common.validation import validate_all


def _weighted_choice(rng: np.random.Generator, items: List[Dict[str, Any]], key: Optional[str] = "name") -> Any:
    """Pick an item from a weighted list.

    If ``key`` is None, returns the full selected item dict.
    """
    weights = np.array([item.get("weight", 1.0) for item in items], dtype=float)
    weights = weights / weights.sum()
    idx = rng.choice(len(items), p=weights)
    if key is None:
        return items[idx]
    return items[idx][key]


def generate_stores(
    rng: np.random.Generator,
    config: Dict[str, Any],
) -> pd.DataFrame:
    """Generate the stores table.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded random number generator.
    config : Dict[str, Any]
        The ``stores`` section of the synthetic data config.

    Returns
    -------
    pd.DataFrame
        Stores table conforming to :data:`STORES_SCHEMA`.
    """
    store_cfg = config["stores"]
    count = int(store_cfg["count"])
    regions = store_cfg["regions"]
    formats = store_cfg["formats"]
    trading = store_cfg["trading_patterns"]

    # Determine tight-capacity stores (edge case)
    edge_cfg = config.get("generation", {}).get("edge_cases", {})
    tight_count = int(edge_cfg.get("tight_capacity_stores", 0))
    tight_indices = set(rng.choice(count, size=min(tight_count, count), replace=False).tolist())

    rows: List[Dict[str, Any]] = []
    for i in range(count):
        region = _weighted_choice(rng, regions)
        fmt = _weighted_choice(rng, formats, key=None)  # get full dict
        size_band = fmt.get("typical_size_band", "Medium")

        # Choose trading pattern: extended for large-format stores
        pattern_name = "extended" if size_band == "Extra Large" else "standard"
        pattern = trading[pattern_name]

        rows.append(
            {
                "store_id": i + 1,
                "store_name": f"Store {i + 1:02d}",
                "region": region,
                "format": fmt["name"],
                "size_band": size_band,
                "trading_pattern": pattern_name,
                "weekday_open": pattern["weekday_open"],
                "weekday_close": pattern["weekday_close"],
                "saturday_open": pattern["saturday_open"],
                "saturday_close": pattern["saturday_close"],
                "sunday_open": pattern["sunday_open"],
                "sunday_close": pattern["sunday_close"],
                "is_tight_capacity": i in tight_indices,
            }
        )

    df = pd.DataFrame(rows)
    validate_all(df, STORES_SCHEMA, context="stores")
    return df