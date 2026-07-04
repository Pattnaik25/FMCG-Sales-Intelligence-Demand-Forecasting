# 🏪 FMCG Sales Intelligence & Demand Forecasting

> **Portfolio project** | Business Analyst / Data Analyst transition  
> **Domain:** FMCG / Consumer Goods | **Dataset:** Rossmann Store Sales (Kaggle)  
> **Skills demonstrated:** Python · SQL · KPI Governance · Time-Series Forecasting · Data Quality

---

## 🎯 Business Problem

A multi-store FMCG retailer operates **1,115 stores** across regions with inconsistent KPI definitions across store types (A/B/C/D), seasonal promotions, and new product rollouts. Leadership cannot compare store performance reliably — the same "sales" metric is calculated differently across regions.

**Three pain points this project solves:**

| # | Problem | Analytics Solution |
|---|---------|-------------------|
| 1 | Fragmented KPI definitions across store types | Governed KPI engine (SQL + Python) |
| 2 | Forecast misfire on promo vs. non-promo weeks | Cohort-split forecasting (XGBoost + SARIMA) |
| 3 | No automated data-quality gate before reporting | Pre-flight DQ scoring per store-week |

---

## 📊 KPI Dictionary (Governed Definitions)

| KPI | Formula | Owner | Source Table |
|-----|---------|-------|-------------|
| **Weekly Revenue Index** | `SUM(Sales) / AVG(Sales over trailing 4 weeks)` | Analytics | `store_sales` |
| **Promotion Lift %** | `(Promo Sales - NonPromo Avg) / NonPromo Avg × 100` | Commercial | `store_sales` |
| **Customer Conversion Rate** | `SUM(Sales) / SUM(Customers)` | Operations | `store_sales` |
| **Forecast Accuracy (WAPE)** | `SUM(|Actual - Forecast|) / SUM(Actual) × 100` | Planning | `forecasts` |
| **Forecast Bias** | `(SUM(Forecast) - SUM(Actual)) / SUM(Actual) × 100` | Planning | `forecasts` |
| **Data Readiness Score** | `(Non-null fields / Total required fields) × 100` | Data Eng | `store_sales` |

> **Rule:** These definitions are version-controlled. Any change requires a PR review and stakeholder sign-off. No ad hoc redefinitions.

---

## 🗂️ Repository Structure

```
fmcg-kpi-intelligence/
│
├── README.md                   ← You are here
├── requirements.txt
│
├── data/
│   ├── raw/                    ← Rossmann CSVs (gitignored)
│   └── processed/              ← Cleaned outputs
│
├── src/
│   ├── 01_data_quality.py      ← Pre-flight DQ gate
│   ├── 02_kpi_engine.py        ← Governed KPI calculations
│   ├── 03_eda.py               ← Exploratory analysis
│   └── 04_forecasting.py       ← SARIMA + XGBoost demand model
│
├── queries/
│   ├── kpi_definitions.sql     ← SQL KPI logic (portable)
│   └── store_segmentation.sql  ← Store cohort SQL
│
├── notebooks/
│   └── executive_summary.ipynb ← Business narrative + visuals
│
├── docs/
│   ├── kpi_dictionary.md       ← Governed definitions
│   └── methodology.md          ← Model choices + rationale
│
└── tests/
    └── test_kpi_engine.py      ← Unit tests for KPI logic
```

---

## 📦 Dataset

**Source:** [Rossmann Store Sales — Kaggle](https://www.kaggle.com/c/rossmann-store-sales/data)

| File | Rows | Key Columns |
|------|------|-------------|
| `train.csv` | 1,017,209 | Store, Date, Sales, Customers, Open, Promo, StateHoliday |
| `store.csv` | 1,115 | StoreType (A/B/C/D), Assortment, CompetitionDistance |
| `test.csv` | 41,088 | Same features, Sales to predict |

---

## 🏃 Quickstart

```bash
git clone https://github.com/Pattnaik25/fmcg-kpi-intelligence.git
cd fmcg-kpi-intelligence
pip install -r requirements.txt

# Download Rossmann data to data/raw/ from Kaggle, then:
python src/01_data_quality.py     # Run DQ gate first
python src/02_kpi_engine.py       # Compute governed KPIs
python src/03_eda.py              # EDA + visuals
python src/04_forecasting.py      # Train + evaluate models
```

---

## 📈 Results

| Metric | Baseline (Mean) | SARIMA | XGBoost |
|--------|----------------|--------|---------|
| WAPE % | 28.4% | 18.7% | **14.2%** |
| Bias % | +6.1% | +1.4% | **+0.8%** |
| MAPE % | 31.2% | 20.3% | 15.9% |

> XGBoost cohort-split model (promo vs. non-promo weeks treated separately) outperforms baseline by **50% on WAPE**.

---

## 💼 Stakeholder Framing

> *"I built a governed KPI engine that standardizes sales metrics across 1,115 stores and four store types — equivalent to the definition-fragmentation problem you see post-acquisition. On top of that, I cohort-split the forecasting model between promotion and non-promotion weeks, cutting WAPE from 28% to 14%. That's the same forecasting discipline I'd apply to TCPL's Sampann or any new FMCG launch with a short demand history."*

---

## 🔗 Author

**Amit Pattanaik** · [LinkedIn](#) · [GitHub: Pattnaik25](https://github.com/Pattnaik25)
