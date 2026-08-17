# Synthetic Data Layer

Generates a realistic, reproducible synthetic NZ retail workforce dataset.

## Overview

This package produces the foundational data layer for the NZ Retail
Remuneration & Workforce Programme. It creates a coherent set of tables that
mirror real retail entities — stores, employees, leave, rosters, demand, and
remuneration — without using any real employee or commercial data.

## Tables Generated

| Table | Description |
|-------|-------------|
| `stores` | Store locations with region, format, size band, trading hours |
| `employees` | Employee master data (role, employment type, hours, rates) |
| `leave_types` | Static leave-type reference (annual, sick, bereavement, etc.) |
| `leave_transactions` | Leave accrual and usage transactions with balances |
| `rosters` | Worked shifts with dates, times, hours, penalty flags |
| `demand` | Daily demand indices, transaction counts, sales per store |
| `remuneration_components` | Per-employee cost components and fully-loaded rates |
| `calendar_nz` | NZ calendar with public holidays, school terms, retail peaks |

## Usage

### From the CLI

```bash
python scripts/generate_synthetic_data.py
```

### From Python

```python
from src.synthetic_data import generate_synthetic_data

tables = generate_synthetic_data()
# tables is a dict: {"stores": DataFrame, "employees": DataFrame, ...}
```

### Configuration

All generation parameters live in `configs/synthetic_data.yaml`:

- Seed, date range, output directory
- Store count, regions, formats
- Employee headcount, employment mix, roles, rates
- Leave types, accrual rates, usage patterns
- Roster utilisation, shift lengths, weekend probabilities
- Demand seasonality, multipliers, noise
- Remuneration rates (KiwiSaver, leave loading, insurance, flexibility)
- Edge cases (high leave balances, new starters, tight capacity)

## Reproducibility

The dataset is fully reproducible: a fixed random seed (`42` by default)
ensures the same configuration always produces the same output. Change the
seed in the config to generate a different (but still valid) dataset.

## Validation

Every generated table is validated against its schema (columns, dtypes,
ranges, uniqueness) and cross-table foreign-key integrity is checked before
output is written.

## Output

Tables are written to `data/synthetic/v1/` (configurable) as CSV files with
a `_manifest.json` describing the generation parameters and row counts.