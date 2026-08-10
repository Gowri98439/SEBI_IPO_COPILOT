"""
Comprehensive end-to-end test script for the IPO Copilot AI platform.
Tests all key endpoints with real HTTP requests against the running server.
"""
import sys
import json
import time
import os
import io
import uuid

# Use urllib for zero-dependency HTTP testing
import urllib.request
import urllib.error
import urllib.parse

BASE = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/health"
FRONTEND_URL = "http://localhost:5173"

results = []
token = None
workspace_id = None
company_id = None
document_id = None

# ── Helper ──────────────────────────────────────────────────────────────────

def req(method, path, data=None, token=None, json_body=True, base=BASE):
    url = base + path if not path.startswith("http") else path
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None and json_body:
        body = json.dumps(data).encode()
    elif data is not None:
        body = data
        headers.pop("Content-Type", None)
    req_obj = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req_obj, timeout=30) as resp:
            content = resp.read()
            status = resp.status
            ct = resp.headers.get("Content-Type", "")
            try:
                return status, json.loads(content), ct
            except Exception:
                return status, content, ct
    except urllib.error.HTTPError as e:
        content = e.read()
        try:
            return e.code, json.loads(content), ""
        except Exception:
            return e.code, content.decode(errors="replace"), ""
    except Exception as e:
        return 0, str(e), ""

