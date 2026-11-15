import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from agents.decision_agent import DecisionOptimizationAgent
from schemas.agent_schemas import DecisionLLMOutput, DecisionRecommendation, EvidenceItem


def test_decision_agent():
    agent = DecisionOptimizationAgent(gemini_api_key="mock-key")

    # Case 1: High risk / anomaly / loss
    high_risk_llm_output = DecisionLLMOutput(
        analysis_status="completed",
        overall_priority="high",
        recommended_strategy="Defensive Containment and Anomaly Remediation",
        recommendations=[
            DecisionRecommendation(
                recommendation_id="REC-01",
                title="Investigate Anomalies and Contain Losses",
                recommendation="Address transaction anomalies immediately to stem operating losses.",
                reasoning="Operating at negative profit (-5000) with severe risk score (85).",
                supporting_evidence=[
                    EvidenceItem(description="Risk score 85 with anomalies flagged", metric="risk_score", value=85.0)
                ],
                priority="high",
                category="Risk Mitigation",
                implementation_steps=["Freeze flagged transactions", "Audit cost leaks"],
                associated_risk="Temporary operational slowdown",
            )
        ],
    )

    with patch.object(agent, "_invoke_decision_llm", return_value=high_risk_llm_output):
        high_risk_output = agent.recommend(
            analytics={"total_profit": -5000, "profit_margin": -10},
            risk={"risk_level": "HIGH", "risk_score": 85, "anomaly_detected": True},
            scenario={"profit_difference": -2000},
        )
    assert high_risk_output["priority"] == "HIGH"
    assert len(high_risk_output["recommendations"]) > 0
    assert any("anomalies" in r.lower() for r in high_risk_output["recommendations"])
    print("[OK] High Risk Case Passed:", high_risk_output["priority"])

    # Case 2: Healthy business / growth
    healthy_llm_output = DecisionLLMOutput(
        analysis_status="completed",
        overall_priority="low",
        recommended_strategy="Commercial Expansion",
        recommendations=[
            DecisionRecommendation(
                recommendation_id="REC-01",
                title="Scale Profitable Lines",
                recommendation="Operations can be scaled across high-margin business units.",
                reasoning="Profit margins strong at 35% with low risk score (15).",
                supporting_evidence=[
                    EvidenceItem(description="Profit margin 35%", metric="profit_margin", value=35.0)
                ],
                priority="low",
                category="Revenue Expansion",
                implementation_steps=["Identify top regions", "Deploy incremental sales capacity"],
                associated_risk="Market saturation risks",
            )
        ],
    )

    with patch.object(agent, "_invoke_decision_llm", return_value=healthy_llm_output):
        healthy_output = agent.recommend(
            analytics={"total_profit": 50000, "profit_margin": 35},
            risk={"risk_level": "LOW", "risk_score": 15, "anomaly_detected": False},
            scenario={"profit_difference": 12000},
        )
    assert healthy_output["priority"] == "LOW"
    assert any("scaled" in r.lower() for r in healthy_output["recommendations"])
    print("[OK] Healthy Growth Case Passed:", healthy_output["priority"])


if __name__ == "__main__":
    test_decision_agent()
    print("All DecisionOptimizationAgent tests passed!")
