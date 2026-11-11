"""
EVORA Pydantic Schemas
======================
Strongly-typed validation models for:
- Analytics Agent Output
- Risk Agent Output
- Decision Optimization Agent Output
- LangGraph Workflow State & API Request/Response
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EVORABaseSchema(BaseModel):
    """Common base schema enforcing strict attributes."""
    model_config = ConfigDict(extra="ignore")


def _validate_finite_float(val: Optional[float]) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return round(f, 2)
    except (ValueError, TypeError):
        return 0.0


# Evidence supporting an agent's findings
class EvidenceItem(EVORABaseSchema):
    description: str
    metric: Optional[str] = None
    value: Optional[Any] = None
    source: Optional[str] = None


# Analytics Agent Output
class AnalyticsAgentOutput(EVORABaseSchema):
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None
    total_profit: Optional[float] = None
    profit_margin: Optional[float] = None

    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)

    product_performance: List[Dict[str, Any]] = Field(default_factory=list)
    monthly_trends: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    summary: str = ""

    model_used: Optional[str] = None
    execution_mode: Literal["llm", "groq_fallback", "deterministic_fallback"] = "llm"
    model_error: Optional[str] = None

    @field_validator("total_revenue", "total_expenses", "total_profit", "profit_margin", mode="before")
    @classmethod
    def check_finite(cls, v: Any) -> Optional[float]:
        return _validate_finite_float(v)


# Risk Agent Output
class RiskFinding(EVORABaseSchema):
    risk_type: str
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    recommended_action: Optional[str] = None


class RiskAgentOutput(EVORABaseSchema):
    risk_score: float = Field(default=0.0, ge=0, le=100)
    risk_level: Literal["low", "medium", "high", "critical"] = "low"

    anomaly_detected: bool = False
    anomaly_count: int = 0
    predicted_profit: Optional[float] = None
    findings: List[RiskFinding] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)

    summary: str = ""

    model_used: Optional[str] = None
    execution_mode: Literal["llm", "groq_fallback", "deterministic_fallback"] = "llm"
    model_error: Optional[str] = None

    @field_validator("risk_score", mode="before")
    @classmethod
    def check_score(cls, v: Any) -> float:
        val = _validate_finite_float(v)
        if val is None:
            return 0.0
        return max(0.0, min(100.0, float(val)))

    @field_validator("predicted_profit", mode="before")
    @classmethod
    def check_pred_profit(cls, v: Any) -> Optional[float]:
        return _validate_finite_float(v)


# Decision Optimization Agent Output
class DecisionAction(EVORABaseSchema):
    action: str
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    expected_impact: Optional[str] = None
    estimated_financial_impact: Optional[float] = None
    reason: str
    risk: Optional[str] = None

    @field_validator("estimated_financial_impact", mode="before")
    @classmethod
    def check_impact(cls, v: Any) -> Optional[float]:
        return _validate_finite_float(v)


class ScenarioSimulationResult(EVORABaseSchema):
    scenario_name: str
    projected_revenue: float
    projected_expenses: float
    projected_profit: float
    profit_delta: float
    notes: str = ""


class DecisionAgentOutput(EVORABaseSchema):
    overall_priority: Literal["low", "medium", "high", "critical"] = "medium"

    recommended_strategy: str
    alternative_strategies: List[str] = Field(default_factory=list)
    actions: List[DecisionAction] = Field(default_factory=list)
    scenarios: List[ScenarioSimulationResult] = Field(default_factory=list)

    expected_outcome: str = ""
    assumptions: List[str] = Field(default_factory=list)
    human_approval_required: bool = True
    summary: str = ""

    model_used: Optional[str] = None
    execution_mode: Literal["llm", "groq_fallback", "deterministic_fallback"] = "llm"
    model_error: Optional[str] = None


# Final Synthesized Executive Business Report
class FinalReportOutput(EVORABaseSchema):
    executive_summary: str
    business_health_status: str
    overall_risk_level: Literal["low", "medium", "high", "critical"]
    risk_score: float
    financial_highlights: Dict[str, Any] = Field(default_factory=dict)
    key_insights: List[str] = Field(default_factory=list)
    immediate_actions: List[DecisionAction] = Field(default_factory=list)
    scenario_projections: List[ScenarioSimulationResult] = Field(default_factory=list)
    governance_disclaimer: str = (
        "EVORA provides decision-support evidence. "
        "The final business decision and execution remain under human control."
    )

    models_used: Dict[str, str] = Field(default_factory=dict)
    execution_modes: Dict[str, str] = Field(default_factory=dict)


# Agent Workflow Input
class AgentWorkflowRequest(EVORABaseSchema):
    dataset_id: str
    user_id: Optional[str] = None
    user_query: str = ""


# Final Workflow Output
class AgentWorkflowResponse(EVORABaseSchema):
    dataset_id: str
    user_query: str = ""

    analytics: Optional[AnalyticsAgentOutput] = None
    risk: Optional[RiskAgentOutput] = None
    decision: Optional[DecisionAgentOutput] = None
    final_report: Optional[FinalReportOutput] = None

    status: Literal["completed", "partial", "failed"] = "completed"
    errors: List[str] = Field(default_factory=list)
    step_durations: Dict[str, float] = Field(default_factory=dict)
    agent_statuses: Dict[str, str] = Field(default_factory=dict)
    models_used: Dict[str, str] = Field(default_factory=dict)
    execution_modes: Dict[str, str] = Field(default_factory=dict)
    analysis_id: Optional[str] = None
    created_at: Optional[int] = None
