import json
import urllib.request
from pathlib import Path

def test_full_pipeline():
    csv_path = Path("data/sample_business_data.csv")
    content = csv_path.read_text(encoding="utf-8")

    # 1. Test /upload with real sample CSV
    boundary = "----WebKitFormBoundaryUploadTest123"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="sample_business_data.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{content}\r\n"
        f"--{boundary}--\r\n"
    )
    body = header.encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:8000/upload",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary}
    )

    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
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
        print("Anomaly Indices:", res.get("anomaly_indices"))

        # Exact verified business calculations
        assert res["metrics"]["total_revenue"] == 142000.0, "Revenue sum mismatch"
        assert res["metrics"]["total_expense"] == 87000.0, "Expense sum mismatch"
        assert res["metrics"]["total_profit"] == 55000.0, "Profit calculation mismatch"
        assert round(res["metrics"]["profit_margin"], 2) == 38.73, "Profit margin mismatch"
        assert res["metrics"]["total_sales"] == 710.0, "Total units sold mismatch"
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
    whatif_req = urllib.request.Request(
        "http://127.0.0.1:8000/what-if",
        data=json.dumps(whatif_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(whatif_req) as resp:
        res_wf = json.loads(resp.read().decode())
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
