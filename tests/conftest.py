"""Pytest fixtures that load the synthetic data layer."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.io import load_dataset


@pytest.fixture(scope="session")
def synthetic_tables() -> dict:
    """Load the versioned synthetic dataset (session-scoped)."""
    data_dir = PROJECT_ROOT / "data" / "synthetic" / "v1"
    if not data_dir.exists():
        pytest.skip(f"Synthetic data not found at {data_dir}. Run generate_synthetic_data first.")
    return load_dataset(data_dir)


@pytest.fixture
def employees_df(synthetic_tables) -> pd.DataFrame:
    """The employees table."""
    return synthetic_tables["employees"]


@pytest.fixture
def leave_types_df(synthetic_tables) -> pd.DataFrame:
    """The leave_types table."""
    return synthetic_tables["leave_types"]


@pytest.fixture
def leave_transactions_df(synthetic_tables) -> pd.DataFrame:
    """The leave_transactions table."""
    return synthetic_tables["leave_transactions"]


@pytest.fixture
def rosters_df(synthetic_tables) -> pd.DataFrame:
    """The rosters table."""
    return synthetic_tables["rosters"]


@pytest.fixture
def stores_df(synthetic_tables) -> pd.DataFrame:
    """The stores table."""
    return synthetic_tables["stores"]


@pytest.fixture
def demand_df(synthetic_tables) -> pd.DataFrame:
    """The demand table."""
    return synthetic_tables["demand"]


@pytest.fixture
def remuneration_df(synthetic_tables) -> pd.DataFrame:
    """The remuneration_components table."""
    return synthetic_tables["remuneration_components"]


@pytest.fixture
def calendar_df(synthetic_tables) -> pd.DataFrame:
    """The calendar_nz table."""
    return synthetic_tables["calendar_nz"]