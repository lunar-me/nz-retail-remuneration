"""
Shared utilities for the Streamlit visualisation app.
Loads pre-calculated data from data/synthetic/v1 and outputs/ directories.
"""
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

# Project root (parent of /app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Key paths
DATA_DIR = PROJECT_ROOT / "data" / "synthetic" / "v1"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
def data_path(filename: str) -> Path:
    """Return full path to a file in data/synthetic/v1."""
    return DATA_DIR / filename


def output_path(subdir: str, filename: str) -> Path:
    """Return full path to a file in outputs/<subdir>/."""
    return OUTPUTS_DIR / subdir / filename


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_stores() -> pd.DataFrame:
    return pd.read_csv(data_path("stores.csv"))


@st.cache_data(show_spinner=False)
def load_employees() -> pd.DataFrame:
    return pd.read_csv(data_path("employees.csv"))


@st.cache_data(show_spinner=False)
def load_leave_types() -> pd.DataFrame:
    return pd.read_csv(data_path("leave_types.csv"))


@st.cache_data(show_spinner=False)
def load_leave_transactions() -> pd.DataFrame:
    return pd.read_csv(data_path("leave_transactions.csv"))


@st.cache_data(show_spinner=False)
def load_rosters() -> pd.DataFrame:
    return pd.read_csv(data_path("rosters.csv"))


@st.cache_data(show_spinner=False)
def load_demand() -> pd.DataFrame:
    return pd.read_csv(data_path("demand.csv"))


@st.cache_data(show_spinner=False)
def load_remuneration_components() -> pd.DataFrame:
    return pd.read_csv(data_path("remuneration_components.csv"))


@st.cache_data(show_spinner=False)
def load_calendar() -> pd.DataFrame:
    return pd.read_csv(data_path("calendar_nz.csv"))


@st.cache_data(show_spinner=False)
def load_manifest() -> dict:
    import json
    with open(data_path("_manifest.json"), "r") as f:
        return json.load(f)


# --- Leave engine outputs ---
@st.cache_data(show_spinner=False)
def load_current_balances() -> pd.DataFrame:
    return pd.read_csv(output_path("leave_balances", "current_balances.csv"))


@st.cache_data(show_spinner=False)
def load_balance_projections() -> pd.DataFrame:
    return pd.read_csv(output_path("leave_balances", "balance_projections.csv"))


@st.cache_data(show_spinner=False)
def load_balance_explanations() -> str:
    return (output_path("leave_balances", "balance_explanations.txt")).read_text(
        encoding="utf-8"
    )


# --- Remuneration outputs ---
@st.cache_data(show_spinner=False)
def load_cost_summary() -> pd.DataFrame:
    return pd.read_csv(output_path("costing_scenarios", "cost_summary.csv"))


@st.cache_data(show_spinner=False)
def load_cost_breakdown() -> pd.DataFrame:
    return pd.read_csv(output_path("costing_scenarios", "cost_breakdown.csv"))


@st.cache_data(show_spinner=False)
def load_scenario_comparison() -> pd.DataFrame:
    return pd.read_csv(output_path("costing_scenarios", "scenario_comparison.csv"))


# --- Capacity outputs ---
@st.cache_data(show_spinner=False)
def load_capacity_gaps() -> pd.DataFrame:
    return pd.read_csv(output_path("capacity_reports", "capacity_gaps.csv"))


@st.cache_data(show_spinner=False)
def load_roster_suggestions() -> pd.DataFrame:
    return pd.read_csv(output_path("capacity_reports", "roster_suggestions.csv"))


@st.cache_data(show_spinner=False)
def load_capacity_by_store() -> pd.DataFrame:
    return pd.read_csv(output_path("capacity_reports", "capacity_by_store.csv"))


@st.cache_data(show_spinner=False)
def load_capacity_by_status() -> pd.DataFrame:
    return pd.read_csv(output_path("capacity_reports", "capacity_by_status.csv"))


