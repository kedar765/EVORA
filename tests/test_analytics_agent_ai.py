"""
EVORA Analytics Agent AI Test Suite
====================================
Comprehensive verification for AI-powered Analytics Agent:
  1. Gemini Flash primary success
  2. Gemini-to-Groq fallback (when Gemini returns None)
  3. Gemini fallback when Gemini invocation raises an exception (not only None)
  4. Unit test: _call_gemini catches all underlying exceptions and returns None
  5. Both providers fail -> Deterministic rule-based fallback
  6. Both providers raise exceptions -> Deterministic rule-based fallback
  7. Missing / empty API keys -> Immediate rule-based fallback
  8. Malformed LLM output -> Validation failure & safe fallback
  9. Financial calculations integrity (Pandas ground truth never altered)
 10. Privacy & compact summary safety (no raw records, PII, or customer data)
 11. Large-scale dataset privacy and payload bounded-size invariance
 12. Missing columns & empty DataFrame handling
 13. Live Gemini Flash integration test (with network probe & clear provider failure handling)
"""

import json
import os
import socket
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from agents.analytics_agent import AnalyticsAgent, AnalyticsLLMOutput


class TestAnalyticsAgentAI(unittest.TestCase):

    def setUp(self):
        self.sample_df = pd.DataFrame({
            "Date": ["2026-01-10", "2026-01-15", "2026-02-05", "2026-02-20"],
            "Product": ["Alpha", "Beta", "Alpha", "Beta"],
            "Revenue": [10000.0, 15000.0, 20000.0, 25000.0],
            "Expense": [6000.0, 9000.0, 12000.0, 16000.0],
            "Customer": ["Corp A", "Corp B", "Corp C", "Corp D"],  # Sensitive customer field
        })

    # -------------------------------------------------------------------------
    # 1. Gemini Success
    # -------------------------------------------------------------------------
    def test_gemini_success(self):
        """Verifies successful primary LLM execution with Google Gemini Flash."""
        agent = AnalyticsAgent(gemini_api_key="mock-gemini-key")

        mock_gemini_output = (
            [
                "Revenue grew by 60% from January to February.",
                "Alpha product line demonstrates higher profit efficiency than Beta.",
                "Expense-to-revenue ratio held steady at 61%."
            ],
            [
                "Expand marketing spend on Alpha to capture higher margin volume.",
                "Renegotiate vendor terms for Beta to reduce unit expense."
            ]
        )

        with patch.object(agent, "_call_gemini", return_value=mock_gemini_output) as mock_gemini:
            with patch.object(agent, "_call_groq") as mock_groq:
                result = agent.analyze(self.sample_df)

                mock_gemini.assert_called_once()
                mock_groq.assert_not_called()

                # Verify all required keys
                self.assertIn("total_revenue", result)
                self.assertIn("total_expense", result)
                self.assertIn("total_profit", result)
                self.assertIn("profit_margin", result)
                self.assertIn("insights", result)
                self.assertIn("recommendations", result)
                self.assertIn("product_performance", result)
                self.assertIn("monthly_trends", result)

                # Verify financial metrics match Pandas calculations exactly
                self.assertEqual(result["total_revenue"], 70000.0)
                self.assertEqual(result["total_expense"], 43000.0)
                self.assertEqual(result["total_profit"], 27000.0)
                self.assertAlmostEqual(result["profit_margin"], 38.57, places=2)

                # Verify LLM insights are present
                self.assertTrue(any("Alpha" in s for s in result["insights"]))
                self.assertTrue(any("Beta" in s for s in result["recommendations"]))

                # Verify foundational profitability status is preserved
                self.assertTrue(any("profitable" in s.lower() for s in result["insights"]))

    # -------------------------------------------------------------------------
    # 2. Gemini-to-Groq Fallback (Gemini returns None)
    # -------------------------------------------------------------------------
    def test_gemini_to_groq_fallback(self):
        """Verifies graceful fallback to Groq when Gemini returns None."""
        agent = AnalyticsAgent(
            gemini_api_key="mock-gemini-key",
            groq_api_key="mock-groq-key"
        )

        mock_groq_output = (
            [
                "Groq Insight: Healthy gross cash flow across both operating periods.",
                "Groq Insight: Operating margin stands at a resilient 38.57%."
            ],
            [
                "Groq Recommendation: Streamline operational overhead in Q2.",
                "Groq Recommendation: Introduce tiered pricing for enterprise clients."
            ]
        )

        # Gemini fails by returning None
        with patch.object(agent, "_call_gemini", return_value=None) as mock_gemini:
            with patch.object(agent, "_call_groq", return_value=mock_groq_output) as mock_groq:
                result = agent.analyze(self.sample_df)

                mock_gemini.assert_called_once()
                mock_groq.assert_called_once()

                # Metrics remain exact Pandas numbers
                self.assertEqual(result["total_revenue"], 70000.0)
                self.assertEqual(result["total_profit"], 27000.0)

                # Insights come from Groq
                self.assertTrue(any("Groq Insight" in s for s in result["insights"]))
                self.assertTrue(any("Groq Recommendation" in s for s in result["recommendations"]))

    # -------------------------------------------------------------------------
    # 3. Gemini Fallback when Gemini Invocation Raises an Exception
    # -------------------------------------------------------------------------
    def test_gemini_exception_fallback_to_groq(self):
        """
        Verifies that when Gemini raises an exception (API error, rate limit, timeout),
        _call_gemini catches it safely, returns None, and the agent cascades to Groq.
        """
        agent = AnalyticsAgent(
            gemini_api_key="mock-gemini-key",
            groq_api_key="mock-groq-key"
        )

        mock_groq_output = (
            [
                "Groq Exception Fallback Insight: Operations remain cash positive.",
                "Groq Exception Fallback Insight: Solid 38.57% net margin."
            ],
            [
                "Groq Exception Fallback Rec: Optimize inventory turnaround times."
            ]
        )

        # Simulate Gemini LLM raising an exception (e.g. HTTP 503, Quota 429, Timeout)
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini_cls:
            mock_llm_instance = MagicMock()
            mock_structured_llm = MagicMock()
            mock_structured_llm.invoke.side_effect = RuntimeError(
                "ResourceExhausted: 429 Quota exceeded for quota metric 'GenerateContent requests'"
            )
            mock_llm_instance.with_structured_output.return_value = mock_structured_llm
            mock_gemini_cls.return_value = mock_llm_instance

            with patch.object(agent, "_call_groq", return_value=mock_groq_output) as mock_groq:
                result = agent.analyze(self.sample_df)

                # Groq fallback must be invoked
                mock_groq.assert_called_once()

                # Metrics remain ground truth
                self.assertEqual(result["total_revenue"], 70000.0)
                self.assertEqual(result["total_profit"], 27000.0)

                # Output reflects Groq fallback
                self.assertTrue(any("Groq Exception Fallback Insight" in s for s in result["insights"]))
                self.assertTrue(any("Groq Exception Fallback Rec" in s for s in result["recommendations"]))
                self.assertTrue(any("profitable" in s.lower() for s in result["insights"]))

    # -------------------------------------------------------------------------
    # 4. _call_gemini Exception Resilience Unit Test
    # -------------------------------------------------------------------------
    def test_call_gemini_catches_underlying_exceptions(self):
        """
        Directly verifies that _call_gemini swallows any underlying exceptions
        (network disconnect, API error, instantiation failure) and returns None
        without allowing unhandled exceptions to crash callers.
        """
        agent = AnalyticsAgent(gemini_api_key="mock-gemini-key")
        summary_payload = {"financial_summary": {"total_revenue": 70000.0}}

        # Case A: Instantiation exception
        with patch("langchain_google_genai.ChatGoogleGenerativeAI", side_effect=Exception("Initialization failure")):
            res_a = agent._call_gemini(summary_payload)
            self.assertIsNone(res_a)

        # Case B: Invocation timeout / socket error
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini_cls:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.invoke.side_effect = TimeoutError("Connection timed out after 25s")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_gemini_cls.return_value = mock_llm

            res_b = agent._call_gemini(summary_payload)
            self.assertIsNone(res_b)

    # -------------------------------------------------------------------------
    # 5. Both Providers Fail -> Deterministic Rule-Based Fallback
    # -------------------------------------------------------------------------
    def test_both_providers_fail_rule_based_fallback(self):
        """Verifies fallback to rule-based analytics when both Gemini and Groq fail."""
        agent = AnalyticsAgent(
            gemini_api_key="mock-gemini-key",
            groq_api_key="mock-groq-key"
        )

        with patch.object(agent, "_call_gemini", return_value=None):
            with patch.object(agent, "_call_groq", return_value=None):
                result = agent.analyze(self.sample_df)

                # Metrics remain exact
                self.assertEqual(result["total_revenue"], 70000.0)
                self.assertEqual(result["total_profit"], 27000.0)

                # Rule-based fallback insights and recommendations
                self.assertTrue(any("profitable" in s.lower() for s in result["insights"]))
                self.assertTrue(any("profit margin" in s.lower() for s in result["insights"]))
                self.assertTrue(len(result["recommendations"]) > 0)

    # -------------------------------------------------------------------------
    # 6. Both Providers Raise Exceptions -> Deterministic Rule-Based Fallback
    # -------------------------------------------------------------------------
    def test_both_providers_raise_exceptions_rule_based_fallback(self):
        """Verifies graceful degradation to rule-based when both LLMs raise exceptions."""
        agent = AnalyticsAgent(
            gemini_api_key="mock-gemini-key",
            groq_api_key="mock-groq-key"
        )

        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini_cls, \
             patch("langchain_groq.ChatGroq") as mock_groq_cls:

            # Gemini raises exception
            mock_gemini_llm = MagicMock()
            mock_gemini_struct = MagicMock()
            mock_gemini_struct.invoke.side_effect = ConnectionResetError("Gemini connection lost")
            mock_gemini_llm.with_structured_output.return_value = mock_gemini_struct
            mock_gemini_cls.return_value = mock_gemini_llm

            # Groq raises exception
            mock_groq_llm = MagicMock()
            mock_groq_struct = MagicMock()
            mock_groq_struct.invoke.side_effect = RuntimeError("Groq 500 Internal Server Error")
            mock_groq_llm.with_structured_output.return_value = mock_groq_struct
            mock_groq_cls.return_value = mock_groq_llm

            result = agent.analyze(self.sample_df)

            # Must not crash; must fall back to deterministic rule-based
            self.assertEqual(result["total_revenue"], 70000.0)
            self.assertEqual(result["total_profit"], 27000.0)
            self.assertTrue(any("profitable" in s.lower() for s in result["insights"]))
            self.assertTrue(len(result["recommendations"]) > 0)

    # -------------------------------------------------------------------------
    # 7. Missing API Keys -> Immediate Rule-Based Fallback
    # -------------------------------------------------------------------------
    def test_missing_api_keys_rule_based_fallback(self):
        """Verifies rule-based execution when no API keys are provided."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GROQ_API_KEY": ""}, clear=False):
            agent = AnalyticsAgent()
            agent.gemini_api_key = None
            agent.groq_api_key = None

            result = agent.analyze(self.sample_df)

            self.assertEqual(result["total_revenue"], 70000.0)
            self.assertEqual(result["total_expense"], 43000.0)
            self.assertEqual(result["total_profit"], 27000.0)
            self.assertTrue(any("profitable" in s.lower() for s in result["insights"]))
            self.assertTrue(len(result["recommendations"]) >= 1)

    # -------------------------------------------------------------------------
    # 8. Malformed LLM Output Handled Safely
    # -------------------------------------------------------------------------
    def test_malformed_llm_output_handling(self):
        """Verifies that invalid or malformed LLM outputs are rejected and fall back safely."""
        agent = AnalyticsAgent()
        agent.gemini_api_key = None
        agent.groq_api_key = None

        # Case A: Empty output
        self.assertIsNone(agent._validate_llm_output(None))
        self.assertIsNone(agent._validate_llm_output(""))

        # Case B: Dict with empty lists
        self.assertIsNone(agent._validate_llm_output({"insights": [], "recommendations": []}))

        # Case C: Non-string elements
        self.assertIsNone(agent._validate_llm_output({"insights": [123, 456], "recommendations": []}))

        # Case D: Valid Pydantic model
        valid_model = AnalyticsLLMOutput(
            insights=["Valid insight observation."],
            recommendations=["Valid recommendation action."]
        )
        validated = agent._validate_llm_output(valid_model)
        self.assertIsNotNone(validated)
        self.assertEqual(len(validated[0]), 1)
        self.assertEqual(len(validated[1]), 1)

        # Case E: Valid raw JSON string with markdown formatting
        raw_json_str = '```json\n{"insights": ["Markdown insight"], "recommendations": ["Markdown rec"]}\n```'
        validated_str = agent._validate_llm_output(raw_json_str)
        self.assertIsNotNone(validated_str)
        self.assertEqual(validated_str[0], ["Markdown insight"])

    # -------------------------------------------------------------------------
    # 9. Financial Calculations Integrity
    # -------------------------------------------------------------------------
    def test_financial_calculations_never_overwritten(self):
        """Verifies that Pandas calculations are the single source of truth for numbers."""
        agent = AnalyticsAgent()
        agent.gemini_api_key = None
        agent.groq_api_key = None

        loss_df = pd.DataFrame({
            "Revenue": [20000.0, 15000.0],
            "Expense": [30000.0, 25000.0],
            "Product": ["X", "Y"]
        })

        result = agent.analyze(loss_df)

        self.assertEqual(result["total_revenue"], 35000.0)
        self.assertEqual(result["total_expense"], 55000.0)
        self.assertEqual(result["total_profit"], -20000.0)
        self.assertAlmostEqual(result["profit_margin"], -57.14, places=2)
        self.assertTrue(any("loss" in s.lower() for s in result["insights"]))

    # -------------------------------------------------------------------------
    # 10. Privacy & Compact Summary Safety (Comprehensive PII & Row Checks)
    # -------------------------------------------------------------------------
    def test_compact_summary_privacy_safety(self):
        """
        Verifies that no customer data, PII, account numbers, or raw row records
        are included in the compact LLM summary payload.
        """
        agent = AnalyticsAgent()
        agent.gemini_api_key = None
        agent.groq_api_key = None

        # Rich sensitive enterprise DataFrame with multiple transactions per product
        sensitive_df = pd.DataFrame({
            "Date": ["2026-01-10", "2026-01-15", "2026-02-05", "2026-02-20", "2026-02-25", "2026-02-28"],
            "Product": ["Alpha", "Beta", "Alpha", "Beta", "Gamma", "Gamma"],
            "Revenue": [10000.0, 15000.0, 20000.0, 25000.0, 6789.23, 7000.0],
            "Expense": [6000.0, 9000.0, 12000.0, 16000.0, 4412.11, 4000.0],
            "Customer": ["Acme Corp", "Cyberdyne Systems", "Wayne Enterprises", "Stark Industries", "Umbrella Corp", "Initech LLC"],
            "Customer_Email": ["ceo@acme.com", "contact@cyberdyne.org", "bruce@wayne.com", "tony@stark.com", "lab@umbrella.corp", "bill@initech.com"],
            "Customer_Phone": ["+1-555-0100", "+1-555-0101", "+1-555-0102", "+1-555-0103", "+1-555-0104", "+1-555-0105"],
            "Account_Number": ["ACC-987654", "ACC-876543", "ACC-765432", "ACC-654321", "ACC-543210", "ACC-432109"],
            "Credit_Card": ["4111-2222-3333-4444", "5500-0000-0000-0001", "3782-822463-10005", "6011-0009-9999-0000", "3528-0000-0000-0000", "4000-1234-5678-9010"],
            "Transaction_ID": ["TXN-90210-A", "TXN-90210-B", "TXN-90210-C", "TXN-90210-D", "TXN-90210-E", "TXN-90210-F"],
            "Billing_Address": ["100 Secret Blvd", "200 Hidden Way", "300 Private Ave", "400 Restricted St", "500 Confidential Rd", "600 Silicon Way"],
            "Internal_Notes": ["VIP client NDA", "Disputed fee", "Legal review", "Offshore entity", "Special waiver", "Pending audit"],
        })

        metrics = agent._compute_metrics(sensitive_df)
        summary = agent._generate_compact_summary(sensitive_df, metrics)
        summary_json = json.dumps(summary)

        # 1. Verify all customer identities are strictly excluded
        for customer in sensitive_df["Customer"]:
            self.assertNotIn(customer, summary_json)

        # 2. Verify all PII (email, phone, address) is strictly excluded
        for email in sensitive_df["Customer_Email"]:
            self.assertNotIn(email, summary_json)
        for phone in sensitive_df["Customer_Phone"]:
            self.assertNotIn(phone, summary_json)
        for address in sensitive_df["Billing_Address"]:
            self.assertNotIn(address, summary_json)

        # 3. Verify financial identifiers (account numbers, credit cards, transaction IDs) are excluded
        for acc in sensitive_df["Account_Number"]:
            self.assertNotIn(acc, summary_json)
        for cc in sensitive_df["Credit_Card"]:
            self.assertNotIn(cc, summary_json)
        for txn in sensitive_df["Transaction_ID"]:
            self.assertNotIn(txn, summary_json)

        # 4. Verify confidential business notes are excluded
        for note in sensitive_df["Internal_Notes"]:
            self.assertNotIn(note, summary_json)

        # 5. Verify no raw row-level transaction amounts appear as isolated records
        # (Row 5 has Revenue 6789.23, Expense 4412.11; neither appears in summary because Gamma is aggregated as 13789.23 / 8412.11)
        self.assertNotIn("6789.23", summary_json)
        self.assertNotIn("4412.11", summary_json)

        # 6. Verify structural keys: only aggregated metrics and top summaries
        allowed_keys = {
            "financial_summary",
            "top_profitable_products",
            "unprofitable_products",
            "recent_monthly_performance",
            "recent_trend"
        }
        self.assertTrue(set(summary.keys()).issubset(allowed_keys))
        self.assertNotIn("rows", summary)
        self.assertNotIn("records", summary)
        self.assertNotIn("transactions", summary)
        self.assertNotIn("data", summary)

    # -------------------------------------------------------------------------
    # 11. Large-Scale Dataset Privacy & Bounded Size Invariance Test
    # -------------------------------------------------------------------------
    def test_summary_payload_scale_invariance_and_no_raw_records(self):
        """
        Verifies that even with a large dataset (e.g. 500 rows with unique customers),
        the LLM summary payload remains bounded in size O(1) and never contains
        raw row records or customer data.
        """
        agent = AnalyticsAgent()
        agent.gemini_api_key = None
        agent.groq_api_key = None

        # Generate 500 synthetic rows with unique sensitive customer data
        n_rows = 500
        large_df = pd.DataFrame({
            "Date": ["2026-01-15"] * n_rows,
            "Product": [f"Product_{i % 5}" for i in range(n_rows)],
            "Revenue": [100.0 + i for i in range(n_rows)],
            "Expense": [60.0 + i for i in range(n_rows)],
            "Customer_Name": [f"SensitiveCustomer_{i:04d}" for i in range(n_rows)],
            "Customer_Email": [f"user_{i:04d}@privatecompany.com" for i in range(n_rows)],
            "SSN_or_TaxID": [f"999-00-{i:04d}" for i in range(n_rows)],
        })

        metrics = agent._compute_metrics(large_df)
        summary = agent._generate_compact_summary(large_df, metrics)
        summary_json = json.dumps(summary)

        # 1. Total transaction count is captured accurately in metadata
        self.assertEqual(summary["financial_summary"]["total_transactions_analyzed"], n_rows)

        # 2. Payload size remains strictly compact (< 1500 chars) regardless of 500 rows
        self.assertLess(
            len(summary_json),
            1500,
            f"Summary payload exceeds compact size limit: {len(summary_json)} chars"
        )

        # 3. None of the 500 customer names or emails appear in the summary
        self.assertNotIn("SensitiveCustomer", summary_json)
        self.assertNotIn("privatecompany.com", summary_json)
        self.assertNotIn("999-00-", summary_json)

        # 4. Top products are capped (at most 3 profitable, at most 3 unprofitable)
        self.assertLessEqual(len(summary.get("top_profitable_products", [])), 3)
        self.assertLessEqual(len(summary.get("unprofitable_products", [])), 3)

    # -------------------------------------------------------------------------
    # 12. Missing Columns & Empty DataFrame Handling
    # -------------------------------------------------------------------------
    def test_empty_dataframe_and_missing_columns(self):
        """Verifies resilience on empty dataframes and missing optional columns."""
        agent = AnalyticsAgent()
        agent.gemini_api_key = None
        agent.groq_api_key = None

        # Empty DataFrame
        empty_res = agent.analyze(pd.DataFrame())
        self.assertEqual(empty_res["total_revenue"], 0.0)
        self.assertEqual(empty_res["total_profit"], 0.0)
        self.assertEqual(empty_res["product_performance"], [])
        self.assertEqual(empty_res["monthly_trends"], [])
        self.assertTrue(len(empty_res["insights"]) > 0)

        # Missing Product and Date columns
        minimal_df = pd.DataFrame({
            "Revenue": [5000.0, 3000.0],
            "Expense": [2000.0, 1000.0]
        })
        min_res = agent.analyze(minimal_df)
        self.assertEqual(min_res["total_revenue"], 8000.0)
        self.assertEqual(min_res["total_profit"], 5000.0)
        self.assertEqual(min_res["product_performance"], [])
        self.assertEqual(min_res["monthly_trends"], [])

    # -------------------------------------------------------------------------
    # 13. Live Gemini Integration Test (Strict Verification, No Rule-Based False Passes)
    # -------------------------------------------------------------------------
    def test_live_gemini_execution_if_available(self):
        """
        Executes live Google Gemini Flash if API key and network connectivity are available.
        Requirements:
          - Skip if API key is unavailable.
          - Skip clearly if network endpoint is unreachable (e.g. sandbox or offline).
          - If key and network are available, verify that Gemini actually succeeds.
          - Do NOT allow rule-based fallback to make this live integration test pass.
          - Handle network / provider failures clearly (e.g. 429 quota exhaustion, 503).
        """
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key or not api_key.strip() or api_key.strip().startswith("mock"):
            self.skipTest("Live Gemini test skipped: GEMINI_API_KEY is not configured in environment.")

        # Probe network connectivity to Google Generative AI host before attempting invocation.
        try:
            with socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=3.0):
                pass
        except (socket.timeout, OSError) as conn_err:
            self.skipTest(
                f"Live Gemini test skipped: Network connection to Google API host is unreachable ({conn_err}). "
                "Run test outside sandbox or with network access enabled for live verification."
            )

        agent = AnalyticsAgent(gemini_api_key=api_key, timeout=25.0)
        metrics = agent._compute_metrics(self.sample_df)
        summary = agent._generate_compact_summary(self.sample_df, metrics)

        # Directly invoke Gemini LLM to distinguish provider limits (quota/rate-limit) from actual code failures
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=agent.gemini_model,
            api_key=agent.gemini_api_key,
            temperature=0.2,
            max_output_tokens=800,
            timeout=agent.timeout,
        )
        structured_llm = llm.with_structured_output(AnalyticsLLMOutput)
        prompt_text = (
            "Analyze this financial summary and return structured business insights and recommendations:\n"
            f"{json.dumps(summary, indent=2)}"
        )

        try:
            raw_response = structured_llm.invoke(prompt_text)
        except Exception as provider_err:
            err_msg = str(provider_err)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                self.skipTest(
                    f"Live Gemini test skipped: Provider free-tier quota/rate-limit exceeded ({err_msg}). "
                    "Handle network/provider failures clearly per test specification."
                )
            elif "503" in err_msg or "unavailable" in err_msg.lower():
                self.skipTest(f"Live Gemini test skipped: Provider service temporarily unavailable (503): {err_msg}")
            else:
                self.fail(f"Live Gemini invocation failed unexpectedly: {err_msg}")

        # Verify structured response output validation succeeds
        validated = agent._validate_llm_output(raw_response)
        self.assertIsNotNone(
            validated,
            "Live Gemini integration test failed: Output validation returned None. "
            "Rule-based fallback is disallowed from making this integration test pass."
        )
        gemini_insights, gemini_recs = validated
        self.assertGreaterEqual(len(gemini_insights), 1, "Gemini generated an empty insights list.")
        self.assertGreaterEqual(len(gemini_recs), 1, "Gemini generated an empty recommendations list.")

        # Verify end-to-end analyze() produces genuine LLM output (not rule-based fallback)
        result = agent.analyze(self.sample_df)
        self.assertEqual(result["total_revenue"], 70000.0)
        self.assertEqual(result["total_profit"], 27000.0)

        static_rule_templates = {
            "Review expenses and identify ways to improve profitability.",
            "Explore opportunities to improve profit margins.",
            "Maintain high-margin product volume while reviewing cost drivers.",
            "Review expense allocations across low-margin periods to improve EBITDA margin.",
            "Optimize inventory and supply chain terms to protect operating cash flow.",
            "Conduct urgent cost restructuring to stop operating losses.",
            "Evaluate pricing strategy and cut non-essential operational expenditure.",
            "Audit product-level contribution margins and discontinue value-destroying items.",
        }

        has_gemini_recs = any(
            rec not in static_rule_templates for rec in result["recommendations"]
        )
        self.assertTrue(
            has_gemini_recs,
            "Live Gemini test failed: All recommendations matched static rule-based templates, "
            "indicating that Gemini silently failed and fell back to rule-based logic."
        )


if __name__ == "__main__":
    unittest.main()
