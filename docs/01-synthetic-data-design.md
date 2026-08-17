# Synthetic Data Layer — Design Document

## 1. Purpose

The synthetic data layer is the foundational, privacy-safe dataset for the
NZ Retail Remuneration & Workforce Programme. It provides realistic,
reproducible data that all downstream engines (Leave, Remuneration Costing,
Capacity Planning, Scorecard) consume and validate against.

**No real employee or commercial data is used.** Everything is generated
from configurable rules with a fixed random seed.

## 2. Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Privacy first** | All data is synthetic; no real PII or commercial data |
| **Reproducibility** | Fixed seed (`42` default) → identical output every run |
| **NZ retail context** | NZ regions, Holidays Act concepts, school terms, retail peaks |
| **Realism** | Higher part-time/casual ratios, weekend/evening demand, seasonal effects |
| **Controlled edge cases** | Deliberate stress-test scenarios for downstream engines |
| **Versioning** | Output written to `data/synthetic/v1/` with a manifest |
| **Transparency** | Every assumption is documented and configurable |

## 3. Table Design

### 3.1 Stores / Locations

| Column | Type | Description |
|--------|------|-------------|
| `store_id` | int | Primary key |
| `store_name` | str | Display name |
| `region` | str | Auckland, Wellington, Christchurch, Hamilton, Tauranga, Regional |
| `format` | str | Supermarket, Specialty, Large Format |
| `size_band` | str | Small, Medium, Large, Extra Large |
| `trading_pattern` | str | `standard` or `extended` |
| `weekday_open/close` | time | Trading hours (Mon–Fri) |
| `saturday_open/close` | time | Trading hours (Sat) |
| `sunday_open/close` | time | Trading hours (Sun) |
| `is_tight_capacity` | bool | Edge-case flag for capacity stress-testing |

### 3.2 Employees

| Column | Type | Description |
|--------|------|-------------|
| `employee_id` | int | Primary key |
| `store_id` | int | FK → stores |
| `first_name` / `last_name` | str | Faker-generated NZ names |
| `role` | str | Checkout, Grocery, Fresh, Online, Supervisor, Management, Other |
| `job_family` | str | Simplified family grouping |
| `employment_type` | str | `full_time`, `part_time`, `casual` |
| `start_date` | date | Derived from tenure |
| `contracted_hours_per_week` | float | By employment type |
| `base_hourly_rate` | float | By role range |
| `insurance_enrolled` | bool | ~58% enrolment |
| `flexibility_preference` | float | 0–1 score |
| `is_high_leave_balance` | bool | Edge case |
| `is_new_starter` | bool | Edge case (started < 90 days ago) |
| `is_high_flexibility` | bool | Edge case |

### 3.3 Leave Types (Static Reference)

| Column | Type | Description |
|--------|------|-------------|
| `leave_code` | str | ANNUAL, SICK, BEREAVEMENT, PUBLIC_HOLIDAY, ALTERNATIVE, PARENTAL |
| `leave_name` | str | Display name |
| `is_paid` | bool | Paid leave flag |
| `carries_over` | bool | Whether balance carries over |
| `accrual_rate_hours_per_week` | float | Annual leave accrual |
| `accrual_rate_days_per_year` | float | Sick/bereavement accrual |
| `max_balance_weeks` / `max_balance_days` | float | Balance caps |

### 3.4 Leave Transactions

| Column | Type | Description |
|--------|------|-------------|
| `transaction_id` | int | Primary key |
| `employee_id` | int | FK → employees |
| `leave_code` | str | FK → leave_types |
| `transaction_date` | date | Date of accrual or usage |
| `transaction_type` | str | `ACCRUAL` or `TAKEN` |
| `hours` | float | Hours accrued or taken |
| `balance_after` | float | Running balance |
| `reason_code` | str | Optional reason |

**Realism patterns:**
- Annual leave peaks around Christmas/New Year (Dec–Jan) and school holidays (April)
- Sick leave higher in winter (May–September, 1.7× multiplier)
- Bereavement leave rare (~9% annual probability)
- Pro-rata accrual for part-time/casual based on contracted hours

### 3.5 Rosters / Worked Hours

| Column | Type | Description |
|--------|------|-------------|
| `roster_id` | int | Primary key |
| `employee_id` | int | FK → employees |
| `store_id` | int | FK → stores |
| `work_date` | date | Shift date |
| `shift_start` / `shift_end` | time | Shift times |
| `hours_worked` | float | Shift duration |
| `role_on_day` | str | Role performed |
| `is_weekend` | bool | Weekend flag |
| `is_public_holiday` | bool | Public holiday flag |
| `penalty_flag` | bool | Weekend or PH work |

