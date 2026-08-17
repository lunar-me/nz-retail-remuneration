"""
NZ Retail Remuneration & Workforce Programme — Streamlit Visualisation App
============================================================================
This app visualises the pre-calculated outputs of the programme. It does NOT
run any engines — all data is loaded from the pre-computed artifacts in
`data/synthetic/v1/` and `outputs/`.

Sections:
  1. Overview         — project intro, architecture, key facts
  2. Synthetic Data   — the 8 data tables, demographics, demand patterns
  3. Leave Engine     — balances, projections, explanations
  4. Remuneration     — cost breakdown, scenarios
  5. Capacity         — gap analysis, roster suggestions
  6. Scorecard        — health metrics, alerts

Run with:  streamlit run app/app.py
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure app/ is on path so `import utils` works
sys.path.insert(0, str(Path(__file__).resolve().parent))

import utils  # noqa: E402

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NZ Retail Remuneration & Workforce",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom theme colours
COLORS = {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "success": "#3A7D44",
    "warning": "#E9C46A",
    "danger": "#D64550",
    "neutral": "#6C757D",
    "bg": "#F8F9FA",
}

# Status colour mapping for consistency
STATUS_COLORS = {
    "OK": "#3A7D44",
    "WARNING": "#E9C46A",
    "CRITICAL": "#D64550",
    "MEDIUM": "#E9C46A",
    "HIGH": "#D64550",
}

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F8F9FA;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #2E86AB;
        margin-bottom: 0.2rem;
    }
    .main-subheader {
        font-size: 1.1rem;
        color: #6C757D;
        margin-bottom: 1.5rem;
    }
    .section-header {
        font-size: 1.6rem;
        font-weight: 600;
        color: #2E86AB;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
        border-bottom: 2px solid #2E86AB;
        padding-bottom: 0.3rem;
    }
    .sub-section {
        font-size: 1.2rem;
        font-weight: 500;
        color: #343A40;
        margin-top: 1rem;
    }
    .info-box {
        background-color: #E3F2FD;
        border-left: 4px solid #2E86AB;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #E8F5E9;
        border-left: 4px solid #3A7D44;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .warning-box {
        background-color: #FFF8E1;
        border-left: 4px solid #E9C46A;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .danger-box {
        background-color: #FDECEA;
        border-left: 4px solid #D64550;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2E86AB;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6C757D;
    }
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Shared helper functions
# ---------------------------------------------------------------------------
def render_metric(label: str, value: str, help_text: str = ""):
    """Render a single metric in a column."""
    st.metric(label=label, value=value, help=help_text)


def status_badge(status: str) -> str:
    """Return a colour-coded HTML badge for a status."""
    colour = STATUS_COLORS.get(status, COLORS["neutral"])
    return f'<span class="status-badge" style="background-color:{colour}22;color:{colour};border:1px solid {colour};">{status}</span>'


def explain_box(text: str, box_type: str = "info"):
    """Render an explanation box with a specific style."""
    css_class = {
        "info": "info-box",
        "success": "success-box",
        "warning": "warning-box",
        "danger": "danger-box",
    }.get(box_type, "info-box")
    st.markdown(f'<div class="{css_class}">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page: Overview
# ---------------------------------------------------------------------------
def page_overview():
    st.markdown('<div class="main-header">NZ Retail Remuneration & Workforce Programme</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subheader">A synthetic-data-driven workforce programme for New Zealand retail — leave, remuneration, capacity, and scorecard.</div>',
        unsafe_allow_html=True,
    )

    # --- Hero metrics ---
    manifest = utils.load_manifest()
    programme = utils.load_programme_metrics()
    pm = {row["metric"]: row["value"] for _, row in programme.iterrows()}

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_metric("Employees", f"{pm.get('headcount', 0):,.0f}", "Total synthetic workforce")
    with c2:
        render_metric("Stores", f"{manifest['tables']['stores']}", "Retail locations across NZ")
    with c3:
        render_metric("Total Cost", f"${pm.get('total_annual_cost', 0):,.0f}", "Fully-loaded annual cost")
    with c4:
        render_metric("Avg Loaded Rate", f"${pm.get('avg_fully_loaded_rate', 0):.2f}/hr", "Average fully-loaded hourly rate")
    with c5:
        render_metric("Leave Txns", f"{manifest['tables']['leave_transactions']:,}", "Total leave transactions")

    st.markdown("---")

    st.markdown('<div class="section-header">What This Programme Does</div>', unsafe_allow_html=True)

    explain_box(
        "This repository delivers a complete, <b>privacy-safe</b>, data-driven workforce programme built entirely on "
        "<b>synthetic data</b>. No real employee or commercial data is used. It provides four interconnected engines: "
        "leave entitlements (NZ Holidays Act 2003 oriented), transparent remuneration costing with what-if scenarios, "
        "demand-driven capacity planning, and an integrated scorecard with exception alerts."
    )

    # Engine cards
    engines = [
        {
            "icon": "🗄️",
            "title": "Synthetic Data Layer",
            "desc": "8 versioned NZ retail tables: 650 employees, 12 stores, 122k leave transactions, 181k roster shifts, 8.8k demand records, and a full NZ calendar.",
            "metric": "8 tables · fixed seed 42",
        },
        {
            "icon": "🏖️",
            "title": "Leave Engine",
            "desc": "Holidays Act 2003-oriented accrual and balance engine. Computes current balances, 52-week projections, and human-readable explanations for every balance.",
            "metric": "3 leave types · 1,950 balances",
        },
        {
            "icon": "💰",
            "title": "Remuneration Costing",
            "desc": "Fully-loaded hourly and annual costs — base pay + KiwiSaver + leave value + insurance + flexibility premium. Seven what-if scenarios quantify package changes.",
            "metric": "$23.2M total · 7 scenarios",
        },
        {
            "icon": "📊",
            "title": "Capacity Planner",
            "desc": "Converts demand signals into required labour hours, overlays available hours after leave, and identifies capacity gaps by store, day, and role.",
            "metric": "2,520 gap rows · 12 stores",
        },
        {
            "icon": "📋",
            "title": "Scorecard & Alerting",
            "desc": "One view of total-reward health and workforce availability. Threshold-based alerts flag leave liability, insurance take-up, flexibility, and capacity exceptions.",
            "metric": "6 programme metrics · 2 alerts",
        },
    ]

    for i in range(0, len(engines), 2):
        cols = st.columns(2)
        for col, eng in zip(cols, engines[i : i + 2]):
            with col:
                st.markdown(
                    f"""
                    <div style="border:1px solid #DEE2E6;border-radius:8px;padding:1rem;margin:0.5rem 0;background:white;">
                        <div style="font-size:1.5rem;">{eng['icon']} <b>{eng['title']}</b></div>
                        <div style="color:#495057;margin:0.5rem 0;">{eng['desc']}</div>
                        <div style="color:#2E86AB;font-weight:600;font-size:0.9rem;">{eng['metric']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown('<div class="section-header">Programme Architecture</div>', unsafe_allow_html=True)

    explain_box(
        "The synthetic data layer feeds four downstream engines. Each engine consumes versioned CSV tables and produces "
        "pre-calculated reports. This Streamlit app visualises those pre-computed outputs — it does not run any calculations."
    )

    # Architecture diagram (simplified)
    fig = go.Figure()
    # Data layer node
    fig.add_trace(
        go.Scatter(
            x=[0.5],
            y=[1.0],
            mode="text",
            text=["<b>SYNTHETIC DATA LAYER</b><br>8 tables · 650 employees · 12 stores"],
            textfont=dict(size=14, color="white"),
            hoverinfo="text",
        )
    )
    fig.add_shape(
        type="rect",
        x0=0.1, y0=0.85, x1=0.9, y1=1.15,
        line=dict(color="#2E86AB", width=2),
        fillcolor="rgba(46,134,171,0.8)",
        layer="below",
    )

    # Engine nodes
    engines_list = [
        ("LEAVE ENGINE", 0.1),
        ("REMUNERATION", 0.35),
        ("CAPACITY PLANNER", 0.6),
        ("SCORECARD", 0.85),
    ]
    for name, xpos in engines_list:
        fig.add_shape(
            type="rect",
            x0=xpos - 0.13, y0=0.45, x1=xpos + 0.13, y1=0.75,
            line=dict(color="#A23B72", width=2),
            fillcolor="rgba(162,59,114,0.8)",
            layer="below",
        )
        fig.add_trace(
            go.Scatter(
                x=[xpos], y=[0.6], mode="text",
                text=[f"<b>{name}</b>"],
                textfont=dict(size=11, color="white"),
                hoverinfo="none",
            )
        )

    # Connecting lines
    for xpos in [e[1] for e in engines_list]:
        fig.add_shape(
            type="line",
            x0=0.5, y0=0.85, x1=xpos, y1=0.75,
            line=dict(color="#6C757D", width=1.5, dash="dot"),
        )

    fig.update_layout(
        height=300,
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[0, 1.3]),
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width='stretch')

    st.markdown('<div class="section-header">Key Principles</div>', unsafe_allow_html=True)

    principles = [
        ("🔒", "Privacy First", "Only synthetic data is used — no real employee or commercial data."),
        ("🧮", "Calculation Logic Over Dashboards", "Models and engines are the primary deliverables; dashboards visualise the outcomes."),
        ("🇳🇿", "NZ Retail Context", "Leave rules, employment mixes, demand patterns, and calendar are tailored to NZ."),
        ("🔁", "Reproducibility", "Fixed seeds (42) and versioned datasets ensure byte-identical regeneration."),
        ("📖", "Transparency", "Every major assumption is documented and configurable in YAML files."),
    ]

    for icon, title, desc in principles:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;margin:0.5rem 0;">
                <span style="font-size:1.5rem;margin-right:0.75rem;">{icon}</span>
                <div>
                    <div style="font-weight:600;">{title}</div>
                    <div style="color:#6C757D;">{desc}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption(
        f"Data generated: {manifest.get('generated_at', 'Unknown')} | "
        f"Seed: {manifest.get('seed', 'Unknown')} | "
        f"Version: {manifest.get('version', 'Unknown')}"
    )


