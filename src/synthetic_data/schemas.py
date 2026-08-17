"""Column schemas for the synthetic data tables.

Defines the expected columns, dtypes, and validation rules for each
generated table. Used by the generators to validate output and by
downstream consumers to understand the data contract.
"""

from __future__ import annotations

from typing import Any, Dict

# ---------------------------------------------------------------------------
# Stores / Locations
# ---------------------------------------------------------------------------
STORES_SCHEMA: Dict[str, Dict[str, Any]] = {
    "store_id": {"dtype": "int64", "required": True, "unique": True},
    "store_name": {"dtype": "object", "required": True},
    "region": {"dtype": "object", "required": True},
    "format": {"dtype": "object", "required": True},
    "size_band": {"dtype": "object", "required": True},
    "trading_pattern": {"dtype": "object", "required": True},
    "weekday_open": {"dtype": "object", "required": True},
    "weekday_close": {"dtype": "object", "required": True},
    "saturday_open": {"dtype": "object", "required": True},
    "saturday_close": {"dtype": "object", "required": True},
    "sunday_open": {"dtype": "object", "required": True},
    "sunday_close": {"dtype": "object", "required": True},
    "is_tight_capacity": {"dtype": "bool", "required": True},
}

# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------
EMPLOYEES_SCHEMA: Dict[str, Dict[str, Any]] = {
    "employee_id": {"dtype": "int64", "required": True, "unique": True},
    "store_id": {"dtype": "int64", "required": True},
    "first_name": {"dtype": "object", "required": True},
    "last_name": {"dtype": "object", "required": True},
    "role": {"dtype": "object", "required": True},
    "job_family": {"dtype": "object", "required": True},
    "employment_type": {"dtype": "object", "required": True},
    "start_date": {"dtype": "object", "required": True},
    "contracted_hours_per_week": {"dtype": "float64", "required": True, "min": 0, "max": 40},
    "base_hourly_rate": {"dtype": "float64", "required": True, "min": 20},
    "insurance_enrolled": {"dtype": "bool", "required": True},
    "flexibility_preference": {"dtype": "float64", "required": True, "min": 0, "max": 1},
    "is_high_leave_balance": {"dtype": "bool", "required": True},
    "is_new_starter": {"dtype": "bool", "required": True},
    "is_high_flexibility": {"dtype": "bool", "required": True},
}

# ---------------------------------------------------------------------------
# Leave Types (static reference)
# ---------------------------------------------------------------------------
LEAVE_TYPES_SCHEMA: Dict[str, Dict[str, Any]] = {
    "leave_code": {"dtype": "object", "required": True, "unique": True},
    "leave_name": {"dtype": "object", "required": True},
    "is_paid": {"dtype": "bool", "required": True},
    "carries_over": {"dtype": "bool", "required": True},
    "accrual_rate_hours_per_week": {"dtype": "float64", "required": False},
    "accrual_rate_days_per_year": {"dtype": "float64", "required": False},
    "max_balance_weeks": {"dtype": "float64", "required": False},
    "max_balance_days": {"dtype": "float64", "required": False},
}

# ---------------------------------------------------------------------------
# Leave Accrual & Transactions
# ---------------------------------------------------------------------------
LEAVE_TRANSACTIONS_SCHEMA: Dict[str, Dict[str, Any]] = {
    "transaction_id": {"dtype": "int64", "required": True, "unique": True},
    "employee_id": {"dtype": "int64", "required": True},
    "leave_code": {"dtype": "object", "required": True},
    "transaction_date": {"dtype": "object", "required": True},
    "transaction_type": {"dtype": "object", "required": True},  # ACCRUAL | TAKEN
    "hours": {"dtype": "float64", "required": True, "min": 0},
    "balance_after": {"dtype": "float64", "required": True, "min": 0},
    "reason_code": {"dtype": "object", "required": False},
}

