"""
EVORA Risk Agent
================
Multi-agent risk identification, anomaly detection, and operational risk scoring agent.
Integrates:
- Unsupervised Isolation Forest anomaly detection
- Financial risk scoring and margin stress testing
- Revenue drop and expense inflation pattern analysis
- LangChain create_agent() execution with 7 registered risk tools
- Tiered fallback: Gemini 4 -> Groq (openai/gpt-oss-120b) -> Deterministic ML
- Preserves backward compatibility with RiskAgent.analyze().
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from agents.config import (
    ModelQuotaManager,
    create_gemini_chat_model,
    create_groq_chat_model,
    get_groq_model,
    get_risk_model,
    resolve_active_gemini_model,
)
from schemas.agent_schemas import EvidenceItem, RiskAgentOutput, RiskFinding
from tools.risk_tools import (
    RISK_TOOLS,
    calculate_risk_score,
    detect_anomalies,
)

# Load environment configuration without overriding deployment-provided variables
_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE, override=False)
else:
    load_dotenv(override=False)

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
        self.gemini_model = resolve_active_gemini_model(gemini_model or get_risk_model())
        self.groq_model = groq_model or get_groq_model()
        self.timeout = float(timeout or os.getenv("LLM_TIMEOUT") or 15.0)

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
        """Original rule-based risk evaluation interface preserved for /upload and /analyze-risk."""
        reasons = [
            "An unusual business pattern was detected." if anomaly_detected else "No unusual business pattern was detected.",
            "Predicted profit is negative." if predicted_profit < 0 else (
                "Predicted profit is at break-even." if predicted_profit == 0 else "Predicted profit is positive."
            ),
            "The calculated risk score indicates a high-risk condition." if risk_score > 60 else (
                "The calculated risk score indicates a medium-risk condition." if risk_score > 30 else
                "The calculated risk score indicates a low-risk condition."
            ),
        ]
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
                logger.warning("Failed to initialize Gemini chat model for RiskAgent: %s", e)
                if ModelQuotaManager.is_quota_error(e):
                    ModelQuotaManager.mark_exhausted(self.gemini_model, str(e))

        if self.groq_api_key:
            try:
                return create_groq_chat_model(
                    model_name=self.groq_model,
                    api_key=self.groq_api_key,
                    temperature=0.1,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning("Failed to initialize Groq chat model for RiskAgent: %s", e)

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
        return create_agent(model=llm or self.get_llm(), tools=RISK_TOOLS, system_prompt=system_prompt)

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

        # 1. Tiered Agent Execution Loop
        model_used = self.gemini_model
        execution_mode = "llm"
        model_error: Optional[str] = None
        res: Optional[Dict[str, Any]] = None

        is_exhausted, exhaust_reason = ModelQuotaManager.is_exhausted(self.gemini_model)
        if not is_exhausted and os.getenv("EVORA_SKIP_EXTERNAL_LLM", "0") != "1":
            try:
                primary_agent = self.build_langchain_agent()
                res = primary_agent.invoke({"messages": [HumanMessage(content=prompt)]})
                execution_mode = "llm"
                model_used = self.gemini_model
            except Exception as e:
                model_error = str(e)
                logger.warning("Primary LangChain risk agent (%s) invocation failed (%s); checking fallback.", self.gemini_model, e)
                if ModelQuotaManager.is_quota_error(e):
                    ModelQuotaManager.mark_exhausted(self.gemini_model, str(e))

        # Secondary Tier: Groq fallback
        if res is None and self.groq_api_key:
            try:
                groq_llm = create_groq_chat_model(
                    model_name=self.groq_model,
                    api_key=self.groq_api_key,
                    temperature=0.1,
                    timeout=self.timeout,
                )
                groq_agent = self.build_langchain_agent(llm=groq_llm)
                res = groq_agent.invoke({"messages": [HumanMessage(content=prompt)]})
                execution_mode = "groq_fallback"
                model_used = self.groq_model
            except Exception as ge:
                logger.warning("Groq fallback failed for RiskAgent: %s", ge)

        # Tertiary Tier: Deterministic ML/statistical tool-calling fallback
        if res is None:
            execution_mode = "deterministic_fallback"
            model_used = f"deterministic_fallback (requested: {self.gemini_model})"
            model_error = model_error or exhaust_reason or "External LLM skipped or quota exhausted"
            fallback_agent = self.build_langchain_agent(llm=RiskToolCallingModel(agent_instance=self))
            res = fallback_agent.invoke({"messages": [HumanMessage(content=prompt)]})

        # 2. Extract tool messages from conversation
        messages = res.get("messages", [])
        tool_results: Dict[str, Any] = {}
        for m in messages:
            if isinstance(m, ToolMessage):
                tool_name = getattr(m, "name", None) or "unknown"
                try:
                    tool_results[tool_name] = json.loads(m.content) if isinstance(m.content, str) else m.content
                except Exception:
                    tool_results[tool_name] = m.content

        # 3. Ensure core risk calculations and anomalies are present
        risk_data = tool_results.get("calculate_risk_score")
        if not risk_data or not isinstance(risk_data, dict):
            risk_data = json.loads(calculate_risk_score.invoke({"dataset_id": dataset_id, "user_id": user_id}))

        anomaly_data = tool_results.get("detect_anomalies")
        if not anomaly_data or not isinstance(anomaly_data, dict):
            anomaly_data = json.loads(detect_anomalies.invoke({"dataset_id": dataset_id, "user_id": user_id}))

        expense_data = tool_results.get("analyze_expense_growth") or {}
        loss_data = tool_results.get("identify_loss_patterns") or {}
        forecast_data = tool_results.get("forecast_business_risks") or {}

        # 4. Parse core findings and levels
        score = float(risk_data.get("risk_score", 5.0))
        level = str(risk_data.get("risk_level", "low")).lower()
        if level not in {"low", "medium", "high", "critical"}:
            level = "low"

        anomaly_detected = bool(anomaly_data.get("anomaly_detected", False))
        anomaly_count = int(anomaly_data.get("anomaly_count", 0))
        pred_profit = risk_data.get("predicted_profit") or forecast_data.get("predicted_mean_profit")

        # 5. Assemble structured findings and evidence items
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
                    description=f"{anomaly_count} transactions flagged as statistical IsolationForest pattern anomalies.",
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
    Autonomously executes all 7 specialized risk tools.
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

        # Turn 1: LLM tool selection turn - invokes the 7 risk tools
        if not tool_messages:
            human_text = ""
            for m in reversed(messages):
                if getattr(m, "type", None) == "human" or m.__class__.__name__ == "HumanMessage":
                    human_text = str(m.content)
                    break

            dataset_id, user_id = "", ""
            for line in human_text.splitlines():
                if line.startswith("Dataset ID:"):
                    dataset_id = line.split(":", 1)[1].strip()
                elif line.startswith("User ID:"):
                    user_id = line.split(":", 1)[1].strip()

            tool_definitions = [
                ("calculate_risk_score", {"dataset_id": dataset_id, "user_id": user_id}),
                ("detect_anomalies", {"dataset_id": dataset_id, "user_id": user_id}),
                ("analyze_expense_growth", {"dataset_id": dataset_id, "user_id": user_id}),
                ("identify_loss_patterns", {"dataset_id": dataset_id, "user_id": user_id}),
                ("forecast_business_risks", {"dataset_id": dataset_id, "user_id": user_id}),
                ("analyze_revenue_drops", {"dataset_id": dataset_id, "user_id": user_id}),
                ("explain_risk_records", {"dataset_id": dataset_id, "user_id": user_id, "limit": 5}),
            ]
            tool_calls = [
                {
                    "name": name,
                    "args": args,
                    "id": f"call_{idx}",
                    "type": "tool_call",
                }
                for idx, (name, args) in enumerate(tool_definitions, 1)
            ]
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
