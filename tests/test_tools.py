"""
EVORA Tools Test Suite
======================
Unit tests for all 20 business tools and the centralized dataset access layer:
- dataset_tools.py: load_user_dataset, resolve_safe_dataset_path, identify_semantic_columns, sanitize_dataframe
- analytics_tools.py: 7 analytics tools
- risk_tools.py: 7 risk tools
- decision_tools.py: 6 decision tools
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import backend.auth as auth
import backend.main as main
from tools.dataset_tools import (
    COLUMN_CANDIDATES,
    DatasetAccessError,
    identify_semantic_columns,
    load_user_dataset,
    resolve_safe_dataset_path,
    sanitize_dataframe,
)
from tools.analytics_tools import (
    analyze_product_performance,
    analyze_relationships,
    analyze_time_trends,
    calculate_business_metrics,
    compare_business_segments,
    get_dataset_profile,
    query_business_data,
)
from tools.risk_tools import (
    analyze_expense_growth,
    analyze_revenue_drops,
    calculate_risk_score,
    detect_anomalies,
    explain_risk_records,
    forecast_business_risks,
    identify_loss_patterns,
)
from tools.decision_tools import (
    compare_business_strategies,
    estimate_financial_impact,
    evaluate_decision_options,
    generate_action_plan,
    optimize_resource_allocation,
    simulate_business_scenario,
)


class TestEVORATools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="evora_tools_test_")
        cls.temp_dir = Path(cls.temp_dir_obj.name)

        cls.orig_db_path = auth.DB_PATH
        cls.orig_upload_dir = main.UPLOAD_STORAGE_DIR

        cls.test_db = cls.temp_dir / "backend" / "evora.db"
        cls.test_uploads = cls.temp_dir / "backend" / "storage" / "uploads"
        cls.test_uploads.mkdir(parents=True, exist_ok=True)
        auth.DB_PATH = cls.test_db
        main.UPLOAD_STORAGE_DIR = cls.test_uploads
        import os
        os.environ["EVORA_UPLOAD_DIR"] = str(cls.test_uploads)


        auth.initialize_database()

        # Seed test user
        cls.test_user_id = "user-tools-test-123"
        cls.other_user_id = "user-unauthorized-456"
        with auth.database() as conn:
            conn.execute(
                "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.test_user_id, "Tools Tester", "toolstester@example.com", "hash123", 1000000),
            )
            conn.execute(
                "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.other_user_id, "Other User", "other@example.com", "hash456", 1000000),
            )

        # Create valid test CSV file
        cls.dataset_id = "dataset-valid-001"
        cls.csv_filename = f"{cls.dataset_id}.csv"
        cls.csv_path = cls.test_uploads / cls.csv_filename

        cls.sample_df = pd.DataFrame({
            "Date": ["2026-01-10", "2026-01-15", "2026-02-10", "2026-02-20", "2026-03-05"],
            "Item Name": ["Product A", "Product B", "Product A", "Product B", "Product C"],
            "Volume": [10, 15, 20, 25, 30],
            "Gross Sales": [10000.0, 15000.0, 20000.0, 25000.0, 12000.0],
            "Total Cost": [6000.0, 9000.0, 12000.0, 16000.0, 18000.0],
            "Category": ["Electronics", "Electronics", "Hardware", "Hardware", "Services"],
            "Region": ["North", "South", "North", "South", "East"],
        })
        cls.sample_df.to_csv(cls.csv_path, index=False)

        # Seed database record for valid dataset
        with auth.database() as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    id, user_id, original_filename, stored_filename, storage_path,
                    uploaded_at, row_count, column_count, columns_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cls.dataset_id,
                    cls.test_user_id,
                    "test_business.csv",
                    cls.csv_filename,
                    str(cls.csv_path.relative_to(ROOT_DIR)) if cls.csv_path.is_relative_to(ROOT_DIR) else str(cls.csv_path),
                    1000000,
                    5,
                    7,
                    json.dumps(list(cls.sample_df.columns)),
                    "ready",
                ),
            )

        # Create empty CSV
        cls.empty_id = "dataset-empty-002"
        cls.empty_path = cls.test_uploads / f"{cls.empty_id}.csv"
        cls.empty_path.write_text("Revenue,Expense,Quantity\n")

        with auth.database() as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    id, user_id, original_filename, stored_filename, storage_path,
                    uploaded_at, row_count, column_count, columns_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cls.empty_id,
                    cls.test_user_id,
                    "empty.csv",
                    f"{cls.empty_id}.csv",
                    str(cls.empty_path),
                    1000000,
                    0,
                    3,
                    "[]",
                    "ready",
                ),
            )

    @classmethod
    def tearDownClass(cls):
        auth.DB_PATH = cls.orig_db_path
        main.UPLOAD_STORAGE_DIR = cls.orig_upload_dir
        import os
        os.environ.pop("EVORA_UPLOAD_DIR", None)
        cls.temp_dir_obj.cleanup()


    # -------------------------------------------------------------------------
    # 1. Centralized Dataset Access Tests
    # -------------------------------------------------------------------------

    def test_semantic_column_mapping(self):
        cols = ["Item Name", "Gross Sales", "Total Cost", "Volume", "Timestamp", "Department", "Territory"]
        mapping = identify_semantic_columns(cols)
        self.assertEqual(mapping.get("revenue"), "Gross Sales")
        self.assertEqual(mapping.get("expense"), "Total Cost")
        self.assertEqual(mapping.get("product"), "Item Name")
        self.assertEqual(mapping.get("quantity"), "Volume")
        self.assertEqual(mapping.get("date"), "Timestamp")
        self.assertEqual(mapping.get("category"), "Department")
        self.assertEqual(mapping.get("region"), "Territory")

    def test_sanitize_dataframe(self):
        dirty_df = pd.DataFrame({
            "Gross Sales": [1000.0, None, float("inf")],
            "Total Cost": [600.0, 200.0, -100.0],
            "Volume": [2, 0, None],
        })
        mapping = {"revenue": "Gross Sales", "expense": "Total Cost", "quantity": "Volume"}
        clean = sanitize_dataframe(dirty_df, mapping)
        self.assertIn("Revenue", clean.columns)
        self.assertIn("Expense", clean.columns)
        self.assertIn("Profit", clean.columns)
        self.assertFalse(clean["Revenue"].isin([float("inf"), float("-inf")]).any())
        self.assertFalse(clean["Revenue"].isna().any())

    def test_dataset_ownership_security(self):
        # Attempt to load dataset owned by user-tools-test-123 using other_user_id
        with self.assertRaises(DatasetAccessError) as ctx:
            load_user_dataset(self.dataset_id, self.other_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_dataset_nonexistent(self):
        with self.assertRaises(DatasetAccessError) as ctx:
            load_user_dataset("non-existent-id", self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_empty_dataset_error(self):
        with self.assertRaises(DatasetAccessError) as ctx:
            load_user_dataset(self.empty_id, self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 400)

    # -------------------------------------------------------------------------
    # 2. Analytics Tools Tests
    # -------------------------------------------------------------------------

    def test_get_dataset_profile(self):
        res_str = get_dataset_profile.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertNotIn("error", res)
        self.assertEqual(res["row_count"], 5)
        self.assertTrue(res["has_date"])
        self.assertTrue(res["has_product"])

    def test_calculate_business_metrics(self):
        res_str = calculate_business_metrics.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertEqual(res["total_revenue"], 82000.0)
        self.assertEqual(res["total_expenses"], 61000.0)
        self.assertEqual(res["total_profit"], 21000.0)
        self.assertAlmostEqual(res["profit_margin_pct"], 25.61, places=1)
        self.assertTrue(res["is_profitable"])

    def test_analyze_time_trends(self):
        res_str = analyze_time_trends.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id, "period": "monthly"})
        res = json.loads(res_str)
        self.assertTrue(res["available"])
        self.assertGreaterEqual(res["period_count"], 2)
        self.assertIsNotNone(res["best_period"])

    def test_compare_business_segments(self):
        res_str = compare_business_segments.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertTrue(res["available"])
        self.assertGreaterEqual(res["segment_count"], 2)

    def test_analyze_product_performance(self):
        res_str = analyze_product_performance.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id, "top_n": 3})
        res = json.loads(res_str)
        self.assertTrue(res["available"])
        self.assertGreaterEqual(len(res["top_profitable_products"]), 1)

    def test_query_business_data(self):
        res_str = query_business_data.invoke({
            "dataset_id": self.dataset_id,
            "user_id": self.test_user_id,
            "min_profit": 0.0,
        })
        res = json.loads(res_str)
        self.assertGreater(res["matched_records"], 0)

    def test_analyze_relationships(self):
        res_str = analyze_relationships.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertIn("correlation_matrix", res)
        self.assertIn("expense_to_revenue_ratio_pct", res)

    # -------------------------------------------------------------------------
    # 3. Risk Tools Tests
    # -------------------------------------------------------------------------

    def test_detect_anomalies(self):
        res_str = detect_anomalies.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertIn("anomaly_detected", res)
        self.assertIn("anomaly_count", res)

    def test_analyze_revenue_drops(self):
        res_str = analyze_revenue_drops.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertTrue(res["available"])

    def test_analyze_expense_growth(self):
        res_str = analyze_expense_growth.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertIn("overall_expense_ratio_pct", res)

    def test_identify_loss_patterns(self):
        res_str = identify_loss_patterns.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertIn("loss_generating_records_count", res)

    def test_calculate_risk_score(self):
        res_str = calculate_risk_score.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertGreaterEqual(res["risk_score"], 0)
        self.assertLessEqual(res["risk_score"], 100)
        self.assertIn(res["risk_level"], ["low", "medium", "high", "critical"])

    def test_forecast_business_risks(self):
        res_str = forecast_business_risks.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertIn("risk_assessment", res)

    def test_explain_risk_records(self):
        res_str = explain_risk_records.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id, "top_n": 2})
        res = json.loads(res_str)
        self.assertEqual(len(res["high_risk_records"]), 2)

    # -------------------------------------------------------------------------
    # 4. Decision Tools Tests
    # -------------------------------------------------------------------------

    def test_simulate_business_scenario(self):
        res_str = simulate_business_scenario.invoke({
            "dataset_id": self.dataset_id,
            "user_id": self.test_user_id,
            "expense_change_pct": -10.0,
            "price_change_pct": 5.0,
        })
        res = json.loads(res_str)
        self.assertGreater(res["profit_delta"], 0.0)
        self.assertEqual(res["baseline"]["revenue"], 82000.0)

    def test_compare_business_strategies(self):
        res_str = compare_business_strategies.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertGreaterEqual(len(res["strategies"]), 4)
        self.assertIsNotNone(res["top_recommended_strategy"])

    def test_estimate_financial_impact(self):
        res_str = estimate_financial_impact.invoke({
            "dataset_id": self.dataset_id,
            "user_id": self.test_user_id,
            "action_type": "renegotiate_vendor_terms",
            "parameters_json": json.dumps({"discount_pct": 5.0}),
        })
        res = json.loads(res_str)
        self.assertGreater(res["estimated_profit_impact"], 0.0)

    def test_optimize_resource_allocation(self):
        res_str = optimize_resource_allocation.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertTrue(res["optimized"])
        self.assertGreater(len(res["allocations"]), 0)

    def test_generate_action_plan(self):
        res_str = generate_action_plan.invoke({
            "dataset_id": self.dataset_id,
            "user_id": self.test_user_id,
            "risk_level": "medium",
        })
        res = json.loads(res_str)
        self.assertGreaterEqual(res["action_count"], 1)

    def test_evaluate_decision_options(self):
        res_str = evaluate_decision_options.invoke({"dataset_id": self.dataset_id, "user_id": self.test_user_id})
        res = json.loads(res_str)
        self.assertIsNotNone(res["top_choice"])


if __name__ == "__main__":
    unittest.main()
