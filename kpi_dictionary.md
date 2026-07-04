# KPI Dictionary — Governed Definitions
**Version:** 1.0 | **Owner:** Analytics Team | **Last Reviewed:** 2026-07

> This is the single source of truth for all KPI definitions in this project.
> Any change to a formula requires a pull request, peer review, and stakeholder sign-off.
> Ad hoc redefinitions are not permitted downstream.

---

## KPI 1 — Weekly Revenue Index

| Field | Value |
|-------|-------|
| **Formula** | `SUM(Sales this week) / AVG(Sales, trailing 4 weeks)` |
| **Numerator** | Current week's total sales (open days only) |
| **Denominator** | 4-week rolling average, excluding current week |
| **Purpose** | Normalize store performance across size/volume tiers |
| **Interpretation** | >1.0 = above-trend; <1.0 = below-trend |
| **Exclusions** | Closed days (`Open = 0`) excluded from both num/denom |
| **Min history** | 2 weeks minimum before first calculation |
| **SQL Reference** | `queries/kpi_definitions.sql` → KPI 1 |

---

## KPI 2 — Promotion Lift %

| Field | Value |
|-------|-------|
| **Formula** | `(Avg promo sales − Avg non-promo sales) / Avg non-promo sales × 100` |
| **Granularity** | Store × Month |
| **Purpose** | Measure incremental revenue attributable to promotions |
| **Interpretation** | Positive = promo added value; Negative = promo cannibalized base |
| **Exclusions** | Closed days excluded; months with zero non-promo days excluded |
| **Common mistake** | Do NOT use total sales on promo days vs. total on non-promo days without controlling for the number of days — use averages |
| **SQL Reference** | `queries/kpi_definitions.sql` → KPI 2 |

---

## KPI 3 — Month-over-Month Sales Growth %

| Field | Value |
|-------|-------|
| **Formula** | `(This Month Sales − Prev Month Sales) / Prev Month Sales × 100` |
| **Granularity** | Store × Month |
| **Window function** | `LAG(monthly_sales, 1) OVER (PARTITION BY Store ORDER BY month_start)` |
| **Purpose** | Track sales momentum — is the store accelerating or decelerating? |
| **Exclusions** | First month per store excluded (no prior period) |
| **SQL Reference** | `queries/kpi_definitions.sql` → KPI 3 |

---

## KPI 4 — Store Performance Tier

| Field | Value |
|-------|-------|
| **Formula** | `NTILE(3) OVER (ORDER BY total_annual_sales)` |
| **Buckets** | Bottom Tier / Mid Tier / Top Tier (equal-count, not equal-value) |
| **Basis** | Full-year open-day sales |
| **Recalculation** | Annually — tiers are fixed within a reporting year |
| **Purpose** | Ensures like-for-like benchmarking — don't compare a Top Tier store to a Bottom Tier store as if they're peers |
| **SQL Reference** | `queries/kpi_definitions.sql` → KPI 4 |

---

## KPI 5 — Forecast Accuracy (WAPE & Bias)

| Field | Value |
|-------|-------|
| **Primary metric** | **WAPE** = `SUM(|Actual − Forecast|) / SUM(Actual) × 100` |
| **Secondary metric** | **Bias** = `(SUM(Forecast) − SUM(Actual)) / SUM(Actual) × 100` |
| **Reference metric** | MAPE (reported for benchmarking only — distorts on low-volume SKUs) |
| **Why WAPE over MAPE** | MAPE inflates when actuals approach zero (division problem); WAPE weights by actual volume |
| **Bias interpretation** | `Positive (+)` = over-forecasting (excess inventory risk); `Negative (−)` = under-forecasting (stockout risk) |
| **Target thresholds** | WAPE < 20%; Bias within ±5% |
| **Reported by cohort** | Promo weeks and Non-Promo weeks reported separately — never blended |
| **SQL Reference** | `queries/kpi_definitions.sql` → KPI 5 |

---

## Change Log

| Date | KPI | Change | Approved By |
|------|-----|--------|-------------|
| 2026-07 | All | Initial version created | Amit Pattanaik |
