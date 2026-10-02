class RiskAgent:

    def analyze(
        self,
        predicted_profit: float,
        anomaly_detected: bool,
        risk_score: float,
        risk_level: str
    ):

        reasons = []

        if anomaly_detected:
            reasons.append(
                "An unusual business pattern was detected."
            )
        else:
            reasons.append(
                "No unusual business pattern was detected."
            )

        if predicted_profit < 0:
            reasons.append(
                "Predicted profit is negative."
            )
        elif predicted_profit == 0:
            reasons.append(
                "Predicted profit is at break-even."
            )
        else:
            reasons.append(
                "Predicted profit is positive."
            )

        if risk_score > 60:
            reasons.append(
                "The calculated risk score indicates a high-risk condition."
            )
        elif risk_score > 30:
            reasons.append(
                "The calculated risk score indicates a medium-risk condition."
            )
        else:
            reasons.append(
                "The calculated risk score indicates a low-risk condition."
            )

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "predicted_profit": predicted_profit,
            "anomaly_detected": anomaly_detected,
            "reasons": reasons
        }