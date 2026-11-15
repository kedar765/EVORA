"""
Unit and Integration Tests for EVORA LLM-Driven Decision Optimization Agent
==========================================================================
Verifies:
1. LLM-authored recommendations containing all required schema fields:
   recommendation_id, title, recommendation, reasoning, supporting_evidence,
   priority, expected_impact, estimated_financial_impact, implementation_steps,
   associated_risk, assumptions.
2. Deduplication and numerical impact validation (unverified claims stripped).
3. Primary Gemini -> secondary Groq fallback on quota exhaustion / failure.
4. Strict refusal of rule-based recommendations: DecisionLLMUnavailableError
   is raised when all providers fail (NEVER silent rule fallback).
5. FastAPI /decision/recommend returns HTTP 503 Service Unavailable with a clean message
   when LLM providers are unavailable.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from agents.decision_agent import (
    DecisionLLMUnavailableError,
    DecisionOptimizationAgent,
)
from schemas.agent_schemas import (
    DecisionAgentOutput,
    DecisionLLMOutput,
    DecisionRecommendation,
    EvidenceItem,
)


class TestDecisionAgentLLMArchitecture(unittest.TestCase):
    """Test suite ensuring strict LLM reasoning and zero rule fallback."""

    def setUp(self):
        self.sample_analytics = {
            "total_revenue": 23411580.19,
            "total_expenses": 20754621.79,
            "total_profit": 2656958.40,
            "profit_margin": 11.35,
            "key_findings": ["Top segment is Enterprise", "Margin compressed by logistics costs"],
        }
        self.sample_risk = {
            "risk_level": "medium",
            "risk_score": 42.0,
            "anomaly_detected": False,
            "findings": [{"risk_type": "Margin", "severity": "medium", "description": "High logistics expense"}],
        }

    def test_schema_fields_complete(self):
        """Verify DecisionRecommendation contains all specified enterprise fields."""
        rec = DecisionRecommendation(
            recommendation_id="REC-01",
            title="Consolidate Regional Logistics",
            recommendation="Renegotiate carrier tiers to recover 2% net margin.",
            reasoning="Logistics represents 38% of total expenses according to Analytics.",
            supporting_evidence=[
                EvidenceItem(description="Expenses reached 20.75M", metric="Expense", value=20754621.79)
            ],
            priority="high",
            category="Cost Optimization",
            expected_impact="Projected margin expansion of 1.5% - 2.0%",
            estimated_financial_impact=20754621.79,
            implementation_steps=["Audit Q3 freight invoices", "RFP regional carriers"],
            associated_risk="Brief transition friction during carrier migration",
            assumptions=["Freight volume remains stable at 2500 units/mo"],
        )
        self.assertEqual(rec.recommendation_id, "REC-01")
        self.assertEqual(rec.title, "Consolidate Regional Logistics")
        self.assertEqual(rec.priority, "high")
        self.assertEqual(rec.associated_risk, rec.risks_and_tradeoffs)
        self.assertEqual(len(rec.implementation_steps), 2)
        self.assertEqual(len(rec.assumptions), 1)

    @patch("agents.decision_agent.resolve_active_gemini_model", return_value="gemini-4-argon")
    @patch("agents.decision_agent.ModelQuotaManager.is_exhausted", return_value=(False, None))
    @patch("agents.decision_agent.create_gemini_chat_model")
    def test_recommend_success_via_gemini(self, mock_create_gemini, _mock_exhausted, _mock_model):
        """Verify successful LLM generation populates structured recommendations."""
        mock_llm = MagicMock()
        mock_create_gemini.return_value = mock_llm

        mock_llm_output = DecisionLLMOutput(
            analysis_status="completed",
            overall_priority="high",
            recommended_strategy="Targeted Operating Expense Rationalization",
            alternative_strategies=["Price Realization", "Volume Expansion"],
            recommendations=[
                DecisionRecommendation(
                    recommendation_id="REC-01",
                    title="Optimize Freight & Handling",
                    recommendation="Transition fulfillment to tier-1 regional contract.",
                    reasoning="Analytics indicates expenses of 20.75M against 23.41M revenue.",
                    supporting_evidence=[
                        EvidenceItem(description="Total Expenses", metric="Expense", value=20754621.79)
                    ],
                    priority="high",
                    category="Cost Optimization",
                    expected_impact="Reduces operating expenses",
                    estimated_financial_impact=20754621.79,
                    implementation_steps=["Step 1: Benchmark rates", "Step 2: Renegotiate contracts"],
                    associated_risk="Short-term supplier re-alignment",
                    assumptions=["Carrier capacity available"],
                )
            ],
            expected_outcome="Margin improvement from 11.3% toward 13.5%",
            assumptions=["Market demand remains stable"],
            summary="Strategic plan focused on operational efficiencies.",
        )

        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_llm_output
        mock_llm.with_structured_output.return_value = mock_structured

        agent = DecisionOptimizationAgent(gemini_api_key="test-key")
        result = agent.recommend(
            analytics=self.sample_analytics,
            risk=self.sample_risk,
        )

        self.assertEqual(result["priority"], "HIGH")
        self.assertEqual(result["recommended_strategy"], "Targeted Operating Expense Rationalization")
        self.assertEqual(len(result["recommendations"]), 1)
        self.assertIn("structured_recommendations", result)
        self.assertEqual(len(result["structured_recommendations"]), 1)
        
        rec_card = result["structured_recommendations"][0]
        self.assertEqual(rec_card["recommendation_id"], "REC-01")
        self.assertEqual(rec_card["title"], "Optimize Freight & Handling")
        self.assertEqual(rec_card["priority"], "high")
        self.assertEqual(rec_card["estimated_financial_impact"], 20754621.79)
        self.assertEqual(len(rec_card["implementation_steps"]), 2)
        self.assertIn("associated_risk", rec_card)

    @patch("agents.decision_agent.resolve_active_gemini_model", return_value="gemini-4-argon")
    @patch("agents.decision_agent.ModelQuotaManager.is_exhausted", return_value=(False, None))
    @patch("agents.decision_agent.create_gemini_chat_model")
    @patch("agents.decision_agent.create_groq_chat_model")
    def test_gemini_failure_falls_back_to_groq(
        self,
        mock_create_groq,
        mock_create_gemini,
        _mock_exhausted,
        _mock_model,
    ):
        """Verify seamless failover from Gemini to Groq when Gemini raises quota error."""
        # Gemini fails
        mock_gemini = MagicMock()
        mock_create_gemini.return_value = mock_gemini
        mock_gemini.with_structured_output.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")

        # Groq succeeds
        mock_groq = MagicMock()
        mock_create_groq.return_value = mock_groq
        mock_groq_output = DecisionLLMOutput(
            analysis_status="completed",
            overall_priority="medium",
            recommended_strategy="Groq Fallback Strategy",
            recommendations=[
                DecisionRecommendation(
                    recommendation_id="REC-01",
                    title="Groq Plan",
                    recommendation="Action from Groq LLM",
                    reasoning="Reasoning from Groq LLM",
                    priority="medium",
                    supporting_evidence=[
                        EvidenceItem(description="Revenue referenced", metric="Revenue", value=23411580.19)
                    ],
                )
            ],
        )
        mock_groq_struct = MagicMock()
        mock_groq_struct.invoke.return_value = mock_groq_output
        mock_groq.with_structured_output.return_value = mock_groq_struct

        agent = DecisionOptimizationAgent(gemini_api_key="gemini-key", groq_api_key="groq-key")
        result = agent.recommend(
            analytics=self.sample_analytics,
            risk=self.sample_risk,
        )

        self.assertEqual(result["priority"], "MEDIUM")
        self.assertEqual(result["recommended_strategy"], "Groq Fallback Strategy")
        self.assertEqual(len(result["recommendations"]), 1)

    @patch("agents.decision_agent.resolve_active_gemini_model", return_value="gemini-4-argon")
    @patch("agents.decision_agent.ModelQuotaManager.is_exhausted", return_value=(False, None))
    @patch("agents.decision_agent.create_gemini_chat_model")
    @patch("agents.decision_agent.create_groq_chat_model")
    def test_strict_refusal_of_rule_based_fallback(
        self,
        mock_create_groq,
        mock_create_gemini,
        _mock_exhausted,
        _mock_model,
    ):
        """
        Critical architectural verification:
        When both Gemini and Groq fail, the Decision Agent MUST raise DecisionLLMUnavailableError.
        It must NEVER silently revert to deterministic/rule-based recommendations.
        """
        mock_gemini = MagicMock()
        mock_create_gemini.return_value = mock_gemini
        mock_gemini.with_structured_output.side_effect = RuntimeError("Gemini Quota Exceeded")

        mock_groq = MagicMock()
        mock_create_groq.return_value = mock_groq
        mock_groq.with_structured_output.side_effect = RuntimeError("Groq Rate Limit")

        agent = DecisionOptimizationAgent(gemini_api_key="gemini-key", groq_api_key="groq-key")

        with self.assertRaises(DecisionLLMUnavailableError) as ctx:
            agent.recommend(
                analytics=self.sample_analytics,
                risk=self.sample_risk,
            )

        self.assertIn("No LLM generated a valid decision", str(ctx.exception))

    def test_numerical_validation_strips_hallucinated_claims(self):
        """Verify unverified numbers in recommendations are removed to protect financial accuracy."""
        recs = [
            DecisionRecommendation(
                recommendation_id="REC-01",
                title="Unverified claim",
                recommendation="Save arbitrary amount",
                reasoning="Arbitrary reasoning",
                priority="low",
                supporting_evidence=[EvidenceItem(description="Context evidence")],
                estimated_financial_impact=9999999.99,  # Hallucinated number
            ),
            DecisionRecommendation(
                recommendation_id="REC-02",
                title="Verified claim",
                recommendation="Verified reduction",
                reasoning="Matches evidence",
                priority="high",
                supporting_evidence=[EvidenceItem(description="Context evidence")],
                estimated_financial_impact=2656958.40,  # Exact total_profit from analytics
            ),
        ]
        verified_numbers = [23411580.19, 20754621.79, 2656958.40]

        deduped = DecisionOptimizationAgent._deduplicate_recommendations(recs, verified_numbers)

        self.assertEqual(len(deduped), 2)
        # REC-01 impact should have been stripped
        self.assertIsNone(deduped[0].estimated_financial_impact)
        self.assertIn("omitted because it could not be matched", deduped[0].expected_impact)
        # REC-02 impact matches verified numbers so it is preserved
        self.assertEqual(deduped[1].estimated_financial_impact, 2656958.40)

    @patch("backend.main.decision_agent.recommend")
    def test_fastapi_decision_recommend_returns_503_on_llm_unavailable(self, mock_recommend):
        """Verify get_decision_recommendations raises HTTP 503 when Decision LLM is unavailable."""
        from fastapi import HTTPException
        from backend.main import DecisionRecommendationRequest, get_decision_recommendations

        mock_recommend.side_effect = DecisionLLMUnavailableError("No LLM provider is available.")

        with self.assertRaises(HTTPException) as ctx:
            get_decision_recommendations(
                data=DecisionRecommendationRequest(
                    analytics=self.sample_analytics,
                    risk=self.sample_risk,
                ),
                user={"id": "test-user-id"},
            )

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("EVORA Decision AI is currently unavailable", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