# --- Scorecard outputs ---
@st.cache_data(show_spinner=False)
def load_programme_metrics() -> pd.DataFrame:
    return pd.read_csv(output_path("scorecards", "programme_metrics.csv"))


@st.cache_data(show_spinner=False)
def load_store_metrics() -> pd.DataFrame:
    return pd.read_csv(output_path("scorecards", "store_metrics.csv"))


@st.cache_data(show_spinner=False)
def load_alerts() -> pd.DataFrame:
    return pd.read_csv(output_path("scorecards", "alerts.csv"))


@st.cache_data(show_spinner=False)
def load_scorecard_report() -> str:
    return (output_path("scorecards", "scorecard_report.txt")).read_text(
        encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Derived data helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def employee_demographics() -> pd.DataFrame:
    """Compute employee demographics summary by employment type."""
    emp = load_employees()
    summary = (
        emp.groupby("employment_type")
        .agg(
            count=("employee_id", "count"),
            avg_hours=("contracted_hours_per_week", "mean"),
            avg_rate=("base_hourly_rate", "mean"),
            avg_flex=("flexibility_preference", "mean"),
        )
        .reset_index()
    )
    summary["pct"] = summary["count"] / summary["count"].sum() * 100
    return summary


@st.cache_data(show_spinner=False)
def employee_by_role() -> pd.DataFrame:
    """Employee counts and rates by role."""
    emp = load_employees()
    summary = (
        emp.groupby("role")
        .agg(
            count=("employee_id", "count"),
            avg_rate=("base_hourly_rate", "mean"),
        )
        .reset_index()
        .sort_values("count", ascending=False)
    )
    return summary


@st.cache_data(show_spinner=False)
def store_summary() -> pd.DataFrame:
    """Join stores with employee counts."""
    stores = load_stores()
    emp = load_employees()
    counts = emp.groupby("store_id").size().reset_index(name="headcount")
    return stores.merge(counts, on="store_id", how="left")


@st.cache_data(show_spinner=False)
def demand_by_dow() -> pd.DataFrame:
    """Average demand by day of week."""
    dem = load_demand()
    day_names = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
        4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    dem["day_name"] = dem["day_of_week"].map(day_names)
    summary = (
        dem.groupby(["day_name", "day_of_week"])
        .agg(
            avg_demand=("demand_index", "mean"),
            avg_sales=("sales_amount", "mean"),
            avg_transactions=("transaction_count", "mean"),
        )
        .reset_index()
        .sort_values("day_of_week")
    )
    return summary


@st.cache_data(show_spinner=False)
def demand_by_month() -> pd.DataFrame:
    """Average demand by month."""
    dem = load_demand()
    dem["month"] = pd.to_datetime(dem["date"]).dt.month
    summary = (
        dem.groupby("month")
        .agg(
            avg_demand=("demand_index", "mean"),
            avg_sales=("sales_amount", "mean"),
            avg_transactions=("transaction_count", "mean"),
        )
        .reset_index()
    )
    return summary


@st.cache_data(show_spinner=False)
def cost_by_role() -> pd.DataFrame:
    """Aggregate costs by role."""
    cs = load_cost_summary()
    summary = (
        cs.groupby("role")
        .agg(
            headcount=("employee_id", "count"),
            total_annual=("annual_cost", "sum"),
            avg_loaded_rate=("fully_loaded_cost_per_hour", "mean"),
            avg_base_rate=("base_hourly_rate", "mean"),
        )
        .reset_index()
        .sort_values("total_annual", ascending=False)
    )
    return summary


@st.cache_data(show_spinner=False)
def cost_by_employment_type() -> pd.DataFrame:
    """Aggregate costs by employment type."""
    cs = load_cost_summary()
    summary = (
        cs.groupby("employment_type")
        .agg(
            headcount=("employee_id", "count"),
            total_annual=("annual_cost", "sum"),
            avg_loaded_rate=("fully_loaded_cost_per_hour", "mean"),
            avg_weekly=("weekly_cost", "mean"),
        )
        .reset_index()
    )
    return summary


@st.cache_data(show_spinner=False)
def cost_by_store() -> pd.DataFrame:
    """Aggregate costs by store."""
    cs = load_cost_summary()
    summary = (
        cs.groupby("store_id")
        .agg(
            headcount=("employee_id", "count"),
            total_annual=("annual_cost", "sum"),
            avg_loaded_rate=("fully_loaded_cost_per_hour", "mean"),
        )
        .reset_index()
        .sort_values("total_annual", ascending=False)
    )
    return summary


@st.cache_data(show_spinner=False)
def leave_balance_summary() -> pd.DataFrame:
    """Summarise current leave balances by leave code."""
    cb = load_current_balances()
    summary = (
        cb.groupby("leave_code")
        .agg(
            employees=("employee_id", "nunique"),
            avg_balance_hours=("balance_hours", "mean"),
            avg_balance_days=("balance_days", "mean"),
            total_balance_hours=("balance_hours", "sum"),
            total_accrued=("accrued_hours", "sum"),
            total_taken=("taken_hours", "sum"),
        )
        .reset_index()
    )
    return summary


@st.cache_data(show_spinner=False)
def leave_balance_by_emp_type() -> pd.DataFrame:
    """Current balances by employment type and leave code."""
    cb = load_current_balances()
    summary = (
        cb.groupby(["employment_type", "leave_code"])
        .agg(
            avg_balance_days=("balance_days", "mean"),
            avg_balance_hours=("balance_hours", "mean"),
            count=("employee_id", "nunique"),
        )
        .reset_index()
    )
    return summary


@st.cache_data(show_spinner=False)
def capacity_by_store_status() -> pd.DataFrame:
    """Pivot capacity gaps by store and status."""
    gaps = load_capacity_gaps()
    summary = (
        gaps.groupby(["store_id", "status"])
        .size()
        .reset_index(name="count")
        .pivot(index="store_id", columns="status", values="count")
        .fillna(0)
        .reset_index()
    )
    return summary


@st.cache_data(show_spinner=False)
def capacity_by_role_status() -> pd.DataFrame:
    """Capacity status counts by role."""
    gaps = load_capacity_gaps()
    summary = (
        gaps.groupby(["role", "status"])
        .size()
        .reset_index(name="count")
        .pivot(index="role", columns="status", values="count")
        .fillna(0)
        .reset_index()
    )
    return summary


@st.cache_data(show_spinner=False)
def roster_hours_by_month() -> pd.DataFrame:
    """Total roster hours by month."""
    ros = load_rosters()
    ros["month"] = pd.to_datetime(ros["work_date"]).dt.month
    summary = (
        ros.groupby("month")
        .agg(
            total_hours=("hours_worked", "sum"),
            avg_hours=("hours_worked", "mean"),
            shifts=("roster_id", "count"),
        )
        .reset_index()
    )
    return summary


@st.cache_data(show_spinner=False)
def roster_hours_by_dow() -> pd.DataFrame:
    """Total roster hours by day of week."""
    ros = load_rosters()
    ros["dow"] = pd.to_datetime(ros["work_date"]).dt.dayofweek
    day_names = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
        4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    ros["day_name"] = ros["dow"].map(day_names)
    summary = (
        ros.groupby(["day_name", "dow"])
        .agg(total_hours=("hours_worked", "sum"), shifts=("roster_id", "count"))
        .reset_index()
        .sort_values("dow")
    )
    return summary


# ---------------------------------------------------------------------------
# Styling helpers
# ---------------------------------------------------------------------------
def metric_card(label: str, value: str, delta: Optional[str] = None, color: str = "#1f77b4"):
    """Render a metric card using Streamlit's column layout."""
    return {"label": label, "value": value, "delta": delta, "color": color}


def format_nzd(value: float) -> str:
    """Format a number as NZD."""
    return f"${value:,.0f}"


def format_pct(value: float) -> str:
    """Format a ratio as a percentage string."""
    return f"{value * 100:.1f}%"