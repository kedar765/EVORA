from typing import Dict, Any, List, Optional


class DecisionOptimizationAgent:
    """
    Decision Optimization Agent for EVORA.
    Answers: 'What should we do?'

    Combines:
    - Analytics Agent insights (What happened?)
    - Risk Agent evaluation (What is wrong?)
    - What-If scenario simulations (What if alternatives are chosen?)

    Outputs an evidence-based recommendation while keeping the final decision
    with the human user.
    """

    def recommend(
        self,
        analytics: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        recommendations: List[str] = []
        action_plan: List[str] = []
        priority = "MEDIUM"

        risk_level = (risk.get("risk_level") if risk else "LOW") or "LOW"
        risk_score = risk.get("risk_score", 0) if risk else 0
        anomaly_detected = risk.get("anomaly_detected", False) if risk else False

        profit_margin = analytics.get("profit_margin", 0.0) if analytics else 0.0
        total_profit = analytics.get("total_profit", 0.0) if analytics else 0.0

        profit_difference = scenario.get("profit_difference", 0.0) if scenario else 0.0

        # High Risk Strategy
        if risk_level == "HIGH" or anomaly_detected or total_profit < 0:
            priority = "HIGH"
            if anomaly_detected:
                recommendations.append(
                    "Investigate operational anomalies immediately to isolate unusual transaction patterns."
                )
            if total_profit < 0 or profit_margin < 0:
                recommendations.append(
                    "Initiate cost containment: Review high expense drivers and pause discretionary spending."
                )
            action_plan.append("Conduct line-item expense audit across highest expenditure categories.")
            action_plan.append("Re-evaluate pricing tiers before expanding operational commitments.")

        # Medium Risk Strategy
        elif risk_level == "MEDIUM" or profit_margin < 15:
            priority = "MEDIUM"
            recommendations.append(
                "Optimize operational efficiency to safeguard current margins against cost fluctuations."
            )
            action_plan.append("Explore supplier renegotiation or volume discounts to stabilize unit expense.")
            action_plan.append("Monitor high-variance products and assess customer return or complaint metrics.")

        # Low Risk / Growth Strategy
        else:
            priority = "LOW"
            recommendations.append(
                "Maintain baseline operations and evaluate scaled investments in top-performing categories."
            )
            action_plan.append("Model scenario expansions for higher sales volume in core profitable products.")

        # Incorporate What-If scenario evidence if available
        if scenario:
            if profit_difference > 0:
                recommendations.append(
                    f"What-If scenario projection indicates an estimated profit increase of ₹{profit_difference:,.2f} if targets are realized."
                )
            elif profit_difference < 0:
                recommendations.append(
                    f"Caution: Simulated target scenario models a projected profit decline of ₹{abs(profit_difference):,.2f}."
                )

        return {
            "question_addressed": "What should we do?",
            "priority": priority,
            "risk_context": {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "anomaly_detected": anomaly_detected,
            },
            "recommendations": recommendations,
            "action_plan": action_plan,
            "decision_disclaimer": "EVORA provides decision-support evidence. Final operational decision execution remains with the human user."
        }
