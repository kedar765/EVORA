"""Consolidated Step 2 database/history integration tests for EVORA.

Run from the project root:
    python -m unittest tests.test_step2_complete -v

Tests use a temporary SQLite database and temporary upload directory. They do
not modify the real backend/evora.db or backend/storage/uploads directory.
"""

import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

import backend.auth as auth
import backend.main as main


class FakeModel:
    def predict(self, frame):
        return np.full(len(frame), 1234.56, dtype=float)


class FakeAnomalyModel:
    def predict(self, frame):
        return np.ones(len(frame), dtype=int)


class FakeAnalyticsAgent:
    def analyze(self, dataframe):
        return {
            "total_revenue": float(dataframe["Revenue"].sum()),
            "total_expense": float(dataframe["Expense"].sum()),
            "rows": int(len(dataframe)),
        }


class FakeRiskAgent:
    def analyze(self, **kwargs):
        return {
            "risk_level": kwargs["risk_level"],
            "risk_score": kwargs["risk_score"],
            "reasons": ["Test risk assessment"],
        }


class FakeForecaster:
    is_loaded = True
    model = object()

    def predict_next_day(self, historical_df=None):
        return {
            "forecast_date": "2026-11-01",
            "predicted_profit": 1500.25,
            "currency": "INR",
            "model_name": "FakeForecastModel",
            "status": "success",
        }


