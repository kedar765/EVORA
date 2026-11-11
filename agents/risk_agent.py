"""
EVORA Risk Agent
================
Multi-agent risk identification, anomaly detection, and operational risk scoring agent.
Integrates:
- IsolationForest anomaly detection
- Financial risk scoring
- Revenue drop and expense inflation pattern analysis
- Forward-looking profit risk estimation
- Exact preservation of existing `RiskAgent.analyze()` contract.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from agents.config import create_gemini_chat_model, get_risk_model, ModelQuotaManager
from schemas.agent_schemas import EvidenceItem, RiskAgentOutput, RiskFinding
from tools.risk_tools import (
    RISK_TOOLS,
    analyze_expense_growth,
    analyze_revenue_drops,
    calculate_risk_score,
    detect_anomalies,
    explain_risk_records,
    forecast_business_risks,
    identify_loss_patterns,
)

_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE, override=False)

logger = logging.getLogger("evora.risk_agent")


class RiskAgent:
    """
    EVORA Risk Agent combining ML-based anomaly detection, financial stress testing,
    and strategic risk scoring.
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
        self.gemini_model = gemini_model or get_risk_model()
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.timeout = float(timeout or os.getenv("LLM_TIMEOUT") or 25.0)

    # -------------------------------------------------------------------------
    # 1. Preserved Legacy Interface (Exact Backward Compatibility)
    # -------------------------------------------------------------------------

    def analyze(
        self,
        predicted_profit: float,
        anomaly_detected: bool,
        risk_score: float,
        risk_level: str,
    ) -> Dict[str, Any]:
        """
        Original rule-based risk evaluation interface.
        Preserved strictly for backward compatibility with /upload and /analyze-risk.
        """
        reasons = []

        if anomaly_detected:
            reasons.append("An unusual business pattern was detected.")
        else:
            reasons.append("No unusual business pattern was detected.")

        if predicted_profit < 0:
            reasons.append("Predicted profit is negative.")
        elif predicted_profit == 0:
            reasons.append("Predicted profit is at break-even.")
        else:
            reasons.append("Predicted profit is positive.")

        if risk_score > 60:
            reasons.append("The calculated risk score indicates a high-risk condition.")
        elif risk_score > 30:
            reasons.append("The calculated risk score indicates a medium-risk condition.")
        else:
            reasons.append("The calculated risk score indicates a low-risk condition.")

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "predicted_profit": predicted_profit,
            "anomaly_detected": anomaly_detected,
            "reasons": reasons,
        }

    # -------------------------------------------------------------------------
    # 2. Multi-Agent Workflow Interface (LangChain Tool-Calling Agent)
    # -------------------------------------------------------------------------

    def get_llm(self) -> Any:
        """Resolves the LLM for the Risk Agent according to tiered fallback strategy."""
        if os.getenv("EVORA_SKIP_EXTERNAL_LLM", "0") == "1":
            return RiskToolCallingModel(agent_instance=self)

        is_exhausted, _ = ModelQuotaManager.is_exhausted(self.gemini_model)
        if not is_exhausted and self.gemini_api_key:
            try:
                return create_gemini_chat_model(
                    model_name=self.gemini_model,
                    api_key=self.gemini_api_key,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize ChatGoogleGenerativeAI for RiskAgent: {e}")
                if ModelQuotaManager.is_quota_error(e):
                    ModelQuotaManager.mark_exhausted(self.gemini_model, str(e))
        elif is_exhausted:
            logger.info("Risk Agent: Model %s is marked quota-exhausted; skipping direct LLM call.", self.gemini_model)

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
                logger.warning(f"Failed to initialize ChatGroq for RiskAgent: {e}")

        return RiskToolCallingModel(agent_instance=self)

    def build_langchain_agent(self, llm: Optional[Any] = None) -> Any:
        """Constructs a real LangChain tool-calling agent using create_agent."""
        from langchain.agents import create_agent

        system_prompt = (
            "You are the EVORA Risk Agent, an expert diagnostic AI identifying business risks.\n"
            "You have access to 7 specialized risk tools including Isolation Forest anomaly detection.\n"
            "Analyze business data risks by invoking the appropriate tools using dataset_id and user_id.\n"
            "Do not guess numbers; use the tools to inspect real calculations, drops, and anomalies.\n"
            "Synthesize your findings into structured, evidence-based risk findings."
        )

        model = llm or self.get_llm()
        return create_agent(model=model, tools=RISK_TOOLS, system_prompt=system_prompt)

    def run_agent(
        self,
        dataset_id: str,
        user_id: str,
        analytics_context: Optional[Dict[str, Any]] = None,
        user_query: str = "",
    ) -> RiskAgentOutput:
        """
        Executes genuine LangChain tool-backed risk identification.
        Consumes analytics context, detects anomalies, assesses financial risks,
        and returns validated RiskAgentOutput schema.
        """
        from langchain_core.messages import HumanMessage, ToolMessage

        analytics_ctx = analytics_context or {}
        analytics_summary = (
            f"Analytics Context: Revenue={analytics_ctx.get('total_revenue', 'N/A')}, "
            f"Expenses={analytics_ctx.get('total_expenses', 'N/A')}, "
            f"NetProfit={analytics_ctx.get('total_profit', 'N/A')}, "
            f"Margin={analytics_ctx.get('profit_margin', 'N/A')}%"
        )

        prompt = (
            f"Dataset ID: {dataset_id}\n"
            f"User ID: {user_id}\n"
            f"{analytics_summary}\n"
            f"User Question: {user_query or 'Perform a diagnostic risk assessment and anomaly detection.'}"
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
            fallback_model = RiskToolCallingModel(agent_instance=self)
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
                logger.warning(f"Primary LangChain risk agent ({self.gemini_model}) invocation failed ({e}); checking fallback.")
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
                    fallback_model = RiskToolCallingModel(agent_instance=self)
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

        # 3. Ensure core risk calculations exist
        risk_data = tool_results.get("calculate_risk_score")
        if not risk_data or not isinstance(risk_data, dict):
            risk_score_raw = calculate_risk_score.invoke({"dataset_id": dataset_id, "user_id": user_id})
            risk_data = json.loads(risk_score_raw)

        anomaly_data = tool_results.get("detect_anomalies")
        if not anomaly_data or not isinstance(anomaly_data, dict):
            anomaly_raw = detect_anomalies.invoke({"dataset_id": dataset_id, "user_id": user_id})
            anomaly_data = json.loads(anomaly_raw)

        expense_data = tool_results.get("analyze_expense_growth") or {}
        loss_data = tool_results.get("identify_loss_patterns") or {}
        forecast_data = tool_results.get("forecast_business_risks") or {}

        # 4. Parse core findings
        score = float(risk_data.get("risk_score", 5.0))
        level = str(risk_data.get("risk_level", "low")).lower()
        if level not in {"low", "medium", "high", "critical"}:
            level = "low"

        anomaly_detected = bool(anomaly_data.get("anomaly_detected", False))
        anomaly_count = int(anomaly_data.get("anomaly_count", 0))
        pred_profit = risk_data.get("predicted_profit") or forecast_data.get("predicted_mean_profit")

        # 5. Assemble structured findings
        findings_list: List[RiskFinding] = []
        key_risks: List[str] = []
        evidence_items: List[EvidenceItem] = []

        for f in risk_data.get("findings", []):
            sev = f.get("severity", "medium").lower()
            if sev not in {"low", "medium", "high", "critical"}:
                sev = "medium"
            findings_list.append(
                RiskFinding(
                    risk_type=f.get("risk_type", "General Risk"),
                    severity=sev,
                    description=f.get("description", ""),
                    recommended_action=f.get("recommended_action"),
                )
            )
            key_risks.append(f.get("description", ""))

        if anomaly_detected:
            evidence_items.append(
                EvidenceItem(
                    description=f"{anomaly_count} transactions flagged as statistical/ML pattern anomalies.",
                    metric="anomaly_count",
                    value=anomaly_count,
                    source="detect_anomalies",
                )
            )

        if loss_data.get("loss_generating_records_count", 0) > 0:
            neg_prof = loss_data.get("total_negative_profit", 0.0)
            loss_cnt = loss_data.get("loss_generating_records_count")
            findings_list.append(
                RiskFinding(
                    risk_type="Loss-Generating Transactions",
                    severity="high" if abs(neg_prof) > 10000 else "medium",
                    description=f"Identified {loss_cnt} unprofitable transactions contributing ₹{abs(neg_prof):,.2f} in net losses.",
                    recommended_action="Audit pricing and vendor costs on unprofitable SKUs.",
                )
            )
            key_risks.append(f"Identified {loss_cnt} loss-generating transaction records.")

        if not key_risks:
            key_risks.append("No critical risk patterns or structural anomalies were identified.")

        summary_text = (
            f"Financial risk score assessed at {score:.1f}/100 ({level.upper()} RISK). "
            f"Operational anomalies: {'Detected (' + str(anomaly_count) + ')' if anomaly_detected else 'None'}. "
            f"Cost structure evaluation: {expense_data.get('cost_control_risk', 'normal')} risk."
        )

        return RiskAgentOutput(
            risk_score=score,
            risk_level=level,  # type: ignore
            anomaly_detected=anomaly_detected,
            anomaly_count=anomaly_count,
            predicted_profit=pred_profit,
            findings=findings_list,
            key_risks=key_risks,
            evidence=evidence_items,
            summary=summary_text,
            model_used=model_used,
            execution_mode=execution_mode,
            model_error=model_error,
        )


class RiskToolCallingModel:
    """
    Deterministic tool-calling chat model for the Risk Agent.
    Implements bind_tools to integrate seamlessly with LangChain's create_agent() runner.
    Autonomously selects appropriate tools based on analytical findings and user question.
    """
    def __init__(self, agent_instance: Any = None):
        self.agent_instance = agent_instance
        self.bound_tools: List[Any] = []

    @property
    def _llm_type(self) -> str:
        return "evora_risk_tool_calling_model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "RiskToolCallingModel":
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
            for line in human_text.splitlines():
                if line.startswith("Dataset ID:"):
                    dataset_id = line.split(":", 1)[1].strip()
                elif line.startswith("User ID:"):
                    user_id = line.split(":", 1)[1].strip()

            q_lower = human_text.lower()
            tool_calls = []
            call_id = 1

            # 1. Always evaluate risk score & IsolationForest anomalies
            tool_calls.append({
                "name": "calculate_risk_score",
                "args": {"dataset_id": dataset_id, "user_id": user_id},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            tool_calls.append({
                "name": "detect_anomalies",
                "args": {"dataset_id": dataset_id, "user_id": user_id},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 2. Expense growth analysis
            tool_calls.append({
                "name": "analyze_expense_growth",
                "args": {"dataset_id": dataset_id, "user_id": user_id},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 3. Loss patterns
            tool_calls.append({
                "name": "identify_loss_patterns",
                "args": {"dataset_id": dataset_id, "user_id": user_id},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 4. Forecast risks if indicated or requested
            if any(k in q_lower for k in ["forecast", "future", "outlook", "forward", "predict"]) or not any(k in q_lower for k in ["drop", "anomaly"]):
                tool_calls.append({
                    "name": "forecast_business_risks",
                    "args": {"dataset_id": dataset_id, "user_id": user_id},
                    "id": f"call_{call_id}",
                    "type": "tool_call",
                })
                call_id += 1

            # 5. Revenue drops if indicated
            if any(k in q_lower for k in ["drop", "decline", "fall", "deceleration"]):
                tool_calls.append({
                    "name": "analyze_revenue_drops",
                    "args": {"dataset_id": dataset_id, "user_id": user_id},
                    "id": f"call_{call_id}",
                    "type": "tool_call",
                })
                call_id += 1

            # 6. Granular anomaly records explanation if requested
            if any(k in q_lower for k in ["explain", "suspicious", "flagged", "detail"]):
                tool_calls.append({
                    "name": "explain_risk_records",
                    "args": {"dataset_id": dataset_id, "user_id": user_id, "limit": 5},
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

        risk_data = tool_results_map.get("calculate_risk_score", {})
        score = risk_data.get("risk_score", 0.0)
        level = risk_data.get("risk_level", "low").upper()
        synthesis = f"Risk assessment completed. Overall risk score: {score:.1f}/100 ({level} RISK)."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=synthesis))])

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        messages = input if isinstance(input, list) else input.get("messages", [])
        return self._generate(messages).generations[0].message


def create_risk_agent(
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
) -> RiskAgent:
    """Factory creating a RiskAgent instance."""
    return RiskAgent(gemini_api_key=gemini_api_key, groq_api_key=groq_api_key)