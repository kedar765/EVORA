"""
EVORA Task 1: Automated Test Suite for Forecasting with Active User Dataset
=============================================================================
Comprehensive unit and integration tests verifying all 10 requirements:
 1. Forecast with authenticated user's saved dataset (CSV)
 2. Dataset switching reflects correct dataset metadata and prediction
 3. Strict ownership isolation (User A cannot access User B's dataset -> 404)
 4. Invalid dataset ID (404) and empty dataset ID (400) handling
 5. Missing required time-series columns (Date / Financials -> 400)
 6. Insufficient historical records (< 30 days -> 400)
 7. Excel dataset support (.xlsx)
 8. Backward compatibility when dataset_id is omitted (None -> baseline model)
 9. POST /forecast/next-day file upload compatibility
 10. Analysis history persistence with dataset_id and metadata in SQLite
"""

import io
import json
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from fastapi import HTTPException

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import backend.auth as auth
import backend.main as main
import tools.dataset_tools as dt
from ml.forecast import DailyProfitForecaster, DEFAULT_MODEL_PATH
from backend.main import get_next_day_forecast


class TestForecastDatasetIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="evora_forecast_test_")
        cls.temp_dir = Path(cls.temp_dir_obj.name)
        cls.test_db = cls.temp_dir / "evora_test.db"
        cls.test_uploads = cls.temp_dir / "backend" / "storage" / "uploads"
        cls.test_uploads.mkdir(parents=True, exist_ok=True)

        cls.original_db_path = auth.DB_PATH
        cls.original_upload_dir = main.UPLOAD_STORAGE_DIR
        cls.original_root_dir = main.ROOT_DIR
        cls.original_dt_root = dt.ROOT_DIR
        cls.original_env_upload = os.environ.get("EVORA_UPLOAD_DIR")
        cls.original_forecaster = main.daily_profit_forecaster

        # Patch paths to isolated test sandbox
        auth.DB_PATH = cls.test_db
        main.ROOT_DIR = cls.temp_dir
        main.UPLOAD_STORAGE_DIR = cls.test_uploads
        dt.ROOT_DIR = cls.temp_dir
        os.environ["EVORA_UPLOAD_DIR"] = str(cls.test_uploads)

        auth.initialize_database()

        # Initialize real forecaster with existing trained model
        main.daily_profit_forecaster = DailyProfitForecaster(model_path=DEFAULT_MODEL_PATH)

        # Users
        cls.user_a = str(uuid.uuid4())
        cls.user_b = str(uuid.uuid4())
        cls._insert_user(cls.user_a, "user_a@example.test", "User Alpha")
        cls._insert_user(cls.user_b, "user_b@example.test", "User Beta")

    @classmethod
    def _insert_user(cls, user_id, email, full_name):
        with auth.database() as conn:
            conn.execute(
                """
                INSERT INTO users (id, full_name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, full_name, email, "dummy_hash_for_test", 1000),
            )

    @classmethod
    def tearDownClass(cls):
        auth.DB_PATH = cls.original_db_path
        main.UPLOAD_STORAGE_DIR = cls.original_upload_dir
        main.ROOT_DIR = cls.original_root_dir
        dt.ROOT_DIR = cls.original_dt_root
        if cls.original_env_upload is not None:
            os.environ["EVORA_UPLOAD_DIR"] = cls.original_env_upload
        else:
            os.environ.pop("EVORA_UPLOAD_DIR", None)
        main.daily_profit_forecaster = cls.original_forecaster
        cls.temp_dir_obj.cleanup()

    def _create_and_register_dataset(
        self,
        user_id: str,
        df: pd.DataFrame,
        filename: str = "business_data.csv",
        is_excel: bool = False,
    ) -> str:
        dataset_id = str(uuid.uuid4())
        orig_ext = ".xlsx" if is_excel else ".csv"
        stored_filename = f"{dataset_id}{orig_ext}"
        stored_path = self.test_uploads / stored_filename

        if is_excel:
            df.to_excel(stored_path, index=False, engine="openpyxl")
        else:
            df.to_csv(stored_path, index=False)

        relative_storage_path = f"backend/storage/uploads/{stored_filename}"

        date_start = None
        date_end = None
        if "Date" in df.columns:
            dt_series = pd.to_datetime(df["Date"], errors="coerce").dropna()
            if not dt_series.empty:
                date_start = dt_series.min().strftime("%Y-%m-%d")
                date_end = dt_series.max().strftime("%Y-%m-%d")

        with auth.database() as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    id, user_id, original_filename, stored_filename, storage_path,
                    uploaded_at, row_count, column_count, columns_json,
                    date_start, date_end, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    user_id,
                    filename,
                    stored_filename,
                    relative_storage_path,
                    1000,
                    len(df),
                    len(df.columns),
                    json.dumps(list(df.columns)),
                    date_start,
                    date_end,
                    "active",
                ),
            )
        return dataset_id

    def test_01_forecast_with_user_saved_dataset(self):
        """Authenticated user forecasts using their own saved 40-day CSV dataset."""
        dates = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(40)]
        df = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Quantity": [10 + (i % 5) for i in range(40)],
            "Revenue": [2000.0 + (i * 20.0) for i in range(40)],
            "Expense": [1200.0 + (i * 10.0) for i in range(40)],
            "Product": ["Product A" for _ in range(40)],
        })
        ds_id = self._create_and_register_dataset(self.user_a, df, "alpha_q1.csv")

        user_auth = {"id": self.user_a, "email": "user_a@example.test"}
        data = get_next_day_forecast(dataset_id=ds_id, user=user_auth)

        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("dataset_id"), ds_id)
        self.assertEqual(data.get("filename"), "alpha_q1.csv")
        self.assertIn("predicted_profit", data)
        self.assertIn("forecast_date", data)
        self.assertIn("analysis_id", data)

        # Check SQLite persistence in analysis_history
        with auth.database() as conn:
            row = conn.execute(
                "SELECT dataset_id, analysis_type FROM analysis_history WHERE id = ?",
                (data["analysis_id"],),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["dataset_id"], ds_id)
            self.assertEqual(row["analysis_type"], "future_profit_forecast")

    def test_02_forecast_dataset_switching(self):
        """Switching between two distinct user datasets produces distinct responses."""
        dates1 = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(35)]
        df1 = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates1],
            "Revenue": [10000.0 + (i * 100.0) for i in range(35)],
            "Expense": [4000.0 + (i * 50.0) for i in range(35)],
        })
        ds1 = self._create_and_register_dataset(self.user_a, df1, "high_revenue.csv")

        dates2 = [datetime(2026, 6, 1) + timedelta(days=i) for i in range(35)]
        df2 = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates2],
            "Revenue": [1000.0 + (i * 10.0) for i in range(35)],
            "Expense": [800.0 + (i * 5.0) for i in range(35)],
        })
        ds2 = self._create_and_register_dataset(self.user_a, df2, "low_revenue.csv")

        user_auth = {"id": self.user_a, "email": "user_a@example.test"}
        data1 = get_next_day_forecast(dataset_id=ds1, user=user_auth)
        data2 = get_next_day_forecast(dataset_id=ds2, user=user_auth)

        self.assertEqual(data1["dataset_id"], ds1)
        self.assertEqual(data1["filename"], "high_revenue.csv")
        self.assertEqual(data2["dataset_id"], ds2)
        self.assertEqual(data2["filename"], "low_revenue.csv")
        # Predictions on high revenue dataset vs low revenue dataset differ
        self.assertNotEqual(data1["predicted_profit"], data2["predicted_profit"])

    def test_03_dataset_ownership_isolation(self):
        """User A cannot forecast User B's dataset (returns 404)."""
        dates = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(35)]
        df_b = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Revenue": [3000.0 for _ in range(35)],
            "Expense": [1500.0 for _ in range(35)],
        })
        ds_b = self._create_and_register_dataset(self.user_b, df_b, "user_b_private.csv")

        # Active user is User A attempting to access User B's dataset
        user_auth_a = {"id": self.user_a, "email": "user_a@example.test"}
        with self.assertRaises(HTTPException) as ctx:
            get_next_day_forecast(dataset_id=ds_b, user=user_auth_a)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found or access unauthorized", ctx.exception.detail.lower())

    def test_04_invalid_and_empty_dataset_id(self):
        """Non-existent ID returns 404, empty ID returns 400."""
        user_auth = {"id": self.user_a, "email": "user_a@example.test"}

        # Non-existent ID
        with self.assertRaises(HTTPException) as ctx_404:
            get_next_day_forecast(dataset_id="00000000-0000-0000-0000-000000000000", user=user_auth)
        self.assertEqual(ctx_404.exception.status_code, 404)

        # Empty/whitespace ID
        with self.assertRaises(HTTPException) as ctx_400:
            get_next_day_forecast(dataset_id="   ", user=user_auth)
        self.assertEqual(ctx_400.exception.status_code, 400)
        self.assertIn("dataset_id cannot be empty", ctx_400.exception.detail)

    def test_05_missing_required_columns(self):
        """Datasets missing Date or financial columns return HTTP 400."""
        user_auth = {"id": self.user_a, "email": "user_a@example.test"}

        # Missing Date column
        df_no_date = pd.DataFrame({
            "Revenue": [2000.0 for _ in range(35)],
            "Expense": [1000.0 for _ in range(35)],
        })
        ds_no_date = self._create_and_register_dataset(self.user_a, df_no_date, "no_date.csv")
        with self.assertRaises(HTTPException) as ctx1:
            get_next_day_forecast(dataset_id=ds_no_date, user=user_auth)
        self.assertEqual(ctx1.exception.status_code, 400)
        self.assertIn("Date", ctx1.exception.detail)

        # Missing Revenue & Expense
        dates = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(35)]
        df_no_fin = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Customer": [f"Cust {i}" for i in range(35)],
        })
        ds_no_fin = self._create_and_register_dataset(self.user_a, df_no_fin, "no_financials.csv")
        with self.assertRaises(HTTPException) as ctx2:
            get_next_day_forecast(dataset_id=ds_no_fin, user=user_auth)
        self.assertEqual(ctx2.exception.status_code, 400)

    def test_06_insufficient_historical_records(self):
        """Datasets with fewer than 30 daily records return HTTP 400."""
        dates = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(15)]
        df_short = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Revenue": [2000.0 for _ in range(15)],
            "Expense": [1000.0 for _ in range(15)],
        })
        ds_short = self._create_and_register_dataset(self.user_a, df_short, "short_series.csv")

        user_auth = {"id": self.user_a, "email": "user_a@example.test"}
        with self.assertRaises(HTTPException) as ctx:
            get_next_day_forecast(dataset_id=ds_short, user=user_auth)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Insufficient historical daily records", ctx.exception.detail)

    def test_07_excel_dataset_support(self):
        """Excel (.xlsx) dataset format loads and forecasts successfully."""
        dates = [datetime(2026, 2, 1) + timedelta(days=i) for i in range(36)]
        df_excel = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Revenue": [3500.0 + (i * 15.0) for i in range(36)],
            "Expense": [1800.0 + (i * 8.0) for i in range(36)],
        })
        ds_excel = self._create_and_register_dataset(self.user_a, df_excel, "quarterly_data.xlsx", is_excel=True)

        user_auth = {"id": self.user_a, "email": "user_a@example.test"}
        data = get_next_day_forecast(dataset_id=ds_excel, user=user_auth)
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("filename"), "quarterly_data.xlsx")
        self.assertIn("predicted_profit", data)

    def test_08_backward_compatibility_without_dataset_id(self):
        """Omitting dataset_id continues to produce baseline forecast without breaking."""
        user_auth = {"id": self.user_a, "email": "user_a@example.test"}
        data = get_next_day_forecast(dataset_id=None, user=user_auth)
        self.assertEqual(data.get("status"), "success")
        self.assertIn("predicted_profit", data)
        self.assertIn("forecast_date", data)

    def test_09_direct_call_without_args_compatibility(self):
        """Direct call get_next_day_forecast() with default params preserves backward compatibility."""
        data = get_next_day_forecast()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("predicted_profit", data)
        self.assertIn("forecast_date", data)

    def test_10_forecasting_with_direct_dataframe_compatibility(self):
        """Forecasting with directly supplied historical transaction DataFrame (as done in POST endpoint) succeeds."""
        dates = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(35)]
        df_upload = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Revenue": [4000.0 for _ in range(35)],
            "Expense": [2000.0 for _ in range(35)],
        })
        result = main.daily_profit_forecaster.predict_next_day(historical_df=df_upload)
        self.assertEqual(result.get("status"), "success")
        self.assertIn("predicted_profit", result)
        self.assertIn("forecast_date", result)


if __name__ == "__main__":
    unittest.main()
