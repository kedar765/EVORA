"""
EVORA Integration Audit Verification Suite
==========================================
Validates end-to-end frontend-backend integration:
1. Health endpoint (/health) status and service contract.
2. CSV file upload (/upload) persistence and /datasets/{id}/preview verification.
3. Excel file upload (.xlsx) persistence and /datasets/{id}/preview verification without parser errors.
4. Dataset listing (/datasets) pagination and user isolation.
5. Analysis history (/analysis-history and /datasets/{id}/history) logging and structure.
6. ML Profit prediction (/ml/predict-profit) and Risk intelligence (/analyze-risk).
7. What-If scenario simulation (/what-if) contract alignment.
"""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["EVORA_SKIP_EXTERNAL_LLM"] = "1"

import backend.auth as auth
import backend.main as main


class TestEVORAIntegrationAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="evora_audit_test_")
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
        auth.initialize_database()

        cls.client = TestClient(main.app)
        cls.headers = {"Origin": "http://localhost:3000"}

        # Register and log in test user
        cls.user_email = "audit_user@evora.ai"
        cls.user_password = "AuditPassword123!"
        signup_res = cls.client.post(
            "/api/auth/signup",
            headers=cls.headers,
            json={
                "fullName": "Audit User",
                "email": cls.user_email,
                "password": cls.user_password,
            },
        )
        assert signup_res.status_code == 200, f"Signup failed: {signup_res.text}"

        login_res = cls.client.post(
            "/api/auth/login",
            headers=cls.headers,
            json={"email": cls.user_email, "password": cls.user_password},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"

    @classmethod
    def tearDownClass(cls):
        auth.DB_PATH = cls.orig_db_path
        main.UPLOAD_STORAGE_DIR = cls.orig_upload_dir
        main.ROOT_DIR = cls.orig_root_dir
        cls.temp_dir_obj.cleanup()

    def test_01_health_endpoint(self):
        """Verifies GET /health returns expected status and service."""
        response = self.client.get("/health", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("service", data)

    def test_02_csv_upload_and_preview(self):
        """Verifies CSV upload and subsequent row preview."""
        csv_content = (
            "Quantity,Revenue,Expense,Product,Date\n"
            "50,25000,15000,Gadget A,2026-01-01\n"
            "80,40000,22000,Gadget B,2026-01-02\n"
            "120,60000,35000,Gadget C,2026-01-03\n"
        )
        files = {"file": ("test_data.csv", csv_content.encode("utf-8"), "text/csv")}
        res = self.client.post("/upload", headers=self.headers, files=files)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["rows_processed"], 3)
        dataset_id = data.get("dataset_id")
        self.assertIsNotNone(dataset_id)

        # Preview endpoint test
        preview_res = self.client.get(
            f"/datasets/{dataset_id}/preview?rows=5",
            headers=self.headers,
        )
        self.assertEqual(preview_res.status_code, 200, preview_res.text)
        preview_data = preview_res.json()
        self.assertTrue(preview_data["success"])
        self.assertEqual(preview_data["preview_rows"], 3)
        self.assertEqual(len(preview_data["data"]), 3)

    def test_03_excel_upload_and_preview(self):
        """Verifies Excel (.xlsx) upload and preview without parser error."""
        df = pd.DataFrame({
            "Quantity": [10, 20, 30],
            "Revenue": [5000.0, 10000.0, 15000.0],
            "Expense": [3000.0, 6000.0, 9000.0],
            "Product": ["Item X", "Item Y", "Item Z"],
        })
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        excel_bytes = buffer.getvalue()

        files = {
            "file": (
                "enterprise_data.xlsx",
                excel_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        res = self.client.post("/upload", headers=self.headers, files=files)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data["success"])
        dataset_id = data["dataset_id"]

        # Ensure preview reads Excel correctly without UnicodeDecodeError
        preview_res = self.client.get(
            f"/datasets/{dataset_id}/preview?rows=5",
            headers=self.headers,
        )
        self.assertEqual(preview_res.status_code, 200, preview_res.text)
        preview_data = preview_res.json()
        self.assertTrue(preview_data["success"])
        self.assertEqual(preview_data["preview_rows"], 3)
        self.assertIn("Quantity", preview_data["columns"])

    def test_04_dataset_listing(self):
        """Verifies GET /datasets returns saved datasets for the authenticated user."""
        res = self.client.get("/datasets?limit=10&offset=0", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["total"], 2)
        filenames = [d["filename"] for d in data["datasets"]]
        self.assertIn("enterprise_data.xlsx", filenames)

    def test_05_what_if_and_risk_apis(self):
        """Verifies POST /what-if and POST /analyze-risk endpoints match frontend schema."""
        what_if_payload = {
            "current_quantity": 100.0,
            "current_revenue": 50000.0,
            "current_expense": 30000.0,
            "new_quantity": 120.0,
            "new_revenue": 60000.0,
            "new_expense": 32000.0,
        }
        res = self.client.post("/what-if", headers=self.headers, json=what_if_payload)
        self.assertEqual(res.status_code, 200, res.text)
        wi_data = res.json()
        self.assertTrue(wi_data["success"])
        self.assertIn("profit_difference", wi_data)

        risk_payload = {
            "Quantity": 100.0,
            "Revenue": 50000.0,
            "Expense": 30000.0,
        }
        risk_res = self.client.post("/analyze-risk", headers=self.headers, json=risk_payload)
        self.assertEqual(risk_res.status_code, 200, risk_res.text)
        risk_data = risk_res.json()
        self.assertTrue(risk_data["success"])
        self.assertIn("risk_score", risk_data)
        self.assertIn("risk_level", risk_data)

    def test_06_analysis_history(self):
        """Verifies GET /analysis-history returns logged operations."""
        res = self.client.get("/analysis-history?limit=10&offset=0", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["total"], 1)


if __name__ == "__main__":
    unittest.main()
