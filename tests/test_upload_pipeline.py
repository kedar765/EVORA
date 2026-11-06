import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app
import backend.auth as auth

def upload_csv_content(csv_str, filename="test.csv"):
    client = TestClient(app)
    headers = {"Origin": "http://localhost:3000"}
    with auth.database() as conn:
        conn.execute("DELETE FROM signup_attempts")
        conn.execute("DELETE FROM login_attempts")
    client.post(
        "/api/auth/signup",
        headers=headers,
        json={"fullName": "Pipeline Tester", "email": "pipeline_up@example.com", "password": "PipelinePass123!"},
    )
    client.post(
        "/api/auth/login",
        headers=headers,
        json={"email": "pipeline_up@example.com", "password": "PipelinePass123!"},
    )
    res = client.post(
        "/upload",
        headers=headers,
        files={"file": (filename, csv_str.encode("utf-8"), "text/csv")},
    )
    if res.status_code != 200:
        raise RuntimeError(f"Upload failed with {res.status_code}: {res.text}")
    return res.json()

def run_tests():
    # 1. Normal data
    normal_csv = "Quantity,Revenue,Expense\n100,50000,30000\n120,60000,35000\n140,70000,40000"
    res1 = upload_csv_content(normal_csv, "normal.csv")
    print("Normal Case Status:", res1["business_status"])
    print("Risk Level:", res1["risk_level"])
    print("Insights:", len(res1["analytics"]["insights"]))
    assert res1["risk_level"] in ["LOW", "MEDIUM"]

    # 2. Operating at a loss (Expenses > Revenue)
    loss_csv = "Quantity,Revenue,Expense\n100,20000,50000\n80,15000,40000"
    res2 = upload_csv_content(loss_csv, "loss.csv")
    print("Loss Case Status:", res2["business_status"])
    print("Risk Level:", res2["risk_level"])
    print("Risk Score:", res2["risk_score"])
    print("Insights:", res2["analytics"]["insights"])
    assert res2["metrics"]["total_profit"] < 0
    assert res2["risk_level"] in ["MEDIUM", "HIGH"]

    print("All upload pipeline tests passed successfully!")

if __name__ == '__main__':
    run_tests()
