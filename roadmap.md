# Roadmap – NZ Retail Remuneration & Workforce Programme

(Assumes the synthetic data layer has already been generated and is stable)

This roadmap turns the synthetic data into a complete, demonstrable set of engines and models. It is sequenced so each phase re-uses the outputs of the previous one, keeps the work modular, and produces tangible SME artefacts at every step.

## Phase 0 – Foundation (Already complete)

- Synthetic data generated and versioned (`data/synthetic/v1`)
- Configuration locked (`configs/synthetic_data.yaml`)
- Basic documentation and repository structure in place

**Exit criteria**: Data can be regenerated reproducibly; schemas are documented; sample notebooks confirm the data looks realistic.

## Phase 1 – Leave Entitlement & Accrual Engine

**Goal**: Trusted, auditable leave balances that respect NZ Holidays Act concepts and different employment types.

### Key activities

- Finalise leave data model (types, eligibility, accrual rules, balances)
- Implement core accrual and balance calculation logic
- Add Holidays Act-oriented helpers (ordinary weekly pay / average earnings flags – simplified but explicit)
- Handle edge cases deliberately planted in the synthetic data (long-tenure high balances, new starters, casuals, etc.)
- Write unit tests against synthetic fixtures
- Produce a clear “Leave Balance Explanation” report for sample employees

### Deliverables

- `src/leave_engine/` package
- Test suite
- Documentation: `docs/02-leave-engine.md`
- Sample output: current leave balances + accrual projections

**Success metric**: Any leave balance can be fully explained from the rules + transaction history.

## Phase 2 – Flexible Remuneration Costing & Scenario Model

**Duration**: 2–3 weeks
**Goal**: Transparent view of the true cost of a competitive package (base + leave value + insurance + flexibility) and the ability to model changes.

### Key activities

- Build remuneration component data model
- Implement fully-loaded hourly / annual cost calculations
- Create scenario engine (e.g. “+2 days annual leave”, “higher insurance contribution”, “flexibility premium for high-preference staff”)
- Link leave balances from Phase 1 into the cost model
- Generate comparison reports (current package vs scenarios)

### Deliverables

- `src/remuneration/` package
- Scenario configuration + results
- Documentation: `docs/03-remuneration-costing.md`
- Costing summary and scenario comparison outputs

**Success metric**: Leadership can see the cost impact of package changes before they are promised.

## Phase 3 – Demand Forecasting → Roster Capacity Planner

**Goal**: Convert demand signals into labour requirements and show capacity gaps against available hours (after leave).

### Key activities

- Simple demand forecasting / profiling (using the synthetic demand series)
- Labour standards by role
- Available hours calculation (contracted hours – leave – other known absences)
- Capacity gap analysis by store / day / role
- Basic roster suggestion rules (respecting flexibility preferences where possible)
- Visual or tabular capacity heatmaps / exception lists

### Deliverables

- `src/capacity/` package
- Capacity reports and gap analysis
- Documentation: `docs/04-capacity-planner.md`
- Example weekly capacity view for selected stores

**Success metric**: The model correctly flags stores/periods that are structurally under- or over-resourced.

## Phase 4 – Integrated Scorecard & Alerting

**Goal**: Single view that combines total-reward health and workforce availability.

### Key activities

- Define a small set of meaningful metrics (leave liability, package cost trends, capacity tightness, flexibility utilisation, insurance take-up, etc.)
- Build metric calculation layer on top of previous engines
- Simple alerting rules for exceptions
- Produce a concise scorecard (store-level and programme-level)

### Deliverables

- `src/scorecard/` package
- Scorecard outputs + alert list
- Documentation: `docs/05-scorecard.md`

**Success metric**: A manager can see in one place whether the remuneration package and the roster capacity are both healthy.

## Phase 5 – Hardening, Documentation & Demonstration Pack

**Duration**: 1.5–2 weeks
**Goal**: Make the whole programme presentation-ready and maintainable.

### Key activities

- End-to-end integration tests
- Polish all documentation
- Create a short demonstration narrative / walkthrough (notebook or markdown)
- Freeze a “demo” version of the synthetic data
- Optional: simple CLI or notebook-based demo script that runs the full chain
- Final README and architecture overview update

### Deliverables

- Complete documentation set
- Demonstration pack
- Test coverage report
- Clean, tagged release of the repository

## Recommended Working Cadence

- Work in thin vertical slices (one engine at a time).
- After each phase, produce a short “what this engine does + sample output” note — these become excellent portfolio / SME evidence.
- Keep the synthetic data version frozen during a phase; only regenerate when you deliberately want to test new edge cases.
- Prioritise clear calculation logic and explainability over fancy visualisations.

## Quick Decision Points

After Phase 1 (Leave Engine) you already have a strong, differentiated asset.
After Phase 2 you can speak confidently about the cost of competitive, flexible packages.
After Phase 3 you can demonstrate end-to-end workforce planning support.
Phase 4 and 5 turn the collection of engines into a coherent programme story.
