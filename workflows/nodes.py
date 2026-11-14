"""
EVORA LangGraph Workflow Nodes
==============================
Implements execution nodes for the multi-agent graph:
1. validate_dataset_node: Securely validates dataset ownership and profile.
2. analytics_agent_node: Generates financial metrics and trends.
3. risk_agent_node: Detects anomalies, evaluates losses, and computes risk score.
4. decision_agent_node: Simulates scenarios, optimizes resources, and creates action plan.
5. final_report_node: Synthesizes executive business intelligence report.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from agents.analytics_agent import AnalyticsAgent
from agents.decision_agent import DecisionOptimizationAgent
from agents.risk_agent import RiskAgent
from tools.dataset_tools import DatasetAccessError, load_user_dataset
from workflows.state import EVORAAgentState

logger = logging.getLogger("evora.workflows.nodes")


def validate_dataset_node(state: EVORAAgentState) -> Dict[str, Any]:
    """Validates user dataset ownership and prepares metadata profile."""
    start_time = time.perf_counter()
    dataset_id = state.get("dataset_id", "")
    user_id = state.get("user_id", "")
    errors = list(state.get("errors", []))
    durations = dict(state.get("step_durations", {}))
    agent_statuses = dict(state.get("agent_statuses", {}))

    try:
        df, meta = load_user_dataset(dataset_id, user_id)
        durations["validate_dataset"] = round(time.perf_counter() - start_time, 4)
        agent_statuses["validate_dataset"] = "completed"
        return {
            "dataset_metadata": meta,
            "current_step": "validate_dataset",
            "execution_status": "running",
            "errors": errors,
            "step_durations": durations,
            "agent_statuses": agent_statuses,
        }
    except DatasetAccessError as e:
        durations["validate_dataset"] = round(time.perf_counter() - start_time, 4)
        agent_statuses["validate_dataset"] = "failed"
        errors.append(f"Dataset validation failed: {e.message}")
        return {
            "errors": errors,
            "current_step": "validate_dataset",
            "execution_status": "failed",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
        }
    except Exception as e:
        durations["validate_dataset"] = round(time.perf_counter() - start_time, 4)
        agent_statuses["validate_dataset"] = "failed"
        errors.append(f"Unexpected dataset error: {str(e)}")
        return {
            "errors": errors,
            "current_step": "validate_dataset",
            "execution_status": "failed",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
        }


def analytics_agent_node(state: EVORAAgentState) -> Dict[str, Any]:
    """Executes Analytics Agent to compute metrics, trends, and product performance."""
    if state.get("execution_status") == "failed":
        return {"current_step": "analytics_agent"}

    start_time = time.perf_counter()
    dataset_id = state.get("dataset_id", "")
    user_id = state.get("user_id", "")
    user_query = state.get("user_query", "")
    errors = list(state.get("errors", []))
    durations = dict(state.get("step_durations", {}))
    agent_statuses = dict(state.get("agent_statuses", {}))
    models_used = dict(state.get("models_used", {}))
    execution_modes = dict(state.get("execution_modes", {}))

    try:
        agent = AnalyticsAgent()
        output = agent.run_agent(dataset_id=dataset_id, user_id=user_id, user_query=user_query)
        durations["analytics_agent"] = round(time.perf_counter() - start_time, 4)
        models_used["analytics_agent"] = output.model_used or agent.gemini_model
        execution_modes["analytics_agent"] = output.execution_mode
        agent_statuses["analytics_agent"] = "completed" if output.execution_mode == "llm" else "fallback"
        return {
            "analytics_results": output.model_dump(),
            "current_step": "analytics_agent",
            "execution_status": "running",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
            "models_used": models_used,
            "execution_modes": execution_modes,
        }
    except Exception as e:
        logger.exception("Analytics agent failed")
        durations["analytics_agent"] = round(time.perf_counter() - start_time, 4)
        agent_statuses["analytics_agent"] = "failed"
        errors.append(f"Analytics agent execution error: {str(e)}")
        return {
            "errors": errors,
            "current_step": "analytics_agent",
            "execution_status": "partial",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
            "models_used": models_used,
            "execution_modes": execution_modes,
        }


def risk_agent_node(state: EVORAAgentState) -> Dict[str, Any]:
    """Executes Risk Agent using analytics context to detect anomalies and assess risk."""
    if state.get("execution_status") == "failed":
        return {"current_step": "risk_agent"}

    start_time = time.perf_counter()
    dataset_id = state.get("dataset_id", "")
    user_id = state.get("user_id", "")
    user_query = state.get("user_query", "")
    analytics_results = state.get("analytics_results", {})
    errors = list(state.get("errors", []))
    durations = dict(state.get("step_durations", {}))
    agent_statuses = dict(state.get("agent_statuses", {}))
    models_used = dict(state.get("models_used", {}))
    execution_modes = dict(state.get("execution_modes", {}))

    try:
        agent = RiskAgent()
        output = agent.run_agent(
            dataset_id=dataset_id,
            user_id=user_id,
            analytics_context=analytics_results,
            user_query=user_query,
        )
        durations["risk_agent"] = round(time.perf_counter() - start_time, 4)
        models_used["risk_agent"] = output.model_used or agent.gemini_model
        execution_modes["risk_agent"] = output.execution_mode
        agent_statuses["risk_agent"] = "completed" if output.execution_mode == "llm" else "fallback"
        return {
            "risk_results": output.model_dump(),
            "current_step": "risk_agent",
            "execution_status": "running",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
            "models_used": models_used,
            "execution_modes": execution_modes,
        }
    except Exception as e:
        logger.exception("Risk agent failed")
        durations["risk_agent"] = round(time.perf_counter() - start_time, 4)
        agent_statuses["risk_agent"] = "failed"
        errors.append(f"Risk agent execution error: {str(e)}")
        return {
            "errors": errors,
            "current_step": "risk_agent",
            "execution_status": "partial",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
            "models_used": models_used,
            "execution_modes": execution_modes,
        }


def decision_agent_node(state: EVORAAgentState) -> Dict[str, Any]:
    """Executes Decision Agent using analytics and risk context to recommend strategies."""
    if state.get("execution_status") == "failed":
        return {"current_step": "decision_agent"}

    start_time = time.perf_counter()
    dataset_id = state.get("dataset_id", "")
    user_id = state.get("user_id", "")
    user_query = state.get("user_query", "")
    analytics_results = state.get("analytics_results", {})
    risk_results = state.get("risk_results", {})
    errors = list(state.get("errors", []))
    durations = dict(state.get("step_durations", {}))
    agent_statuses = dict(state.get("agent_statuses", {}))
    models_used = dict(state.get("models_used", {}))
    execution_modes = dict(state.get("execution_modes", {}))

    try:
        agent = DecisionOptimizationAgent()
        output = agent.run_agent(
            dataset_id=dataset_id,
            user_id=user_id,
            analytics_context=analytics_results,
            risk_context=risk_results,
            user_query=user_query,
        )
        durations["decision_agent"] = round(time.perf_counter() - start_time, 4)
        models_used["decision_agent"] = output.model_used or agent.gemini_model
        execution_modes["decision_agent"] = output.execution_mode
        agent_statuses["decision_agent"] = "completed" if output.execution_mode == "llm" else "fallback"
        return {
            "decision_results": output.model_dump(),
            "current_step": "decision_agent",
            "execution_status": "running",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
            "models_used": models_used,
            "execution_modes": execution_modes,
        }
    except Exception as e:
        logger.exception("Decision agent failed")
        durations["decision_agent"] = round(time.perf_counter() - start_time, 4)
        agent_statuses["decision_agent"] = "failed"
        errors.append(f"Decision agent execution error: {str(e)}")
        return {
            "errors": errors,
            "current_step": "decision_agent",
            "execution_status": "partial",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
            "models_used": models_used,
            "execution_modes": execution_modes,
        }


def final_report_node(state: EVORAAgentState) -> Dict[str, Any]:
    """Synthesizes unified executive business intelligence report across all agent outputs."""
    start_time = time.perf_counter()
    errors = list(state.get("errors", []))
    status = state.get("execution_status", "completed")
    durations = dict(state.get("step_durations", {}))
    agent_statuses = dict(state.get("agent_statuses", {}))
    models_used = dict(state.get("models_used", {}))
    execution_modes = dict(state.get("execution_modes", {}))

    if status == "failed":
        final_report = {
            "executive_summary": "Analysis could not be completed due to dataset validation failure.",
            "business_health_status": "Failed / Invalid Dataset",
            "overall_risk_level": "critical",
            "risk_score": 100.0,
            "financial_highlights": {},
            "key_insights": ["Please ensure a valid dataset is uploaded and owned by the authenticated account."],
            "immediate_actions": [],
            "scenario_projections": [],
            "governance_disclaimer": "EVORA requires a valid accessible dataset to evaluate decisions.",
        }
        durations["final_report"] = round(time.perf_counter() - start_time, 4)
        agent_statuses["final_report"] = "failed"
        return {
            "final_report": final_report,
            "current_step": "final_report",
            "execution_status": "failed",
            "step_durations": durations,
            "agent_statuses": agent_statuses,
        }

    analytics = state.get("analytics_results", {})
    risk = state.get("risk_results", {})
    decision = state.get("decision_results", {})

    total_rev = analytics.get("total_revenue", 0.0)
    total_exp = analytics.get("total_expenses", 0.0)
    total_prof = analytics.get("total_profit", 0.0)
    margin = analytics.get("profit_margin", 0.0)

    risk_score = risk.get("risk_score", 0.0)
    risk_level = risk.get("risk_level", "low")

    # Determine executive health status
    if total_prof > 0 and risk_score <= 30:
        health_status = "Healthy & Profitable Growth"
    elif total_prof > 0 and risk_score <= 60:
        health_status = "Profitable with Moderate Risk"
    elif total_prof < 0:
        health_status = "Critical — Operating at a Loss"
    else:
        health_status = "High Risk — Operational Attention Required"

    exec_summary = (
        f"EVORA Multi-Agent Evaluation: Dataset generated ₹{total_rev:,.2f} in gross revenue against "
        f"₹{total_exp:,.2f} in expenses, realizing ₹{total_prof:,.2f} net profit ({margin:.2f}% margin). "
        f"Risk exposure scored at {risk_score:.1f}/100 ({str(risk_level).upper()}). "
        f"Recommended strategy: '{decision.get('recommended_strategy', 'Operational Optimization')}'."
    )

    final_report = {
        "executive_summary": exec_summary,
        "business_health_status": health_status,
        "overall_risk_level": risk_level,
        "risk_score": risk_score,
        "financial_highlights": {
            "total_revenue": total_rev,
            "total_expenses": total_exp,
            "total_profit": total_prof,
            "profit_margin_pct": margin,
        },
        "key_insights": analytics.get("key_findings", []),
        "immediate_actions": decision.get("actions", []),
        "scenario_projections": decision.get("scenarios", []),
        "governance_disclaimer": (
            "EVORA provides AI-driven decision optimization evidence. "
            "All final decisions, financial commitments, and operational changes "
            "require human verification and approval."
        ),
        "models_used": models_used,
        "execution_modes": execution_modes,
    }

    final_status = "partial" if errors else "completed"
    durations["final_report"] = round(time.perf_counter() - start_time, 4)
    agent_statuses["final_report"] = final_status

    return {
        "final_report": final_report,
        "current_step": "final_report",
        "execution_status": final_status,
        "step_durations": durations,
        "agent_statuses": agent_statuses,
        "models_used": models_used,
        "execution_modes": execution_modes,
    }
