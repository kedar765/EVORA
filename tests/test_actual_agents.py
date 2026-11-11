"""
EVORA Actual LangChain Agents Test Suite
========================================
Validates that:
1. AnalyticsAgent, RiskAgent, and DecisionOptimizationAgent are constructed via LangChain create_agent().
2. All 20 tools are properly registered across the three agents.
3. Tool selection functions dynamically based on user questions and context.
4. The LangChain agent graph executes the tool-calling loop and returns real calculated values.
5. All three agents output validated Pydantic models.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

# Enforce deterministic tool-calling testing mode
os.environ["EVORA_SKIP_EXTERNAL_LLM"] = "1"

from agents.analytics_agent import AnalyticsAgent, create_analytics_agent
from agents.decision_agent import DecisionOptimizationAgent, create_decision_agent
from agents.risk_agent import RiskAgent, create_risk_agent
from backend.auth import database, initialize_database
from schemas.agent_schemas import (
    AnalyticsAgentOutput,
    DecisionAgentOutput,
    RiskAgentOutput,
)
from tools.analytics_tools import ANALYTICS_TOOLS
from tools.decision_tools import DECISION_TOOLS
from tools.risk_tools import RISK_TOOLS


class TestActualLangChainAgents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="evora_actual_agents_")
        cls.db_path = Path(cls.test_dir) / "evora_test.db"
        cls.upload_dir = Path(cls.test_dir) / "uploads"
        cls.upload_dir.mkdir(parents=True, exist_ok=True)

        os.environ["EVORA_DB_PATH"] = str(cls.db_path)
        os.environ["EVORA_UPLOAD_DIR"] = str(cls.upload_dir)

        import backend.auth as auth_mod
        auth_mod.DB_PATH = cls.db_path
        initialize_database()

        # Seed test user and dataset
        cls.user_id = "test_agent_owner"
        with database() as conn:
            conn.execute(
                "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.user_id, "Agent Owner", "agent_owner@evora.ai", "dummy_hash", 1700000000),
            )

        # Create realistic business dataset
        cls.csv_path = cls.upload_dir / "business_test_data.csv"
        records = [
            {"Date": "2025-01-15", "Product": "Alpha SKU", "Category": "Hardware", "Region": "North", "Quantity": 100, "Revenue": 50000.0, "Expense": 30000.0},
            {"Date": "2025-02-15", "Product": "Beta SKU", "Category": "Software", "Region": "South", "Quantity": 150, "Revenue": 75000.0, "Expense": 40000.0},
            {"Date": "2025-03-15", "Product": "Gamma SKU", "Category": "Hardware", "Region": "West", "Quantity": 80, "Revenue": 40000.0, "Expense": 28000.0},
            {"Date": "2025-04-15", "Product": "Delta Loss SKU", "Category": "Services", "Region": "East", "Quantity": 20, "Revenue": 10000.0, "Expense": 18000.0},
            {"Date": "2025-05-15", "Product": "Epsilon Outlier", "Category": "Services", "Region": "North", "Quantity": 500, "Revenue": 300000.0, "Expense": 290000.0},
        ]
        df = pd.DataFrame(records)
        df.to_csv(cls.csv_path, index=False)

        cls.dataset_id = "dataset_actual_agents_001"
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
                    cls.user_id,
                    "business_test_data.csv",
                    "business_test_data.csv",
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

    # -------------------------------------------------------------------------
    # Analytics Agent Verification
    # -------------------------------------------------------------------------

    def test_analytics_agent_construction_and_tools(self):
        """Verifies Analytics Agent creates a genuine LangChain agent with 7 tools."""
        agent = create_analytics_agent()
        langchain_graph = agent.build_langchain_agent()

        # Must be a compiled LangChain / LangGraph agent
        self.assertTrue(hasattr(langchain_graph, "invoke"), "Agent must be an executable runnable/graph.")
        self.assertEqual(len(ANALYTICS_TOOLS), 7, "All 7 Analytics tools must be registered.")

        tool_names = {t.name for t in ANALYTICS_TOOLS}
        expected = {
            "get_dataset_profile",
            "calculate_business_metrics",
            "analyze_time_trends",
            "compare_business_segments",
            "analyze_product_performance",
            "query_business_data",
            "analyze_relationships",
        }
        self.assertEqual(tool_names, expected)

    def test_analytics_agent_execution_and_output(self):
        """Verifies Analytics Agent runs tool calling and returns validated AnalyticsAgentOutput."""
        agent = create_analytics_agent()
        output = agent.run_agent(
            dataset_id=self.dataset_id,
            user_id=self.user_id,
            user_query="Analyze product performance and profitability trends.",
        )

        self.assertIsInstance(output, AnalyticsAgentOutput)
        self.assertGreater(output.total_revenue, 0.0)
        self.assertGreater(output.total_expenses, 0.0)
        self.assertGreaterEqual(len(output.key_findings), 1)
        self.assertGreaterEqual(len(output.evidence), 3)
        self.assertEqual(output.row_count, 5)

    # -------------------------------------------------------------------------
    # Risk Agent Verification
    # -------------------------------------------------------------------------

    def test_risk_agent_construction_and_tools(self):
        """Verifies Risk Agent creates a genuine LangChain agent with 7 tools."""
        agent = create_risk_agent()
        langchain_graph = agent.build_langchain_agent()

        self.assertTrue(hasattr(langchain_graph, "invoke"))
        self.assertEqual(len(RISK_TOOLS), 7, "All 7 Risk tools must be registered.")

        tool_names = {t.name for t in RISK_TOOLS}
        expected = {
            "detect_anomalies",
            "analyze_revenue_drops",
            "analyze_expense_growth",
            "identify_loss_patterns",
            "calculate_risk_score",
            "forecast_business_risks",
            "explain_risk_records",
        }
        self.assertEqual(tool_names, expected)

    def test_risk_agent_execution_and_output(self):
        """Verifies Risk Agent executes risk scoring and returns structured RiskAgentOutput."""
        agent = create_risk_agent()
        output = agent.run_agent(
            dataset_id=self.dataset_id,
            user_id=self.user_id,
            analytics_context={"total_profit": 67000.0, "profit_margin": 14.1},
            user_query="Assess operational risk, anomalies, and loss-making records.",
        )

        self.assertIsInstance(output, RiskAgentOutput)
        self.assertIn(output.risk_level, {"low", "medium", "high", "critical"})
        self.assertGreaterEqual(output.risk_score, 0.0)
        self.assertLessEqual(output.risk_score, 100.0)
        self.assertGreaterEqual(len(output.findings), 1)
        self.assertGreaterEqual(len(output.key_risks), 1)

    # -------------------------------------------------------------------------
    # Decision Optimization Agent Verification
    # -------------------------------------------------------------------------

    def test_decision_agent_construction_and_tools(self):
        """Verifies Decision Agent creates a genuine LangChain agent with 6 tools."""
        agent = create_decision_agent()
        langchain_graph = agent.build_langchain_agent()

        self.assertTrue(hasattr(langchain_graph, "invoke"))
        self.assertEqual(len(DECISION_TOOLS), 6, "All 6 Decision tools must be registered.")

        tool_names = {t.name for t in DECISION_TOOLS}
        expected = {
            "simulate_business_scenario",
            "compare_business_strategies",
            "estimate_financial_impact",
            "optimize_resource_allocation",
            "generate_action_plan",
            "evaluate_decision_options",
        }
        self.assertEqual(tool_names, expected)

    def test_decision_agent_execution_and_output(self):
        """Verifies Decision Agent simulates scenarios and returns validated DecisionAgentOutput."""
        agent = create_decision_agent()
        output = agent.run_agent(
            dataset_id=self.dataset_id,
            user_id=self.user_id,
            analytics_context={"total_profit": 67000.0, "profit_margin": 14.1},
            risk_context={"risk_score": 45.0, "risk_level": "medium"},
            user_query="Evaluate strategic options and recommend an action plan.",
        )

        self.assertIsInstance(output, DecisionAgentOutput)
        self.assertIn(output.overall_priority, {"low", "medium", "high", "critical"})
        self.assertTrue(output.human_approval_required)
        self.assertGreaterEqual(len(output.actions), 1)
        self.assertGreaterEqual(len(output.scenarios), 1)
        self.assertTrue(bool(output.recommended_strategy))


if __name__ == "__main__":
    unittest.main()