# ---------------------------------------------------------------------------
# Roster / Worked Hours
# ---------------------------------------------------------------------------
ROSTERS_SCHEMA: Dict[str, Dict[str, Any]] = {
    "roster_id": {"dtype": "int64", "required": True, "unique": True},
    "employee_id": {"dtype": "int64", "required": True},
    "store_id": {"dtype": "int64", "required": True},
    "work_date": {"dtype": "object", "required": True},
    "shift_start": {"dtype": "object", "required": True},
    "shift_end": {"dtype": "object", "required": True},
    "hours_worked": {"dtype": "float64", "required": True, "min": 0},
    "role_on_day": {"dtype": "object", "required": True},
    "is_weekend": {"dtype": "bool", "required": True},
    "is_public_holiday": {"dtype": "bool", "required": True},
    "penalty_flag": {"dtype": "bool", "required": True},
}

# ---------------------------------------------------------------------------
# Demand / Activity Drivers
# ---------------------------------------------------------------------------
DEMAND_SCHEMA: Dict[str, Dict[str, Any]] = {
    "store_id": {"dtype": "int64", "required": True},
    "date": {"dtype": "object", "required": True},
    "day_of_week": {"dtype": "int64", "required": True, "min": 0, "max": 6},
    "is_weekend": {"dtype": "bool", "required": True},
    "is_public_holiday": {"dtype": "bool", "required": True},
    "is_school_term": {"dtype": "bool", "required": True},
    "is_retail_peak": {"dtype": "bool", "required": True},
    "demand_index": {"dtype": "float64", "required": True, "min": 0},
    "transaction_count": {"dtype": "int64", "required": True, "min": 0},
    "sales_amount": {"dtype": "float64", "required": True, "min": 0},
}

# ---------------------------------------------------------------------------
# Remuneration Components
# ---------------------------------------------------------------------------
REMUNERATION_SCHEMA: Dict[str, Dict[str, Any]] = {
    "employee_id": {"dtype": "int64", "required": True, "unique": True},
    "base_hourly_rate": {"dtype": "float64", "required": True, "min": 20},
    "kiwisaver_employer_rate": {"dtype": "float64", "required": True},
    "kiwisaver_employer_cost_per_hour": {"dtype": "float64", "required": True, "min": 0},
    "leave_loading_rate": {"dtype": "float64", "required": True},
    "leave_loading_cost_per_hour": {"dtype": "float64", "required": True, "min": 0},
    "insurance_monthly_cost": {"dtype": "float64", "required": True, "min": 0},
    "insurance_cost_per_hour": {"dtype": "float64", "required": True, "min": 0},
    "flexibility_premium_rate": {"dtype": "float64", "required": True, "min": 0},
    "flexibility_premium_cost_per_hour": {"dtype": "float64", "required": True, "min": 0},
    "fully_loaded_cost_per_hour": {"dtype": "float64", "required": True, "min": 0},
}

# ---------------------------------------------------------------------------
# Calendar & NZ Reference Data
# ---------------------------------------------------------------------------
CALENDAR_SCHEMA: Dict[str, Dict[str, Any]] = {
    "date": {"dtype": "object", "required": True, "unique": True},
    "year": {"dtype": "int64", "required": True},
    "month": {"dtype": "int64", "required": True, "min": 1, "max": 12},
    "day": {"dtype": "int64", "required": True, "min": 1, "max": 31},
    "day_of_week": {"dtype": "int64", "required": True, "min": 0, "max": 6},
    "is_weekend": {"dtype": "bool", "required": True},
    "is_public_holiday": {"dtype": "bool", "required": True},
    "public_holiday_name": {"dtype": "object", "required": False},
    "public_holiday_region": {"dtype": "object", "required": False},
    "is_school_term": {"dtype": "bool", "required": True},
    "is_retail_peak": {"dtype": "bool", "required": True},
}

# ---------------------------------------------------------------------------
# Master schema registry
# ---------------------------------------------------------------------------
ALL_SCHEMAS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "stores": STORES_SCHEMA,
    "employees": EMPLOYEES_SCHEMA,
    "leave_types": LEAVE_TYPES_SCHEMA,
    "leave_transactions": LEAVE_TRANSACTIONS_SCHEMA,
    "rosters": ROSTERS_SCHEMA,
    "demand": DEMAND_SCHEMA,
    "remuneration_components": REMUNERATION_SCHEMA,
    "calendar_nz": CALENDAR_SCHEMA,
}