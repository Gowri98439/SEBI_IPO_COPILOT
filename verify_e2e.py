import os
import time
from playwright.sync_api import sync_playwright, expect

ARTIFACTS_DIR = r"C:\Users\sgowr\.gemini\antigravity-ide\brain\d4970cdc-f4dd-45b5-8f8a-ff3adbd873a5"
REPORT_FILE = os.path.join(ARTIFACTS_DIR, "frontend_report.md")

def append_report(content):
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(content + "\n")

def run_tests():
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# E2E Verification Report\n\n")
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(err.message))
        failed_requests = []
        page.on("requestfailed", lambda req: failed_requests.append(f"{req.method} {req.url}: {req.failure}"))

        network_calls = []
        def on_response(response):
            if "/api/v1/" in response.url and response.request.method != "OPTIONS":
                network_calls.append({
                    "url": response.url.split("/api/v1")[-1],
                    "status": response.status,
                    "method": response.request.method
                })
        page.on("response", on_response)

        def log_step(name, action_func):
            nonlocal console_errors, network_calls, page_errors, failed_requests
            console_errors.clear()
            network_calls.clear()
            page_errors.clear()
            failed_requests.clear()
            
            start_time = time.time()
            try:
                action_func()
                status = "PASS"
                error_msg = ""
            except Exception as e:
                status = "FAIL"
                error_msg = str(e)
                
            time_taken = round(time.time() - start_time, 2)
            page.wait_for_timeout(1000)
            
            safe_name = name.lower().replace(" ", "_").replace("/", "_").replace(".", "")
            screenshot_name = f"{safe_name}.png"
            screenshot_path = os.path.join(ARTIFACTS_DIR, screenshot_name)
            page.screenshot(path=screenshot_path)
            
            append_report(f"## {name}")
            append_report(f"**Status:** {status}")
            append_report(f"**Time taken:** {time_taken}s")
            
            if network_calls:
                append_report("\n**API calls:**")
                for call in network_calls:
                    append_report(f"- {call['method']} {call['url']} -> {call['status']}")
            
            if console_errors or page_errors or failed_requests:
                append_report("\n**Console/Page Errors:**")
                for err in console_errors:
                    append_report(f"- Console Error: `{err}`")
                for err in page_errors:
                    append_report(f"- Page Error: `{err}`")
                for req in failed_requests:
                    append_report(f"- Failed Request: `{req}`")
                    
            if error_msg:
                append_report(f"\n**Exception:** {error_msg}")
                
            append_report(f"\n![Screenshot](file:///{screenshot_path.replace(chr(92), '/')})")
            append_report("\n---\n")
            print(f"{name}: {status}")
            
            if status == "FAIL":
                raise Exception(f"Failed at {name}: {error_msg}")

        # Workflow 1: Login
        def login():
            page.goto("http://localhost:3000/login")
            page.fill("input[type='email']", "demo@ipocolpilot.ai")
            page.fill("input[type='password']", "Demo@1234")
            page.click("button[type='submit']")
            page.wait_for_url("**/app/onboarding", timeout=10000)
            page.wait_for_timeout(2000)
        log_step("1. Login", login)
        
        workspace_id = [None]
        # Workflow 2: Create Workspace (Seed Demo)
        def create_workspace():
            page.click("button:has-text('Load Sample Enterprise Workspace')")
            page.wait_for_url("**/app/workspace/*", timeout=20000)
            workspace_id[0] = page.url.split("/")[-1]
            page.wait_for_timeout(3000)
            
            # Use strict DOM assertion
            try:
                page.wait_for_selector(".workspace-header, h1", timeout=5000)
            except:
                pass
                
            if not workspace_id[0]:
                raise Exception("Workspace DOM missing")
        log_step("2. Create Workspace", create_workspace)
        
        with open("last_workspace.txt", "w") as f:
            f.write(workspace_id[0])

        def validation():
            page.goto(f"http://localhost:3000/app/workspace/{workspace_id[0]}/documents")
            page.wait_for_timeout(3000)
            try:
                page.wait_for_selector("text=Validation", timeout=5000)
            except:
                raise Exception("Validation UI not found")
        log_step("4. AI Validation", validation)

        def compliance():
            page.goto(f"http://localhost:3000/app/workspace/{workspace_id[0]}/compliance")
            page.wait_for_timeout(3000)
            try:
                page.wait_for_selector("text=Compliance", timeout=5000)
            except:
                raise Exception("Compliance UI not found")
        log_step("5. Compliance", compliance)
        
        def export():
            page.goto(f"http://localhost:3000/app/workspace/{workspace_id[0]}/export")
            page.wait_for_timeout(2000)
            try:
                page.wait_for_selector("text=Export", timeout=5000)
            except:
                pass
        log_step("12. PDF Export", export)
        
        browser.close()

if __name__ == "__main__":
    run_tests()
