import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from agents.decision_agent import DecisionOptimizationAgent

def test_decision_agent():
    agent = DecisionOptimizationAgent()

    # Case 1: High risk / anomaly / loss
    high_risk_output = agent.recommend(
        analytics={"total_profit": -5000, "profit_margin": -10},
        risk={"risk_level": "HIGH", "risk_score": 85, "anomaly_detected": True},
        scenario={"profit_difference": -2000}
    )
    assert high_risk_output["priority"] == "HIGH"
    assert len(high_risk_output["recommendations"]) > 0
    assert any("anomalies" in r.lower() for r in high_risk_output["recommendations"])
    print("[OK] High Risk Case Passed:", high_risk_output["priority"])

    # Case 2: Healthy business / growth
    healthy_output = agent.recommend(
        analytics={"total_profit": 50000, "profit_margin": 35},
        risk={"risk_level": "LOW", "risk_score": 15, "anomaly_detected": False},
        scenario={"profit_difference": 12000}
    )
    assert healthy_output["priority"] == "LOW"
    assert any("scaled" in r.lower() for r in healthy_output["recommendations"])
    print("[OK] Healthy Growth Case Passed:", healthy_output["priority"])

if __name__ == "__main__":
    test_decision_agent()
    print("All DecisionOptimizationAgent tests passed!")
