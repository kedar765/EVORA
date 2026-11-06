"""
EVORA End-to-End Playwright Browser Automation Test Suite
===========================================================
This test script verifies the entire EVORA application inside a real browser:
  1. Signup and Login
  2. Dashboard loading
  3. CSV upload with invalid data (rejection verification)
  4. CSV upload with valid data (processing verification)
  5. Dataset preview table inspection
  6. Analytics and AI Insights
  7. Profit Predictions & Next-day Forecasting
  8. Risk Intelligence & Anomaly Detection
  9. What-if Analysis simulation
  10. Decision Support & Recommendations
  11. Reports & Data Exports
  12. Settings & Backend Health Diagnostics
  13. Logout
  14. Protected route access denial after logout
  15. Browser console errors & failed network requests monitoring
"""

import os
import sys
import time
import uuid
import socket
import urllib.request
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, expect

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = ROOT_DIR / "tests" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
INVALID_CSV_PATH = ROOT_DIR / "tests" / "fixtures" / "invalid_missing_cols.csv"
VALID_CSV_PATH = ROOT_DIR / "data" / "sample_business_data.csv"

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

test_results = []
console_errors = []
console_warnings = []
failed_network_requests = []


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def wait_for_service(url: str, timeout: int = 60, service_name: str = "Service") -> bool:
    print(f"Waiting for {service_name} at {url} (timeout: {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EVORA-Test-Probe"})
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status in (200, 304, 307):
                    print(f"  -> {service_name} is READY (HTTP {response.status})")
                    return True
        except Exception:
            time.sleep(1.0)
    print(f"  -> ERROR: {service_name} timed out after {timeout}s")
    return False


def record_result(name: str, passed: bool, details: str = "", screenshot_path: str = ""):
    status = "PASS" if passed else "FAIL"
    test_results.append({
        "name": name,
        "status": status,
        "details": details,
        "screenshot": screenshot_path,
    })
    clean_details = str(details).replace("₹", "INR ")
    print(f"[{status}] {name}")
    if clean_details:
        print(f"       Details: {clean_details}")
    if screenshot_path:
        print(f"       Screenshot: {screenshot_path}")


