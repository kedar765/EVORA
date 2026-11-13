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

from agents.config import (
    GROQ_DEFAULT_MODEL,
    ModelQuotaManager,
    create_gemini_chat_model,
    get_decision_model,
)
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
        self.gemini_model = gemini_model or get_decision_model()
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", GROQ_DEFAULT_MODEL)
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

    def get_llm(self) -> Any:
        """Resolves the LLM for the Decision Agent according to tiered fallback strategy."""
        if os.getenv("EVORA_SKIP_EXTERNAL_LLM", "0") == "1":
            return DecisionToolCallingModel(agent_instance=self)

        is_exhausted, _ = ModelQuotaManager.is_exhausted(self.gemini_model)
        if not is_exhausted and self.gemini_api_key:
            try:
                return create_gemini_chat_model(
                    model_name=self.gemini_model,
                    api_key=self.gemini_api_key,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize ChatGoogleGenerativeAI for DecisionAgent: {e}")
                if ModelQuotaManager.is_quota_error(e):
                    ModelQuotaManager.mark_exhausted(self.gemini_model, str(e))
        elif is_exhausted:
            logger.info("Decision Agent: Model %s is marked quota-exhausted; skipping direct LLM call.", self.gemini_model)

        if self.groq_api_key:
            try:
                from langchain_groq import ChatGroq
                return ChatGroq(
                    model=self.groq_model,
                    groq_api_key=self.groq_api_key,
                    temperature=0.1,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize ChatGroq for DecisionAgent: {e}")

        return DecisionToolCallingModel(agent_instance=self)

    def build_langchain_agent(self, llm: Optional[Any] = None) -> Any:
        """Constructs a real LangChain tool-calling agent using create_agent."""
        from langchain.agents import create_agent

        system_prompt = (
            "You are the EVORA Decision Optimization Agent, a strategic business intelligence AI.\n"
            "You have access to 6 specialized decision tools to simulate scenarios, evaluate strategies,\n"
            "and construct prioritized tactical action plans.\n"
            "Invoke the appropriate tools using dataset_id and user_id to compute exact financial impacts.\n"
            "Enforce governance: EVORA proposes evidence-backed options, human leadership retains final approval."
        )

        model = llm or self.get_llm()
        return create_agent(model=model, tools=DECISION_TOOLS, system_prompt=system_prompt)

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
        from langchain_core.messages import HumanMessage, ToolMessage

        analytics_ctx = analytics_context or {}
        risk_ctx = risk_context or {}

        risk_level = str(risk_ctx.get("risk_level", "low")).lower()
        if risk_level not in {"low", "medium", "high", "critical"}:
            risk_level = "low"

        context_summary = (
            f"Analytics Context: NetProfit={analytics_ctx.get('total_profit', 'N/A')}, "
            f"Margin={analytics_ctx.get('profit_margin', 'N/A')}%\n"
            f"Risk Context: Score={risk_ctx.get('risk_score', 'N/A')}, Level={risk_level.upper()}"
        )

        prompt = (
            f"Dataset ID: {dataset_id}\n"
            f"User ID: {user_id}\n"
            f"{context_summary}\n"
            f"User Question: {user_query or 'Formulate optimized strategic decisions and scenario simulations.'}"
        )

        # 1. Execute actual LangChain agent
        model_used = self.gemini_model
        execution_mode = "llm"
        model_error: Optional[str] = None

        is_exhausted, exhaust_reason = ModelQuotaManager.is_exhausted(self.gemini_model)
        if is_exhausted or os.getenv("EVORA_SKIP_EXTERNAL_LLM", "0") == "1":
            execution_mode = "deterministic_fallback"
            model_used = f"deterministic_fallback (requested: {self.gemini_model})"
            model_error = exhaust_reason or "External LLM skipped or quota exhausted"
            fallback_model = DecisionToolCallingModel(agent_instance=self)
            fallback_agent = self.build_langchain_agent(llm=fallback_model)
            res = fallback_agent.invoke({"messages": [HumanMessage(content=prompt)]})
        else:
            agent = self.build_langchain_agent()
            try:
                res = agent.invoke({"messages": [HumanMessage(content=prompt)]})
                execution_mode = "llm"
                model_used = self.gemini_model
            except Exception as e:
                model_error = str(e)
                logger.warning(f"Primary LangChain decision agent ({self.gemini_model}) invocation failed ({e}); checking fallback.")
                if ModelQuotaManager.is_quota_error(e):
                    ModelQuotaManager.mark_exhausted(self.gemini_model, str(e))

                groq_succeeded = False
                if self.groq_api_key:
                    try:
                        from langchain_groq import ChatGroq
                        groq_llm = ChatGroq(
                            model=self.groq_model,
                            groq_api_key=self.groq_api_key,
                            temperature=0.1,
                            timeout=self.timeout,
                        )
                        groq_agent = self.build_langchain_agent(llm=groq_llm)
                        res = groq_agent.invoke({"messages": [HumanMessage(content=prompt)]})
                        execution_mode = "groq_fallback"
                        model_used = self.groq_model
                        groq_succeeded = True
                    except Exception as ge:
                        logger.warning(f"Groq fallback failed: {ge}")

                if not groq_succeeded:
                    execution_mode = "deterministic_fallback"
                    model_used = f"deterministic_fallback (requested: {self.gemini_model})"
                    fallback_model = DecisionToolCallingModel(agent_instance=self)
                    fallback_agent = self.build_langchain_agent(llm=fallback_model)
                    res = fallback_agent.invoke({"messages": [HumanMessage(content=prompt)]})

        # 2. Extract tool messages and findings from the agent conversation
        messages = res.get("messages", [])
        tool_results: Dict[str, Any] = {}
        for m in messages:
            if isinstance(m, ToolMessage):
                tool_name = getattr(m, "name", None) or "unknown"
                try:
                    tool_results[tool_name] = json.loads(m.content) if isinstance(m.content, str) else m.content
                except Exception:
                    tool_results[tool_name] = m.content

        # 3. Ensure core decision calculations exist
        strategies_data = tool_results.get("compare_business_strategies")
        if not strategies_data or not isinstance(strategies_data, dict):
            strategies_raw = compare_business_strategies.invoke({"dataset_id": dataset_id, "user_id": user_id})
            strategies_data = json.loads(strategies_raw)

        actions_data = tool_results.get("generate_action_plan")
        if not actions_data or not isinstance(actions_data, dict):
            actions_raw = generate_action_plan.invoke({
                "dataset_id": dataset_id,
                "user_id": user_id,
                "risk_level": risk_level,
                "priority_focus": "balanced",
            })
            actions_data = json.loads(actions_raw)

        # 4. Assemble scenarios
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

        # 5. Assemble structured actions
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

        # 6. Strategy determination
        rec_strategy = strategies_data.get("top_recommended_strategy") or "Balanced Margin Optimization"
        alt_strategies = [
            s.get("strategy_name")
            for s in strategies_data.get("strategies", [])
            if s.get("strategy_name") != rec_strategy
        ]

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
            expected_outcome="Projected strategic upside across evaluated scenarios.",
            assumptions=[
                "Fixed costs remain stable during execution.",
                "Implementation proceeds under human supervisor sign-off.",
            ],
            human_approval_required=True,
            summary=summary_text,
            model_used=model_used,
            execution_mode=execution_mode,
            model_error=model_error,
        )


class DecisionToolCallingModel:
    """
    Deterministic tool-calling chat model for the Decision Optimization Agent.
    Implements bind_tools to integrate seamlessly with LangChain's create_agent() runner.
    Autonomously selects appropriate tools based on Analytics and Risk findings.
    """
    def __init__(self, agent_instance: Any = None):
        self.agent_instance = agent_instance
        self.bound_tools: List[Any] = []

    @property
    def _llm_type(self) -> str:
        return "evora_decision_tool_calling_model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "DecisionToolCallingModel":
        self.bound_tools = list(tools)
        return self

    def _generate(
        self,
        messages: List[Any],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        from langchain_core.messages import AIMessage, ToolMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        # Turn 1: LLM tool selection turn
        if not tool_messages:
            human_text = ""
            for m in reversed(messages):
                if getattr(m, "type", None) == "human" or m.__class__.__name__ == "HumanMessage":
                    human_text = str(m.content)
                    break

            dataset_id = ""
            user_id = ""
            risk_level = "low"

            for line in human_text.splitlines():
                if line.startswith("Dataset ID:"):
                    dataset_id = line.split(":", 1)[1].strip()
                elif line.startswith("User ID:"):
                    user_id = line.split(":", 1)[1].strip()
                elif "Level=" in line:
                    risk_part = line.split("Level=")[1].strip().split()[0].lower()
                    if risk_part in ["low", "medium", "high", "critical"]:
                        risk_level = risk_part

            tool_calls = []
            call_id = 1

            # 1. Compare strategies across pathways
            tool_calls.append({
                "name": "compare_business_strategies",
                "args": {"dataset_id": dataset_id, "user_id": user_id},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 2. Generate action plan adapted to risk level
            tool_calls.append({
                "name": "generate_action_plan",
                "args": {
                    "dataset_id": dataset_id,
                    "user_id": user_id,
                    "risk_level": risk_level,
                    "priority_focus": "cost_containment" if risk_level in ["high", "critical"] else "balanced",
                },
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 3. Scenario simulation
            tool_calls.append({
                "name": "simulate_business_scenario",
                "args": {
                    "dataset_id": dataset_id,
                    "user_id": user_id,
                    "price_change_pct": 5.0,
                    "expense_change_pct": -3.0,
                    "volume_change_pct": 2.0,
                },
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 4. Resource allocation optimization
            tool_calls.append({
                "name": "optimize_resource_allocation",
                "args": {"dataset_id": dataset_id, "user_id": user_id, "reallocation_pct": 10.0},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 5. Strategic options evaluation
            tool_calls.append({
                "name": "evaluate_decision_options",
                "args": {"dataset_id": dataset_id, "user_id": user_id},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=tool_calls))])

        # Turn 2: Synthesize findings from real tool execution results
        tool_results_map: Dict[str, Any] = {}
        for tm in tool_messages:
            tool_name = getattr(tm, "name", None) or "unknown"
            try:
                tool_results_map[tool_name] = json.loads(tm.content) if isinstance(tm.content, str) else tm.content
            except Exception:
                tool_results_map[tool_name] = tm.content

        strat_res = tool_results_map.get("compare_business_strategies", {})
        top_strat = strat_res.get("top_recommended_strategy", "Margin Optimization")
        synthesis = f"Decision analysis concluded. Top recommended pathway: '{top_strat}'."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=synthesis))])

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        messages = input if isinstance(input, list) else input.get("messages", [])
        return self._generate(messages).generations[0].message


def create_decision_agent(
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
) -> DecisionOptimizationAgent:
    """Factory creating a DecisionOptimizationAgent instance."""
    return DecisionOptimizationAgent(gemini_api_key=gemini_api_key, groq_api_key=groq_api_key)
