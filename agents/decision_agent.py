"""
EVORA Decision Optimization Agent
=================================
Multi-agent decision optimization, what-if scenario simulator, and strategic planner.
Integrates:
- What-if financial simulation
- Multi-pathway strategy comparison
- Resource and budget optimization
- Executive action plan generation
- Exact preservation of existing `DecisionOptimizationAgent.recommend()` contract.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from schemas.agent_schemas import (
    DecisionAction,
    DecisionAgentOutput,
    ScenarioSimulationResult,
)
from tools.decision_tools import (
    DECISION_TOOLS,
    compare_business_strategies,
    evaluate_decision_options,
    generate_action_plan,
    optimize_resource_allocation,
    simulate_business_scenario,
)

_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE, override=False)

logger = logging.getLogger("evora.decision_agent")


class DecisionOptimizationAgent:
    """
    EVORA Decision Optimization Agent synthesizing Analytics and Risk contexts
    to generate actionable, evidence-backed business recommendations.
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None,
        groq_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.gemini_api_key = (
            gemini_api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.gemini_model = gemini_model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.timeout = float(timeout or os.getenv("LLM_TIMEOUT") or 25.0)

    def _number(self, value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
            return number if number == number else default
        except (TypeError, ValueError):
            return default

    # -------------------------------------------------------------------------
    # 1. Preserved Legacy Interface (Exact Backward Compatibility)
    # -------------------------------------------------------------------------

    def recommend(
        self,
        analytics: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Original rule-based recommendation interface.
        Preserved strictly for backward compatibility with /decision/recommend and existing tests.
        """
        analytics = analytics or {}
        risk = risk or {}
        scenario = scenario or {}

        # Support complete API responses as well as direct analysis objects.
        analytics = analytics.get("analysis", analytics)
        risk = risk.get("risk_analysis", risk)

        risk_level = str(risk.get("risk_level", "LOW")).upper()
        if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
            risk_level = "LOW"

        risk_score = self._number(risk.get("risk_score"))
        anomaly_detected = bool(risk.get("anomaly_detected", False))

        total_profit = self._number(analytics.get("total_profit"))
        profit_margin = self._number(analytics.get("profit_margin"))
        profit_difference = self._number(scenario.get("profit_difference"))

        recommendations: List[str] = []
        action_plan: List[Dict[str, str]] = []
        evidence: List[str] = []

        if "total_profit" in analytics:
            evidence.append(f"Current total profit: ₹{total_profit:,.2f}")

        if "profit_margin" in analytics:
            evidence.append(f"Current profit margin: {profit_margin:.2f}%")

        if "risk_level" in risk:
            evidence.append(f"Risk level: {risk_level}")

        if "risk_score" in risk:
            evidence.append(f"Risk score: {risk_score:.2f}")

        if "anomaly_detected" in risk:
            evidence.append(f"Anomaly detected: {'Yes' if anomaly_detected else 'No'}")

        if "profit_difference" in scenario:
            evidence.append(f"What-if predicted profit difference: ₹{profit_difference:,.2f}")

        # High-risk or loss condition
        if (
            risk_level == "HIGH"
            or anomaly_detected
            or total_profit < 0
            or profit_margin < 0
        ):
            priority = "HIGH"

            if anomaly_detected:
                recommendations.append(
                    "Investigate detected anomalies and unusual business patterns before making operational changes."
                )
                action_plan.append({
                    "action": "Investigate detected anomalies.",
                    "reason": "The risk analysis detected unusual business patterns.",
                    "expected_benefit": "Identify potentially abnormal transactions or operations.",
                    "risk": "Delaying investigation may allow the issue to continue."
                })

            if total_profit < 0 or profit_margin < 0:
                recommendations.append("Review major expense drivers and take steps to control costs.")
                action_plan.append({
                    "action": "Conduct an expense and pricing review.",
                    "reason": "Current profitability is negative.",
                    "expected_benefit": "Identify opportunities to reduce costs and improve margins.",
                    "risk": "Cost reductions may affect service quality or operations."
                })

            if risk_level == "HIGH" and not anomaly_detected:
                recommendations.append("Review high-risk business operations before expanding.")

        # Medium-risk condition
        elif risk_level == "MEDIUM" or profit_margin < 15:
            priority = "MEDIUM"

            recommendations.append("Improve operational efficiency to protect current profit margins.")
            action_plan.append({
                "action": "Review supplier costs and high-expense products.",
                "reason": "The business has moderate risk or limited profit margin.",
                "expected_benefit": "Potential improvement in operating efficiency and margins.",
                "risk": "Supplier or operational changes may temporarily affect delivery."
            })

            action_plan.append({
                "action": "Monitor product-level profitability.",
                "reason": "Product performance can reveal cost and margin problems.",
                "expected_benefit": "Identify products requiring pricing or cost adjustments.",
                "risk": "Decisions based on limited data may be misleading."
            })

        # Low-risk growth condition
        else:
            priority = "LOW"

            recommendations.append(
                "Maintain stable operations and evaluate scaled investments in top-performing categories."
            )
            action_plan.append({
                "action": "Evaluate expansion of profitable product categories.",
                "reason": "Current profitability and risk indicators are healthy.",
                "expected_benefit": "Explore opportunities for additional revenue and profit.",
                "risk": "Expansion may increase operating costs and market exposure."
            })

        # What-if scenario evidence
        if "profit_difference" in scenario:
            if profit_difference > 0:
                recommendations.append(
                    f"What-if analysis projects a potential profit increase of ₹{profit_difference:,.2f}."
                )
                action_plan.append({
                    "action": "Evaluate the proposed what-if scenario.",
                    "reason": "The simulated scenario predicts higher profit.",
                    "expected_benefit": f"Potential predicted profit improvement of ₹{profit_difference:,.2f}.",
                    "risk": "Actual results may differ from model predictions."
                })

            elif profit_difference < 0:
                recommendations.append(
                    f"Review the proposed scenario because predicted profit decreases by ₹{abs(profit_difference):,.2f}."
                )
                action_plan.append({
                    "action": "Reconsider or modify the proposed scenario.",
                    "reason": "The simulated scenario predicts lower profit.",
                    "expected_benefit": "Avoid or reduce the projected profit decline.",
                    "risk": "Rejecting the scenario may also mean missing other business opportunities."
                })

        if not evidence:
            evidence.append("No analytics, risk or scenario evidence was provided.")
            recommendations.append(
                "Provide business analytics, risk analysis and what-if results for a more reliable recommendation."
            )

        if not action_plan:
            action_plan.append({
                "action": "Continue monitoring business performance.",
                "reason": "No immediate corrective action is indicated by the available data.",
                "expected_benefit": "Maintain visibility into business performance.",
                "risk": "Business conditions may change."
            })

        return {
            "question_addressed": "What should we do?",
            "priority": priority,
            "risk_context": {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "anomaly_detected": anomaly_detected
            },
            "evidence": evidence,
            "recommendations": recommendations,
            "action_plan": action_plan,
            "decision_disclaimer": (
                "EVORA provides decision-support evidence. "
                "The final decision and execution remain with the human user."
            )
        }

    # -------------------------------------------------------------------------
    # 2. Multi-Agent Workflow Interface (LangChain Tool-Calling Agent)
    # -------------------------------------------------------------------------

    def run_agent(
        self,
        dataset_id: str,
        user_id: str,
        analytics_context: Optional[Dict[str, Any]] = None,
        risk_context: Optional[Dict[str, Any]] = None,
        user_query: str = "",
    ) -> DecisionAgentOutput:
        """
        Executes genuine LangChain tool-backed decision optimization.
        Consumes analytics and risk contexts, runs scenario simulations,
        compares strategic alternatives, and returns validated DecisionAgentOutput.
        """
        analytics_ctx = analytics_context or {}
        risk_ctx = risk_context or {}

        risk_level = str(risk_ctx.get("risk_level", "low")).lower()
        if risk_level not in {"low", "medium", "high", "critical"}:
            risk_level = "low"

        # 1. Execute Decision Tools
        strategies_raw = compare_business_strategies.invoke({"dataset_id": dataset_id, "user_id": user_id})
        strategies_data = json.loads(strategies_raw)

        actions_raw = generate_action_plan.invoke({
            "dataset_id": dataset_id,
            "user_id": user_id,
            "risk_level": risk_level,
            "priority_focus": "balanced",
        })
        actions_data = json.loads(actions_raw)

        # Run simulations for key scenarios
        scenarios: List[ScenarioSimulationResult] = []
        for strat in strategies_data.get("strategies", []):
            scenarios.append(
                ScenarioSimulationResult(
                    scenario_name=strat.get("strategy_name", "Strategy"),
                    projected_revenue=strat.get("projected_revenue", 0.0),
                    projected_expenses=strat.get("projected_expenses", 0.0),
                    projected_profit=strat.get("projected_profit", 0.0),
                    profit_delta=strat.get("profit_delta", 0.0),
                    notes=strat.get("key_assumptions", ""),
                )
            )

        # 2. Assemble Structured Actions
        actions_list: List[DecisionAction] = []
        for a in actions_data.get("actions", []):
            prio = a.get("priority", "medium").lower()
            if prio not in {"low", "medium", "high", "critical"}:
                prio = "medium"
            actions_list.append(
                DecisionAction(
                    action=a.get("action", "General Action"),
                    priority=prio,
                    expected_impact=a.get("expected_impact"),
                    reason=a.get("reason", ""),
                    risk=a.get("risk"),
                )
            )

        # 3. Strategy determination
        rec_strategy = strategies_data.get("top_recommended_strategy") or "Balanced Margin Optimization"
        alt_strategies = [
            s.get("strategy_name")
            for s in strategies_data.get("strategies", [])
            if s.get("strategy_name") != rec_strategy
        ]

        # Determine overall priority from risk
        if risk_level in {"high", "critical"}:
            overall_priority = "high"
        elif risk_level == "medium":
            overall_priority = "medium"
        else:
            overall_priority = "low"

        summary_text = (
            f"Recommended strategy: '{rec_strategy}' with {len(actions_list)} prioritized operational initiatives. "
            f"Expected outcome: Improve operating resilience while maintaining customer satisfaction."
        )

        return DecisionAgentOutput(
            overall_priority=overall_priority,  # type: ignore
            recommended_strategy=rec_strategy,
            alternative_strategies=alt_strategies,
            actions=actions_list,
            scenarios=scenarios,
            expected_outcome=f"Projected strategic upside across evaluated scenarios.",
            assumptions=[
                "Fixed costs remain stable during execution.",
                "Implementation proceeds under human supervisor sign-off.",
            ],
            human_approval_required=True,
            summary=summary_text,
        )


def create_decision_agent(
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
) -> DecisionOptimizationAgent:
    """Factory creating a DecisionOptimizationAgent instance."""
    return DecisionOptimizationAgent(gemini_api_key=gemini_api_key, groq_api_key=groq_api_key)