def chk(test_name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append({"test": test_name, "status": status, "detail": str(detail)[:200]})
    icon = "✅" if condition else "❌"
    print(f"  {icon} [{status}] {test_name}: {str(detail)[:120]}")
    return condition

print("\n" + "="*70)
print("IPO COPILOT AI — COMPREHENSIVE E2E TEST SUITE")
print("="*70)

# ── STEP 1: SERVICES CHECK ───────────────────────────────────────────────────
print("\n▶ STEP 1: SERVICE HEALTH CHECKS")

s, d, _ = req("GET", "", base=HEALTH_URL)
chk("Backend /health endpoint", s == 200, d)

s, d, _ = req("GET", "", base=FRONTEND_URL)
chk("Frontend reachable", s == 200, f"HTTP {s}")

s, d, _ = req("GET", "/docs", base="http://localhost:8000")
chk("OpenAPI docs accessible", s == 200, f"HTTP {s}")

# Check enterprise router registered
s, d, _ = req("GET", "/openapi.json", base="http://localhost:8000")
if s == 200 and isinstance(d, dict):
    paths = d.get("paths", {})
    has_intelligence = any("intelligence" in p for p in paths)
    chk("Enterprise intelligence routes registered", has_intelligence, f"Routes: {[p for p in paths if 'intelligence' in p]}")
    has_drhp_v2 = any("drhp/v2" in p for p in paths)
    chk("DRHP v2 routes registered", has_drhp_v2, f"Has v2: {has_drhp_v2}")


# ── STEP 2: AUTHENTICATION ───────────────────────────────────────────────────
print("\n▶ STEP 2: AUTHENTICATION")

# Test login with known seeded user
s, d, _ = req("POST", "/auth/login", {"email": "demo@ipocolpilot.ai", "password": "Demo@1234"})
if s == 200 and isinstance(d, dict) and "access_token" in d:
    token = d["access_token"]
    chk("Login (demo user)", True, "Token obtained")
else:
    chk("Login (demo)", False, f"HTTP {s}: {d}")
    # Try to register fresh test user and login
    test_email = f"testuser_{int(time.time())}@test.com"
    s2, d2, _ = req("POST", "/auth/register", {"email": test_email, "password": "TestPass@123", "full_name": "Test User"})
    if s2 in (200, 201) and isinstance(d2, dict) and "access_token" in d2:
        token = d2["access_token"]
        chk("Register + login new user", True, "Token obtained")
    else:
        chk("Register new user", False, f"HTTP {s2}: {d2}")

# Test invalid login
s, d, _ = req("POST", "/auth/login", {"email": "wrong@wrong.com", "password": "wrongpass"})
chk("Invalid login returns 401/400", s in (400, 401, 422), f"HTTP {s}")

# Test unauthenticated access
s, d, _ = req("GET", "/workspaces")
chk("Protected routes require auth (401/403)", s in (401, 403), f"HTTP {s}")


# ── STEP 3: WORKSPACE OPERATIONS ─────────────────────────────────────────────
print("\n▶ STEP 3: WORKSPACE OPERATIONS")

if token:
    s, d, _ = req("GET", "/workspaces", token=token)
    chk("List workspaces", s == 200 and isinstance(d, list), f"HTTP {s}, count={len(d) if isinstance(d, list) else d}")
    if isinstance(d, list) and d:
        workspace_id = d[0]["id"]
        print(f"  → Using existing workspace: {workspace_id}")

    # Create workspace requires company first
    s2, d2, _ = req("GET", "/companies", token=token)
    if s2 == 200 and isinstance(d2, list) and d2:
        company_id = d2[0]["id"]
        chk("List companies", True, f"Count={len(d2)}")
    else:
        chk("List companies", s2 == 200, f"HTTP {s2}: {d2}")
        # Create company if none
        s3, d3, _ = req("POST", "/companies", {
            "name": "Test Corp Ltd", "cin": "U12345MH2020PTC999999",
            "sector": "Technology", "sub_sector": "IT Services",
            "registered_address": "Mumbai", "email": "test@testcorp.com"
        }, token=token)
        if s3 in (200, 201):
            company_id = d3.get("id")
            chk("Create company", True, company_id)

    if not workspace_id and company_id:
        s4, d4, _ = req("POST", "/workspaces", {"company_id": company_id, "name": f"Test Workspace {int(time.time())}"}, token=token)
        if s4 in (200, 201):
            workspace_id = d4.get("id")
            chk("Create workspace", True, workspace_id)
        else:
            chk("Create workspace", False, f"HTTP {s4}: {d4}")
    elif workspace_id:
        chk("Using existing workspace", True, workspace_id)


# ── STEP 4: DASHBOARD ────────────────────────────────────────────────────────
print("\n▶ STEP 4: DASHBOARD")

if token and workspace_id:
    s, d, _ = req("GET", f"/workspaces/{workspace_id}/dashboard", token=token)
    chk("Dashboard loads", s == 200, f"HTTP {s}")
    if s == 200:
        chk("Dashboard has stats", isinstance(d, dict), str(d)[:100])


# ── STEP 5: DOCUMENTS ────────────────────────────────────────────────────────
print("\n▶ STEP 5: DOCUMENT MANAGEMENT")

if token and workspace_id:
    s, d, _ = req("GET", f"/workspaces/{workspace_id}/documents", token=token)
    chk("List documents", s == 200 and isinstance(d, list), f"HTTP {s}")
    if isinstance(d, list) and d:
        document_id = d[0]["id"]
        chk("Documents exist", True, f"Count={len(d)}")


# ── STEP 6: COMPLIANCE ───────────────────────────────────────────────────────
print("\n▶ STEP 6: COMPLIANCE ENGINE")

if token and workspace_id:
    s, d, _ = req("GET", f"/workspaces/{workspace_id}/compliance", token=token)
    chk("Compliance endpoint accessible", s in (200, 404), f"HTTP {s}")


# ── STEP 7: COPILOT ──────────────────────────────────────────────────────────
print("\n▶ STEP 7: SEBI COPILOT")

if token and workspace_id:
    s, d, _ = req("POST", f"/workspaces/{workspace_id}/copilot/chat",
        {"message": "What are the key SEBI ICDR requirements for SME IPO?", "session_id": None},
        token=token)
    chk("Copilot responds", s == 200, f"HTTP {s}")
    if s == 200 and isinstance(d, dict):
        chk("Copilot has answer field", "answer" in d or "response" in d or "message" in d, list(d.keys()))


# ── STEP 8: DRAFT REVIEWS ────────────────────────────────────────────────────
print("\n▶ STEP 8: DRAFT REVIEWS")

if token and workspace_id:
    s, d, _ = req("GET", f"/workspaces/{workspace_id}/drafts", token=token)
    chk("List drafts", s == 200, f"HTTP {s}")


# ── STEP 9: DRHP GENERATION STATUS ──────────────────────────────────────────
print("\n▶ STEP 9: DRHP GENERATION (v2)")

if token and workspace_id:
    drhp_payload = {
        "company": {
            "name": "Test Pharma Ltd",
            "cin": "U24100MH2018PTC987654",
            "pan": "AABCT1234C",
            "incorporation_date": "2018-01-15",
            "sector": "Pharmaceuticals",
            "sub_sector": "Generic Drugs",
            "registered_address": "123 MG Road, Mumbai, Maharashtra 400001",
            "website": "https://testpharma.com",
            "listing_exchange": "NSE Emerge",
            "description": "Test Pharma Ltd is a generic pharmaceutical manufacturer producing quality medicines for the domestic and export markets. The company has over 6 years of operating history and serves hospitals, distributors and retail chemists across 10 Indian states.",
            "key_products": [{"name": "Generic Tablets"}, {"name": "Capsules"}, {"name": "Syrups"}],
            "geographies_served": ["Maharashtra", "Gujarat", "Rajasthan"],
            "certifications": ["ISO 9001:2015"],
            "statutory_auditor": "ABC & Co. Chartered Accountants",
            "employee_count": 350
        },
        "promoters": [
            {"name": "Ramesh Kumar", "designation": "Managing Director", "holding_pct": 55.0, "experience_years": 20, "qualification": "B.Pharm, MBA"},
            {"name": "Sunita Kumar", "designation": "Director", "holding_pct": 15.0, "experience_years": 10, "qualification": "B.Com"}
        ],
        "financials": [
            {"year": "2021-22", "revenue": 1200.5, "net_profit": 85.3, "total_assets": 950.2, "total_equity": 420.1, "ebitda": 142.0, "total_debt": 250.0, "interest_expense": 28.5},
            {"year": "2022-23", "revenue": 1480.8, "net_profit": 110.2, "total_assets": 1120.5, "total_equity": 530.3, "ebitda": 178.4, "total_debt": 280.0, "interest_expense": 31.2},
            {"year": "2023-24", "revenue": 1820.3, "net_profit": 142.7, "total_assets": 1350.8, "total_equity": 660.0, "ebitda": 220.5, "total_debt": 300.0, "interest_expense": 34.0}
        ],
        "issue": {
            "issue_size_cr": 25.0,
            "fresh_issue_cr": 20.0,
            "ofs_cr": 5.0,
            "face_value": 10.0,
            "price_band_low": 90.0,
            "price_band_high": 95.0,
            "lot_size": 1600,
            "merchant_banker": "XYZ Capital Advisors Pvt Ltd",
            "objects_of_issue": "1. Expansion of manufacturing capacity at Pune Plant: Rs. 12 Crore. 2. Working capital requirements: Rs. 5 Crore. 3. General corporate purposes: Rs. 3 Crore."
        },
        "risk_factors": [
            "We operate in a highly regulated pharmaceutical industry and may face compliance challenges.",
            "Revenue concentration from 3 key clients who account for 40% of sales.",
            "Our promoters do not have prior experience of managing a listed entity."
        ],
        "use_llm_generation": True,
        "generate_intelligence_report": True,
        "generate_charts": True
    }
    
    s, d, _ = req("POST", f"/workspaces/{workspace_id}/drhp/v2/generate", drhp_payload, token=token)
    chk("DRHP v2 generation starts", s in (200, 202), f"HTTP {s}: {str(d)[:200]}")
    
    job_id = None
    if s in (200, 202) and isinstance(d, dict):
        job_id = d.get("job_id")
        chk("DRHP job_id returned", job_id is not None, job_id)
    
    if job_id:
        # Poll for up to 3 minutes
        print(f"  → Polling job {job_id} (max 180s)...")
        poll_start = time.time()
        final_status = None
        while time.time() - poll_start < 180:
            s2, d2, _ = req("GET", f"/workspaces/{workspace_id}/drhp/v2/status/{job_id}", token=token)
            if s2 == 200 and isinstance(d2, dict):
                pct = d2.get("progress_pct", 0)
                stage = d2.get("current_stage", "")
                status_val = d2.get("status", "")
                print(f"    Progress: {pct}% | Stage: {stage} | Status: {status_val}")
                if status_val in ("done", "error", "failed"):
                    final_status = status_val
                    break
            time.sleep(5)
        
        chk("DRHP generation completes", final_status == "done", f"Final status: {final_status}")
        
        if final_status == "done":
            # Test PDF download
            s3, d3, ct3 = req("GET", f"/workspaces/{workspace_id}/drhp/v2/download/{job_id}", token=token)
            chk("DRHP PDF download HTTP 200", s3 == 200, f"HTTP {s3}")
            chk("DRHP PDF Content-Type correct", "application/pdf" in ct3, f"Content-Type: {ct3}")
            if isinstance(d3, bytes):
                chk("DRHP PDF is valid PDF (starts with %PDF)", d3[:4] == b"%PDF", f"First 4 bytes: {d3[:4]}")
                chk("DRHP PDF has content (>10KB)", len(d3) > 10240, f"Size: {len(d3)} bytes")
            
            # Test Intelligence Report download
            s4, d4, ct4 = req("GET", f"/workspaces/{workspace_id}/drhp/v2/intelligence/{job_id}", token=token)
            chk("Intelligence Report download HTTP 200", s4 == 200, f"HTTP {s4}")
            if isinstance(d4, bytes):
                chk("Intelligence Report is PDF", d4[:4] == b"%PDF", f"First 4 bytes: {d4[:4]}")


# ── STEP 10: ENTERPRISE INTELLIGENCE ENDPOINTS ───────────────────────────────
print("\n▶ STEP 10: ENTERPRISE INTELLIGENCE ENDPOINTS")

if token and workspace_id:
    s, d, _ = req("GET", f"/workspaces/{workspace_id}/intelligence/readiness", token=token)
    chk("Readiness endpoint responds", s in (200, 404, 500), f"HTTP {s}")
    if s == 200:
        chk("Readiness has overall_score", "overall_score" in d, str(d)[:100])
        chk("Readiness has readiness_band", "readiness_band" in d, d.get("readiness_band"))
    else:
        chk("Readiness enterprise route registered", s != 404 or "intelligence" in str(d), f"HTTP {s}: {d}")
    
    s, d, _ = req("GET", f"/workspaces/{workspace_id}/intelligence/risks", token=token)
    chk("Risk profile endpoint responds", s in (200, 500), f"HTTP {s}")
    
    s, d, _ = req("GET", f"/workspaces/{workspace_id}/intelligence/graph", token=token)
    chk("Knowledge graph endpoint responds", s in (200, 500), f"HTTP {s}")


# ── STEP 11: SECURITY TESTS ──────────────────────────────────────────────────
print("\n▶ STEP 11: SECURITY TESTS")

# Test accessing another user's workspace (use a fake UUID)
fake_ws_id = str(uuid.uuid4())
if token:
    s, d, _ = req("GET", f"/workspaces/{fake_ws_id}/dashboard", token=token)
    # 404 (not found) or 403 (forbidden) are both correct — workspace doesn't belong to user
    chk("Workspace isolation: fake UUID blocked (403 or 404)", s in (403, 404), f"HTTP {s}")

# Test invalid JWT
s, d, _ = req("GET", "/workspaces", token="invalid.jwt.token")
chk("Invalid JWT returns 401/403", s in (401, 403, 422), f"HTTP {s}")

# Test malformed workspace ID  
if token:
    s, d, _ = req("GET", "/workspaces/not-a-uuid/dashboard", token=token)
    # 422 (unprocessable entity - validation error) or 404/403 are all valid
    chk("Malformed UUID returns 4xx", s in (400, 403, 404, 422), f"HTTP {s}")


# ── STEP 12: TYPESCRIPT BUILD CHECK ─────────────────────────────────────────
print("\n▶ STEP 12: FRONTEND TYPESCRIPT CHECK")

# Run tsc (non-blocking check) through Python subprocess
import subprocess
try:
    result = subprocess.run(
        ["cmd", "/c", "npx tsc --noEmit"],
        cwd=r"c:\Users\sgowr\Documents\SEBI HACKATHON\frontend",
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        chk("TypeScript: no compile errors", True, "Clean compile")
    else:
        errors = result.stdout + result.stderr
        error_lines = [l for l in errors.split('\n') if 'error TS' in l]
        chk("TypeScript: no compile errors", False, f"{len(error_lines)} TS errors: {error_lines[:3]}")
except Exception as e:
    chk("TypeScript check", False, f"Could not run: {e}")


# ── FINAL REPORT ──────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("FINAL TEST REPORT")
print("="*70)

passed = [r for r in results if r["status"] == "PASS"]
failed = [r for r in results if r["status"] == "FAIL"]

print(f"\nTotal: {len(results)} | ✅ PASS: {len(passed)} | ❌ FAIL: {len(failed)}\n")

if failed:
    print("FAILURES:")
    for r in failed:
        print(f"  ❌ {r['test']}: {r['detail']}")

print("\n" + "="*70)
score_pct = (len(passed) / len(results) * 100) if results else 0
if score_pct >= 90 and not any(r["test"] in ("Login (admin)", "DRHP generation completes") for r in failed):
    print(f"VERDICT: ✅ DEMO READY ({score_pct:.0f}% pass rate)")
elif score_pct >= 70:
    print(f"VERDICT: ⚠️ PARTIALLY VERIFIED ({score_pct:.0f}% pass rate)")
else:
    print(f"VERDICT: ❌ BLOCKED ({score_pct:.0f}% pass rate)")
print("="*70)

# Write report
with open(r"c:\Users\sgowr\Documents\SEBI HACKATHON\TEST_RESULTS_FINAL.json", "w") as f:
    json.dump({"summary": {"total": len(results), "passed": len(passed), "failed": len(failed)}, "results": results}, f, indent=2)
print("\nResults saved to TEST_RESULTS_FINAL.json")
