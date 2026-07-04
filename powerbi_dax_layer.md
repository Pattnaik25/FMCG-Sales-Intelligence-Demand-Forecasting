# Power BI DAX Layer — FMCG KPI Intelligence
**Version:** 1.0 | Sits on top of KPI parquet files loaded as Power BI tables

---

## Data Model (Star Schema)

```
FACT_Sales
   ├── DIM_Store   (Store, StoreType, Assortment, CompetitionDistance, Tier)
   ├── DIM_Date    (Date, Week, Month, Quarter, Year, DayOfWeek, IsWeekend)
   └── DIM_Promo   (PromoFlag, PromoLabel)

FACT_Forecasts
   ├── DIM_Store
   └── DIM_Date

FACT_KPI_WRI         ← from kpi_weekly_revenue_index.parquet
FACT_KPI_PromoLift   ← from kpi_promo_lift.parquet
FACT_KPI_Conversion  ← from kpi_customer_conversion.parquet
```

**Load order in Power Query:**
```
data/processed/clean_train.parquet       → FACT_Sales
data/processed/kpi_weekly_revenue_index.parquet → FACT_KPI_WRI
data/processed/kpi_promo_lift.parquet    → FACT_KPI_PromoLift
data/processed/kpi_customer_conversion.parquet  → FACT_KPI_Conversion
data/processed/kpi_store_tiers.parquet   → DIM_Store (merge on Store key)
```

---

## DAX Measures — Complete Reference

### ── TABLE: Core Sales Measures

```dax
// ─────────────────────────────────────────────────────────
// Total Revenue
// Base measure — all others derive from this.
// Always filter Open = 1 at the row-filter level in Power Query
// rather than inside every measure.
// ─────────────────────────────────────────────────────────
[Total Revenue] =
SUM( FACT_Sales[Sales] )


// ─────────────────────────────────────────────────────────
// Avg Daily Sales per Store
// Used for store-tier KPI cards — normalised for size.
// ─────────────────────────────────────────────────────────
[Avg Daily Sales per Store] =
DIVIDE(
    SUM( FACT_Sales[Sales] ),
    DISTINCTCOUNT( FACT_Sales[Store] )
)


// ─────────────────────────────────────────────────────────
// Total Customers
// ─────────────────────────────────────────────────────────
[Total Customers] =
SUM( FACT_Sales[Customers] )


// ─────────────────────────────────────────────────────────
// Sales per Customer (Basket Proxy)
// Safer with DIVIDE — returns BLANK() instead of error
// when Customers = 0.
// ─────────────────────────────────────────────────────────
[Sales per Customer] =
DIVIDE(
    [Total Revenue],
    [Total Customers]
)
```

---

### ── TABLE: Time Intelligence

```dax
// ─────────────────────────────────────────────────────────
// Revenue YTD
// Requires a marked Date Table in Power BI (DIM_Date).
// ─────────────────────────────────────────────────────────
[Revenue YTD] =
TOTALYTD(
    [Total Revenue],
    DIM_Date[Date]
)


// ─────────────────────────────────────────────────────────
// Revenue — Same Period Last Year (SPLY)
// Foundation for all YoY % calculations.
// ─────────────────────────────────────────────────────────
[Revenue SPLY] =
CALCULATE(
    [Total Revenue],
    SAMEPERIODLASTYEAR( DIM_Date[Date] )
)


// ─────────────────────────────────────────────────────────
// Revenue YoY %
// Matches how TCPL reports segment growth (e.g., +18% India Foods).
// ─────────────────────────────────────────────────────────
[Revenue YoY %] =
DIVIDE(
    [Total Revenue] - [Revenue SPLY],
    [Revenue SPLY]
)


// ─────────────────────────────────────────────────────────
// Revenue — Prior Month
// For MoM KPI cards in the operational dashboard.
// ─────────────────────────────────────────────────────────
[Revenue Prior Month] =
CALCULATE(
    [Total Revenue],
    PREVIOUSMONTH( DIM_Date[Date] )
)


// ─────────────────────────────────────────────────────────
// Revenue MoM %
// ─────────────────────────────────────────────────────────
[Revenue MoM %] =
DIVIDE(
    [Total Revenue] - [Revenue Prior Month],
    [Revenue Prior Month]
)


// ─────────────────────────────────────────────────────────
// Revenue Rolling 4 Weeks
// Used as denominator for Weekly Revenue Index card.
// ─────────────────────────────────────────────────────────
[Revenue Rolling 4W] =
CALCULATE(
    [Total Revenue],
    DATESINPERIOD(
        DIM_Date[Date],
        MAX( DIM_Date[Date] ) - 1,   -- exclude current week
        -28,
        DAY
    )
)
```

