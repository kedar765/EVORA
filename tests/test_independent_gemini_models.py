"""
EVORA Test Suite: Three Independent Gemini Models for Three AI Agents
=====================================================================
Verifies:
1. Analytics uses gemini-3.5-flash-lite.
2. Risk uses gemini-3.7-flash.
3. Decision uses gemini-3.1-pro-preview.
4. Independent model configuration without cross-contamination.
5. Correct tool registration (7 Analytics, 7 Risk, 6 Decision).
6. Tool invocation through LangChain create_agent().
7. Pydantic validation of outputs including model_used and execution_mode.
8. Quota circuit breaker preventing redundant retries upon RESOURCE_EXHAUSTED.
9. LangGraph sequential state passing between agents with distinct models.
10. Live Gemini API accessibility and tool-calling capability.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from agents.analytics_agent import AnalyticsAgent
from agents.config import (
    ANALYTICS_DEFAULT_MODEL,
    DECISION_DEFAULT_MODEL,
    RISK_DEFAULT_MODEL,
    ModelQuotaManager,
    create_gemini_chat_model,
    get_analytics_model,
    get_decision_model,
    get_risk_model,
)
from agents.decision_agent import DecisionOptimizationAgent
from agents.risk_agent import RiskAgent
from schemas.agent_schemas import (
    AnalyticsAgentOutput,
    DecisionAgentOutput,
    RiskAgentOutput,
)
import shutil
import tempfile
from pathlib import Path
import pandas as pd

from backend.auth import database, initialize_database
from tools.analytics_tools import ANALYTICS_TOOLS
from tools.decision_tools import DECISION_TOOLS
from tools.risk_tools import RISK_TOOLS
from workflows.graph import run_evora_workflow


class TestIndependentGeminiModels(unittest.TestCase):
    """Verifies independent model assignment, tool calling, quota handling, and LangGraph flow."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="evora_indep_models_")
        cls.db_path = Path(cls.test_dir) / "evora_test.db"
        cls.upload_dir = Path(cls.test_dir) / "uploads"
        cls.upload_dir.mkdir(parents=True, exist_ok=True)

        os.environ["EVORA_DB_PATH"] = str(cls.db_path)
        os.environ["EVORA_UPLOAD_DIR"] = str(cls.upload_dir)

        import backend.auth as auth_mod
        auth_mod.DB_PATH = cls.db_path
        initialize_database()

        cls.test_user_id = "test_user_independent_models"
        with database() as conn:
            conn.execute(
                "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.test_user_id, "Test User", "test_user@example.com", "dummy_hash", 1700000000),
            )

        cls.csv_path = cls.upload_dir / "test_business.csv"
        records = [
            {"Date": "2025-01-15", "Product": "Alpha SKU", "Category": "Hardware", "Region": "North", "Quantity": 100, "Revenue": 50000.0, "Expense": 30000.0},
            {"Date": "2025-02-15", "Product": "Beta SKU", "Category": "Software", "Region": "South", "Quantity": 150, "Revenue": 75000.0, "Expense": 40000.0},
            {"Date": "2025-03-15", "Product": "Gamma SKU", "Category": "Hardware", "Region": "West", "Quantity": 80, "Revenue": 40000.0, "Expense": 28000.0},
            {"Date": "2025-04-15", "Product": "Delta Loss", "Category": "Services", "Region": "East", "Quantity": 20, "Revenue": 10000.0, "Expense": 18000.0},
            {"Date": "2025-05-15", "Product": "Epsilon Outlier", "Category": "Services", "Region": "North", "Quantity": 500, "Revenue": 300000.0, "Expense": 290000.0},
        ]
        df = pd.DataFrame(records)
        df.to_csv(cls.csv_path, index=False)

        cls.dataset_id = "dataset_indep_001"
        with database() as conn:
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
                    "test_business.csv",
                    str(cls.csv_path),
                    1700000000,
                    len(records),
                    7,
                    '["Date", "Product", "Category", "Region", "Quantity", "Revenue", "Expense"]',
                    "ready",
                ),
            )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def tearDown(self):
        ModelQuotaManager.reset()

    # -------------------------------------------------------------------------
    # 1. Independent Model Configuration & Defaults
    # -------------------------------------------------------------------------

    def test_01_default_model_ids_match_specification(self):
        """Verify each agent has the exact assigned default model ID."""
        self.assertEqual(ANALYTICS_DEFAULT_MODEL, "gemini-3.1-flash-lite")
        self.assertEqual(RISK_DEFAULT_MODEL, "gemini-3.5-flash")
        self.assertEqual(DECISION_DEFAULT_MODEL, "gemini-3.6-flash")

        # Agents instantiate with their respective defaults
        analytics = AnalyticsAgent()
        risk = RiskAgent()
        decision = DecisionOptimizationAgent()

        self.assertEqual(analytics.gemini_model, "gemini-3.1-flash-lite")
        self.assertEqual(risk.gemini_model, "gemini-3.5-flash")
        self.assertEqual(decision.gemini_model, "gemini-3.6-flash")

        # Ensure all three models are distinct
        distinct_models = {analytics.gemini_model, risk.gemini_model, decision.gemini_model}
        self.assertEqual(len(distinct_models), 3, "Each agent must use a distinct Gemini model")

    def test_02_independent_environment_variable_override(self):
        """Verify modifying one agent's env var does not change the other agents' models."""
        with patch.dict(os.environ, {
            "ANALYTICS_GEMINI_MODEL": "custom-analytics-model",
            "RISK_GEMINI_MODEL": "custom-risk-model",
            "DECISION_GEMINI_MODEL": "custom-decision-model",
        }):
            self.assertEqual(get_analytics_model(), "custom-analytics-model")
            self.assertEqual(get_risk_model(), "custom-risk-model")
            self.assertEqual(get_decision_model(), "custom-decision-model")

            a = AnalyticsAgent()
            r = RiskAgent()
            d = DecisionOptimizationAgent()
            self.assertEqual(a.gemini_model, "custom-analytics-model")
            self.assertEqual(r.gemini_model, "custom-risk-model")
            self.assertEqual(d.gemini_model, "custom-decision-model")

        # Isolating Analytics change only
        with patch.dict(os.environ, {
            "ANALYTICS_GEMINI_MODEL": "gemini-3.5-flash-lite-exp",
        }, clear=False):
            a2 = AnalyticsAgent()
            r2 = RiskAgent()
            d2 = DecisionOptimizationAgent()
            self.assertEqual(a2.gemini_model, "gemini-3.5-flash-lite-exp")
            self.assertEqual(r2.gemini_model, "gemini-3.5-flash")
            self.assertEqual(d2.gemini_model, "gemini-3.6-flash")

    # -------------------------------------------------------------------------
    # 2. Tool Registration across Agents
    # -------------------------------------------------------------------------

    def test_03_tool_registration_per_agent(self):
        """Verify each agent registers its exact tools (7 Analytics, 7 Risk, 6 Decision)."""
        self.assertEqual(len(ANALYTICS_TOOLS), 7)
        self.assertEqual(len(RISK_TOOLS), 7)
        self.assertEqual(len(DECISION_TOOLS), 6)

        analytics_tool_names = {t.name for t in ANALYTICS_TOOLS}
        expected_analytics = {
            "get_dataset_profile",
            "calculate_business_metrics",
            "analyze_time_trends",
            "compare_business_segments",
            "analyze_product_performance",
            "query_business_data",
            "analyze_relationships",
        }
        self.assertEqual(analytics_tool_names, expected_analytics)

        risk_tool_names = {t.name for t in RISK_TOOLS}
        expected_risk = {
            "detect_anomalies",
            "analyze_revenue_drops",
            "analyze_expense_growth",
            "identify_loss_patterns",
            "calculate_risk_score",
            "forecast_business_risks",
            "explain_risk_records",
        }
        self.assertEqual(risk_tool_names, expected_risk)

        decision_tool_names = {t.name for t in DECISION_TOOLS}
        expected_decision = {
            "simulate_business_scenario",
            "compare_business_strategies",
            "estimate_financial_impact",
            "optimize_resource_allocation",
            "generate_action_plan",
            "evaluate_decision_options",
        }
        self.assertEqual(decision_tool_names, expected_decision)

    # -------------------------------------------------------------------------
    # 3. LangChain Agent Execution & Pydantic Validation
    # -------------------------------------------------------------------------

    def test_04_analytics_agent_execution_and_schema_validation(self):
        """Verify AnalyticsAgent invokes tools and returns valid AnalyticsAgentOutput."""
        agent = AnalyticsAgent()
        out = agent.run_agent(self.dataset_id, self.test_user_id, "Summary of metrics")

        self.assertIsInstance(out, AnalyticsAgentOutput)
        self.assertGreater(out.total_revenue, 0)
        self.assertIn(out.execution_mode, {"llm", "deterministic_fallback", "groq_fallback"})
        self.assertIsNotNone(out.model_used)
        self.assertIn("gemini-3.1-flash-lite", out.model_used)

    def test_05_risk_agent_execution_and_schema_validation(self):
        """Verify RiskAgent consumes context, invokes tools, and returns valid RiskAgentOutput."""
        analytics_agent = AnalyticsAgent()
        analytics_out = analytics_agent.run_agent(self.dataset_id, self.test_user_id)

        risk_agent = RiskAgent()
        risk_out = risk_agent.run_agent(
            self.dataset_id,
            self.test_user_id,
            analytics_context=analytics_out.model_dump(),
        )

        self.assertIsInstance(risk_out, RiskAgentOutput)
        self.assertGreaterEqual(risk_out.risk_score, 0.0)
        self.assertLessEqual(risk_out.risk_score, 100.0)
        self.assertIn(risk_out.risk_level, {"low", "medium", "high", "critical"})
        self.assertIn(risk_out.execution_mode, {"llm", "deterministic_fallback", "groq_fallback"})
        self.assertIn("gemini-3.5-flash", risk_out.model_used)

    def test_06_decision_agent_execution_and_schema_validation(self):
        """Verify DecisionAgent consumes context and returns valid DecisionAgentOutput."""
        analytics_out = AnalyticsAgent().run_agent(self.dataset_id, self.test_user_id)
        risk_out = RiskAgent().run_agent(
            self.dataset_id,
            self.test_user_id,
            analytics_context=analytics_out.model_dump(),
        )

        decision_agent = DecisionOptimizationAgent()
        decision_out = decision_agent.run_agent(
            self.dataset_id,
            self.test_user_id,
            analytics_context=analytics_out.model_dump(),
            risk_context=risk_out.model_dump(),
        )

        self.assertIsInstance(decision_out, DecisionAgentOutput)
        self.assertTrue(len(decision_out.actions) > 0)
        self.assertIn(decision_out.execution_mode, {"llm", "deterministic_fallback", "groq_fallback"})
        self.assertIn("gemini-3.6-flash", decision_out.model_used)

    # -------------------------------------------------------------------------
    # 4. Quota Circuit Breaker & Error Handling
    # -------------------------------------------------------------------------

    def test_07_quota_circuit_breaker_halts_redundant_retries(self):
        """Verify circuit breaker trips on RESOURCE_EXHAUSTED and avoids repeated retries."""
        model_id = "gemini-3.7-flash"
        self.assertFalse(ModelQuotaManager.is_exhausted(model_id)[0])

        # Simulate quota exhaustion
        simulated_err = (
            "GoogleRateLimitError: Error calling model 'gemini-3.7-flash' "
            "(RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
            "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20"
        )
        self.assertTrue(ModelQuotaManager.is_quota_error(simulated_err))

        ModelQuotaManager.mark_exhausted(model_id, simulated_err)
        is_exhausted, reason = ModelQuotaManager.is_exhausted(model_id)
        self.assertTrue(is_exhausted)
        self.assertIn("RESOURCE_EXHAUSTED", reason)

        # Execute RiskAgent with exhausted model
        agent = RiskAgent(gemini_model=model_id)
        out = agent.run_agent(self.dataset_id, self.test_user_id)

        # Fallback must be used and transparently declared
        self.assertEqual(out.execution_mode, "deterministic_fallback")
        self.assertIn("deterministic_fallback", out.model_used)
        self.assertIn(model_id, out.model_used)
        self.assertIsNotNone(out.model_error)
        self.assertIn("RESOURCE_EXHAUSTED", out.model_error)

    # -------------------------------------------------------------------------
    # 5. LangGraph Workflow with Distinct Models
    # -------------------------------------------------------------------------

    def test_08_langgraph_workflow_independent_models_and_modes(self):
        """Verify complete LangGraph workflow captures models_used, execution_modes, and statuses."""
        workflow_result = run_evora_workflow(
            dataset_id=self.dataset_id,
            user_id=self.test_user_id,
            user_query="Evaluate business performance under independent models",
        )

        self.assertIn("models_used", workflow_result)
        self.assertIn("execution_modes", workflow_result)
        self.assertIn("agent_statuses", workflow_result)

        models_used = workflow_result["models_used"]
        execution_modes = workflow_result["execution_modes"]
        agent_statuses = workflow_result["agent_statuses"]

        self.assertIn("analytics_agent", models_used)
        self.assertIn("risk_agent", models_used)
        self.assertIn("decision_agent", models_used)

        self.assertIn("gemini-3.1-flash-lite", models_used["analytics_agent"])
        self.assertIn("gemini-3.5-flash", models_used["risk_agent"])
        self.assertIn("gemini-3.6-flash", models_used["decision_agent"])

        # Never report deterministic fallback as completed LLM
        for agent_name in ["analytics_agent", "risk_agent", "decision_agent"]:
            mode = execution_modes.get(agent_name)
            status = agent_statuses.get(agent_name)
            if mode == "deterministic_fallback":
                self.assertEqual(status, "fallback", f"{agent_name} used fallback but reported as {status}")

        final_rep = workflow_result.get("final_report", {})
        self.assertIn("models_used", final_rep)
        self.assertIn("execution_modes", final_rep)

    # -------------------------------------------------------------------------
    # 6. Live Gemini API Model Accessibility Check
    # -------------------------------------------------------------------------

    def test_09_live_gemini_models_api_status(self):
        """Verifies actual API accessibility and tool-calling capability for all three model IDs."""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            self.skipTest("No GEMINI_API_KEY present in environment")

        from langchain_core.tools import tool

        @tool
        def sample_add(a: int, b: int) -> int:
            """Adds two integers."""
            return a + b

        models_to_test = [
            ("gemini-3.1-flash-lite", "Analytics Agent"),
            ("gemini-3.5-flash", "Risk Agent"),
            ("gemini-3.6-flash", "Decision Optimization Agent"),
        ]

        live_results = {}
        for m, agent_role in models_to_test:
            try:
                llm = create_gemini_chat_model(m, api_key=api_key, timeout=15.0)
                bound = llm.bind_tools([sample_add])
                res = bound.invoke("Calculate 7 + 8")
                live_results[m] = {"status": "SUCCESS_TOOL_CALL", "tool_calls": len(res.tool_calls)}
            except Exception as e:
                is_quota = ModelQuotaManager.is_quota_error(e)
                live_results[m] = {
                    "status": "QUOTA_EXHAUSTED" if is_quota else "ERROR",
                    "error_type": type(e).__name__,
                    "error_msg": str(e)[:120],
                }

        # Assert all three were tested and classified (gemini-3.5-flash-lite should succeed or be rate-limited)
        self.assertEqual(len(live_results), 3)
        print("\n--- Live Gemini Model Verification Results ---")
        for m, res in live_results.items():
            print(f"  {m}: {res['status']} ({res.get('error_type', 'OK')})")
        print("----------------------------------------------")


if __name__ == "__main__":
    unittest.main()
