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
        self.gemini_model = gemini_model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
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
        # 1. Execute deterministic risk tools
        risk_score_raw = calculate_risk_score.invoke({"dataset_id": dataset_id, "user_id": user_id})
        risk_data = json.loads(risk_score_raw)

        anomaly_raw = detect_anomalies.invoke({"dataset_id": dataset_id, "user_id": user_id})
        anomaly_data = json.loads(anomaly_raw)

        expense_raw = analyze_expense_growth.invoke({"dataset_id": dataset_id, "user_id": user_id})
        expense_data = json.loads(expense_raw)

        loss_raw = identify_loss_patterns.invoke({"dataset_id": dataset_id, "user_id": user_id})
        loss_data = json.loads(loss_raw)

        forecast_raw = forecast_business_risks.invoke({"dataset_id": dataset_id, "user_id": user_id})
        forecast_data = json.loads(forecast_raw)

        # 2. Parse core findings
        score = float(risk_data.get("risk_score", 5.0))
        level = str(risk_data.get("risk_level", "low")).lower()
        if level not in {"low", "medium", "high", "critical"}:
            level = "low"

        anomaly_detected = bool(anomaly_data.get("anomaly_detected", False))
        anomaly_count = int(anomaly_data.get("anomaly_count", 0))
        pred_profit = risk_data.get("predicted_profit") or forecast_data.get("predicted_mean_profit")

        # 3. Assemble structured findings
        findings_list: List[RiskFinding] = []
        key_risks: List[str] = []
        evidence_items: List[EvidenceItem] = []

        # Add findings from risk calculation
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
        )


def create_risk_agent(
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
) -> RiskAgent:
    """Factory creating a RiskAgent instance."""
    return RiskAgent(gemini_api_key=gemini_api_key, groq_api_key=groq_api_key)