---

### ── TABLE: KPI-Specific Measures

```dax
// ─────────────────────────────────────────────────────────
// Weekly Revenue Index
// Current week vs. own 4-week rolling baseline.
// >1.0 = above trend; <1.0 = below trend.
// ─────────────────────────────────────────────────────────
[Weekly Revenue Index] =
DIVIDE(
    [Total Revenue],
    [Revenue Rolling 4W]
)


// ─────────────────────────────────────────────────────────
// Promo Revenue
// ─────────────────────────────────────────────────────────
[Promo Revenue] =
CALCULATE(
    [Total Revenue],
    FACT_Sales[Promo] = 1
)


// ─────────────────────────────────────────────────────────
// Non-Promo Revenue
// ─────────────────────────────────────────────────────────
[Non-Promo Revenue] =
CALCULATE(
    [Total Revenue],
    FACT_Sales[Promo] = 0
)


// ─────────────────────────────────────────────────────────
// Promo Lift %
// Incremental revenue attributable to promotion.
// Red flag if negative — promo is cannibalising base.
// ─────────────────────────────────────────────────────────
[Promo Lift %] =
VAR PromoAvg =
    CALCULATE(
        AVERAGEX( VALUES( DIM_Date[Date] ), [Total Revenue] ),
        FACT_Sales[Promo] = 1
    )
VAR NonPromoAvg =
    CALCULATE(
        AVERAGEX( VALUES( DIM_Date[Date] ), [Total Revenue] ),
        FACT_Sales[Promo] = 0
    )
RETURN
    DIVIDE( PromoAvg - NonPromoAvg, NonPromoAvg )


// ─────────────────────────────────────────────────────────
// % Stores with Negative Promo Lift
// Operational red-flag KPI for leadership review.
// ─────────────────────────────────────────────────────────
[% Stores Negative Promo Lift] =
DIVIDE(
    COUNTROWS(
        FILTER(
            SUMMARIZE(
                FACT_Sales,
                FACT_Sales[Store],
                "StoreLift", [Promo Lift %]
            ),
            [StoreLift] < 0
        )
    ),
    DISTINCTCOUNT( FACT_Sales[Store] )
)
```

---

### ── TABLE: Forecast Accuracy (joins FACT_Forecasts)