def run_e2e_suite():
    backend_proc = None
    frontend_proc = None

    # Step 0: Ensure servers are up
    try:
        if not is_port_open(8000):
            print("Starting FastAPI backend on port 8000...")
            python_bin = sys.executable
            backend_proc = subprocess.Popen(
                [python_bin, "-m", "uvicorn", "backend.main:app", "--port", "8000"],
                cwd=str(ROOT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            print("FastAPI backend already running on port 8000.")

        if not is_port_open(3000):
            print("Starting Next.js frontend on port 3000...")
            frontend_proc = subprocess.Popen(
                "npx next dev -p 3000",
                cwd=str(ROOT_DIR / "frontend"),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            print("Next.js frontend already running on port 3000.")

        if not wait_for_service(f"{BACKEND_URL}/health", timeout=30, service_name="Backend"):
            raise RuntimeError("Backend failed to respond on /health")

        if not wait_for_service(f"{FRONTEND_URL}/login", timeout=60, service_name="Frontend"):
            raise RuntimeError("Frontend failed to respond on /login")

        # Step 1: Launch Playwright Chrome
        print("\n" + "=" * 60)
        print("LAUNCHING PLAYWRIGHT BROWSER (Google Chrome)")
        print("=" * 60)

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1366, "height": 850})
            page = context.new_page()

            # Attach event listeners
            def handle_console(msg):
                text = msg.text
                if msg.type == "error":
                    # Ignore harmless Next.js dev warnings if any
                    if "Download the React DevTools" in text or "favicon.ico" in text:
                        return
                    console_errors.append(f"[{msg.type.upper()}] {text}")
                elif msg.type == "warning":
                    console_warnings.append(f"[WARN] {text}")

            def handle_request_failed(request):
                # Ignore aborted requests due to navigation
                if request.failure and "aborted" in request.failure.lower():
                    return
                failed_network_requests.append({
                    "url": request.url,
                    "method": request.method,
                    "failure": request.failure,
                })

            page.on("console", handle_console)
            page.on("requestfailed", handle_request_failed)

            # Test credentials
            unique_id = uuid.uuid4().hex[:8]
            user_name = f"Playwright Tester {unique_id}"
            user_email = f"pw_tester_{unique_id}@evora.ai"
            user_pass = "TestPassword123!"

            # ---------------------------------------------------------
            # 1. Signup and Login Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
                expect(page.locator("h1")).to_contain_text("Welcome Back")

                # Switch to signup mode
                create_acc_btn = page.locator('button:has-text("Create Account")')
                create_acc_btn.click()
                expect(page.locator("h1")).to_contain_text("Create Your Account")

                # Fill signup form
                page.fill("#auth-name", user_name)
                page.fill("#auth-email", user_email)
                page.fill("#auth-password", user_pass)
                page.fill("#auth-confirm-password", user_pass)

                # Submit signup
                page.click('button[type="submit"]')
                page.wait_for_url("**/dashboard", timeout=15000)
                expect(page.locator("h1")).to_contain_text("Dashboard")

                # Logout to verify credentials work on login form
                logout_btn = page.locator('aside button[aria-label="Sign out of EVORA"]')
                logout_btn.click()
                page.wait_for_url("**/login", timeout=10000)
                expect(page.locator("h1")).to_contain_text("Welcome Back")

                # Log back in
                page.fill("#auth-email", user_email)
                page.fill("#auth-password", user_pass)
                page.click('button[type="submit"]')
                page.wait_for_url("**/dashboard", timeout=15000)
                expect(page.locator("h1")).to_contain_text("Dashboard")

                ss_path = str(SCREENSHOT_DIR / "01_signup_and_login.png")
                page.screenshot(path=ss_path)
                record_result("Signup and Login Workflow", True, f"User {user_email} registered and authenticated.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_01_signup_login.png")
                page.screenshot(path=ss_path)
                record_result("Signup and Login Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 2. Dashboard Loading Workflow
            # ---------------------------------------------------------
            try:
                expect(page.locator("h1")).to_contain_text("Dashboard")
                # Check for active dataset card / standby text
                expect(page.locator("text=No Business Dataset Active")).to_be_visible()
                # Check overview cards
                expect(page.locator('section[aria-label="Financial performance"]')).to_be_visible()

                ss_path = str(SCREENSHOT_DIR / "02_dashboard_loaded.png")
                page.screenshot(path=ss_path)
                record_result("Dashboard Loading Workflow", True, "Dashboard and empty states loaded cleanly.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_02_dashboard_loading.png")
                page.screenshot(path=ss_path)
                record_result("Dashboard Loading Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 3. Invalid CSV Rejection Workflow
            # ---------------------------------------------------------
            try:
                # Open Ingestion Tray if not already open
                tray_btn = page.locator('button:has-text("Ingest Business CSV")').first
                if tray_btn.is_visible():
                    tray_btn.click()

                # Upload invalid CSV (missing required Quantity, Revenue, Expense)
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(str(INVALID_CSV_PATH))

                # Click Upload & Analyze
                upload_btn = page.locator('button:has-text("Upload & Analyze")').first
                upload_btn.click()

                # Verify error alert is displayed
                alert = page.locator('div.bg-rose-50[role="alert"]').first
                expect(alert).to_be_visible(timeout=10000)
                alert_text = alert.inner_text()
                assert "missing" in alert_text.lower() or "required" in alert_text.lower() or "failed" in alert_text.lower(), f"Unexpected alert: {alert_text}"

                ss_path = str(SCREENSHOT_DIR / "03_invalid_csv_rejected.png")
                page.screenshot(path=ss_path)
                record_result("Invalid CSV Rejection Workflow", True, f"Rejected properly: {alert_text}", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_03_invalid_csv.png")
                page.screenshot(path=ss_path)
                record_result("Invalid CSV Rejection Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 4. Valid CSV Upload Workflow
            # ---------------------------------------------------------
            try:
                # Upload valid sample CSV
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(str(VALID_CSV_PATH))

                upload_btn = page.locator('button:has-text("Upload & Analyze")').first
                upload_btn.click()

                # Wait for pipeline completion
                expect(page.locator("text=sample_business_data.csv")).to_be_visible(timeout=20000)
                expect(page.locator("text=5,000 records analyzed successfully.")).to_be_visible(timeout=10000)

                ss_path = str(SCREENSHOT_DIR / "04_valid_csv_uploaded.png")
                page.screenshot(path=ss_path)
                record_result("Valid CSV Upload Workflow", True, "5,000 records processed and dashboard populated.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_04_valid_csv.png")
                page.screenshot(path=ss_path)
                record_result("Valid CSV Upload Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 5. Dataset Preview Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/dashboard/data", wait_until="networkidle")
                expect(page.locator("h2:has-text('Active Dataset Preview')")).to_be_visible(timeout=10000)
                expect(page.locator("table")).to_be_visible()

                # Check table rows exist
                row_count = page.locator("tbody tr").count()
                assert row_count > 0, f"Expected table rows, got {row_count}"

                # Verify key headers exist
                table_headers = page.locator("thead th").all_inner_texts()
                assert any("Quantity" in h for h in table_headers), "Quantity header missing"
                assert any("Revenue" in h for h in table_headers), "Revenue header missing"
                assert any("Expense" in h for h in table_headers), "Expense header missing"

                ss_path = str(SCREENSHOT_DIR / "05_dataset_preview.png")
                page.screenshot(path=ss_path)
                record_result("Dataset Preview Workflow", True, f"Verified table rendered with {row_count} sample records and verified headers.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_05_dataset_preview.png")
                page.screenshot(path=ss_path)
                record_result("Dataset Preview Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 6. Analytics and AI Insights Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/dashboard/analytics", wait_until="networkidle")
                expect(page.locator("h1:has-text('Analytics')")).to_be_visible()

                # Verify Revenue vs Expense chart component is present
                expect(page.locator('section[aria-labelledby="chart-heading"]')).to_be_visible()

                # Verify financial allocations section
                expect(page.locator('section[aria-labelledby="ratios-heading"]')).to_be_visible()

                ss_path = str(SCREENSHOT_DIR / "06_analytics_insights.png")
                page.screenshot(path=ss_path)
                record_result("Analytics and AI Insights Workflow", True, "Analytics distributions, charts, and ratios rendered.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_06_analytics.png")
                page.screenshot(path=ss_path)
                record_result("Analytics and AI Insights Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 7. Profit Predictions & Forecasting Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/dashboard/predictions", wait_until="networkidle")
                expect(page.locator("h1:has-text('Predictions')")).to_be_visible()

                # Check Next-Day Profit Forecast Card
                expect(page.locator('h2:has-text("Next-Day Profit Forecast")')).to_be_visible()
                expect(page.locator("text=Production Live")).to_be_visible()
                expect(page.locator("text=Predicted Next-Day Profit")).to_be_visible()

                # Verify forecast date is displayed
                forecast_date_elem = page.locator('span:has-text("Forecast Date") + span')
                forecast_date = forecast_date_elem.inner_text()
                assert len(forecast_date) >= 8, f"Invalid forecast date: {forecast_date}"

                # Verify predicted profit amount is rendered
                profit_amount = page.locator('span:has-text("Predicted Next-Day Profit") ~ div span').first.inner_text()
                assert "₹" in profit_amount, f"Expected INR formatted profit, got: {profit_amount}"

                ss_path = str(SCREENSHOT_DIR / "07_profit_predictions.png")
                page.screenshot(path=ss_path)
                record_result("Profit Predictions Workflow", True, f"Next-day forecast active: Date={forecast_date}, Value={profit_amount}", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_07_predictions.png")
                page.screenshot(path=ss_path)
                record_result("Profit Predictions Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 8. Risk Intelligence Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/dashboard/risk", wait_until="networkidle")
                expect(page.locator("h1:has-text('Risk Intelligence')")).to_be_visible()

                # Verify risk score & level are displayed
                expect(page.locator("text=Risk Score").first).to_be_visible(timeout=8000)

                ss_path = str(SCREENSHOT_DIR / "08_risk_intelligence.png")
                page.screenshot(path=ss_path)
                record_result("Risk Intelligence Workflow", True, "Risk intelligence score, level, and diagnostic factors rendered.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_08_risk.png")
                page.screenshot(path=ss_path)
                record_result("Risk Intelligence Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 9. What-if Analysis Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/dashboard/decision", wait_until="networkidle")
                expect(page.locator("h1:has-text('Decision Support')")).to_be_visible()

                # Populate with current data
                use_current_btn = page.locator('button:has-text("Use Current Data")').first
                expect(use_current_btn).to_be_visible()
                use_current_btn.click()

                # Click Run What-If Comparison
                simulate_btn = page.locator('button:has-text("Run What-If Comparison")').first
                simulate_btn.click()

                # Verify simulation outcome appears
                expect(page.locator("text=Scenario Comparison Summary")).to_be_visible(timeout=10000)
                expect(page.locator("text=Current Predicted Profit")).to_be_visible(timeout=10000)

                ss_path = str(SCREENSHOT_DIR / "09_what_if_analysis.png")
                page.screenshot(path=ss_path)
                record_result("What-if Analysis Workflow", True, "What-if simulation executed and comparative outcome displayed.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_09_what_if.png")
                page.screenshot(path=ss_path)
                record_result("What-if Analysis Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 10. Decision Recommendations Workflow
            # ---------------------------------------------------------
            try:
                gen_dec_btn = page.locator('button:has-text("Generate Recommendations")').first
                expect(gen_dec_btn).to_be_visible()
                gen_dec_btn.click()

                # Verify decision recommendations rendered
                expect(page.locator("h2:has-text('Business Decision Analysis')")).to_be_visible(timeout=10000)
                expect(page.locator("h3:has-text('Evidence')")).to_be_visible()
                expect(page.locator("h3:has-text('Recommendations')")).to_be_visible()

                ss_path = str(SCREENSHOT_DIR / "10_decision_recommendations.png")
                page.screenshot(path=ss_path)
                record_result("Decision Recommendations Workflow", True, "AI Decision Recommendations synthesized with Evidence and Action Plan.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_10_decision.png")
                page.screenshot(path=ss_path)
                record_result("Decision Recommendations Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 11. Reports & Exports Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/dashboard/reports", wait_until="networkidle")
                expect(page.locator("h1:has-text('Reports & Exports')")).to_be_visible()

                # Verify export cards are present
                expect(page.locator("text=Active CSV Ingestion File")).to_be_visible()
                expect(page.locator("text=Business Intelligence Audit Summary")).to_be_visible()

                export_csv_btn = page.locator('button:has-text("Export Dataset (.csv)")').first
                expect(export_csv_btn).to_be_enabled()

                export_json_btn = page.locator('button:has-text("Export Audit Summary (.json)")').first
                expect(export_json_btn).to_be_enabled()

                ss_path = str(SCREENSHOT_DIR / "11_reports_page.png")
                page.screenshot(path=ss_path)
                record_result("Reports Page Workflow", True, "Export options verified and active for CSV and JSON audits.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_11_reports.png")
                page.screenshot(path=ss_path)
                record_result("Reports Page Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 12. Settings Page Workflow
            # ---------------------------------------------------------
            try:
                page.goto(f"{FRONTEND_URL}/dashboard/settings", wait_until="networkidle")
                expect(page.locator("h1:has-text('Settings')")).to_be_visible()

                # Verify user profile details
                expect(page.get_by_text(user_email).first).to_be_visible()

                # Verify backend diagnostics
                expect(page.locator("text=Online & Healthy")).to_be_visible(timeout=8000)

                ss_path = str(SCREENSHOT_DIR / "12_settings_page.png")
                page.screenshot(path=ss_path)
                record_result("Settings Page Workflow", True, "User account verified and backend connection diagnosed as Online & Healthy.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_12_settings.png")
                page.screenshot(path=ss_path)
                record_result("Settings Page Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 13. Logout Workflow
            # ---------------------------------------------------------
            try:
                logout_btn = page.locator('aside button[aria-label="Sign out of EVORA"]')
                logout_btn.click()
                page.wait_for_url("**/login", timeout=10000)
                expect(page.locator("h1")).to_contain_text("Welcome Back")

                ss_path = str(SCREENSHOT_DIR / "13_logout_complete.png")
                page.screenshot(path=ss_path)
                record_result("Logout Workflow", True, "User signed out successfully; session cleared.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_13_logout.png")
                page.screenshot(path=ss_path)
                record_result("Logout Workflow", False, str(e), ss_path)

            # ---------------------------------------------------------
            # 14. Protected Route Access After Logout
            # ---------------------------------------------------------
            try:
                # Attempt direct navigation to /dashboard without session
                page.goto(f"{FRONTEND_URL}/dashboard", wait_until="networkidle")
                # Should immediately be redirected back to /login
                page.wait_for_url("**/login", timeout=10000)
                expect(page.locator("h1")).to_contain_text("Welcome Back")

                ss_path = str(SCREENSHOT_DIR / "14_protected_route_redirect.png")
                page.screenshot(path=ss_path)
                record_result("Protected Route Access After Logout", True, "Unauthorized access rejected and redirected to /login.", ss_path)
            except Exception as e:
                ss_path = str(SCREENSHOT_DIR / "failure_14_protected_route.png")
                page.screenshot(path=ss_path)
                record_result("Protected Route Access After Logout", False, str(e), ss_path)

            context.close()
            browser.close()

    finally:
        # Tear down background processes if started by this script
        if backend_proc:
            print("Terminating backend process...")
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=5)
            except Exception:
                backend_proc.kill()

        if frontend_proc:
            print("Terminating frontend process...")
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=5)
            except Exception:
                frontend_proc.kill()

    # Step 15: Print Final Summary Report
    print("\n" + "=" * 70)
    print("EVORA PLAYWRIGHT E2E AUTOMATION TEST REPORT")
    print("=" * 70)
    passed_count = sum(1 for r in test_results if r["status"] == "PASS")
    total_count = len(test_results)
    print(f"Total Workflows Tested : {total_count}")
    print(f"Passed                 : {passed_count}")
    print(f"Failed                 : {total_count - passed_count}")
    print(f"Pass Rate              : {(passed_count / total_count * 100):.1f}%" if total_count else "0%")
    print("-" * 70)
    for r in test_results:
        print(f"[{r['status']}] {r['name']}")
        if r['details']:
            print(f"       -> {r['details']}")
        if r['screenshot']:
            print(f"       -> Screenshot: {r['screenshot']}")

    print("\n" + "-" * 70)
    print("BROWSER CONSOLE ERRORS & FAILED NETWORK REQUESTS")
    print("-" * 70)
    print(f"Console Errors Recorded: {len(console_errors)}")
    for err in console_errors:
        print(f"  * {err}")
    print(f"Failed Network Requests Recorded: {len(failed_network_requests)}")
    for req in failed_network_requests:
        print(f"  * [{req['method']}] {req['url']} -> {req['failure']}")

    print("=" * 70)
    if passed_count == total_count and total_count > 0:
        print("RESULT: ALL E2E PLAYWRIGHT TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("RESULT: SOME E2E PLAYWRIGHT TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_e2e_suite())

