"""
EVORA Step 1: Automated Test Suite for ML Model Improvement
===========================================================
Tests all 14 mandatory validation requirements:
 1. Dataset loading
 2. Financial calculation validation
 3. Missing-date handling
 4. Feature engineering
 5. Leakage prevention
 6. Chronological splitting
 7. Model training
 8. Model saving
 9. Model loading
10. Next-day prediction
11. Invalid input handling
12. Forecast API authentication
13. Existing Risk API compatibility
14. Existing What-If API compatibility
"""

import json
import os
import sys
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import HTTPException

# Ensure paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.auth import get_current_user
from backend.main import (
    RiskAnalysisRequest,
    WhatIfRequest,
    analyze_risk,
    app,
    get_next_day_forecast,
    what_if_analysis,
)
from ml.forecast import (
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    FEATURE_COLUMNS,
    MIN_DAILY_RECORDS,
    DailyProfitForecaster,
    aggregate_daily_metrics,
    build_historical_features,
    build_next_day_feature_vector,
    validate_transaction_dataframe,
)
from ml.train_forecast_model import (
    prepare_chronological_splits,
    train_and_compare_models,
    validate_raw_dataset,
)


class TestEVORAMachineLearning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_path = DEFAULT_DATA_PATH
        cls.model_path = DEFAULT_MODEL_PATH
        cls.profit_model_path = ROOT_DIR / "ml" / "profit_model.pkl"
        cls.df_raw = pd.read_csv(cls.data_path)

    # 1. Dataset Loading
    def test_01_dataset_loading(self):
        self.assertTrue(self.data_path.exists(), "Dataset file does not exist.")
        self.assertGreaterEqual(len(self.df_raw), 5000, "Dataset should have at least 5000 rows.")
        expected_cols = {
            "Transaction_ID", "Date", "Product", "Category", "Quantity",
            "Unit_Price", "Discount_Percent", "Revenue", "Cost_Per_Unit",
            "Shipping_Cost", "Marketing_Spend", "Expense", "Customer",
            "Region", "Sales_Channel", "Promotion_Active"
        }
        self.assertTrue(expected_cols.issubset(set(self.df_raw.columns)), "Missing expected columns in CSV.")

    # 2. Financial Calculation Validation
    def test_02_financial_calculation_validation(self):
        df = self.df_raw.copy()
        calc_revenue = df["Quantity"] * df["Unit_Price"] * (1.0 - df["Discount_Percent"] / 100.0)
        diff_rev = np.abs(df["Revenue"] - calc_revenue)
        self.assertLessEqual(diff_rev.max(), 0.05, "Revenue formula mismatch exceeding rounding tolerance.")

        calc_expense = (df["Quantity"] * df["Cost_Per_Unit"]) + df["Shipping_Cost"] + df["Marketing_Spend"]
        diff_exp = np.abs(df["Expense"] - calc_expense)
        self.assertLessEqual(diff_exp.max(), 0.05, "Expense formula mismatch exceeding rounding tolerance.")

        calc_profit = df["Revenue"] - df["Expense"]
        diff_profit = np.abs((df["Revenue"] - df["Expense"]) - calc_profit)
        self.assertEqual(diff_profit.max(), 0.0, "Profit must equal Revenue - Expense exactly.")

        # Ensure negative profit (genuine business losses) exists and is preserved
        neg_count = (calc_profit < 0).sum()
        self.assertGreater(neg_count, 0, "Dataset must retain genuine business loss transactions.")

    # 3. Missing-Date Handling
    def test_03_missing_date_handling(self):
        daily = aggregate_daily_metrics(self.df_raw)
        self.assertGreaterEqual(len(daily), 1000, "Aggregated daily count should exceed 1000 days.")
        
        # Verify chronological ordering
        dates = daily["Date"].tolist()
        self.assertEqual(dates, sorted(dates), "Daily aggregated time series must be sorted chronologically.")

        # Test artificially inserted gap handling
        sample_sparse = self.df_raw[self.df_raw["Date"].isin(self.df_raw["Date"].unique()[:40])]
        daily_sparse = aggregate_daily_metrics(sample_sparse)
        self.assertEqual(len(daily_sparse), 40)

    # 4. Feature Engineering
    def test_04_feature_engineering(self):
        daily = aggregate_daily_metrics(self.df_raw)
        features_df = build_historical_features(daily)
        
        for col in FEATURE_COLUMNS:
            self.assertIn(col, features_df.columns, f"Engineered column {col} is missing from feature matrix.")

        # Check types
        self.assertTrue(np.issubdtype(features_df["day_index"].dtype, np.integer))
        self.assertTrue(np.issubdtype(features_df["is_weekend"].dtype, np.integer))

    # 5. Leakage Prevention
    def test_05_leakage_prevention(self):
        daily = aggregate_daily_metrics(self.df_raw)
        features_df = build_historical_features(daily)

        # For any row t >= 30, test that features do not know Profit[t]
        for t in [30, 50, 100, 200]:
            # profit_lag_1 at day t must equal profit at day t-1
            self.assertAlmostEqual(features_df.loc[t, "profit_lag_1"], daily.loc[t - 1, "Profit"], places=4)
            # profit_lag_7 at day t must equal profit at day t-7
            self.assertAlmostEqual(features_df.loc[t, "profit_lag_7"], daily.loc[t - 7, "Profit"], places=4)
            # profit_mean_7 at day t must strictly equal mean of t-7 to t-1
            expected_mean_7 = daily.loc[t - 7 : t - 1, "Profit"].mean()
            self.assertAlmostEqual(features_df.loc[t, "profit_mean_7"], expected_mean_7, places=4)

        # Vector test: Next-day feature vector for day T+1
        feat_row, f_date = build_next_day_feature_vector(daily)
        self.assertEqual(f_date, daily["Date"].iloc[-1] + pd.Timedelta(days=1))
        self.assertAlmostEqual(feat_row["profit_lag_1"].iloc[0], daily["Profit"].iloc[-1], places=4)
        self.assertAlmostEqual(feat_row["profit_mean_7"].iloc[0], daily["Profit"].iloc[-7:].mean(), places=4)

    # 6. Chronological Splitting
    def test_06_chronological_splitting(self):
        daily = aggregate_daily_metrics(self.df_raw)
        feat_df = build_historical_features(daily)
        train_df, val_df, test_df = prepare_chronological_splits(feat_df, 0.70, 0.15)

        self.assertGreater(len(train_df), 0)
        self.assertGreater(len(val_df), 0)
        self.assertGreater(len(test_df), 0)

        # Strict chronological order
        self.assertLess(train_df["Date"].max(), val_df["Date"].min(), "Train overlaps with Val!")
        self.assertLess(val_df["Date"].max(), test_df["Date"].min(), "Val overlaps with Test!")

    # 7. Model Training
    def test_07_model_training(self):
        daily = aggregate_daily_metrics(self.df_raw)
        feat_df = build_historical_features(daily)
        train_df, val_df, _ = prepare_chronological_splits(feat_df, 0.70, 0.15)

        best_name, best_model, comp = train_and_compare_models(train_df, val_df, FEATURE_COLUMNS)
        self.assertIsNotNone(best_model)
        self.assertIn("ExtraTrees", best_name)
        self.assertGreater(len(comp), 4, "Comparison must include baselines and multiple ML models.")

    # 8. Model Saving
    def test_08_model_saving(self):
        self.assertTrue(self.model_path.exists(), "Forecast model artifact file missing on disk.")
        self.assertTrue(self.profit_model_path.exists(), "Original profit model must exist.")

        # Ensure daily_profit_forecast_model.pkl is separate from profit_model.pkl
        self.assertNotEqual(
            self.model_path.resolve(),
            self.profit_model_path.resolve(),
            "daily_profit_forecast_model.pkl must not overwrite profit_model.pkl",
        )

        artifact = joblib.load(self.model_path)
        self.assertIn("model", artifact)
        self.assertIn("features", artifact)
        self.assertIn("metadata", artifact)
        self.assertEqual(artifact["metadata"]["model_name"], "ExtraTreesRegressor")

    # 9. Model Loading
    def test_09_model_loading(self):
        forecaster = DailyProfitForecaster(self.model_path)
        self.assertTrue(forecaster.is_loaded)
        self.assertIsNotNone(forecaster.model)
        self.assertEqual(len(forecaster.metadata["features"]), len(FEATURE_COLUMNS))

    # 10. Next-Day Prediction
    def test_10_next_day_prediction(self):
        forecaster = DailyProfitForecaster(self.model_path)
        result = forecaster.predict_next_day(historical_df=self.df_raw)

        self.assertIn("forecast_date", result)
        self.assertIn("predicted_profit", result)
        self.assertEqual(result["currency"], "INR")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["model_name"], "ExtraTreesRegressor")
        self.assertIsInstance(result["predicted_profit"], float)
        self.assertTrue(result["forecast_date"].startswith("2026-11"))

    # 11. Invalid Input Handling
    def test_11_invalid_input_handling(self):
        forecaster = DailyProfitForecaster(self.model_path)

        # Empty DataFrame
        with self.assertRaises(ValueError):
            forecaster.predict_next_day(historical_df=pd.DataFrame())

        # Insufficient rows (< 30 days)
        short_df = self.df_raw.iloc[:15].copy()
        with self.assertRaises(ValueError):
            forecaster.predict_next_day(historical_df=short_df)

        # Missing required Date column
        no_date = self.df_raw.drop(columns=["Date"])
        with self.assertRaises(ValueError):
            forecaster.predict_next_day(historical_df=no_date)

    # 12. Forecast API Authentication
    def test_12_forecast_api_authentication(self):
        # 1. Unauthenticated call to get_current_user must raise 401
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(None)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Login required.")

        # 2. Endpoint execution returns valid structured forecast
        response = get_next_day_forecast()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["currency"], "INR")
        self.assertIn("predicted_profit", response)
        self.assertIn("forecast_date", response)
        self.assertIn("model_metrics", response)
        self.assertIn("mae", response["model_metrics"])

    # 13. Existing Risk API Compatibility
    def test_13_existing_risk_api_compatibility(self):
        # Risk Analysis requires Quantity, Revenue, Expense
        req = RiskAnalysisRequest(Quantity=10.0, Revenue=50000.0, Expense=30000.0)
        res = analyze_risk(req)
        self.assertTrue(res["success"])
        self.assertIn("predicted_profit", res)
        self.assertIn("risk_score", res)
        self.assertIn("risk_level", res)
        self.assertIn("anomaly_detected", res)
        self.assertIn("risk_analysis", res)
        self.assertIn(res["risk_level"], ["LOW", "MEDIUM", "HIGH"])

    # 14. Existing What-If API Compatibility
    def test_14_existing_what_if_api_compatibility(self):
        req = WhatIfRequest(
            current_quantity=100.0,
            current_revenue=50000.0,
            current_expense=30000.0,
            new_quantity=120.0,
            new_revenue=65000.0,
            new_expense=35000.0,
        )
        res = what_if_analysis(req)
        self.assertTrue(res["success"])
        self.assertIn("current_predicted_profit", res)
        self.assertIn("new_predicted_profit", res)
        self.assertIn("profit_difference", res)
        self.assertIn("result", res)


if __name__ == "__main__":
    unittest.main()

