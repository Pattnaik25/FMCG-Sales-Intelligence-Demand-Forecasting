"""
src/02_kpi_engine.py
====================
Governed KPI calculation engine.
All definitions here are the single source of truth — no ad hoc redefinitions.

Business rationale:
    A KPI calculated differently per BU is not a KPI — it's an opinion.
    This engine enforces one formula, one version, per KPI, and is the
    only layer that writes to the KPI output table.
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROC_DIR = Path("data/processed")
PROC_DIR.mkdir(parents=True, exist_ok=True)

# ── LOAD CLEAN DATA ───────────────────────────────────────────────────────────
def load_clean() -> pd.DataFrame:
    df = pd.read_parquet(PROC_DIR / "clean_train.parquet")
    df["Week"]  = df["Date"].dt.to_period("W").apply(lambda r: r.start_time)
    df["Month"] = df["Date"].dt.to_period("M").apply(lambda r: r.start_time)
    df["Year"]  = df["Date"].dt.year
    return df

# ── KPI 1: Weekly Revenue Index ───────────────────────────────────────────────
def kpi_weekly_revenue_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes weekly sales against that store's own 4-week rolling average.
    >1.0 = above-trend week; <1.0 = below-trend.
    Allows apples-to-apples comparison across stores of different sizes.
    """
    weekly = df[df["Open"] == 1].groupby(["Store", "Week"])["Sales"].sum().reset_index()
    weekly = weekly.sort_values(["Store", "Week"])
    weekly["rolling_4wk_avg"] = (
        weekly.groupby("Store")["Sales"]
              .transform(lambda x: x.shift(1).rolling(4, min_periods=2).mean())
    )
    weekly["weekly_revenue_index"] = (weekly["Sales"] / weekly["rolling_4wk_avg"]).round(3)
    return weekly.dropna(subset=["weekly_revenue_index"])

# ── KPI 2: Promotion Lift % ───────────────────────────────────────────────────
def kpi_promo_lift(df: pd.DataFrame) -> pd.DataFrame:
    """
    Measures true incremental uplift of promotions per store per month.
    Formula: (avg promo sales - avg non-promo sales) / avg non-promo sales * 100
    """
    open_df = df[df["Open"] == 1]
    grouped = open_df.groupby(["Store", "Month", "Promo"])["Sales"].mean().unstack("Promo").reset_index()
    grouped.columns = ["Store", "Month", "sales_no_promo", "sales_promo"]
    grouped["promo_lift_pct"] = (
        (grouped["sales_promo"] - grouped["sales_no_promo"]) /
        grouped["sales_no_promo"] * 100
    ).round(2)
    return grouped.dropna(subset=["promo_lift_pct"])

# ── KPI 3: Customer Conversion Rate ──────────────────────────────────────────
def kpi_customer_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sales per customer visit — a proxy for basket size / conversion quality.
    Computed weekly per store to track operational degradation.
    """
    open_df = df[(df["Open"] == 1) & (df["Customers"] > 0)]
    weekly = open_df.groupby(["Store", "Week"]).agg(
        total_sales=("Sales", "sum"),
        total_customers=("Customers", "sum")
    ).reset_index()
    weekly["sales_per_customer"] = (weekly["total_sales"] / weekly["total_customers"]).round(2)
    return weekly

# ── KPI 4: MoM Sales Growth % ────────────────────────────────────────────────
def kpi_mom_growth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Month-over-month sales growth per store.
    Equivalent to the YoY % TCPL reports at the segment level, applied at store level.
    """
    monthly = df[df["Open"] == 1].groupby(["Store", "Month"])["Sales"].sum().reset_index()
    monthly = monthly.sort_values(["Store", "Month"])
    monthly["prev_month_sales"] = monthly.groupby("Store")["Sales"].shift(1)
    monthly["mom_growth_pct"] = (
        (monthly["Sales"] - monthly["prev_month_sales"]) /
        monthly["prev_month_sales"] * 100
    ).round(2)
    return monthly.dropna(subset=["mom_growth_pct"])

# ── KPI 5: Store Performance Tier ────────────────────────────────────────────
def kpi_store_tier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ranks stores into Top/Mid/Bottom tercile based on 12-month sales.
    Enables like-for-like benchmarking within a tier (avoids comparing
    a high-volume A-type to a small D-type store).
    """
    annual = df[df["Open"] == 1].groupby("Store")["Sales"].sum().reset_index()
    annual.columns = ["Store", "annual_sales"]
    annual["tier"] = pd.qcut(
        annual["annual_sales"], q=3,
        labels=["Bottom Tier", "Mid Tier", "Top Tier"]
    )
    return annual

# ── RUNNER ────────────────────────────────────────────────────────────────────
def run_kpi_engine():
    df = load_clean()
    print(f"Loaded {len(df):,} clean rows across {df['Store'].nunique()} stores\n")

    print("Computing KPI 1: Weekly Revenue Index...")
    wri = kpi_weekly_revenue_index(df)
    wri.to_parquet(PROC_DIR / "kpi_weekly_revenue_index.parquet", index=False)
    print(f"  → {len(wri):,} store-week rows | avg index: {wri['weekly_revenue_index'].mean():.3f}\n")

    print("Computing KPI 2: Promo Lift %...")
    pl = kpi_promo_lift(df)
    pl.to_parquet(PROC_DIR / "kpi_promo_lift.parquet", index=False)
    print(f"  → {len(pl):,} store-month rows | median lift: {pl['promo_lift_pct'].median():.1f}%\n")

    print("Computing KPI 3: Customer Conversion...")
    cc = kpi_customer_conversion(df)
    cc.to_parquet(PROC_DIR / "kpi_customer_conversion.parquet", index=False)
    print(f"  → {len(cc):,} store-week rows | avg sales/customer: {cc['sales_per_customer'].mean():.2f}\n")

    print("Computing KPI 4: MoM Growth...")
    mom = kpi_mom_growth(df)
    mom.to_parquet(PROC_DIR / "kpi_mom_growth.parquet", index=False)
    print(f"  → {len(mom):,} store-month rows | avg MoM growth: {mom['mom_growth_pct'].mean():.1f}%\n")

    print("Computing KPI 5: Store Tiers...")
    tiers = kpi_store_tier(df)
    tiers.to_parquet(PROC_DIR / "kpi_store_tiers.parquet", index=False)
    print(f"  → Tier distribution:\n{tiers['tier'].value_counts().to_string()}\n")

    print("✅ All KPIs computed and saved to data/processed/")

if __name__ == "__main__":
    run_kpi_engine()
