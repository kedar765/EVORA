"""
EVORA Comprehensive Automated Test Suite
========================================
Covers all phases:
- Phase 1: Backend Testing (CSV validation, missing data, negative/zero, inf/nan, 25MB limit, ML input, risk score, anomalies, forecasting, what-if, dataset storage)
- Phase 2: API Testing (all endpoints, status codes, response formats, invalid requests, 401 unauthorized, error handling, DB persistence)
- Phase 4: Security Testing (auth protection, data isolation, session cookie flags, CSRF origin guard, rate limiting, path traversal)
- Phase 5: Integration Testing (full 12-step end-to-end user workflow)
"""

import io
import json
import math
import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import backend.auth as auth
import backend.main as main
from backend.features import prepare_features
from ml.forecast import (
    DEFAULT_DATA_PATH,
    DailyProfitForecaster,
    aggregate_daily_metrics,
    build_historical_features,
    build_next_day_feature_vector,
)


class TestEVORAComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create isolated temporary environment
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="evora_test_suite_")
        cls.temp_dir = Path(cls.temp_dir_obj.name)

        cls.orig_db_path = auth.DB_PATH
        cls.orig_upload_dir = main.UPLOAD_STORAGE_DIR
        cls.orig_root_dir = main.ROOT_DIR

        # Point DB and uploads to temporary directory
        cls.test_db = cls.temp_dir / "backend" / "evora.db"
        cls.test_uploads = cls.temp_dir / "backend" / "storage" / "uploads"
        cls.test_uploads.mkdir(parents=True, exist_ok=True)

        auth.DB_PATH = cls.test_db
        main.ROOT_DIR = cls.temp_dir
        main.UPLOAD_STORAGE_DIR = cls.test_uploads

        auth.initialize_database()

        cls.client = TestClient(main.app)
        cls.trusted_headers = {"Origin": "http://localhost:3000"}

        # Sample valid CSV string
        cls.valid_csv = (
            "Date,Product,Quantity,Revenue,Expense,Customer\n"
            "2026-08-01,Product A,100,20000,12000,Customer 1\n"
            "2026-08-02,Product B,150,30000,18000,Customer 2\n"
            "2026-08-03,Product C,200,40000,25000,Customer 3\n"
            "2026-08-04,Product A,120,24000,15000,Customer 4\n"
            "2026-08-05,Product B,140,28000,17000,Customer 5\n"
        )

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        auth.DB_PATH = cls.orig_db_path
        main.UPLOAD_STORAGE_DIR = cls.orig_upload_dir
        main.ROOT_DIR = cls.orig_root_dir
        cls.temp_dir_obj.cleanup()

    def setUp(self):
        # Create a fresh client for each test method to isolate cookies
        self.client = TestClient(main.app)
        with auth.database() as conn:
            conn.execute("DELETE FROM signup_attempts")
            conn.execute("DELETE FROM login_attempts")

    def _signup_user(self, full_name, email, password):
        return self.client.post(
            "/api/auth/signup",
            headers=self.trusted_headers,
            json={"fullName": full_name, "email": email, "password": password},
        )

    def _login_user(self, email, password):
        return self.client.post(
            "/api/auth/login",
            headers=self.trusted_headers,
            json={"email": email, "password": password},
        )

    # =========================================================================
    # PHASE 1: BACKEND TESTING
    # =========================================================================

    def test_p1_01_csv_validation_valid_csv(self):
        """Test CSV file validation with valid business data."""
        self._signup_user("P1 User", "p1_valid@example.com", "SecurePass123!")
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("business.csv", self.valid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["rows_processed"], 5)
        self.assertEqual(data["metrics"]["total_revenue"], 142000.0)
        self.assertEqual(data["metrics"]["total_expense"], 87000.0)
        self.assertEqual(data["metrics"]["total_profit"], 55000.0)
        self.assertAlmostEqual(data["metrics"]["profit_margin"], 38.73, places=2)

    def test_p1_02_csv_validation_missing_required_columns(self):
        """Test CSV validation rejects missing required columns with 400 detail."""
        self._signup_user("P1 User 2", "p1_missing@example.com", "SecurePass123!")
        # Missing Expense column
        bad_csv = "Quantity,Revenue\n100,5000\n200,8000\n"
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("missing_col.csv", bad_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 400)
        detail = res.json()["detail"]
        self.assertIn("missing_columns", detail)
        self.assertIn("Expense", detail["missing_columns"])

    def test_p1_03_csv_validation_non_csv_extension(self):
        """Test non-CSV files (.txt, .xlsx, .json) are rejected."""
        self._signup_user("P1 User 3", "p1_noncsv@example.com", "SecurePass123!")
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("data.txt", b"Quantity,Revenue,Expense\n1,2,3", "text/plain")},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Please select a CSV file", res.json()["detail"])

    def test_p1_04_csv_validation_empty_csv(self):
        """Test empty CSV file is rejected with 400."""
        self._signup_user("P1 User 4", "p1_empty@example.com", "SecurePass123!")
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        self.assertEqual(res.status_code, 400)

    def test_p1_05_csv_missing_values_and_invalid_data(self):
        """Test missing values and non-numeric rows are coerced and dropped safely."""
        self._signup_user("P1 User 5", "p1_nan@example.com", "SecurePass123!")
        mixed_csv = (
            "Quantity,Revenue,Expense\n"
            "100,20000,12000\n"
            ",25000,15000\n"        # missing quantity
            "150,not_a_num,18000\n" # invalid string
            "200,40000,\n"          # missing expense
            "120,24000,15000\n"     # valid
        )
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("mixed.csv", mixed_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Only 2 rows are valid numeric rows
        self.assertEqual(data["rows_processed"], 2)
        self.assertEqual(data["metrics"]["total_revenue"], 44000.0)

    def test_p1_06_csv_duplicate_rows(self):
        """Test duplicate rows are ingested and processed correctly."""
        self._signup_user("P1 User 6", "p1_dup@example.com", "SecurePass123!")
        dup_csv = (
            "Quantity,Revenue,Expense\n"
            "100,20000,12000\n"
            "100,20000,12000\n"
            "100,20000,12000\n"
        )
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("dup.csv", dup_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["rows_processed"], 3)
        self.assertEqual(data["metrics"]["total_revenue"], 60000.0)

    def test_p1_07_csv_negative_revenue_and_expense(self):
        """Test negative financial values (refunds, losses) are preserved and analyzed."""
        self._signup_user("P1 User 7", "p1_neg@example.com", "SecurePass123!")
        neg_csv = (
            "Quantity,Revenue,Expense\n"
            "10,-5000,8000\n"
            "20,10000,15000\n"
        )
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("neg.csv", neg_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["metrics"]["total_revenue"], 5000.0)
        self.assertEqual(data["metrics"]["total_expense"], 23000.0)
        self.assertEqual(data["metrics"]["total_profit"], -18000.0)
        self.assertEqual(data["business_status"], "Critical — Operating at a Loss")

    def test_p1_08_zero_quantity_and_zero_revenue_division_safety(self):
        """Test zero quantity and zero revenue do not trigger ZeroDivisionError."""
        self._signup_user("P1 User 8", "p1_zero@example.com", "SecurePass123!")
        zero_csv = (
            "Quantity,Revenue,Expense\n"
            "0,0,500\n"
            "0,1000,800\n"
        )
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("zero.csv", zero_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["rows_processed"], 2)
        # Margin calculated safely
        self.assertIsInstance(data["metrics"]["profit_margin"], (int, float))

    def test_p1_09_nan_and_infinity_handling(self):
        """Test inf and -inf values are treated as invalid numeric data and filtered safely."""
        self._signup_user("P1 User 9", "p1_inf@example.com", "SecurePass123!")
        inf_csv = (
            "Quantity,Revenue,Expense\n"
            "100,inf,12000\n"
            "150,30000,-inf\n"
            "200,40000,25000\n"
        )
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("inf.csv", inf_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Only the 3rd row with finite values is kept
        self.assertEqual(data["rows_processed"], 1)
        self.assertEqual(data["metrics"]["total_revenue"], 40000.0)

    def test_p1_10_large_csv_upload_limit(self):
        """Test upload rejects files exceeding 25 MB limit with HTTP 413."""
        self._signup_user("P1 User 10", "p1_limit@example.com", "SecurePass123!")
        # 26 MB dummy content
        oversized = b"Quantity,Revenue,Expense\n" + b"1,2,3\n" * (26 * 1024 * 1024 // 6)
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("huge.csv", oversized, "text/csv")},
        )
        self.assertEqual(res.status_code, 413)
        self.assertIn("exceeds the 25 MB", res.json()["detail"])

    def test_p1_11_ml_prediction_input_validation(self):
        """Test ML prediction input validation handles standard, boundary, and zero values."""
        self._signup_user("P1 User 11", "p1_ml_val@example.com", "SecurePass123!")
        # 1. Normal values
        res1 = self.client.post(
            "/ml/predict-profit",
            headers=self.trusted_headers,
            json={"Quantity": 100, "Revenue": 50000, "Expense": 30000},
        )
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()["success"])
        self.assertIsInstance(res1.json()["predicted_profit"], float)

        # 2. Zero values
        res2 = self.client.post(
            "/ml/predict-profit",
            headers=self.trusted_headers,
            json={"Quantity": 0, "Revenue": 0, "Expense": 0},
        )
        self.assertEqual(res2.status_code, 200)

        # 3. Missing fields -> 422
        res3 = self.client.post(
            "/ml/predict-profit",
            headers=self.trusted_headers,
            json={"Quantity": 100},
        )
        self.assertEqual(res3.status_code, 422)

    def test_p1_12_risk_score_calculations_and_boundaries(self):
        """Test risk score calculation is bounded between 0 and 100, and levels are correct."""
        from backend.main import risk_details

        # Low risk: no anomalies, high margin >= 20, positive profit
        score_low, level_low = risk_details(predicted_profit=5000.0, anomaly_percentage=0.0, profit_margin=25.0)
        self.assertGreaterEqual(score_low, 0)
        self.assertLessEqual(score_low, 30)
        self.assertEqual(level_low, "LOW")

        # Medium risk: small anomalies or low margin
        score_med, level_med = risk_details(predicted_profit=500.0, anomaly_percentage=1.5, profit_margin=8.0)
        self.assertGreater(score_med, 30)
        self.assertLessEqual(score_med, 60)
        self.assertEqual(level_med, "MEDIUM")

        # High risk: heavy anomalies, negative margin, negative profit
        score_high, level_high = risk_details(predicted_profit=-2000.0, anomaly_percentage=5.0, profit_margin=-15.0)
        self.assertGreater(score_high, 60)
        self.assertLessEqual(score_high, 100)
        self.assertEqual(level_high, "HIGH")

    def test_p1_13_anomaly_detection_execution(self):
        """Test Isolation Forest anomaly detection returns count, indices, and flags."""
        self._signup_user("P1 User 13", "p1_anomaly@example.com", "SecurePass123!")
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("business.csv", self.valid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("anomaly_detected", data)
        self.assertIn("anomaly_count", data)
        self.assertIn("anomaly_indices", data)
        self.assertIsInstance(data["anomaly_indices"], list)

    def test_p1_14_what_if_analysis_calculations(self):
        """Test what-if simulation calculates correct direction and profit difference."""
        self._signup_user("P1 User 14", "p1_whatif@example.com", "SecurePass123!")
        payload = {
            "current_quantity": 100,
            "current_revenue": 50000,
            "current_expense": 30000,
            "new_quantity": 150,
            "new_revenue": 75000,
            "new_expense": 35000,
        }
        res = self.client.post("/what-if", headers=self.trusted_headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn(data["result"], ["Profit may increase", "Profit may decrease", "No significant change"])
        expected_diff = round(data["new_predicted_profit"] - data["current_predicted_profit"], 2)
        self.assertAlmostEqual(data["profit_difference"], expected_diff, places=2)

    def test_p1_15_forecasting_module_and_leakage_safety(self):
        """Test forecasting engine builds feature vector with strictly historical data."""
        forecaster = DailyProfitForecaster()
        self.assertTrue(forecaster.is_loaded)
        result = forecaster.predict_next_day()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["currency"], "INR")
        self.assertIsInstance(result["predicted_profit"], (int, float))
        self.assertIn("forecast_date", result)

    def test_p1_16_dataset_storage_and_history_persistence(self):
        """Test dataset file is saved privately and recorded in SQLite database."""
        self._signup_user("P1 User 16", "p1_storage@example.com", "SecurePass123!")
        res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("store_test.csv", self.valid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        dataset_id = res.json()["dataset_id"]

        # Verify in DB
        with auth.database() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["original_filename"], "store_test.csv")
            self.assertEqual(row["row_count"], 5)

            # Verify file exists on disk
            disk_file = main.ROOT_DIR / row["storage_path"]
            self.assertTrue(disk_file.is_file())

            # Verify upload_analysis recorded
            history = conn.execute(
                "SELECT * FROM analysis_history WHERE dataset_id = ? AND analysis_type = 'upload_analysis'",
                (dataset_id,),
            ).fetchone()
            self.assertIsNotNone(history)

    # =========================================================================
    # PHASE 2: API TESTING
    # =========================================================================

    def test_p2_01_public_health_and_root(self):
        """Test public endpoints return 200 without authentication."""
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertEqual(res_root.json()["status"], "online")

        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "healthy")

    def test_p2_02_auth_signup_login_me_logout(self):
        """Test full authentication lifecycle: signup, me, logout, login."""
        # 1. Signup
        res_signup = self._signup_user("Auth User", "auth_cycle@example.com", "MyPassword123!")
        self.assertEqual(res_signup.status_code, 201)
        self.assertTrue(res_signup.json()["success"])
        self.assertIn("user", res_signup.json())

        # 2. Get current user
        res_me = self.client.get("/api/auth/me")
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.json()["user"]["email"], "auth_cycle@example.com")

        # 3. Logout
        res_logout = self.client.post("/api/auth/logout", headers=self.trusted_headers)
        self.assertEqual(res_logout.status_code, 200)

        # 4. Accessing /me after logout -> 401
        res_me_after = self.client.get("/api/auth/me")
        self.assertEqual(res_me_after.status_code, 401)

        # 5. Login
        res_login = self._login_user("auth_cycle@example.com", "MyPassword123!")
        self.assertEqual(res_login.status_code, 200)
        self.assertTrue(res_login.json()["success"])

    def test_p2_03_unauthorized_access_to_protected_endpoints(self):
        """Test all protected endpoints return 401 when accessed without session."""
        endpoints = [
            ("GET", "/api/auth/me"),
            ("GET", "/datasets"),
            ("GET", "/datasets/nonexistent/preview"),
            ("GET", "/analysis-history"),
            ("GET", "/forecast/next-day"),
            ("POST", "/upload"),
            ("POST", "/ml/predict-profit"),
            ("POST", "/analyze-risk"),
            ("POST", "/what-if"),
            ("POST", "/decision/recommend"),
            ("POST", "/analytics"),
            ("POST", "/forecast/next-day"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                res = self.client.get(endpoint)
            else:
                res = self.client.post(endpoint, headers=self.trusted_headers, json={})
            self.assertEqual(res.status_code, 401, f"{method} {endpoint} should reject with 401")

    def test_p2_04_dataset_endpoints_crud_and_preview(self):
        """Test /datasets, /datasets/{id}, /datasets/{id}/preview, /datasets/{id}/history."""
        self._signup_user("Dataset User", "dataset_api@example.com", "SecurePass123!")
        # Upload
        up_res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("sales.csv", self.valid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(up_res.status_code, 200)
        dataset_id = up_res.json()["dataset_id"]

        # List
        list_res = self.client.get("/datasets")
        self.assertEqual(list_res.status_code, 200)
        datasets = list_res.json()["datasets"]
        self.assertGreaterEqual(len(datasets), 1)

        # Get single
        get_res = self.client.get(f"/datasets/{dataset_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["dataset"]["dataset_id"], dataset_id)

        # Preview
        preview_res = self.client.get(f"/datasets/{dataset_id}/preview?rows=3")
        self.assertEqual(preview_res.status_code, 200)
        self.assertEqual(preview_res.json()["preview_rows"], 3)
        self.assertEqual(len(preview_res.json()["data"]), 3)

        # Dataset history
        dh_res = self.client.get(f"/datasets/{dataset_id}/history")
        self.assertEqual(dh_res.status_code, 200)
        self.assertGreaterEqual(dh_res.json()["total"], 1)

    def test_p2_05_analysis_history_endpoints_and_filtering(self):
        """Test /analysis-history with filtering by analysis_type and date."""
        self._signup_user("History User", "history_api@example.com", "SecurePass123!")
        # Trigger profit prediction
        self.client.post(
            "/ml/predict-profit",
            headers=self.trusted_headers,
            json={"Quantity": 100, "Revenue": 50000, "Expense": 30000},
        )
        # Trigger what-if
        self.client.post(
            "/what-if",
            headers=self.trusted_headers,
            json={
                "current_quantity": 100, "current_revenue": 50000, "current_expense": 30000,
                "new_quantity": 120, "new_revenue": 60000, "new_expense": 35000,
            },
        )

        # List all
        all_hist = self.client.get("/analysis-history")
        self.assertEqual(all_hist.status_code, 200)
        self.assertGreaterEqual(all_hist.json()["total"], 2)

        # Filter by type
        filtered = self.client.get("/analysis-history?analysis_type=profit_prediction")
        self.assertEqual(filtered.status_code, 200)
        types = [h["analysis_type"] for h in filtered.json()["history"]]
        self.assertTrue(all(t == "profit_prediction" for t in types))

        # Get specific history item
        first_id = all_hist.json()["history"][0]["analysis_id"]
        item_res = self.client.get(f"/analysis-history/{first_id}")
        self.assertEqual(item_res.status_code, 200)
        self.assertIn("result", item_res.json()["analysis"])

    def test_p2_06_decision_recommendations_endpoint(self):
        """Test POST /decision/recommend returns structured decision advice and saves history."""
        self._signup_user("Decision User", "decision_api@example.com", "SecurePass123!")
        payload = {
            "analytics": {"total_profit": 55000, "profit_margin": 38.7},
            "risk": {"risk_level": "LOW", "risk_score": 15, "anomaly_detected": False},
            "scenario": {"profit_difference": 5000},
        }
        res = self.client.post("/decision/recommend", headers=self.trusted_headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("decision", data)
        self.assertIn("recommendations", data["decision"])
        self.assertIn("action_plan", data["decision"])
        self.assertIn("analysis_id", data)

    def test_p2_07_forecast_next_day_endpoints(self):
        """Test GET and POST /forecast/next-day return next day's profit forecast."""
        self._signup_user("Forecast User", "forecast_api@example.com", "SecurePass123!")
        # GET default
        get_res = self.client.get("/forecast/next-day")
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.json()
        self.assertEqual(get_data["currency"], "INR")
        self.assertIn("predicted_profit", get_data)
        self.assertIn("forecast_date", get_data)
        self.assertIn("analysis_id", get_data)

        # POST custom CSV
        # Need at least 30 distinct dates for rolling computation
        dates = [f"2026-01-{(i%28)+1:02d}" for i in range(35)]
        forecast_csv = "Date,Revenue,Expense\n" + "\n".join(
            f"2026-0{1 + (i//28)}-{(i%28)+1:02d},5000,3000" for i in range(35)
        )
        post_res = self.client.post(
            "/forecast/next-day",
            headers=self.trusted_headers,
            files={"file": ("f_test.csv", forecast_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.json()
        self.assertEqual(post_data["currency"], "INR")
        self.assertIn("predicted_profit", post_data)

    # =========================================================================
    # PHASE 4: SECURITY TESTING
    # =========================================================================

    def test_p4_01_user_data_isolation(self):
        """Verify User A cannot access, preview, or read User B's datasets and history."""
        # Create User A
        self._signup_user("User A", "user_a_sec@example.com", "Password123!")
        up_a = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("secret_a.csv", self.valid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(up_a.status_code, 200)
        dataset_a_id = up_a.json()["dataset_id"]

        # Create User B in fresh client
        client_b = TestClient(main.app)
        client_b.post(
            "/api/auth/signup",
            headers=self.trusted_headers,
            json={"fullName": "User B", "email": "user_b_sec@example.com", "password": "Password123!"},
        )

        # User B listing datasets must NOT show dataset A
        b_list = client_b.get("/datasets")
        self.assertEqual(b_list.status_code, 200)
        b_ids = [d["dataset_id"] for d in b_list.json()["datasets"]]
        self.assertNotIn(dataset_a_id, b_ids)

        # User B requesting User A's dataset -> 404
        b_get = client_b.get(f"/datasets/{dataset_a_id}")
        self.assertEqual(b_get.status_code, 404)

        # User B requesting preview of User A's dataset -> 404
        b_prev = client_b.get(f"/datasets/{dataset_a_id}/preview")
        self.assertEqual(b_prev.status_code, 404)

        # User B requesting history of User A's dataset -> 404
        b_hist = client_b.get(f"/datasets/{dataset_a_id}/history")
        self.assertEqual(b_hist.status_code, 404)

        client_b.close()

    def test_p4_02_session_cookie_security_and_token_hashing(self):
        """Verify session cookie attributes and check tokens are hashed in DB."""
        res = self._signup_user("Cookie Sec", "cookie_sec@example.com", "Password123!")
        self.assertEqual(res.status_code, 201)

        # Check Set-Cookie header
        set_cookie = res.headers.get("set-cookie", "")
        self.assertIn("evora_session=", set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("samesite=lax", set_cookie.lower())

        # Check that plain cookie value is NOT stored in the database
        raw_cookie_val = self.client.cookies.get("evora_session")
        self.assertIsNotNone(raw_cookie_val)

        with auth.database() as conn:
            # Query sessions
            rows = conn.execute("SELECT token_hash FROM sessions").fetchall()
            hashes = [r["token_hash"] for r in rows]
            self.assertNotIn(raw_cookie_val, hashes, "Plain session token must not be stored in plaintext")

    def test_p4_03_csrf_origin_protection(self):
        """Verify untrusted origin on state-changing POST requests returns 403 Forbidden."""
        self._signup_user("CSRF User", "csrf_test@example.com", "Password123!")

        # Untrusted origin
        evil_res = self.client.post(
            "/ml/predict-profit",
            headers={"Origin": "http://evil-attacker-site.com"},
            json={"Quantity": 10, "Revenue": 500, "Expense": 300},
        )
        self.assertEqual(evil_res.status_code, 403)
        self.assertIn("CSRF protection", evil_res.json()["detail"])

        # No origin and no referer
        no_origin_res = self.client.post(
            "/ml/predict-profit",
            json={"Quantity": 10, "Revenue": 500, "Expense": 300},
        )
        self.assertEqual(no_origin_res.status_code, 403)

    def test_p4_04_login_rate_limiting(self):
        """Verify login rate limiter blocks after 5 failed attempts with 429 and Retry-After."""
        test_email = "rate_limit_victim@example.com"
        # First signup
        self._signup_user("RL User", test_email, "RealPassword123!")

        # Create unauthenticated client
        attacker_client = TestClient(main.app)

        # 5 failed login attempts
        for _ in range(5):
            attacker_client.post(
                "/api/auth/login",
                headers=self.trusted_headers,
                json={"email": test_email, "password": "WrongPassword!"},
            )

        # 6th attempt must trigger rate limit 429
        blocked_res = attacker_client.post(
            "/api/auth/login",
            headers=self.trusted_headers,
            json={"email": test_email, "password": "WrongPassword!"},
        )
        self.assertEqual(blocked_res.status_code, 429)
        self.assertIn("Too many login attempts", blocked_res.json()["detail"])
        self.assertIn("Retry-After", blocked_res.headers)
        attacker_client.close()

    def test_p4_05_path_traversal_protection(self):
        """Verify path traversal attempts in preview are rejected."""
        self._signup_user("Traversal User", "traversal@example.com", "Password123!")
        up = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("normal.csv", self.valid_csv.encode("utf-8"), "text/csv")},
        )
        dataset_id = up.json()["dataset_id"]

        # Manually alter storage path in DB to point outside uploads
        with auth.database() as conn:
            conn.execute(
                "UPDATE datasets SET storage_path = ? WHERE id = ?",
                ("../../../etc/passwd", dataset_id),
            )

        res = self.client.get(f"/datasets/{dataset_id}/preview")
        self.assertEqual(res.status_code, 500)
        self.assertIn("outside private storage", res.json()["detail"])

    # =========================================================================
    # PHASE 5: INTEGRATION TESTING (12-STEP END-TO-END WORKFLOW)
    # =========================================================================

    def test_p5_full_12_step_integration_workflow(self):
        """
        Execute full business workflow:
        1. User signup/login
        2. Upload business CSV
        3. Backend validates CSV
        4. Business analytics generated
        5. ML profit prediction runs
        6. Anomaly detection runs
        7. Risk score & level calculated
        8. What-if simulation runs
        9. Profit forecasting runs
        10. Decision recommendations generated
        11. Dataset & history visible on dashboard
        12. User logs out and APIs reject access
        """
        email = f"e2e_{int(time.time())}@evora.test"
        password = "E2EProductionPass2026!"

        # Step 1: User logs in / signs up
        signup_res = self._signup_user("Enterprise Executive", email, password)
        self.assertEqual(signup_res.status_code, 201)
        user_info = signup_res.json()["user"]
        self.assertEqual(user_info["email"], email)

        # Step 2: Upload valid CSV
        upload_res = self.client.post(
            "/upload",
            headers=self.trusted_headers,
            files={"file": ("enterprise_data.csv", self.valid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(upload_res.status_code, 200)
        upload_data = upload_res.json()

        # Step 3: Backend validates CSV
        self.assertTrue(upload_data["success"])
        self.assertEqual(upload_data["rows_processed"], 5)
        dataset_id = upload_data["dataset_id"]

        # Step 4: Business analytics generated
        metrics = upload_data["metrics"]
        self.assertEqual(metrics["total_revenue"], 142000.0)
        self.assertEqual(metrics["total_profit"], 55000.0)
        self.assertIn("analytics", upload_data)
        self.assertIn("insights", upload_data["analytics"])

        # Step 5: ML profit prediction runs
        self.assertIsNotNone(upload_data["predicted_profit"])
        self.assertIsInstance(upload_data["predicted_profit"], float)

        # Step 6: Anomaly detection runs
        self.assertIn("anomaly_detected", upload_data)
        self.assertIn("anomaly_count", upload_data)

        # Step 7: Risk score and level calculated
        self.assertIn("risk_score", upload_data)
        self.assertIn("risk_level", upload_data)
        self.assertIn(upload_data["risk_level"], ["LOW", "MEDIUM", "HIGH"])

        # Step 8: What-if analysis works
        what_if_res = self.client.post(
            "/what-if",
            headers=self.trusted_headers,
            json={
                "current_quantity": metrics["total_sales"],
                "current_revenue": metrics["total_revenue"],
                "current_expense": metrics["total_expense"],
                "new_quantity": metrics["total_sales"] * 1.2,
                "new_revenue": metrics["total_revenue"] * 1.2,
                "new_expense": metrics["total_expense"] * 1.1,
            },
        )
        self.assertEqual(what_if_res.status_code, 200)
        what_if_data = what_if_res.json()
        self.assertTrue(what_if_data["success"])

        # Step 9: Forecasting works
        forecast_res = self.client.get("/forecast/next-day")
        self.assertEqual(forecast_res.status_code, 200)
        forecast_data = forecast_res.json()
        self.assertEqual(forecast_data["currency"], "INR")
        self.assertIsInstance(forecast_data["predicted_profit"], (int, float))

        # Step 10: AI recommendations generated
        decision_res = self.client.post(
            "/decision/recommend",
            headers=self.trusted_headers,
            json={
                "analytics": {"total_profit": metrics["total_profit"], "profit_margin": metrics["profit_margin"]},
                "risk": {"risk_level": upload_data["risk_level"], "risk_score": upload_data["risk_score"]},
                "scenario": {"profit_difference": what_if_data["profit_difference"]},
            },
        )
        self.assertEqual(decision_res.status_code, 200)
        decision_data = decision_res.json()
        self.assertTrue(decision_data["success"])
        self.assertIn("action_plan", decision_data["decision"])

        # Step 11: Results appear on dashboard (dataset list, preview, history)
        ds_res = self.client.get("/datasets")
        self.assertEqual(ds_res.status_code, 200)
        self.assertEqual(ds_res.json()["total"], 1)

        prev_res = self.client.get(f"/datasets/{dataset_id}/preview")
        self.assertEqual(prev_res.status_code, 200)
        self.assertEqual(prev_res.json()["filename"], "enterprise_data.csv")

        hist_res = self.client.get("/analysis-history")
        self.assertEqual(hist_res.status_code, 200)
        # Multiple analysis operations persisted
        self.assertGreaterEqual(hist_res.json()["total"], 4)

        # Step 12: User logs out and protected APIs reject access
        logout_res = self.client.post("/api/auth/logout", headers=self.trusted_headers)
        self.assertEqual(logout_res.status_code, 200)

        # Verify access rejected now
        rejected_res = self.client.get("/datasets")
        self.assertEqual(rejected_res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