# ---------------------------------------------------------------------------
# Page: Synthetic Data
# ---------------------------------------------------------------------------
def page_synthetic_data():
    st.markdown('<div class="main-header">Synthetic Data Layer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subheader">Explore the versioned, reproducible dataset that powers all four engines.</div>',
        unsafe_allow_html=True,
    )

    manifest = utils.load_manifest()

    # Overview metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Data Version", f"v{manifest['version']}", "Versioned dataset")
    with c2:
        render_metric("Seed", f"{manifest['seed']}", "Fixed random seed for reproducibility")
    with c3:
        render_metric("Date Range", f"{manifest['start_date']} → {manifest['end_date']}", "24 months of data")
    with c4:
        render_metric("Time Zone", manifest["timezone"].split("/")[-1], "NZ timezone")

    st.markdown("---")

    st.markdown('<div class="section-header">Table Inventory</div>', unsafe_allow_html=True)

    explain_box(
        "All data is generated from configurable rules in <code>configs/synthetic_data.yaml</code> with a fixed random seed (42). "
        "Running the generator again produces byte-identical output — essential for auditable calculations and regression testing."
    )

    tables = pd.DataFrame(
        [
            {"Table": "stores", "Rows": manifest["tables"]["stores"], "Description": "Retail locations with regions, formats, and trading hours"},
            {"Table": "employees", "Rows": manifest["tables"]["employees"], "Description": "Employee master data — roles, employment types, hours, rates"},
            {"Table": "leave_types", "Rows": manifest["tables"]["leave_types"], "Description": "Static reference for leave codes and accrual rules"},
            {"Table": "leave_transactions", "Rows": manifest["tables"]["leave_transactions"], "Description": "Accrual and usage history for every employee"},
            {"Table": "rosters", "Rows": manifest["tables"]["rosters"], "Description": "Worked shifts with hours, roles, and penalty flags"},
            {"Table": "demand", "Rows": manifest["tables"]["demand"], "Description": "Daily demand proxies — index, transactions, sales"},
            {"Table": "remuneration_components", "Rows": manifest["tables"]["remuneration_components"], "Description": "Per-employee cost components — KiwiSaver, leave, insurance, flexibility"},
            {"Table": "calendar_nz", "Rows": manifest["tables"]["calendar_nz"], "Description": "NZ calendar — public holidays, school terms, retail peaks"},
        ]
    )
    st.dataframe(tables, width='stretch', hide_index=True)

    st.markdown('<div class="section-header">Employee Demographics</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        demo = utils.employee_demographics()
        fig = px.pie(
            demo,
            names="employment_type",
            values="count",
            title="Workforce by Employment Type",
            color_discrete_sequence=["#2E86AB", "#A23B72", "#3A7D44"],
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    with c2:
        roles = utils.employee_by_role()
        fig = px.bar(
            roles,
            x="role",
            y="count",
            title="Headcount by Role",
            color="count",
            color_continuous_scale="Blues",
            labels={"count": "Employees", "role": ""},
        )
        fig.update_layout(height=380, xaxis_tickangle=-30)
        st.plotly_chart(fig, width='stretch')

    # Demographics detail table
    st.markdown('<div class="sub-section">Demographic Summary</div>', unsafe_allow_html=True)
    st.dataframe(
        demo.rename(
            columns={
                "employment_type": "Employment Type",
                "count": "Count",
                "pct": "% of Workforce",
                "avg_hours": "Avg Hours/Week",
                "avg_rate": "Avg Base Rate ($/hr)",
                "avg_flex": "Avg Flexibility",
            }
        ),
        width='stretch',
        hide_index=True,
    )

    st.markdown('<div class="section-header">Demand Patterns</div>', unsafe_allow_html=True)

    explain_box(
        "Demand is the primary driver for the Capacity Planner. The synthetic data encodes realistic NZ retail patterns: "
        "weekend peaks, Christmas uplift, public holiday boosts, and school-term effects — all with configurable multipliers."
    )

    c1, c2 = st.columns(2)

    with c1:
        dow = utils.demand_by_dow()
        fig = px.bar(
            dow,
            x="day_name",
            y="avg_demand",
            title="Average Demand by Day of Week",
            color="avg_demand",
            color_continuous_scale="Blues",
            labels={"avg_demand": "Demand Index", "day_name": ""},
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    with c2:
        mon = utils.demand_by_month()
        month_names = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
        }
        mon["month_name"] = mon["month"].map(month_names)
        fig = px.line(
            mon,
            x="month_name",
            y="avg_demand",
            title="Average Demand by Month (Seasonality)",
            markers=True,
            color_discrete_sequence=["#2E86AB"],
            labels={"avg_demand": "Demand Index", "month_name": ""},
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    st.markdown('<div class="section-header">Roster Activity</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        ros_month = utils.roster_hours_by_month()
        ros_month["month_name"] = ros_month["month"].map(month_names)
        fig = px.bar(
            ros_month,
            x="month_name",
            y="total_hours",
            title="Total Roster Hours by Month",
            color="total_hours",
            color_continuous_scale="Purples",
            labels={"total_hours": "Hours", "month_name": ""},
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    with c2:
        ros_dow = utils.roster_hours_by_dow()
        fig = px.bar(
            ros_dow,
            x="day_name",
            y="total_hours",
            title="Total Roster Hours by Day of Week",
            color="total_hours",
            color_continuous_scale="Purples",
            labels={"total_hours": "Hours", "day_name": ""},
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    st.markdown('<div class="section-header">Store Network</div>', unsafe_allow_html=True)

    stores = utils.store_summary()

    # Store table with key attributes
    store_display = stores[
        ["store_id", "store_name", "region", "format", "size_band", "trading_pattern", "headcount", "is_tight_capacity"]
    ].rename(
        columns={
            "store_id": "ID",
            "store_name": "Name",
            "region": "Region",
            "format": "Format",
            "size_band": "Size Band",
            "trading_pattern": "Trading Pattern",
            "headcount": "Headcount",
            "is_tight_capacity": "Tight Capacity",
        }
    )
    store_display["Tight Capacity"] = store_display["Tight Capacity"].map({True: "⚠️ Yes", False: "—"})
    st.dataframe(store_display, width='stretch', hide_index=True)

    # Store size chart
    fig = px.bar(
        stores.sort_values("headcount", ascending=False),
        x="store_name",
        y="headcount",
        title="Headcount by Store",
        color="region",
        labels={"store_name": "", "headcount": "Employees", "region": "Region"},
    )
    fig.update_layout(height=400, xaxis_tickangle=-30)
    st.plotly_chart(fig, width='stretch')


# ---------------------------------------------------------------------------
# Page: Leave Engine
# ---------------------------------------------------------------------------
def page_leave_engine():
    st.markdown('<div class="main-header">Leave Entitlement & Accrual Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subheader">Holidays Act 2003-oriented leave balances, projections, and explanations.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

    explain_box(
        "The Leave Engine is the <b>compliance-critical foundation</b> for leave balance management. It encodes simplified "
        "NZ Holidays Act 2003 concepts — <b>4 weeks annual leave after 12 months</b>, <b>10 days sick leave after 6 months</b>, "
        "and <b>3 days bereavement</b> — with pro-rated accrual for part-time and casual staff. Every balance is auditable: "
        "each employee's full transaction history explains exactly how their balance was reached."
    )

    balances = utils.load_current_balances()
    leave_types = utils.load_leave_types()
    projections = utils.load_balance_projections()

    # Key metrics
    annual = balances[balances["leave_code"] == "ANNUAL"]
    sick = balances[balances["leave_code"] == "SICK"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Employees", f"{balances['employee_id'].nunique():,}", "Employees with balances")
    with c2:
        render_metric("Avg Annual (days)", f"{annual['balance_days'].mean():.1f}", "Average annual leave balance in days")
    with c3:
        render_metric("Avg Sick (days)", f"{sick['balance_days'].mean():.1f}", "Average sick leave balance in days")
    with c4:
        render_metric("Total Annual Hours", f"{annual['balance_hours'].sum():,.0f}", "Total annual leave liability in hours")

    st.markdown('<div class="section-header">Leave Types & Rules</div>', unsafe_allow_html=True)

    explain_box(
        "Leave rules are defined in <code>configs/leave_rules.yaml</code>. Annual leave accrues weekly at 3.08 hours/week "
        "(≈4 weeks on a 40-hour week), capped at 8 weeks. Sick leave accrues at 10 days/year, capped at 20 days. "
        "Bereavement is 3 days/year with no cap. Accrual is pro-rated by contracted hours for part-time and casual staff."
    )

    leave_types_display = leave_types[
        ["leave_code", "leave_name", "is_paid", "carries_over", "accrual_rate_hours_per_week", "accrual_rate_days_per_year", "max_balance_weeks", "max_balance_days"]
    ].rename(
        columns={
            "leave_code": "Code",
            "leave_name": "Name",
            "is_paid": "Paid",
            "carries_over": "Carries Over",
            "accrual_rate_hours_per_week": "Accrual (hrs/wk)",
            "accrual_rate_days_per_year": "Accrual (days/yr)",
            "max_balance_weeks": "Max Balance (wks)",
            "max_balance_days": "Max Balance (days)",
        }
    )
    leave_types_display["Paid"] = leave_types_display["Paid"].map({True: "✅ Yes", False: "❌ No"})
    leave_types_display["Carries Over"] = leave_types_display["Carries Over"].map({True: "✅ Yes", False: "❌ No"})
    st.dataframe(leave_types_display, width='stretch', hide_index=True)

    st.markdown('<div class="section-header">Balance Summary</div>', unsafe_allow_html=True)

    bal_summary = utils.leave_balance_summary()
    bal_display = bal_summary.rename(
        columns={
            "leave_code": "Leave Type",
            "employees": "Employees",
            "avg_balance_hours": "Avg Balance (hrs)",
            "avg_balance_days": "Avg Balance (days)",
            "total_balance_hours": "Total Balance (hrs)",
            "total_accrued": "Total Accrued (hrs)",
            "total_taken": "Total Taken (hrs)",
        }
    )
    st.dataframe(bal_display, width='stretch', hide_index=True)

    # Balance distribution chart
    c1, c2 = st.columns(2)

    with c1:
        fig = px.histogram(
            balances[balances["leave_code"] == "ANNUAL"],
            x="balance_days",
            nbins=30,
            title="Annual Leave Balance Distribution (days)",
            color_discrete_sequence=["#2E86AB"],
            labels={"balance_days": "Balance (days)", "count": "Employees"},
        )
        fig.add_vline(x=30, line_dash="dash", line_color="#E9C46A", annotation_text="Warning: 30d")
        fig.add_vline(x=50, line_dash="dash", line_color="#D64550", annotation_text="Critical: 50d")
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    with c2:
        fig = px.histogram(
            balances[balances["leave_code"] == "SICK"],
            x="balance_days",
            nbins=30,
            title="Sick Leave Balance Distribution (days)",
            color_discrete_sequence=["#A23B72"],
            labels={"balance_days": "Balance (days)", "count": "Employees"},
        )
        fig.add_vline(x=20, line_dash="dash", line_color="#D64550", annotation_text="Max: 20d")
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    # Balance by employment type
    st.markdown('<div class="sub-section">Average Balances by Employment Type</div>', unsafe_allow_html=True)

    by_type = utils.leave_balance_by_emp_type()
    fig = px.bar(
        by_type[by_type["leave_code"].isin(["ANNUAL", "SICK"])],
        x="leave_code",
        y="avg_balance_days",
        color="employment_type",
        barmode="group",
        title="Average Leave Balance (days) by Employment Type",
        color_discrete_sequence=["#2E86AB", "#A23B72", "#3A7D44"],
        labels={"avg_balance_days": "Avg Balance (days)", "leave_code": "", "employment_type": ""},
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, width='stretch')

    st.markdown('<div class="section-header">Balance Projections</div>', unsafe_allow_html=True)

    explain_box(
        "The engine projects each employee's balance 52 weeks forward, applying weekly accrual rates and enforcing balance caps. "
        "This is useful for leave liability forecasting and annual planning."
    )

    c1, c2 = st.columns(2)

    with c1:
        # Employee selector for projections
        emp_ids = sorted(projections["employee_id"].unique())
        selected_emp = st.selectbox("Select Employee ID", emp_ids, key="proj_emp")
        emp_proj = projections[projections["employee_id"] == selected_emp]

        fig = go.Figure()
        for code in ["ANNUAL", "SICK"]:
            subset = emp_proj[emp_proj["leave_code"] == code]
            if not subset.empty:
                fig.add_trace(
                    go.Bar(
                        x=[code],
                        y=[subset["current_balance_hours"].iloc[0]],
                        name=f"{code} Current",
                        marker_color="#2E86AB",
                        text=[f"{subset['current_balance_hours'].iloc[0]:.1f} h"],
                        textposition="outside",
                    )
                )
                fig.add_trace(
                    go.Bar(
                        x=[code],
                        y=[subset["projected_hours"].iloc[0]],
                        name=f"{code} Projected (52wk)",
                        marker_color="#A23B72",
                        text=[f"{subset['projected_hours'].iloc[0]:.1f} h"],
                        textposition="outside",
                    )
                )
        fig.update_layout(
            title=f"Employee {selected_emp} — Current vs Projected Balance",
            barmode="group",
            height=380,
            yaxis_title="Hours",
        )
        st.plotly_chart(fig, width='stretch')

        # Show projection details
        proj_display = emp_proj[
            ["leave_code", "current_balance_hours", "projected_hours", "weekly_accrual_hours", "projected_date"]
        ].rename(
            columns={
                "leave_code": "Type",
                "current_balance_hours": "Current (hrs)",
                "projected_hours": "Projected (hrs)",
                "weekly_accrual_hours": "Weekly Accrual (hrs)",
                "projected_date": "Projected To",
            }
        )
        st.dataframe(proj_display, width='stretch', hide_index=True)

    with c2:
        # Aggregate projection summary
        proj_agg = (
            projections.groupby("leave_code")
            .agg(
                avg_current=("current_balance_hours", "mean"),
                avg_projected=("projected_hours", "mean"),
            )
            .reset_index()
        )
        fig = go.Figure()
        for code in proj_agg["leave_code"]:
            row = proj_agg[proj_agg["leave_code"] == code].iloc[0]
            fig.add_trace(
                go.Bar(
                    x=[f"{code}"],
                    y=[row["avg_current"]],
                    name="Current",
                    marker_color="#2E86AB",
                    text=[f"{row['avg_current']:.1f}"],
                    textposition="outside",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=[f"{code}"],
                    y=[row["avg_projected"]],
                    name="Projected 52wk",
                    marker_color="#A23B72",
                    text=[f"{row['avg_projected']:.1f}"],
                    textposition="outside",
                )
            )
        fig.update_layout(
            title="Average Balance — Current vs Projected (All Employees)",
            barmode="group",
            height=380,
            yaxis_title="Hours",
        )
        st.plotly_chart(fig, width='stretch')

        explain_box(
            "Projected balances account for weekly accrual and cap enforcement. The gap between current and projected "
            "shows how much leave liability will grow over the next year if usage stays at current levels."
        )

    st.markdown('<div class="section-header">Balance Explanations</div>', unsafe_allow_html=True)

    explain_box(
        "Every balance is fully explainable. The engine produces human-readable reports showing the calculation path: "
        "employment type, contracted hours, start date, eligibility, pay method, and weekly accrual rate."
    )

    explanations = utils.load_balance_explanations()
    with st.expander("View Sample Balance Explanations", expanded=False):
        st.text(explanations[:4000])


# ---------------------------------------------------------------------------
# Page: Remuneration
# ---------------------------------------------------------------------------
def page_remuneration():
    st.markdown('<div class="main-header">Remuneration Costing & Scenarios</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subheader">Transparent, fully-loaded package costs with what-if scenario modelling.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

    explain_box(
        "The Remuneration engine calculates the <b>true cost of a competitive NZ retail package</b> — base pay + KiwiSaver + "
        "leave value + insurance + flexibility premium. It quantifies what-if scenario impacts before package changes are "
        "promised to employees. All assumptions are configurable in <code>configs/costing_assumptions.yaml</code>."
    )

    cost_summary = utils.load_cost_summary()
    breakdown = utils.load_cost_breakdown()
    scenarios = utils.load_scenario_comparison()

    # Key metrics
    total_cost = breakdown[breakdown["component"] == "total"]["annual_cost"].iloc[0]
    base_cost = breakdown[breakdown["component"] == "base_pay"]["annual_cost"].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Total Annual Cost", f"${total_cost:,.0f}", "Fully-loaded annual cost for 650 employees")
    with c2:
        render_metric("Base Pay Share", f"{base_cost / total_cost * 100:.1f}%", "Portion of cost from base pay")
    with c3:
        render_metric("Avg Loaded Rate", f"${cost_summary['fully_loaded_cost_per_hour'].mean():.2f}/hr", "Average fully-loaded hourly rate")
    with c4:
        render_metric("Avg Base Rate", f"${cost_summary['base_hourly_rate'].mean():.2f}/hr", "Average base hourly rate")

    st.markdown('<div class="section-header">Cost Breakdown</div>', unsafe_allow_html=True)

    explain_box(
        "Fully-loaded cost per hour = <b>base rate</b> + <b>KiwiSaver (3%)</b> + <b>leave loading (8%)</b> + "
        "<b>insurance ($/month ÷ 160h)</b> + <b>flexibility premium (up to 6%)</b>. Annual cost = weekly cost × 52."
    )

    # Breakdown chart
    bd = breakdown[breakdown["component"] != "total"]
    component_labels = {
        "base_pay": "Base Pay",
        "kiwisaver": "KiwiSaver (3%)",
        "leave_loading": "Leave Loading (8%)",
        "insurance": "Insurance",
        "flexibility": "Flexibility Premium",
    }
    bd["label"] = bd["component"].map(component_labels)
    bd["pct"] = bd["annual_cost"] / total_cost * 100

    c1, c2 = st.columns(2)

    with c1:
        fig = px.pie(
            bd,
            names="label",
            values="annual_cost",
            title="Annual Cost by Component",
            color_discrete_sequence=["#2E86AB", "#3A7D44", "#A23B72", "#E9C46A", "#6C757D"],
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    with c2:
        bd_sorted = bd.sort_values("annual_cost", ascending=True)
        fig = px.bar(
            bd_sorted,
            x="annual_cost",
            y="label",
            orientation="h",
            title="Annual Cost by Component",
            color="annual_cost",
            color_continuous_scale="Blues",
            text=bd_sorted["annual_cost"].apply(lambda x: f"${x:,.0f}"),
            labels={"annual_cost": "Cost ($)", "label": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    # Component detail table
    st.markdown('<div class="sub-section">Component Detail</div>', unsafe_allow_html=True)
    st.dataframe(
        bd[["label", "annual_cost", "pct"]].rename(
            columns={"label": "Component", "annual_cost": "Annual Cost ($)", "pct": "% of Total"}
        ).assign(
            **{"Annual Cost ($)": lambda df: df["Annual Cost ($)"].apply(lambda x: f"${x:,.0f}"),
               "% of Total": lambda df: df["% of Total"].apply(lambda x: f"{x:.1f}%")}
        ),
        width='stretch',
        hide_index=True,
    )

    st.markdown('<div class="section-header">Costs by Role & Employment Type</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        by_role = utils.cost_by_role()
        fig = px.bar(
            by_role,
            x="role",
            y="total_annual",
            title="Total Annual Cost by Role",
            color="total_annual",
            color_continuous_scale="Blues",
            text=by_role["total_annual"].apply(lambda x: f"${x/1e6:.1f}M"),
            labels={"total_annual": "Cost ($)", "role": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=400, xaxis_tickangle=-30)
        st.plotly_chart(fig, width='stretch')

    with c2:
        by_type = utils.cost_by_employment_type()
        fig = px.bar(
            by_type,
            x="employment_type",
            y="total_annual",
            title="Total Annual Cost by Employment Type",
            color="employment_type",
            color_discrete_sequence=["#2E86AB", "#A23B72", "#3A7D44"],
            text=by_type["total_annual"].apply(lambda x: f"${x/1e6:.1f}M"),
            labels={"total_annual": "Cost ($)", "employment_type": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=400)
        st.plotly_chart(fig, width='stretch')

    # Cost by store
    st.markdown('<div class="sub-section">Cost by Store</div>', unsafe_allow_html=True)
    by_store = utils.cost_by_store()
    fig = px.bar(
        by_store,
        x="store_id",
        y="total_annual",
        title="Total Annual Cost by Store",
        color="avg_loaded_rate",
        color_continuous_scale="Purples",
        text=by_store["total_annual"].apply(lambda x: f"${x/1e6:.1f}M"),
        labels={"total_annual": "Cost ($)", "store_id": "Store ID", "avg_loaded_rate": "Avg Loaded Rate ($/hr)"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=400)
    st.plotly_chart(fig, width='stretch')

    st.markdown('<div class="section-header">Scenario Modelling</div>', unsafe_allow_html=True)

    explain_box(
        "The Scenario Engine models the cost impact of proposed package changes before they are committed. "
        "Each scenario adjusts one or more cost components and computes the annual impact across the full workforce."
    )

    # Scenario comparison chart
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=scenarios["scenario"],
            y=scenarios["total_annual_cost"],
            name="Total Cost",
            marker_color="#2E86AB",
            text=scenarios["total_annual_cost"].apply(lambda x: f"${x/1e6:.1f}M"),
            textposition="outside",
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=scenarios["scenario"],
            y=scenarios["annual_cost_impact"],
            name="Cost Impact",
            mode="lines+markers",
            line=dict(color="#D64550", width=2),
            marker=dict(size=8),
            yaxis="y2",
        )
    )
    fig.update_layout(
        title="Scenario Cost Impact",
        barmode="group",
        height=450,
        yaxis=dict(title="Total Cost ($)", title_font=dict(color="#2E86AB")),
        yaxis2=dict(title="Impact ($)", overlaying="y", side="right", title_font=dict(color="#D64550")),
        xaxis=dict(title=""),
    )
    st.plotly_chart(fig, width='stretch')

    # Scenario detail table
    st.markdown('<div class="sub-section">Scenario Comparison</div>', unsafe_allow_html=True)
    scenario_display = scenarios.rename(
        columns={
            "scenario": "Scenario",
            "description": "Description",
            "total_annual_cost": "Total Annual Cost ($)",
            "annual_cost_impact": "Cost Impact ($)",
            "pct_impact": "% Impact",
            "avg_fully_loaded_rate": "Avg Loaded Rate ($/hr)",
            "per_employee_annual_impact": "Per Employee Impact ($)",
        }
    )
    scenario_display = scenario_display.assign(
        **{
            "Total Annual Cost ($)": scenario_display["Total Annual Cost ($)"].apply(lambda x: f"${x:,.0f}"),
            "Cost Impact ($)": scenario_display["Cost Impact ($)"].apply(lambda x: f"${x:,.0f}"),
            "% Impact": scenario_display["% Impact"].apply(lambda x: f"{x:.1f}%"),
            "Avg Loaded Rate ($/hr)": scenario_display["Avg Loaded Rate ($/hr)"].apply(lambda x: f"${x:.2f}"),
            "Per Employee Impact ($)": scenario_display["Per Employee Impact ($)"].apply(lambda x: f"${x:,.2f}"),
        }
    )
    st.dataframe(scenario_display, width='stretch', hide_index=True)


# ---------------------------------------------------------------------------
# Page: Capacity
# ---------------------------------------------------------------------------
def page_capacity():
    st.markdown('<div class="main-header">Demand → Roster Capacity Planner</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subheader">Convert demand signals into labour requirements and identify capacity gaps.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

    explain_box(
        "The Capacity Planner converts demand indices into <b>required labour hours</b> using role-specific productivity "
        "standards, then compares them against <b>available hours</b> (contracted hours minus leave). Gaps are classified as "
        "<b>UNDER_CAPACITY</b>, <b>BALANCED</b>, or <b>OVER_CAPACITY</b> per store-day-role. The engine also generates roster "
        "suggestions that prefer high-flexibility employees."
    )

    gaps = utils.load_capacity_gaps()
    by_status = utils.load_capacity_by_status()
    by_store = utils.load_capacity_by_store()
    suggestions = utils.load_roster_suggestions()

    # Key metrics
    under_count = by_status[by_status["status"] == "UNDER_CAPACITY"]["count"].sum()
    over_count = by_status[by_status["status"] == "OVER_CAPACITY"]["count"].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Gap Rows", f"{len(gaps):,}", "Total store-day-role rows analysed")
    with c2:
        render_metric("Under Capacity", f"{under_count}", "Rows where available < required")
    with c3:
        render_metric("Over Capacity", f"{over_count}", "Rows where available > required")
    with c4:
        render_metric("Suggestions", f"{len(suggestions):,}", "Roster adjustment suggestions")

    st.markdown('<div class="section-header">Capacity Status Overview</div>', unsafe_allow_html=True)

    explain_box(
        "Capacity status thresholds: <b>UNDER_CAPACITY</b> if available/required < 0.90, <b>BALANCED</b> if 0.90–1.15, "
        "and <b>OVER_CAPACITY</b> if > 1.15. The synthetic dataset deliberately includes 2 'tight-capacity' stores that "
        "frequently show under-capacity — these are edge-case stress tests."
    )

    # Status distribution
    c1, c2 = st.columns(2)

    with c1:
        fig = px.pie(
            by_status,
            names="status",
            values="count",
            title="Capacity Status Distribution",
            color="status",
            color_discrete_map={
                "UNDER_CAPACITY": "#D64550",
                "OVER_CAPACITY": "#2E86AB",
                "BALANCED": "#3A7D44",
            },
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    with c2:
        # Store capacity summary
        store_cap = utils.capacity_by_store_status()
        store_cap_melted = store_cap.melt(
            id_vars="store_id", var_name="status", value_name="count"
        )
        fig = px.bar(
            store_cap_melted,
            x="store_id",
            y="count",
            color="status",
            title="Capacity Status by Store",
            barmode="stack",
            color_discrete_map={
                "UNDER_CAPACITY": "#D64550",
                "OVER_CAPACITY": "#2E86AB",
                "BALANCED": "#3A7D44",
            },
            labels={"store_id": "Store ID", "count": "Day-Role Rows", "status": ""},
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, width='stretch')

    # Capacity by store table
    st.markdown('<div class="sub-section">Capacity by Store</div>', unsafe_allow_html=True)
    by_store_display = by_store.rename(
        columns={
            "store_id": "Store ID",
            "total_required": "Total Required (hrs)",
            "total_available": "Total Available (hrs)",
            "total_gap": "Total Gap (hrs)",
            "under_capacity_days": "Under Days",
            "over_capacity_days": "Over Days",
            "balanced_days": "Balanced Days",
            "avg_ratio": "Avg Ratio",
        }
    )
    st.dataframe(by_store_display, width='stretch', hide_index=True)

    st.markdown('<div class="section-header">Gap Analysis</div>', unsafe_allow_html=True)

    # Filters
    c1, c2, c3 = st.columns(3)
    with c1:
        stores_filter = st.multiselect(
            "Filter by Store", sorted(gaps["store_id"].unique()), default=[]
        )
    with c2:
        status_filter = st.multiselect(
            "Filter by Status",
            sorted(gaps["status"].unique()),
            default=[],
        )
    with c3:
        role_filter = st.multiselect(
            "Filter by Role", sorted(gaps["role"].unique()), default=[]
        )

    filtered = gaps.copy()
    if stores_filter:
        filtered = filtered[filtered["store_id"].isin(stores_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if role_filter:
        filtered = filtered[filtered["role"].isin(role_filter)]

    if len(filtered) > 0:
        st.markdown(f"Showing **{len(filtered):,}** gap rows out of **{len(gaps):,}** total.")

        # Heatmap-style chart
        pivot_data = (
            filtered.groupby(["store_id", "status"])
            .size()
            .reset_index(name="count")
            .pivot(index="store_id", columns="status", values="count")
            .fillna(0)
            .reset_index()
        )

        fig = go.Figure()
        if "UNDER_CAPACITY" in pivot_data.columns:
            fig.add_trace(
                go.Bar(
                    x=pivot_data["store_id"],
                    y=pivot_data["UNDER_CAPACITY"],
                    name="Under Capacity",
                    marker_color="#D64550",
                )
            )
        if "BALANCED" in pivot_data.columns:
            fig.add_trace(
                go.Bar(
                    x=pivot_data["store_id"],
                    y=pivot_data["BALANCED"],
                    name="Balanced",
                    marker_color="#3A7D44",
                )
            )
        if "OVER_CAPACITY" in pivot_data.columns:
            fig.add_trace(
                go.Bar(
                    x=pivot_data["store_id"],
                    y=pivot_data["OVER_CAPACITY"],
                    name="Over Capacity",
                    marker_color="#2E86AB",
                )
            )
        fig.update_layout(
            title="Capacity Status by Store (Filtered)",
            barmode="stack",
            height=400,
            xaxis_title="Store ID",
            yaxis_title="Day-Role Rows",
        )
        st.plotly_chart(fig, width='stretch')

        # Under-capacity detail table
        under = filtered[filtered["status"] == "UNDER_CAPACITY"].sort_values(
            "gap_hours", ascending=False
        )
        if len(under) > 0:
            st.markdown('<div class="sub-section">Under-Capacity Details (Priority View)</div>', unsafe_allow_html=True)
            under_display = under[
                ["store_id", "date", "role", "required_hours", "available_hours", "gap_hours", "gap_ratio"]
            ].rename(
                columns={
                    "store_id": "Store",
                    "date": "Date",
                    "role": "Role",
                    "required_hours": "Required (hrs)",
                    "available_hours": "Available (hrs)",
                    "gap_hours": "Gap (hrs)",
                    "gap_ratio": "Ratio",
                }
            )
            st.dataframe(under_display, width='stretch', hide_index=True)
        else:
            st.info("No under-capacity rows match the current filters.")

        # Show raw data
        with st.expander("View Raw Gap Data", expanded=False):
            st.dataframe(filtered, width='stretch', hide_index=True)
    else:
        st.warning("No rows match the current filter selection.")

    st.markdown('<div class="section-header">Roster Suggestions</div>', unsafe_allow_html=True)

    explain_box(
        "The Roster Suggester generates practical adjustments: <b>ADD_SHIFT</b> suggestions for under-capacity gaps "
        "(preferring high-flexibility employees) and <b>REDUCE_HOURS</b> suggestions for over-capacity. Suggestions respect "
        "flexibility preferences where possible."
    )

    sugg_counts = suggestions["suggestion_type"].value_counts()
    if not sugg_counts.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(
                suggestions,
                names="suggestion_type",
                title="Suggestion Type Distribution",
                color_discrete_sequence=["#2E86AB", "#3A7D44"],
                hole=0.4,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=380)
            st.plotly_chart(fig, width='stretch')
        with c2:
            # Suggestions by store
            sugg_by_store = suggestions.groupby("store_id").size().reset_index(name="count")
            fig = px.bar(
                sugg_by_store,
                x="store_id",
                y="count",
                title="Suggestions by Store",
                color="count",
                color_continuous_scale="Blues",
                labels={"store_id": "Store ID", "count": "Suggestions"},
            )
            fig.update_layout(height=380)
            st.plotly_chart(fig, width='stretch')

        # Sample suggestions
        with st.expander("View Sample Roster Suggestions", expanded=False):
            st.dataframe(suggestions.head(50), width='stretch', hide_index=True)
    else:
        st.info("No roster suggestions available.")


# ---------------------------------------------------------------------------
# Page: Scorecard
# ---------------------------------------------------------------------------
def page_scorecard():
    st.markdown('<div class="main-header">Integrated Scorecard & Alerting</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subheader">One view of total-reward health and workforce availability.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

    explain_box(
        "The Scorecard combines <b>total-reward health</b> (leave liability, insurance take-up, flexibility, cost) with "
        "<b>workforce availability</b> (capacity ratios) into a single view. A manager can see in one place whether the "
        "remuneration package and roster capacity are both healthy, with exception alerts flagging problems early."
    )

    programme = utils.load_programme_metrics()
    store_metrics = utils.load_store_metrics()
    alerts = utils.load_alerts()

    # Programme metrics
    pm = {row["metric"]: row["value"] for _, row in programme.iterrows()}

    st.markdown('<div class="section-header">Programme-Level Health</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric("Annual Leave Liability", f"{pm.get('avg_annual_leave_balance_days', 0):.1f} days", "Avg annual leave balance (liability proxy)")
    with c2:
        render_metric("Insurance Take-up", f"{pm.get('insurance_takeup_rate', 0) * 100:.1f}%", "Employees enrolled in employer insurance")
    with c3:
        render_metric("Avg Flexibility", f"{pm.get('avg_flexibility_preference', 0):.2f}", "Average flexibility preference (0–1)")

    c4, c5, c6 = st.columns(3)
    with c4:
        render_metric("Total Annual Cost", f"${pm.get('total_annual_cost', 0):,.0f}", "Fully-loaded annual cost")
    with c5:
        render_metric("Avg Loaded Rate", f"${pm.get('avg_fully_loaded_rate', 0):.2f}/hr", "Average fully-loaded hourly rate")
    with c6:
        render_metric("Headcount", f"{pm.get('headcount', 0):,.0f}", "Total workforce")

    # Status table
    st.markdown('<div class="sub-section">Metric Status</div>', unsafe_allow_html=True)
    metric_labels = {
        "avg_annual_leave_balance_days": "Annual Leave Balance",
        "insurance_takeup_rate": "Insurance Take-up",
        "avg_flexibility_preference": "Flexibility Preference",
        "total_annual_cost": "Total Annual Cost",
        "avg_fully_loaded_rate": "Avg Fully-Loaded Rate",
        "headcount": "Headcount",
    }
    status_rows = []
    for _, row in programme.iterrows():
        metric = row["metric"]
        val = row["value"]
        if metric == "insurance_takeup_rate":
            val_str = f"{val * 100:.1f}%"
        elif metric == "total_annual_cost":
            val_str = f"${val:,.0f}"
        elif metric == "headcount":
            val_str = f"{val:,.0f}"
        else:
            val_str = f"{val:,.2f}"
        status_rows.append(
            {
                "Metric": metric_labels.get(metric, metric),
                "Value": val_str,
                "Status": status_badge(row["status"]),
                "Notes": row["notes"],
            }
        )
    status_df = pd.DataFrame(status_rows)
    st.markdown(status_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    st.markdown('<div class="section-header">Store-Level Scorecards</div>', unsafe_allow_html=True)

    explain_box(
        "Each store has its own scorecard with headcount, insurance take-up, average flexibility, and a 7-day capacity ratio. "
        "Stores flagged as 'structurally tight on capacity' are called out for special attention."
    )

    # Store metrics pivot
    store_pivot = store_metrics.pivot(index="store_id", columns="metric", values="value").reset_index()

    # Merge with store names
    stores = utils.load_stores()
    store_pivot = store_pivot.merge(stores[["store_id", "store_name", "region"]], on="store_id", how="left")

    # Check for tight capacity stores
    tight_stores = store_metrics[store_metrics["metric"] == "tight_capacity_store"]["store_id"].tolist()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=store_pivot["store_name"],
            y=store_pivot["headcount"],
            name="Headcount",
            marker_color="#2E86AB",
            text=store_pivot["headcount"],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=store_pivot["store_name"],
            y=store_pivot["insurance_takeup"] * 100,
            name="Insurance Take-up (%)",
            mode="lines+markers",
            line=dict(color="#3A7D44", width=2),
            marker=dict(size=8),
            yaxis="y2",
        )
    )
    fig.update_layout(
        title="Store Scorecard: Headcount & Insurance Take-up",
        height=450,
        yaxis=dict(title="Headcount", title_font=dict(color="#2E86AB")),
        yaxis2=dict(title="Insurance Take-up (%)", overlaying="y", side="right", title_font=dict(color="#3A7D44")),
        xaxis=dict(title=""),
    )
    st.plotly_chart(fig, width='stretch')

    # Store capacity chart
    fig = px.bar(
        store_pivot,
        x="store_name",
        y="capacity_ratio",
        title="7-Day Capacity Ratio by Store",
        color="capacity_ratio",
        color_continuous_scale="RdYlGn",
        labels={"store_name": "", "capacity_ratio": "Ratio"},
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="#3A7D44", annotation_text="Balanced = 1.0")
    fig.update_layout(height=400, xaxis_tickangle=-30)
    st.plotly_chart(fig, width='stretch')

    # Store metrics table
    st.markdown('<div class="sub-section">Store Metrics Detail</div>', unsafe_allow_html=True)
    store_display = store_pivot[
        ["store_id", "store_name", "region", "headcount", "insurance_takeup", "avg_flexibility", "capacity_ratio"]
    ].rename(
        columns={
            "store_id": "ID",
            "store_name": "Store",
            "region": "Region",
            "headcount": "Headcount",
            "insurance_takeup": "Insurance Take-up",
            "avg_flexibility": "Avg Flexibility",
            "capacity_ratio": "Capacity Ratio",
        }
    )
    store_display["Insurance Take-up"] = store_display["Insurance Take-up"].apply(lambda x: f"{x * 100:.1f}%")
    store_display["Avg Flexibility"] = store_display["Avg Flexibility"].apply(lambda x: f"{x:.2f}")
    store_display["Capacity Ratio"] = store_display["Capacity Ratio"].apply(lambda x: f"{x:.2f}")
    store_display["Tight"] = store_display["ID"].apply(
        lambda x: "⚠️" if x in tight_stores else ""
    )
    st.dataframe(store_display, width='stretch', hide_index=True)

    st.markdown('<div class="section-header">Exception Alerts</div>', unsafe_allow_html=True)

    if len(alerts) > 0:
        explain_box(
            f"<b>{len(alerts)} active alerts</b> are currently flagging issues that need attention. "
            "Alerts are threshold-based and rule-driven — not ML-based.",
            box_type="warning" if any(a["severity"] in ["HIGH", "CRITICAL"] for _, a in alerts.iterrows()) else "info",
        )

        for _, alert in alerts.iterrows():
            sev = alert["severity"]
            box_type = "danger" if sev in ["HIGH", "CRITICAL"] else "warning"
            icon = "🔴" if sev in ["HIGH", "CRITICAL"] else "🟡"
            store_info = f" Store {alert['store_id']}:" if pd.notna(alert["store_id"]) else ""
            explain_box(
                f"{icon} <b>[{sev}]</b>{store_info} {alert['message']}",
                box_type=box_type,
            )

        # Alerts table
        alert_display = alerts.rename(
            columns={
                "alert_type": "Alert Type",
                "severity": "Severity",
                "store_id": "Store",
                "message": "Message",
                "metric_name": "Metric",
                "metric_value": "Value",
                "threshold": "Threshold",
            }
        )
        st.dataframe(alert_display, width='stretch', hide_index=True)
    else:
        explain_box("No active alerts. The workforce programme is currently healthy.", box_type="success")

    st.markdown('<div class="section-header">Raw Scorecard Report</div>', unsafe_allow_html=True)

    report_text = utils.load_scorecard_report()
    with st.expander("View Full Scorecard Report", expanded=False):
        st.text(report_text)


# ---------------------------------------------------------------------------
# Main app entry point
# ---------------------------------------------------------------------------
def main():
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 🏪 NZ Retail Workforce")
        st.markdown("**Remuneration & Workforce Programme**")
        st.markdown("---")

        page = st.radio(
            "Navigation",
            [
                "Overview",
                "Synthetic Data",
                "Leave Engine",
                "Remuneration",
                "Capacity Planner",
                "Scorecard",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown(
            "### ℹ️ About\n"
            "This app visualises outputs from the "
            "NZ Retail Remuneration & Workforce Model.\n\n"
            "All data is **synthetic** — no real employee data is used for this demo project."
        )
        st.markdown("---")
        st.caption("Data v1.0 · Seed 42 · MIT License")

    # Route to the selected page
    if page == "Overview":
        page_overview()
    elif page == "Synthetic Data":
        page_synthetic_data()
    elif page == "Leave Engine":
        page_leave_engine()
    elif page == "Remuneration":
        page_remuneration()
    elif page == "Capacity Planner":
        page_capacity()
    elif page == "Scorecard":
        page_scorecard()


if __name__ == "__main__":
    main()