import json
import urllib.request
import io
import pandas as pd

BASE_URL = "http://127.0.0.1:8000"

def post_json(endpoint, data):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def post_csv(endpoint, csv_content, filename="test.csv"):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{csv_content}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def run_evaluation():
    print("==================================================")
    print("EVORA AGENT EVALUATION SUITE")
    print("==================================================")
    
    # 1. Analytics Agent Evaluation
    print("\n--- 1. Evaluating Analytics Agent (/analytics) ---")
    
    # Normal / Positive profit CSV
    normal_csv = "Revenue,Expense,Quantity\n50000,30000,100\n60000,35000,120\n70000,40000,140"
    res_normal = post_csv("/analytics", normal_csv)
    print("\nCase 1.1: Normal Business (Positive Profit, High Margin >= 20%)")
    print("Analytics Output:", json.dumps(res_normal, indent=2))
    assert res_normal["success"] is True
    assert res_normal["analysis"]["total_profit"] > 0
    assert any("profitable" in s.lower() for s in res_normal["analysis"]["insights"])
    
    # Negative profit CSV
    loss_csv = "Revenue,Expense,Quantity\n20000,45000,100\n15000,35000,80"
    res_loss = post_csv("/analytics", loss_csv)
    print("\nCase 1.2: Negative Profit (Operating at loss, negative margin)")
    print("Analytics Output:", json.dumps(res_loss, indent=2))
    assert res_loss["success"] is True
    assert res_loss["analysis"]["total_profit"] < 0
    assert any("loss" in s.lower() for s in res_loss["analysis"]["insights"])

    # Break-even CSV
    breakeven_csv = "Revenue,Expense,Quantity\n50000,50000,100"
    res_breakeven = post_csv("/analytics", breakeven_csv)
    print("\nCase 1.3: Break-Even")
    print("Analytics Output:", json.dumps(res_breakeven, indent=2))
    assert res_breakeven["analysis"]["total_profit"] == 0
    assert any("break-even" in s.lower() for s in res_breakeven["analysis"]["insights"])

    # 2. Risk Agent Evaluation
    print("\n--- 2. Evaluating Risk Agent (/analyze-risk) ---")
    
    # Test cases for risk agent
    test_scenarios = [
        {"name": "Low Risk (Healthy margins, normal metrics)", "Quantity": 100, "Revenue": 80000, "Expense": 40000},
        {"name": "Medium Risk (Moderate margin, lower profit)", "Quantity": 50, "Revenue": 20000, "Expense": 17000},
        {"name": "High Risk / Loss (Expenses exceed revenue)", "Quantity": 100, "Revenue": 20000, "Expense": 60000},
        {"name": "Anomaly Detected (Extreme outlier values)", "Quantity": 1, "Revenue": 999999, "Expense": 100},
    ]

    for sc in test_scenarios:
        payload = {"Quantity": sc["Quantity"], "Revenue": sc["Revenue"], "Expense": sc["Expense"]}
        risk_res = post_json("/analyze-risk", payload)
        print(f"\nScenario: {sc['name']}")
        print(f"Inputs: {payload}")
        print(f"Risk Score: {risk_res['risk_score']}, Risk Level: {risk_res['risk_level']}")
        print(f"Anomaly Detected: {risk_res['anomaly_detected']}")
        print(f"Predicted Profit: {risk_res['predicted_profit']}")
        print(f"Reasons: {risk_res['risk_analysis']['reasons']}")
        
        # Verify alignment
        if risk_res["risk_score"] <= 30:
            assert risk_res["risk_level"] == "LOW"
        elif risk_res["risk_score"] <= 60:
            assert risk_res["risk_level"] == "MEDIUM"
        else:
            assert risk_res["risk_level"] == "HIGH"
            
        assert len(risk_res["risk_analysis"]["reasons"]) > 0

    print("\n==================================================")
    print("ALL EVALUATION CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_evaluation()