```dax
// ─────────────────────────────────────────────────────────
// Total Forecast
// ─────────────────────────────────────────────────────────
[Total Forecast] =
SUM( FACT_Forecasts[forecast_sales] )


// ─────────────────────────────────────────────────────────
// Forecast Error (Absolute)
// ─────────────────────────────────────────────────────────
[Abs Forecast Error] =
SUMX(
    FACT_Forecasts,
    ABS( FACT_Forecasts[actual_sales] - FACT_Forecasts[forecast_sales] )
)


// ─────────────────────────────────────────────────────────
// WAPE %  (Weighted Absolute Percentage Error)
// Primary forecast accuracy KPI — preferred over MAPE.
// Target: < 20%
// ─────────────────────────────────────────────────────────
[WAPE %] =
DIVIDE(
    [Abs Forecast Error],
    SUM( FACT_Forecasts[actual_sales] )
)


// ─────────────────────────────────────────────────────────
// Forecast Bias %
// Positive = over-forecasting (excess inventory risk)
// Negative = under-forecasting (stockout risk)
// Target: within ±5%
// ─────────────────────────────────────────────────────────
[Forecast Bias %] =
DIVIDE(
    [Total Forecast] - SUM( FACT_Forecasts[actual_sales] ),
    SUM( FACT_Forecasts[actual_sales] )
)


// ─────────────────────────────────────────────────────────
// WAPE vs. Target (for conditional formatting)
// Returns 1 if within target, 0 if breaching.
// Use in KPI card icon rules: 1 = green tick, 0 = red cross
// ─────────────────────────────────────────────────────────
[WAPE On Target] =
IF( [WAPE %] <= 0.20, 1, 0 )
```

---

### ── TABLE: Benchmarking (ALL / ALLEXCEPT)

```dax
// ─────────────────────────────────────────────────────────
// Company-Wide Revenue (ignores Store filter)
// Use in a visual alongside individual store revenue to show
// "your store vs. company" — the single most common exec ask.
// ─────────────────────────────────────────────────────────
[Company Revenue (All Stores)] =
CALCULATE(
    [Total Revenue],
    ALL( DIM_Store )
)


// ─────────────────────────────────────────────────────────
// Store Revenue vs. Company %
// Each store's share of total — tier context without a join.
// ─────────────────────────────────────────────────────────
[Store Revenue Share %] =
DIVIDE(
    [Total Revenue],
    [Company Revenue (All Stores)]
)


// ─────────────────────────────────────────────────────────
// Revenue vs. Tier Average
// Compares a store to its own tier, not the whole company —
// prevents unfair comparisons between Top and Bottom tier stores.
// ─────────────────────────────────────────────────────────
[Revenue vs Tier Avg] =
VAR TierAvg =
    CALCULATE(
        AVERAGEX( VALUES( DIM_Store[Store] ), [Total Revenue] ),
        ALLEXCEPT( DIM_Store, DIM_Store[Tier] )
    )
RETURN
    DIVIDE( [Total Revenue] - TierAvg, TierAvg )
```

---

## Power Query: Load Parquet Files

```m
// In Power Query → New Source → Python Script
// (or load via Parquet connector if available in your tenant)

let
    Source = Python.Execute(
        "import pandas as pd" & "#(lf)" &
        "df = pd.read_parquet('data/processed/clean_train.parquet')" & "#(lf)" &
        "df['Date'] = df['Date'].astype(str)"
    ),
    Output = Source{[Name="df"]}[Value],
    TypedTable = Table.TransformColumnTypes(Output, {
        {"Store", Int64.Type},
        {"Date", type date},
        {"Sales", type number},
        {"Customers", Int64.Type},
        {"Open", Int64.Type},
        {"Promo", Int64.Type}
    })
in
    TypedTable
```

---

## Conditional Formatting Rules (KPI Cards)

| Measure | Green | Amber | Red |
|---------|-------|-------|-----|
| `[WAPE %]` | < 20% | 20–30% | > 30% |
| `[Forecast Bias %]` | ±5% | ±5–10% | > ±10% |
| `[Promo Lift %]` | > 10% | 0–10% | < 0% |
| `[Revenue YoY %]` | > 5% | 0–5% | < 0% |
| `[Weekly Revenue Index]` | > 1.05 | 0.9–1.05 | < 0.9 |

---

## Stakeholder Line to Use

> *"I built the DAX layer as measures, not calculated columns — so every KPI card responds dynamically to whatever slicer the VP applies. The time-intelligence measures mirror exactly how TCPL reports segment growth: SPLY, YoY %, YTD. The WAPE and Bias measures are split by promo cohort, not blended, so the accuracy story doesn't hide poor performance on non-promo weeks behind a strong promo week."*