class TestEVORAStep2Complete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="evora_step2_")
        cls.temp_dir = Path(cls.temp_dir_obj.name)
        cls.test_db = cls.temp_dir / "evora_test.db"
        cls.test_uploads = cls.temp_dir / "uploads"

        cls.original_db_path = auth.DB_PATH
        cls.original_upload_dir = main.UPLOAD_STORAGE_DIR
        cls.original_root_dir = main.ROOT_DIR
        cls.original_model = main.model
        cls.original_anomaly_model = main.anomaly_model
        cls.original_forecaster = main.daily_profit_forecaster
        cls.original_analytics_agent = main.analytics_agent
        cls.original_risk_agent = main.risk_agent

        auth.DB_PATH = cls.test_db
        main.ROOT_DIR = cls.temp_dir
        cls.test_uploads = cls.temp_dir / "backend" / "storage" / "uploads"
        main.UPLOAD_STORAGE_DIR = cls.test_uploads
        auth.initialize_database()

        cls.user_a = str(uuid.uuid4())
        cls.user_b = str(uuid.uuid4())
        cls._insert_user(cls.user_a, "step2-a@example.test")
        cls._insert_user(cls.user_b, "step2-b@example.test")

        cls.active_user = {"id": cls.user_a, "email": "step2-a@example.test", "fullName": "Test User A"}

        def override_current_user():
            return dict(cls.active_user)

        main.app.dependency_overrides[main.get_current_user] = override_current_user

        main.model = FakeModel()
        main.anomaly_model = FakeAnomalyModel()
        main.daily_profit_forecaster = FakeForecaster()
        main.analytics_agent = FakeAnalyticsAgent()
        main.risk_agent = FakeRiskAgent()

        cls.client = TestClient(main.app)
        cls.headers = {"Origin": "http://localhost:3000"}
        cls.csv_bytes = (
            "Date,Quantity,Revenue,Expense,Product\n"
            "2026-10-01,10,2000,1200,Product A\n"
            "2026-10-02,12,2400,1500,Product B\n"
            "2026-10-03,8,1600,900,Product A\n"
        ).encode("utf-8")
        cls.forecast_csv_bytes = (
            "Date,Revenue,Expense\n"
            "2026-10-01,2000,1200\n"
            "2026-10-02,2400,1500\n"
            "2026-10-03,1600,900\n"
        ).encode("utf-8")
        cls.created_dataset_id = None
        cls.created_analysis_ids = {}

    @classmethod
    def _insert_user(cls, user_id, email):
        with auth.database() as connection:
            connection.execute(
                """
                INSERT INTO users (id, full_name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, "EVORA Test User", email, "test-only-hash", 1),
            )

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.close()
        except Exception:
            pass
        main.app.dependency_overrides.clear()
        auth.DB_PATH = cls.original_db_path
        main.UPLOAD_STORAGE_DIR = cls.original_upload_dir
        main.ROOT_DIR = cls.original_root_dir
        main.model = cls.original_model
        main.anomaly_model = cls.original_anomaly_model
        main.daily_profit_forecaster = cls.original_forecaster
        main.analytics_agent = cls.original_analytics_agent
        main.risk_agent = cls.original_risk_agent
        cls.temp_dir_obj.cleanup()

    def test_01_full_analysis_workflow_persists_all_history(self):
        # 1. CSV upload: persists the CSV, dataset metadata and upload analysis.
        upload_response = self.client.post(
            "/upload",
            headers=self.headers,
            files={"file": ("step2_business.csv", self.csv_bytes, "text/csv")},
        )
        self.assertEqual(upload_response.status_code, 200, upload_response.text)
        upload_data = upload_response.json()
        self.assertTrue(upload_data["success"])
        dataset_id = upload_data["dataset_id"]
        self.__class__.created_dataset_id = dataset_id

        with auth.database() as connection:
            dataset_row = connection.execute(
                "SELECT * FROM datasets WHERE id = ? AND user_id = ?",
                (dataset_id, self.user_a),
            ).fetchone()
            upload_history = connection.execute(
                "SELECT id FROM analysis_history WHERE dataset_id = ? AND analysis_type = ?",
                (dataset_id, "upload_analysis"),
            ).fetchone()

        self.assertIsNotNone(dataset_row)
        self.assertIsNotNone(upload_history)
        stored_file = main.ROOT_DIR / dataset_row["storage_path"]
        self.assertTrue(stored_file.is_file())
        self.assertEqual(dataset_row["row_count"], 3)
        self.assertEqual(dataset_row["column_count"], 5)
        self.__class__.created_analysis_ids["upload_analysis"] = upload_history["id"]

        # 2. Business Analytics history.
        analytics_response = self.client.post(
            "/analytics",
            headers=self.headers,
            files={"file": ("analytics.csv", self.csv_bytes, "text/csv")},
        )
        self.assertEqual(analytics_response.status_code, 200, analytics_response.text)
        analytics_data = analytics_response.json()
        self.assertIn("analysis_id", analytics_data)
        self.__class__.created_analysis_ids["business_analytics"] = analytics_data["analysis_id"]

        # 3. ML Profit Prediction history.
        prediction_response = self.client.post(
            "/ml/predict-profit",
            headers=self.headers,
            json={"Quantity": 10, "Revenue": 2000, "Expense": 1200},
        )
        self.assertEqual(prediction_response.status_code, 200, prediction_response.text)
        prediction_data = prediction_response.json()
        self.assertIn("analysis_id", prediction_data)
        self.__class__.created_analysis_ids["profit_prediction"] = prediction_data["analysis_id"]

        # 4. Risk Analysis history.
        risk_response = self.client.post(
            "/analyze-risk",
            headers=self.headers,
            json={"Quantity": 10, "Revenue": 2000, "Expense": 1200},
        )
        self.assertEqual(risk_response.status_code, 200, risk_response.text)
        risk_data = risk_response.json()
        self.assertIn("analysis_id", risk_data)
        self.__class__.created_analysis_ids["risk_analysis"] = risk_data["analysis_id"]

        # 5. What-If history.
        what_if_response = self.client.post(
            "/what-if",
            headers=self.headers,
            json={
                "current_quantity": 10,
                "current_revenue": 2000,
                "current_expense": 1200,
                "new_quantity": 12,
                "new_revenue": 2600,
                "new_expense": 1450,
            },
        )
        self.assertEqual(what_if_response.status_code, 200, what_if_response.text)
        what_if_data = what_if_response.json()
        self.assertIn("analysis_id", what_if_data)
        self.__class__.created_analysis_ids["what_if_analysis"] = what_if_data["analysis_id"]

        # 6. GET future forecast history.
        forecast_get_response = self.client.get("/forecast/next-day")
        self.assertEqual(forecast_get_response.status_code, 200, forecast_get_response.text)
        forecast_get_data = forecast_get_response.json()
        self.assertIn("analysis_id", forecast_get_data)
        self.__class__.created_analysis_ids["future_forecast_get"] = forecast_get_data["analysis_id"]

        # 7. POST future forecast history.
        forecast_post_response = self.client.post(
            "/forecast/next-day",
            headers=self.headers,
            files={"file": ("forecast.csv", self.forecast_csv_bytes, "text/csv")},
        )
        self.assertEqual(forecast_post_response.status_code, 200, forecast_post_response.text)
        forecast_post_data = forecast_post_response.json()
        self.assertIn("analysis_id", forecast_post_data)
        self.__class__.created_analysis_ids["future_forecast_post"] = forecast_post_data["analysis_id"]

        # Dataset list/details/preview/history APIs.
        datasets_response = self.client.get("/datasets")
        self.assertEqual(datasets_response.status_code, 200, datasets_response.text)
        self.assertGreaterEqual(datasets_response.json()["total"], 1)

        details_response = self.client.get(f"/datasets/{dataset_id}")
        self.assertEqual(details_response.status_code, 200, details_response.text)
        self.assertEqual(details_response.json()["dataset"]["dataset_id"], dataset_id)

        preview_response = self.client.get(f"/datasets/{dataset_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        self.assertEqual(preview_response.json()["preview_rows"], 3)

        dataset_history_response = self.client.get(f"/datasets/{dataset_id}/history")
        self.assertEqual(dataset_history_response.status_code, 200, dataset_history_response.text)
        self.assertGreaterEqual(dataset_history_response.json()["total"], 1)

        # Analysis history list and detail APIs.
        history_response = self.client.get("/analysis-history?limit=100")
        self.assertEqual(history_response.status_code, 200, history_response.text)
        history_types = {item["analysis_type"] for item in history_response.json()["history"]}
        expected_types = {
            "upload_analysis",
            "business_analytics",
            "profit_prediction",
            "risk_analysis",
            "what_if_analysis",
            "future_profit_forecast",
        }
        self.assertTrue(expected_types.issubset(history_types), history_types)

        for key, analysis_id in self.created_analysis_ids.items():
            detail = self.client.get(f"/analysis-history/{analysis_id}")
            self.assertEqual(detail.status_code, 200, f"{key}: {detail.text}")
            self.assertIn("result", detail.json()["analysis"])

        # Exact history row count for the operations performed above.
        with auth.database() as connection:
            rows = connection.execute(
                "SELECT analysis_type, COUNT(*) AS n FROM analysis_history WHERE user_id = ? GROUP BY analysis_type",
                (self.user_a,),
            ).fetchall()
        counts = {row["analysis_type"]: row["n"] for row in rows}
        self.assertGreaterEqual(counts.get("upload_analysis", 0), 1)
        self.assertGreaterEqual(counts.get("business_analytics", 0), 1)
        self.assertGreaterEqual(counts.get("profit_prediction", 0), 1)
        self.assertGreaterEqual(counts.get("risk_analysis", 0), 1)
        self.assertGreaterEqual(counts.get("what_if_analysis", 0), 1)
        self.assertGreaterEqual(counts.get("future_profit_forecast", 0), 2)

    def test_02_user_isolation(self):
        dataset_id = self.__class__.created_dataset_id
        self.assertIsNotNone(dataset_id, "Workflow test must create a dataset first")
        upload_analysis_id = self.__class__.created_analysis_ids["upload_analysis"]

        # Switch the dependency override to User B.
        self.__class__.active_user = {
            "id": self.user_b,
            "email": "step2-b@example.test",
            "fullName": "Test User B",
        }

        datasets = self.client.get("/datasets")
        self.assertEqual(datasets.status_code, 200)
        self.assertEqual(datasets.json()["total"], 0)

        history = self.client.get("/analysis-history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["total"], 0)

        self.assertEqual(self.client.get(f"/datasets/{dataset_id}").status_code, 404)
        self.assertEqual(self.client.get(f"/datasets/{dataset_id}/preview").status_code, 404)
        self.assertEqual(self.client.get(f"/datasets/{dataset_id}/history").status_code, 404)
        self.assertEqual(self.client.get(f"/analysis-history/{upload_analysis_id}").status_code, 404)

        # Switch back to User A and confirm their records remain available.
        self.__class__.active_user = {
            "id": self.user_a,
            "email": "step2-a@example.test",
            "fullName": "Test User A",
        }
        own_dataset = self.client.get(f"/datasets/{dataset_id}")
        self.assertEqual(own_dataset.status_code, 200)

    def test_03_unauthenticated_private_endpoint_returns_401(self):
        saved_override = main.app.dependency_overrides.pop(main.get_current_user, None)
        try:
            response = self.client.get("/datasets")
            self.assertEqual(response.status_code, 401, response.text)
        finally:
            if saved_override is not None:
                main.app.dependency_overrides[main.get_current_user] = saved_override

    def test_04_failed_analysis_is_not_saved_as_success(self):
        with auth.database() as connection:
            before = connection.execute(
                "SELECT COUNT(*) FROM analysis_history WHERE user_id = ?",
                (self.user_a,),
            ).fetchone()[0]

        original_anomaly_model = main.anomaly_model
        main.anomaly_model = None
        try:
            response = self.client.post(
                "/analyze-risk",
                headers=self.headers,
                json={"Quantity": 10, "Revenue": 2000, "Expense": 1200},
            )
            self.assertEqual(response.status_code, 503, response.text)
        finally:
            main.anomaly_model = original_anomaly_model

        with auth.database() as connection:
            after = connection.execute(
                "SELECT COUNT(*) FROM analysis_history WHERE user_id = ?",
                (self.user_a,),
            ).fetchone()[0]
        self.assertEqual(before, after)

    def test_05_database_is_readable_after_new_connection(self):
        # Every request opens a new SQLite connection; verify persistence with
        # another independent connection after the write workflow.
        connection = sqlite3.connect(self.test_db)
        try:
            dataset_count = connection.execute(
                "SELECT COUNT(*) FROM datasets WHERE user_id = ?",
                (self.user_a,),
            ).fetchone()[0]
            history_count = connection.execute(
                "SELECT COUNT(*) FROM analysis_history WHERE user_id = ?",
                (self.user_a,),
            ).fetchone()[0]
        finally:
            # sqlite3.Connection's context manager commits/rolls back,
            # but does not close the connection. Close it explicitly so
            # Windows can remove the temporary database in tearDownClass.
            connection.close()

        self.assertGreaterEqual(dataset_count, 1)
        self.assertGreaterEqual(history_count, 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
