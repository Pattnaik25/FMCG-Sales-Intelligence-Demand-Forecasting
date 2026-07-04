"""
src/01_data_quality.py
======================
Pre-flight data quality gate — must pass before any KPI or model runs.
Mirrors the DQ governance logic used for regulated FMCG launches.

Business rationale:
    A KPI built on bad data is worse than no KPI — it creates false
    confidence. This gate scores each store-week record and routes
    Amber/Red records for review before they pollute downstream logic.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

# ── CONFIG ───────────────────────────────────────────────────────────────────
RAW_DIR   = Path("data/raw")
PROC_DIR  = Path("data/processed")
PROC_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLS = ["Store", "Date", "Sales", "Customers", "Open", "Promo"]
GREEN_THRESHOLD  = 90   # % readiness → passes automatically
AMBER_THRESHOLD  = 70   # % readiness → routes for human review
# below AMBER_THRESHOLD → Red (blocked from downstream)

# ── LOAD ─────────────────────────────────────────────────────────────────────
def load_raw() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "train.csv", parse_dates=["Date"], low_memory=False)
    store = pd.read_csv(RAW_DIR / "store.csv")
    return df.merge(store, on="Store", how="left")

# ── CHECKS ───────────────────────────────────────────────────────────────────
def check_nulls(df: pd.DataFrame) -> pd.Series:
    """Returns null % per column for required fields."""
    return df[REQUIRED_COLS].isnull().mean().mul(100).round(2)

def check_duplicates(df: pd.DataFrame) -> int:
    return int(df.duplicated(subset=["Store", "Date"]).sum())

def check_negative_sales(df: pd.DataFrame) -> int:
    return int((df["Sales"] < 0).sum())

def check_sales_when_closed(df: pd.DataFrame) -> int:
    """Stores reporting sales > 0 when Open == 0 — a data integrity flag."""
    return int(((df["Open"] == 0) & (df["Sales"] > 0)).sum())

def check_date_continuity(df: pd.DataFrame) -> dict:
    """Checks for missing dates per store — gaps break time-series models."""
    full_range = pd.date_range(df["Date"].min(), df["Date"].max(), freq="D")
    gaps = {}
    for store_id, grp in df.groupby("Store"):
        missing = len(full_range) - grp["Date"].nunique()
        if missing > 0:
            gaps[int(store_id)] = missing
    return {"stores_with_gaps": len(gaps), "max_gap_days": max(gaps.values()) if gaps else 0}

# ── READINESS SCORE ───────────────────────────────────────────────────────────
def readiness_score(null_pct: pd.Series) -> float:
    """
    Simple completeness score: average non-null % across required fields.
    Extend with weighted fields for production use.
    """
    return round(100 - null_pct.mean(), 2)

# ── GATE LOGIC ────────────────────────────────────────────────────────────────
def classify(score: float) -> str:
    if score >= GREEN_THRESHOLD:
        return "GREEN  ✅ — Passes to KPI engine"
    elif score >= AMBER_THRESHOLD:
        return "AMBER  ⚠️  — Route to data owner for review"
    else:
        return "RED    ❌  — Blocked: too many quality issues"

# ── REPORT ────────────────────────────────────────────────────────────────────
def run_gate(df: pd.DataFrame) -> dict:
    null_pct  = check_nulls(df)
    score     = readiness_score(null_pct)
    status    = classify(score)
    date_info = check_date_continuity(df)

    report = {
        "dataset_shape":          list(df.shape),
        "null_pct_by_field":      null_pct.to_dict(),
        "duplicate_store_dates":  check_duplicates(df),
        "negative_sales_rows":    check_negative_sales(df),
        "sales_while_closed":     check_sales_when_closed(df),
        "date_continuity":        date_info,
        "readiness_score_pct":    score,
        "gate_status":            status,
    }

    print("\n── DATA QUALITY GATE REPORT ──────────────────────────────")
    for k, v in report.items():
        print(f"  {k:<30} {v}")
    print("──────────────────────────────────────────────────────────\n")

    # Persist report
    with open(PROC_DIR / "dq_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Filter clean rows only for downstream
    clean_df = df[
        df["Sales"].notna() &
        df["Customers"].notna() &
        (df["Sales"] >= 0) &
        ~((df["Open"] == 0) & (df["Sales"] > 0))
    ].copy()

    clean_df.to_parquet(PROC_DIR / "clean_train.parquet", index=False)
    print(f"  Clean rows saved: {len(clean_df):,} / {len(df):,}")
    return report


if __name__ == "__main__":
    df = load_raw()
    run_gate(df)
