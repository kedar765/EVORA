
from typing import Any, Dict, List, Optional


class DecisionOptimizationAgent:

    def _number(self, value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
            return number if number == number else default
        except (TypeError, ValueError):
            return default

    def recommend(
        self,
        analytics: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        analytics = analytics or {}
        risk = risk or {}
        scenario = scenario or {}

        # Support complete API responses as well as direct analysis objects.
        analytics = analytics.get("analysis", analytics)
        risk = risk.get("risk_analysis", risk)

        risk_level = str(risk.get("risk_level", "LOW")).upper()
        if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
            risk_level = "LOW"

        risk_score = self._number(risk.get("risk_score"))
        anomaly_detected = bool(risk.get("anomaly_detected", False))

        total_profit = self._number(analytics.get("total_profit"))
        profit_margin = self._number(analytics.get("profit_margin"))
        profit_difference = self._number(
            scenario.get("profit_difference")
        )

        recommendations: List[str] = []
        action_plan: List[Dict[str, str]] = []
        evidence: List[str] = []

        if "total_profit" in analytics:
            evidence.append(f"Current total profit: ₹{total_profit:,.2f}")

        if "profit_margin" in analytics:
            evidence.append(f"Current profit margin: {profit_margin:.2f}%")

        if "risk_level" in risk:
            evidence.append(f"Risk level: {risk_level}")

        if "risk_score" in risk:
            evidence.append(f"Risk score: {risk_score:.2f}")

        if "anomaly_detected" in risk:
            evidence.append(
                f"Anomaly detected: {'Yes' if anomaly_detected else 'No'}"
            )

        if "profit_difference" in scenario:
            evidence.append(
                f"What-if predicted profit difference: ₹{profit_difference:,.2f}"
            )

        # High-risk or loss condition
        if (
            risk_level == "HIGH"
            or anomaly_detected
            or total_profit < 0
            or profit_margin < 0
        ):
            priority = "HIGH"

            if anomaly_detected:
                    recommendations.append(
                        "Investigate detected anomalies and unusual business patterns before making operational changes."
                    )
                    action_plan.append({
                    "action": "Investigate detected anomalies.",
                    "reason": "The risk analysis detected unusual business patterns.",
                    "expected_benefit": "Identify potentially abnormal transactions or operations.",
                    "risk": "Delaying investigation may allow the issue to continue."
                })

            if total_profit < 0 or profit_margin < 0:
                recommendations.append(
                    "Review major expense drivers and take steps to control costs."
                )
                action_plan.append({
                    "action": "Conduct an expense and pricing review.",
                    "reason": "Current profitability is negative.",
                    "expected_benefit": "Identify opportunities to reduce costs and improve margins.",
                    "risk": "Cost reductions may affect service quality or operations."
                })

            if risk_level == "HIGH" and not anomaly_detected:
                recommendations.append(
                    "Review high-risk business operations before expanding."
                )

        # Medium-risk condition
        elif risk_level == "MEDIUM" or profit_margin < 15:
            priority = "MEDIUM"

            recommendations.append(
                "Improve operational efficiency to protect current profit margins."
            )
            action_plan.append({
                "action": "Review supplier costs and high-expense products.",
                "reason": "The business has moderate risk or limited profit margin.",
                "expected_benefit": "Potential improvement in operating efficiency and margins.",
                "risk": "Supplier or operational changes may temporarily affect delivery."
            })

            action_plan.append({
                "action": "Monitor product-level profitability.",
                "reason": "Product performance can reveal cost and margin problems.",
                "expected_benefit": "Identify products requiring pricing or cost adjustments.",
                "risk": "Decisions based on limited data may be misleading."
            })

        # Low-risk growth condition
        else:
            priority = "LOW"

            recommendations.append(
                "Maintain stable operations and evaluate scaled investments in top-performing categories."
            )
            action_plan.append({
                "action": "Evaluate expansion of profitable product categories.",
                "reason": "Current profitability and risk indicators are healthy.",
                "expected_benefit": "Explore opportunities for additional revenue and profit.",
                "risk": "Expansion may increase operating costs and market exposure."
            })

        # What-if scenario evidence
        if "profit_difference" in scenario:
            if profit_difference > 0:
                recommendations.append(
                    f"What-if analysis projects a potential profit increase of ₹{profit_difference:,.2f}."
                )
                action_plan.append({
                    "action": "Evaluate the proposed what-if scenario.",
                    "reason": "The simulated scenario predicts higher profit.",
                    "expected_benefit": f"Potential predicted profit improvement of ₹{profit_difference:,.2f}.",
                    "risk": "Actual results may differ from model predictions."
                })

            elif profit_difference < 0:
                recommendations.append(
                    f"Review the proposed scenario because predicted profit decreases by ₹{abs(profit_difference):,.2f}."
                )
                action_plan.append({
                    "action": "Reconsider or modify the proposed scenario.",
                    "reason": "The simulated scenario predicts lower profit.",
                    "expected_benefit": "Avoid or reduce the projected profit decline.",
                    "risk": "Rejecting the scenario may also mean missing other business opportunities."
                })

            else:
                recommendations.append(
                    "The what-if scenario shows no predicted profit change."
                )

        if not evidence:
            evidence.append(
                "No analytics, risk or scenario evidence was provided."
            )
            recommendations.append(
                "Provide business analytics, risk analysis and what-if results for a more reliable recommendation."
            )

        if not action_plan:
            action_plan.append({
                "action": "Continue monitoring business performance.",
                "reason": "No immediate corrective action is indicated by the available data.",
                "expected_benefit": "Maintain visibility into business performance.",
                "risk": "Business conditions may change."
            })

        return {
            "question_addressed": "What should we do?",
            "priority": priority,
            "risk_context": {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "anomaly_detected": anomaly_detected
            },
            "evidence": evidence,
            "recommendations": recommendations,
            "action_plan": action_plan,
            "decision_disclaimer": (
                "EVORA provides decision-support evidence. "
                "The final decision and execution remain with the human user."
            )
        }
