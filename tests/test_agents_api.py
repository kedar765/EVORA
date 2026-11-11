"""
EVORA Agents API Endpoint Test Suite
====================================
Tests the POST /agents/run endpoint in FastAPI:
- 401 Unauthorized for unauthenticated requests.
- 400 Bad Request for missing dataset_id.
- 404 Not Found for non-existent datasets.
- 404 / 403 Forbidden for unauthorized datasets belonging to other users.
- 200 OK with full multi-agent output for authenticated valid requests.
- Verifies database persistence in analysis_history table.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["EVORA_SKIP_EXTERNAL_LLM"] = "1"

import backend.auth as auth
import backend.main as main


class TestAgentsAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="evora_api_test_")
        cls.temp_dir = Path(cls.temp_dir_obj.name)

        cls.orig_db_path = auth.DB_PATH
        cls.orig_upload_dir = main.UPLOAD_STORAGE_DIR
        cls.orig_root_dir = main.ROOT_DIR

        cls.test_db = cls.temp_dir / "backend" / "evora.db"
        cls.test_uploads = cls.temp_dir / "backend" / "storage" / "uploads"
        cls.test_uploads.mkdir(parents=True, exist_ok=True)

        auth.DB_PATH = cls.test_db
        main.ROOT_DIR = cls.temp_dir
        main.UPLOAD_STORAGE_DIR = cls.test_uploads
        import tools.dataset_tools as dt
        cls.orig_dt_root = dt.ROOT_DIR
        dt.ROOT_DIR = cls.temp_dir
        os.environ["EVORA_UPLOAD_DIR"] = str(cls.test_uploads)


        auth.initialize_database()

        cls.client = TestClient(main.app)
        cls.trusted_headers = {"Origin": "http://localhost:3000"}

        # Register User A (Owner)
        with auth.database() as conn:
            conn.execute("DELETE FROM signup_attempts")
            conn.execute("DELETE FROM login_attempts")

        signup_a = cls.client.post(
            "/api/auth/signup",
            headers=cls.trusted_headers,
            json={"fullName": "Agent User A", "email": "user_a@example.com", "password": "Password123!"},
        )
        assert signup_a.status_code in [200, 201], f"User A signup failed: {signup_a.text}"
        cls.user_a_id = signup_a.json()["user"]["id"]

        # Register User B (Attacker / Unauthorized)
        signup_b = cls.client.post(
            "/api/auth/signup",
            headers=cls.trusted_headers,
            json={"fullName": "Agent User B", "email": "user_b@example.com", "password": "Password123!"},
        )
        assert signup_b.status_code in [200, 201], f"User B signup failed: {signup_b.text}"
        cls.user_b_id = signup_b.json()["user"]["id"]


        # Log in as User A and create an uploaded dataset
        login_a = cls.client.post(
            "/api/auth/login",
            headers=cls.trusted_headers,
            json={"email": "user_a@example.com", "password": "Password123!"},
        )
        assert login_a.status_code == 200
        cls.user_a_cookies = login_a.cookies

        # Log in as User B
        login_b = cls.client.post(
            "/api/auth/login",
            headers=cls.trusted_headers,
            json={"email": "user_b@example.com", "password": "Password123!"},
        )
        assert login_b.status_code == 200
        cls.user_b_cookies = login_b.cookies

        # Upload a dataset as User A via /upload
        csv_content = (
            "Date,Product,Quantity,Revenue,Expense,Category\n"
            "2026-01-01,Product 1,100,50000,30000,Retail\n"
            "2026-01-02,Product 2,120,60000,35000,Retail\n"
            "2026-01-03,Product 1,140,70000,42000,Retail\n"
        )
        upload_res = cls.client.post(
            "/upload",
            headers=cls.trusted_headers,
            cookies=cls.user_a_cookies,
            files={"file": ("business_records.csv", csv_content.encode("utf-8"), "text/csv")},
        )
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
        cls.dataset_id = upload_res.json()["dataset_id"]

    @classmethod
    def tearDownClass(cls):
        auth.DB_PATH = cls.orig_db_path
        main.UPLOAD_STORAGE_DIR = cls.orig_upload_dir
        main.ROOT_DIR = cls.orig_root_dir
        import tools.dataset_tools as dt
        dt.ROOT_DIR = cls.orig_dt_root
        os.environ.pop("EVORA_UPLOAD_DIR", None)
        cls.temp_dir_obj.cleanup()


    def test_run_unauthenticated(self):
        """Unauthenticated requests must receive 401 Unauthorized."""
        fresh_client = TestClient(main.app)
        res = fresh_client.post(
            "/agents/run",
            headers=self.trusted_headers,
            json={"dataset_id": self.dataset_id},
        )
        self.assertEqual(res.status_code, 401)


    def test_run_missing_dataset_id(self):
        """Empty dataset_id must return 400 Bad Request."""
        res = self.client.post(
            "/agents/run",
            headers=self.trusted_headers,
            cookies=self.user_a_cookies,
            json={"dataset_id": "   "},
        )
        self.assertEqual(res.status_code, 400)

    def test_run_nonexistent_dataset(self):
        """Nonexistent dataset must return 404 Not Found."""
        res = self.client.post(
            "/agents/run",
            headers=self.trusted_headers,
            cookies=self.user_a_cookies,
            json={"dataset_id": "nonexistent-dataset-id"},
        )
        self.assertEqual(res.status_code, 404)

    def test_run_unauthorized_dataset(self):
        """User B attempting to run workflow on User A's dataset must receive 404/Not Found."""
        res = self.client.post(
            "/agents/run",
            headers=self.trusted_headers,
            cookies=self.user_b_cookies,
            json={"dataset_id": self.dataset_id},
        )
        self.assertEqual(res.status_code, 404)

    def test_run_successful_workflow(self):
        """User A running workflow on own dataset receives 200 with structured agent outputs."""
        res = self.client.post(
            "/agents/run",
            headers=self.trusted_headers,
            cookies=self.user_a_cookies,
            json={
                "dataset_id": self.dataset_id,
                "user_query": "Identify major financial risks and strategic recommendations.",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["dataset_id"], self.dataset_id)
        self.assertEqual(data["status"], "completed")

        # Verify Analytics output
        analytics = data.get("analytics")
        self.assertIsNotNone(analytics)
        self.assertEqual(analytics["total_revenue"], 180000.0)
        self.assertEqual(analytics["total_expenses"], 107000.0)
        self.assertEqual(analytics["total_profit"], 73000.0)
        self.assertAlmostEqual(analytics["profit_margin"], 40.56, places=1)

        # Verify Risk output
        risk = data.get("risk")
        self.assertIsNotNone(risk)
        self.assertIn("risk_score", risk)
        self.assertIn(risk["risk_level"], ["low", "medium", "high", "critical"])

        # Verify Decision output
        decision = data.get("decision")
        self.assertIsNotNone(decision)
        self.assertIn("recommended_strategy", decision)
        self.assertGreaterEqual(len(decision["actions"]), 1)
        self.assertTrue(decision["human_approval_required"])

        # Verify Final Report output
        report = data.get("final_report")
        self.assertIsNotNone(report)
        self.assertIn("executive_summary", report)
        self.assertIn("business_health_status", report)

        # Verify Analysis History database persistence
        self.assertIn("analysis_id", data)
        self.assertIn("created_at", data)
        with auth.database() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_history WHERE id = ?",
                (data["analysis_id"],),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["user_id"], self.user_a_id)
            self.assertEqual(row["analysis_type"], "multi_agent_workflow")


if __name__ == "__main__":
    unittest.main()
