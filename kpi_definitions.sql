-- ==========================================================================
-- queries/kpi_definitions.sql
-- Governed KPI definitions — single source of truth
-- All formulas version-controlled. Any change requires PR review.
-- ==========================================================================


-- ── KPI 1: Weekly Revenue Index ──────────────────────────────────────────────
-- Normalises each store-week against that store's own trailing 4-week avg.
-- Enables cross-store comparison regardless of store size/volume.

WITH weekly_sales AS (
    SELECT
        Store,
        DATE_TRUNC('week', Date)          AS week_start,
        SUM(Sales)                        AS weekly_sales
    FROM store_sales
    WHERE Open = 1
    GROUP BY 1, 2
),
rolling_base AS (
    SELECT
        Store,
        week_start,
        weekly_sales,
        AVG(weekly_sales) OVER (
            PARTITION BY Store
            ORDER BY week_start
            ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING   -- trailing 4 weeks, not including current
        ) AS rolling_4wk_avg
    FROM weekly_sales
)
SELECT
    Store,
    week_start,
    weekly_sales,
    rolling_4wk_avg,
    ROUND(weekly_sales / NULLIF(rolling_4wk_avg, 0), 3) AS weekly_revenue_index
FROM rolling_base
WHERE rolling_4wk_avg IS NOT NULL
ORDER BY Store, week_start;


-- ── KPI 2: Promotion Lift % ──────────────────────────────────────────────────
-- True incremental lift: compares average sales on promo vs. non-promo days
-- within the same store and month — controlling for seasonal baseline.

WITH daily_avg AS (
    SELECT
        Store,
        DATE_TRUNC('month', Date)    AS month_start,
        Promo,
        AVG(Sales)                   AS avg_daily_sales
    FROM store_sales
    WHERE Open = 1
    GROUP BY 1, 2, 3
),
pivoted AS (
    SELECT
        Store,
        month_start,
        MAX(CASE WHEN Promo = 0 THEN avg_daily_sales END) AS sales_no_promo,
        MAX(CASE WHEN Promo = 1 THEN avg_daily_sales END) AS sales_promo
    FROM daily_avg
    GROUP BY 1, 2
)
SELECT
    Store,
    month_start,
    ROUND(sales_promo, 2)                                            AS sales_promo,
    ROUND(sales_no_promo, 2)                                         AS sales_no_promo,
    ROUND(
        (sales_promo - sales_no_promo) / NULLIF(sales_no_promo, 0) * 100,
        2
    )                                                                AS promo_lift_pct
FROM pivoted
WHERE sales_no_promo IS NOT NULL
  AND sales_promo    IS NOT NULL
ORDER BY Store, month_start;


-- ── KPI 3: MoM Sales Growth % ────────────────────────────────────────────────
-- Month-over-month growth per store using LAG window function.
-- Equivalent to the YoY% TCPL reports — same SQL pattern, different time window.

WITH monthly AS (
    SELECT
        Store,
        DATE_TRUNC('month', Date)    AS month_start,
        SUM(Sales)                   AS monthly_sales
    FROM store_sales
    WHERE Open = 1
    GROUP BY 1, 2
)
SELECT
    Store,
    month_start,
    monthly_sales,
    LAG(monthly_sales) OVER (
        PARTITION BY Store ORDER BY month_start
    )                                                           AS prev_month_sales,
    ROUND(
        (monthly_sales - LAG(monthly_sales) OVER (
            PARTITION BY Store ORDER BY month_start
        )) / NULLIF(
            LAG(monthly_sales) OVER (
                PARTITION BY Store ORDER BY month_start
            ), 0
        ) * 100,
        2
    )                                                           AS mom_growth_pct
FROM monthly
ORDER BY Store, month_start;


-- ── KPI 4: Store Performance Tier ────────────────────────────────────────────
-- Buckets stores into Top/Mid/Bottom tercile by annual sales.
-- Use NTILE(3) for equal-count buckets; CASE + percentile for unequal thresholds.

WITH annual_sales AS (
    SELECT
        Store,
        SUM(Sales)     AS total_annual_sales
    FROM store_sales
    WHERE Open = 1
    GROUP BY Store
)
SELECT
    Store,
    total_annual_sales,
    NTILE(3) OVER (ORDER BY total_annual_sales)             AS tier_rank,
    CASE NTILE(3) OVER (ORDER BY total_annual_sales)
        WHEN 1 THEN 'Bottom Tier'
        WHEN 2 THEN 'Mid Tier'
        WHEN 3 THEN 'Top Tier'
    END                                                     AS performance_tier
FROM annual_sales
ORDER BY total_annual_sales DESC;


-- ── KPI 5: Forecast Accuracy (WAPE + Bias) ───────────────────────────────────
-- Joins actuals to forecast table and computes WAPE and Bias per cohort.
-- Assumes a `forecasts` table with columns: Store, Date, Promo, forecast_sales.

WITH accuracy_base AS (
    SELECT
        s.Store,
        s.Date,
        s.Promo,
        s.Sales                        AS actual_sales,
        f.forecast_sales,
        ABS(s.Sales - f.forecast_sales) AS abs_error,
        (f.forecast_sales - s.Sales)    AS signed_error
    FROM store_sales s
    JOIN forecasts f
      ON s.Store = f.Store AND s.Date = f.Date
    WHERE s.Open = 1
)
SELECT
    Promo,
    COUNT(*)                                                       AS n_rows,
    ROUND(SUM(abs_error)    / NULLIF(SUM(actual_sales), 0) * 100, 2) AS wape_pct,
    ROUND(SUM(signed_error) / NULLIF(SUM(actual_sales), 0) * 100, 2) AS bias_pct,
    ROUND(AVG(abs_error / NULLIF(actual_sales, 0)) * 100, 2)         AS mape_pct
FROM accuracy_base
GROUP BY Promo
ORDER BY Promo;
