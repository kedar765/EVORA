"""
EVORA LangGraph Agent State
===========================
Defines the shared state passed between nodes in the multi-agent orchestration graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


class EVORAAgentState(TypedDict, total=False):
    # User and dataset identity
    user_id: str
    dataset_id: str
    dataset_path: str

    # User's business query
    user_query: str

    # Dataset profile metadata
    dataset_metadata: Dict[str, Any]

    # Agent output dictionaries
    analytics_results: Dict[str, Any]
    risk_results: Dict[str, Any]
    decision_results: Dict[str, Any]

    # Workflow tracking and error management
    current_step: str
    errors: List[str]
    execution_status: Literal["pending", "running", "completed", "partial", "failed"]

    # Final synthesized executive report
    final_report: Optional[Dict[str, Any]]
