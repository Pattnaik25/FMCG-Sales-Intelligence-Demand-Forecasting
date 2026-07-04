"""
tests/test_kpi_engine.py
========================
Unit tests for governed KPI logic.
Test your formula before your stakeholder questions it.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import importlib
sys.path.insert(0, "src")

kpi_engine  = importlib.import_module("02_kpi_engine")
forecasting = importlib.import_module("04_forecasting")

kpi_promo_lift          = kpi_engine.kpi_promo_lift
kpi_customer_conversion = kpi_engine.kpi_customer_conversion
wape = forecasting.wape
bias = forecasting.bias
mape = forecasting.mape


class TestPromoLift:
    def make_df(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        return pd.DataFrame({
            "Store":     [1] * 60,
            "Date":      dates,
            "Sales":     [100.0 if i % 2 == 0 else 200.0 for i in range(60)],
            "Customers": [50] * 60,
            "Open":      [1] * 60,
            "Promo":     [i % 2 for i in range(60)],
            "Month":     dates.to_period("M").to_timestamp(),
        })

    def test_promo_lift_positive(self):
        df = self.make_df()
        result = kpi_promo_lift(df)
        assert not result.empty
        assert (result["promo_lift_pct"] > 0).all()


class TestForecastMetrics:
    def test_wape_perfect(self):
        a = np.array([100.0, 200.0, 300.0])
        assert wape(a, a) == 0.0

    def test_wape_known_value(self):
        actual   = np.array([100.0, 100.0])
        forecast = np.array([120.0, 80.0])
        assert wape(actual, forecast) == 20.0

    def test_bias_over_forecast(self):
        actual   = np.array([100.0])
        forecast = np.array([110.0])
        assert bias(actual, forecast) > 0

    def test_bias_balanced(self):
        actual   = np.array([100.0, 100.0])
        forecast = np.array([110.0, 90.0])
        assert abs(bias(actual, forecast)) < 0.01

    def test_mape_zero_actuals_excluded(self):
        actual   = np.array([0.0, 100.0])
        forecast = np.array([50.0, 110.0])
        assert mape(actual, forecast) == 10.0
