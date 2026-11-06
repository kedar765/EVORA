import json
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app
import backend.auth as auth

def test_full_pipeline():
    client = TestClient(app)
    headers = {"Origin": "http://localhost:3000"}

    with auth.database() as conn:
        conn.execute("DELETE FROM signup_attempts")
        conn.execute("DELETE FROM login_attempts")

    client.post(
        "/api/auth/signup",
        headers=headers,
        json={"fullName": "Full Verifier", "email": "verifier@example.com", "password": "VerifierPass123!"},
    )
    client.post(
        "/api/auth/login",
        headers=headers,
        json={"email": "verifier@example.com", "password": "VerifierPass123!"},
    )

    csv_path = Path("data/sample_business_data.csv")
    content = csv_path.read_bytes()
    df_expected = pd.read_csv(csv_path)

    # 1. Test /upload with real sample CSV
    resp = client.post(
        "/upload",
        headers=headers,
        files={"file": ("sample_business_data.csv", content, "text/csv")},
    )
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    res = resp.json()

    print("=== Upload Output Verified ===")
    print("Filename:", res.get("filename"))
    print("Rows processed:", res.get("rows_processed"))
    print("Total Revenue:", res["metrics"]["total_revenue"])
    print("Total Expense:", res["metrics"]["total_expense"])
    print("Total Profit:", res["metrics"]["total_profit"])
    print("Profit Margin:", res["metrics"]["profit_margin"])
    print("Total Sales (Units):", res["metrics"]["total_sales"])
    print("Predicted Profit:", res.get("predicted_profit"))
    print("Risk Score:", res.get("risk_score"))
    print("Risk Level:", res.get("risk_level"))
    print("Anomalies Count:", res.get("anomaly_count"))
    print("Anomaly Indices:", len(res.get("anomaly_indices", [])))

    expected_rev = float(df_expected["Revenue"].sum())
    expected_exp = float(df_expected["Expense"].sum())
    expected_profit = expected_rev - expected_exp
    expected_margin = round(expected_profit / expected_rev * 100, 2)
    expected_sales = float(df_expected["Quantity"].sum())

    assert round(res["metrics"]["total_revenue"], 2) == round(expected_rev, 2), "Revenue sum mismatch"
    assert round(res["metrics"]["total_expense"], 2) == round(expected_exp, 2), "Expense sum mismatch"
    assert round(res["metrics"]["total_profit"], 2) == round(expected_profit, 2), "Profit calculation mismatch"
    assert round(res["metrics"]["profit_margin"], 2) == expected_margin, "Profit margin mismatch"
    assert round(res["metrics"]["total_sales"], 2) == round(expected_sales, 2), "Total units sold mismatch"
    assert res["predicted_profit"] is not None, "Predicted profit is missing"
    assert res["risk_score"] is not None, "Risk score is missing"
    assert isinstance(res["anomaly_indices"], list), "Anomaly indices should be a list"

    # 2. Test /what-if simulation endpoint
    whatif_payload = {
        "current_quantity": 710,
        "current_revenue": 142000,
        "current_expense": 87000,
        "new_quantity": 800,
        "new_revenue": 160000,
        "new_expense": 90000
    }
    resp_wf = client.post("/what-if", headers=headers, json=whatif_payload)
    assert resp_wf.status_code == 200, f"What-If failed: {resp_wf.text}"
    res_wf = resp_wf.json()

    print("\n=== What-If Output Verified ===")
    print("Current Predicted Profit:", res_wf.get("current_predicted_profit"))
    print("New Predicted Profit:", res_wf.get("new_predicted_profit"))
    print("Profit Difference:", res_wf.get("profit_difference"))
    print("Result String:", res_wf.get("result"))
    assert res_wf.get("success") is True
    assert res_wf.get("profit_difference") is not None

    print("\nALL BACKEND & INTEGRATION CHECKS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_pipeline()
