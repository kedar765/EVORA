r"""
EVORA LangGraph Multi-Agent Orchestration Graph
==============================================
Orchestrates the multi-agent decision support pipeline:
                  START
                    |
                    v
          [validate_dataset]
             /           \
     (if failed)       (if valid)
           /               \
          |                 v
          |         [analytics_agent]
          |                 |
          |                 v
          |            [risk_agent]
          |                 |
          |                 v
          |          [decision_agent]
          |                 |
          \                /
           v              v
            [final_report]
                  |
                  v
                 END
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph

from workflows.nodes import (
    analytics_agent_node,
    decision_agent_node,
    final_report_node,
    risk_agent_node,
    validate_dataset_node,
)
from workflows.state import EVORAAgentState


def _route_after_validation(state: EVORAAgentState) -> Literal["analytics_agent", "final_report"]:
    """Conditional router: if dataset validation fails, skip downstream agents to final report."""
    if state.get("execution_status") == "failed":
        return "final_report"
    return "analytics_agent"


def build_evora_graph() -> StateGraph:
    """Builds and wires the StateGraph for EVORA multi-agent system."""
    builder = StateGraph(EVORAAgentState)

    # Register graph nodes
    builder.add_node("validate_dataset", validate_dataset_node)
    builder.add_node("analytics_agent", analytics_agent_node)
    builder.add_node("risk_agent", risk_agent_node)
    builder.add_node("decision_agent", decision_agent_node)
    builder.add_node("final_report", final_report_node)

    # Wire edges
    builder.add_edge(START, "validate_dataset")

    # Conditional edge from validation
    builder.add_conditional_edges(
        "validate_dataset",
        _route_after_validation,
        {
            "analytics_agent": "analytics_agent",
            "final_report": "final_report",
        },
    )

    # Sequential execution of analytical, risk, and decision agents
    builder.add_edge("analytics_agent", "risk_agent")
    builder.add_edge("risk_agent", "decision_agent")
    builder.add_edge("decision_agent", "final_report")
    builder.add_edge("final_report", END)

    return builder


def compile_workflow():
    """Compiles the EVORA multi-agent graph into an executable runnable workflow."""
    builder = build_evora_graph()
    return builder.compile()


# Global singleton workflow instance
evora_workflow = compile_workflow()


def run_evora_workflow(
    dataset_id: str,
    user_id: str,
    user_query: str = "",
) -> Dict[str, Any]:
    """
    Executes the complete compiled EVORA LangGraph workflow.
    """
    initial_state: EVORAAgentState = {
        "dataset_id": dataset_id,
        "user_id": user_id,
        "user_query": user_query,
        "errors": [],
        "execution_status": "pending",
        "current_step": "start",
    }

    final_state = evora_workflow.invoke(initial_state)
    return final_state