**Realism patterns:**
- Utilisation: full-time 96%, part-time 88%, casual 65% of contracted hours
- Weekend work more likely for part-time/casual
- Public holiday work ~35% probability
- Shift lengths: 4, 5, 6, 8, 9 hours

### 3.6 Demand / Activity Drivers

| Column | Type | Description |
|--------|------|-------------|
| `store_id` | int | FK → stores |
| `date` | date | Day |
| `day_of_week` | int | 0=Mon … 6=Sun |
| `is_weekend` | bool | Weekend flag |
| `is_public_holiday` | bool | PH flag |
| `is_school_term` | bool | School term flag |
| `is_retail_peak` | bool | Peak period flag |
| `demand_index` | float | Scaled demand proxy |
| `transaction_count` | int | Approx transactions |
| `sales_amount` | float | Approx sales $ |

**Realism patterns:**
- Weekend peaks (Sat 1.35×, Sun 1.20×)
- Christmas peak (Dec 1.35×)
- Public holiday uplift (1.45×)
- School holiday / retail peak uplift (1.15×)
- Store size factor (Small 0.6× … Extra Large 1.8×)
- Daily noise (σ = 0.08)

### 3.7 Remuneration Components

| Column | Type | Description |
|--------|------|-------------|
| `employee_id` | int | PK / FK → employees |
| `base_hourly_rate` | float | Base rate |
| `kiwisaver_employer_rate` | float | 3% employer contribution |
| `kiwisaver_employer_cost_per_hour` | float | $/hour |
| `leave_loading_rate` | float | 8% illustrative |
| `leave_loading_cost_per_hour` | float | $/hour |
| `insurance_monthly_cost` | float | $/month (if enrolled) |
| `insurance_cost_per_hour` | float | $/hour (÷160) |
| `flexibility_premium_rate` | float | Up to 6% |
| `flexibility_premium_cost_per_hour` | float | $/hour |
| `fully_loaded_cost_per_hour` | float | Sum of all components |

### 3.8 Calendar & NZ Reference Data

| Column | Type | Description |
|--------|------|-------------|
| `date` | date | PK |
| `year` / `month` / `day` | int | Date parts |
| `day_of_week` | int | 0=Mon … 6=Sun |
| `is_weekend` | bool | Weekend flag |
| `is_public_holiday` | bool | National or regional PH |
| `public_holiday_name` | str | Holiday name |
| `public_holiday_region` | str | Region (if regional) |
| `is_school_term` | bool | NZ school term |
| `is_retail_peak` | bool | Christmas, school holidays |

## 4. Generation Approach

1. **Seed** — a single `numpy.random.default_rng(seed)` is shared across all generators.
2. **Order** — calendar → stores → employees → leave types → leave transactions → rosters → demand → remuneration.
3. **Validation** — each table is validated against its schema; cross-table FK integrity is checked.
4. **Output** — versioned CSV files + `_manifest.json` with generation metadata.

## 5. Edge Cases

| Edge Case | Count | Purpose |
|-----------|-------|---------|
| High leave balance employees | 12 | Long-tenure staff with large annual leave balances |
| New starters (last 90 days) | 35 | Short-tenure employees with minimal accrual history |
| High flexibility preference | 40 | Employees with flexibility score ≥ 0.85 |
| Tight capacity stores | 2 | Stores that will frequently show under-capacity |

## 6. Configuration

All parameters live in `configs/synthetic_data.yaml`. Key sections:

- `meta` — version, seed, output dir, date range, timezone
- `stores` — count, regions, formats, trading patterns
- `employees` — headcount, employment mix, roles, hours, tenure, flexibility
- `leave` — types, accrual rates, usage patterns
- `rosters` — utilisation, shift lengths, weekend/PH probabilities
- `demand` — base index, day/month multipliers, PH uplift, noise
- `remuneration` — KiwiSaver, leave loading, insurance, flexibility premium
- `calendar` — PH inclusion, school terms, regional anniversary days
- `generation` — batch size, validation flags, edge cases

## 7. Reproducibility

Running the generator with the same config and seed produces byte-identical
output. This is essential for:

- Auditable calculation engines
- Regression testing
- Sharing a frozen dataset version for demos

## 8. Assumptions & Simplifications

- Annual leave accrual simplified to a flat weekly rate (3.0769 h/week ≈ 4 weeks on 40h)
- Sick leave accrual simplified to 10 days/year pro-rated
- KiwiSaver employer contribution fixed at 3% (simplified)
- Insurance cost assumed spread over 160 hours/month
- Public holiday rules simplified (observed dates for weekend PHs)
- School term dates are approximate
- No parental leave transactions generated (out of scope for v1)