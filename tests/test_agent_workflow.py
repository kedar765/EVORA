"""
EVORA LangGraph Multi-Agent Workflow Test Suite
==============================================
Verifies the multi-agent orchestration graph:
1. Graph compilation and node registration.
2. End-to-end workflow execution on valid dataset.
3. State passing across nodes:
   - validate_dataset -> analytics_agent
   - analytics_agent -> risk_agent
   - risk_agent -> decision_agent
   - decision_agent -> final_report
4. Conditional routing: validation failure bypasses downstream agents to final report.
5. Error handling and partial execution status.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure offline deterministic execution
os.environ["EVORA_SKIP_EXTERNAL_LLM"] = "1"

import backend.auth as auth
import backend.main as main
from workflows.graph import build_evora_graph, compile_workflow, run_evora_workflow
from workflows.state import EVORAAgentState


class TestAgentWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="evora_wf_test_")
        cls.temp_dir = Path(cls.temp_dir_obj.name)

        cls.orig_db_path = auth.DB_PATH
        cls.orig_upload_dir = main.UPLOAD_STORAGE_DIR

        cls.test_db = cls.temp_dir / "backend" / "evora.db"
        cls.test_uploads = cls.temp_dir / "backend" / "storage" / "uploads"
        cls.test_uploads.mkdir(parents=True, exist_ok=True)

        auth.DB_PATH = cls.test_db
        main.UPLOAD_STORAGE_DIR = cls.test_uploads
        os.environ["EVORA_UPLOAD_DIR"] = str(cls.test_uploads)

        auth.initialize_database()

        # Seed test user
        cls.test_user_id = "user-workflow-test-999"
        cls.other_user_id = "user-workflow-other-888"
        with auth.database() as conn:
            conn.execute(
                "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.test_user_id, "Workflow Tester", "workflow@example.com", "hash999", 1000000),
            )
            conn.execute(
                "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.other_user_id, "Other User", "other_wf@example.com", "hash888", 1000000),
            )

        # Create valid CSV
        cls.valid_dataset_id = "wf-dataset-001"
        cls.valid_csv_path = cls.test_uploads / f"{cls.valid_dataset_id}.csv"
        cls.sample_df = pd.DataFrame({
            "Date": ["2026-01-05", "2026-01-12", "2026-02-05", "2026-02-18", "2026-03-01"],
            "Product": ["Alpha", "Beta", "Alpha", "Beta", "Alpha"],
            "Quantity": [10, 20, 15, 25, 30],
            "Revenue": [20000.0, 30000.0, 25000.0, 35000.0, 45000.0],
            "Expense": [12000.0, 18000.0, 15000.0, 22000.0, 28000.0],
            "Category": ["SaaS", "Hardware", "SaaS", "Hardware", "SaaS"],
            "Region": ["North", "South", "North", "South", "East"],
        })
        cls.sample_df.to_csv(cls.valid_csv_path, index=False)

        with auth.database() as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    id, user_id, original_filename, stored_filename, storage_path,
                    uploaded_at, row_count, column_count, columns_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cls.valid_dataset_id,
                    cls.test_user_id,
                    "workflow_business_data.csv",
                    f"{cls.valid_dataset_id}.csv",
                    str(cls.valid_csv_path),
                    1000000,
                    len(cls.sample_df),
                    len(cls.sample_df.columns),
                    json.dumps(list(cls.sample_df.columns)),
                    "ready",
                ),
            )

    @classmethod
    def tearDownClass(cls):
        auth.DB_PATH = cls.orig_db_path
        main.UPLOAD_STORAGE_DIR = cls.orig_upload_dir
        os.environ.pop("EVORA_UPLOAD_DIR", None)
        cls.temp_dir_obj.cleanup()

    def test_workflow_graph_compilation(self):
        """Verifies StateGraph compiles properly with all registered nodes."""
        builder = build_evora_graph()
        self.assertIsNotNone(builder)
        compiled = compile_workflow()
        self.assertIsNotNone(compiled)

    def test_workflow_successful_execution(self):
        """Verifies complete end-to-end execution across all 5 nodes."""
        final_state = run_evora_workflow(
            dataset_id=self.valid_dataset_id,
            user_id=self.test_user_id,
            user_query="Evaluate business performance and cost control options.",
        )

        # 1. Verification of execution status
        self.assertEqual(final_state.get("execution_status"), "completed")
        self.assertEqual(final_state.get("current_step"), "final_report")
        self.assertEqual(len(final_state.get("errors", [])), 0)

        # 2. Verification of Analytics Node
        analytics = final_state.get("analytics_results")
        self.assertIsNotNone(analytics)
        self.assertEqual(analytics.get("total_revenue"), 155000.0)
        self.assertEqual(analytics.get("total_expenses"), 95000.0)
        self.assertEqual(analytics.get("total_profit"), 60000.0)
        self.assertAlmostEqual(analytics.get("profit_margin"), 38.71, places=1)
        self.assertGreaterEqual(len(analytics.get("key_findings", [])), 1)

        # 3. Verification of Risk Node
        risk = final_state.get("risk_results")
        self.assertIsNotNone(risk)
        self.assertIn("risk_score", risk)
        self.assertIn(risk.get("risk_level"), ["low", "medium", "high", "critical"])
        self.assertIn("anomaly_detected", risk)

        # 4. Verification of Decision Node
        decision = final_state.get("decision_results")
        self.assertIsNotNone(decision)
        self.assertIn("recommended_strategy", decision)
        self.assertGreaterEqual(len(decision.get("actions", [])), 1)
        self.assertTrue(decision.get("human_approval_required"))

        # 5. Verification of Final Report Node
        report = final_state.get("final_report")
        self.assertIsNotNone(report)
        self.assertIn("executive_summary", report)
        self.assertIn("business_health_status", report)
        self.assertIn("financial_highlights", report)
        self.assertIn("governance_disclaimer", report)

        # 6. Verification of step durations and agent statuses
        durations = final_state.get("step_durations", {})
        self.assertIn("validate_dataset", durations)
        self.assertIn("analytics_agent", durations)
        self.assertIn("risk_agent", durations)
        self.assertIn("decision_agent", durations)
        self.assertIn("final_report", durations)

        statuses = final_state.get("agent_statuses", {})
        self.assertIn(statuses.get("analytics_agent"), {"completed", "fallback"})
        self.assertIn(statuses.get("risk_agent"), {"completed", "fallback"})
        self.assertIn(statuses.get("decision_agent"), {"completed", "fallback"})

    def test_workflow_conditional_routing_on_invalid_dataset(self):
        """Verifies that an invalid or unauthorized dataset routes directly to final report."""
        final_state = run_evora_workflow(
            dataset_id="non-existent-dataset-id",
            user_id=self.test_user_id,
            user_query="What is our risk?",
        )

        self.assertEqual(final_state.get("execution_status"), "failed")
        self.assertGreater(len(final_state.get("errors", [])), 0)
        # Downstream agent results should NOT have run
        self.assertNotIn("analytics_results", final_state)
        self.assertNotIn("risk_results", final_state)
        self.assertNotIn("decision_results", final_state)
        # Final report exists reporting the dataset failure
        self.assertIsNotNone(final_state.get("final_report"))
        self.assertIn("dataset validation failure", final_state["final_report"]["executive_summary"].lower())

    def test_workflow_unauthorized_dataset_access(self):
        """Verifies that accessing a dataset owned by another user fails safely."""
        final_state = run_evora_workflow(
            dataset_id=self.valid_dataset_id,
            user_id=self.other_user_id,
            user_query="Can I see this data?",
        )

        self.assertEqual(final_state.get("execution_status"), "failed")
        self.assertIn("unauthorized", final_state["errors"][0].lower())

    def test_workflow_partial_agent_failure(self):
        """Verifies that if an individual agent encounters an error, the workflow preserves earlier results and status is partial."""
        from unittest.mock import patch

        def failing_risk_run(*args, **kwargs):
            raise RuntimeError("Simulated transient ML engine failure")

        with patch("agents.risk_agent.RiskAgent.run_agent", side_effect=failing_risk_run):
            final_state = run_evora_workflow(
                dataset_id=self.valid_dataset_id,
                user_id=self.test_user_id,
                user_query="Run workflow with risk agent fault tolerance.",
            )

            # Workflow should conclude with partial status, NOT crash
            self.assertEqual(final_state.get("execution_status"), "partial")
            self.assertGreaterEqual(len(final_state.get("errors", [])), 1)
            self.assertIn("Simulated transient ML engine failure", final_state["errors"][0])

            # Analytics output from preceding node MUST be preserved intact
            self.assertIsNotNone(final_state.get("analytics_results"))
            self.assertEqual(final_state["analytics_results"]["total_revenue"], 155000.0)

            # Decision agent and final report must still have executed
            self.assertIsNotNone(final_state.get("final_report"))


if __name__ == "__main__":
    unittest.main()
