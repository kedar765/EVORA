import json
import urllib.request

def upload_csv_content(csv_str, filename="test.csv"):
    boundary = '----WebKitFormBoundaryTest123'
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{csv_str}\r\n"
        f"--{boundary}--\r\n"
    )
    body = header.encode("utf-8")

    req = urllib.request.Request(
        'http://127.0.0.1:8000/upload',
        data=body,
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

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
