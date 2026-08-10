import json
import time
import urllib.request
import urllib.error
import urllib.parse
import os
import uuid

BASE = "http://localhost:8000/api/v1"
ARTIFACTS_DIR = r"C:\Users\sgowr\.gemini\antigravity-ide\brain\3e032851-9e54-47c9-8db4-8ca884f78b07"
REPORT_FILE = os.path.join(ARTIFACTS_DIR, "DRHP_RELEASE_VALIDATION_REPORT.md")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def req(method, path, data=None, token=None, json_body=True):
    url = BASE + path
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
        with urllib.request.urlopen(req_obj, timeout=60) as resp:
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

def get_token():
    status, data, _ = req("POST", "/auth/login", {"email": "demo@ipocolpilot.ai", "password": "Demo@1234"})
    if status == 200:
        return data["access_token"]
    raise Exception(f"Failed to login: {data}")

def generate_drhp(token, workspace_id, profile_name, overrides):
    print(f"\n--- Processing Profile: {profile_name} ---")
    
    payload = {
        "company": {
            "name": f"Test Company - {profile_name}",
            "incorporation_date": "2010-01-01",
            "registered_office": "Test Address",
            "registered_address": "Test Address",
            "corporate_office": "Test Address",
            "contact_person": "Test Contact",
            "email": "test@test.com",
            "website": "www.test.com",
            "telephone": "1234567890",
            "industry": "IT Services",
            "sector": "Software",
            "cin": "U72900KA2010PTC123456",
            "pan": "ABCDE1234F",
            "description": "A test company.",
            "business_model": "B2B SaaS",
            "financial_years": [
                {
                    "year": "2023-24",
                    "revenue": 1000.0,
                    "ebitda": 250.0,
                    "net_profit": 150.0,
                    "total_assets": 5000.0,
                    "total_equity": 3000.0,
                    "total_debt": 500.0
                }
            ],
            "key_products": [{"name": "Software", "revenue_contribution_pct": 100.0}],
            "geographies": [{"region": "India", "revenue_contribution_pct": 100.0}]
        },
        "promoters": [
            {
                "name": "Promoter One",
                "age": 45,
                "experience_years": 20,
                "qualification": "MBA",
                "designation": "MD",
                "holding_pct": 51.0
            }
        ],
        "issue": {
            "fresh_issue_shares": 1000000,
            "face_value": 10,
            "issue_price": 100,
            "issue_size_cr": 10.0,
            "price_band_high": 100.0,
            "objects_of_issue": "General Corporate Purposes",
            "merchant_banker": "Test Capital Markets Ltd"
        },
        "industry": {
            "sector": "IT",
            "market_size_cr": 10000,
            "cagr_pct": 15
        },
        "use_of_proceeds": {
            "items": [{"purpose": "General Corporate", "amount_cr": 10.0}]
        }
    }
    
    for key, value in overrides.items():
        if key == "financial_years":
            payload["company"]["financial_years"] = value
        elif key == "issue":
            payload["issue"].update(value)
    
    status, data, _ = req("POST", f"/workspaces/{workspace_id}/drhp/v2/generate", data=payload, token=token)
    if status != 202:
        raise Exception(f"Failed to generate DRHP: HTTP {status} {data}")
    
    job_id = data["job_id"]
    print(f"[{profile_name}] Started generation. Job ID: {job_id}")
    
    max_retries = 30
    for _ in range(max_retries):
        s, d, _ = req("GET", f"/workspaces/{workspace_id}/drhp/v2/status/{job_id}", token=token)
        if s == 200:
            status_val = d.get("status")
            print(f"[{profile_name}] Status: {status_val} | Progress: {d.get('progress')}%")
            if status_val in ["done", "failed", "completed"]:
                break
        else:
            print(f"[{profile_name}] Polling error: HTTP {s} {d}")
        time.sleep(5)
    
    s, pdf_content, ct = req("GET", f"/workspaces/{workspace_id}/drhp/v2/download/{job_id}", token=token)
    if s == 200 and isinstance(pdf_content, bytes):
        pdf_path = os.path.join(ARTIFACTS_DIR, f"DRHP_{profile_name.replace(' ', '_')}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)
        size_kb = len(pdf_content) / 1024
        print(f"[{profile_name}] Downloaded PDF: {pdf_path} ({size_kb:.2f} KB)")
        return pdf_path, size_kb
    else:
        print(f"[{profile_name}] Failed to download PDF. HTTP {s}")
        return None, 0

def run():
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# DRHP Release Validation Report\n\n")
        f.write("Testing 5 DRHP Profiles for Edge Cases.\n\n")

    token = get_token()
    
    status, data, _ = req("GET", "/workspaces", token=token)
    workspace_id = data[0]["id"]
    
    profiles = [
        {
            "name": "Profile_1",
            "overrides": {}
        },
        {
            "name": "Profile_2",
            "overrides": {
                "financial_years": [
                    {
                        "year": "2023-24",
                        "revenue": None,
                        "ebitda": None,
                        "net_profit": None,
                        "total_assets": None,
                        "total_equity": None,
                        "total_debt": None
                    }
                ]
            }
        },
        {
            "name": "Profile_3",
            "overrides": {
                "financial_years": [
                    {
                        "year": "2023-24",
                        "revenue": 100.0,
                        "ebitda": -50.0,
                        "net_profit": -100.0,
                        "total_assets": 500.0,
                        "total_equity": -200.0,
                        "total_debt": 800.0
                    }
                ]
            }
        },
        {
            "name": "Profile_4",
            "overrides": {
                "financial_years": [
                    {
                        "year": "2023-24",
                        "revenue": 500.0,
                        "ebitda": 50.0,
                        "net_profit": 10.0,
                        "total_assets": 10000.0,
                        "total_equity": 100.0,
                        "total_debt": 9000.0,
                        "interest_expense": 900.0
                    }
                ]
            }
        },
        {
            "name": "Profile_5",
            "overrides": {
                "issue": {
                    "fresh_issue_shares": 0,
                    "face_value": 0,
                    "issue_price": 0
                }
            }
        }
    ]
    
    results = []
    for p in profiles:
        try:
            pdf_path, size = generate_drhp(token, workspace_id, p["name"], p["overrides"])
            results.append({"profile": p["name"], "status": "PASS" if pdf_path else "FAIL", "size": size, "path": pdf_path})
        except Exception as e:
            results.append({"profile": p["name"], "status": "FAIL", "error": str(e)})

    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write("## Test Results\n\n")
        f.write("| Profile | Status | PDF Size (KB) | Notes |\n")
        f.write("|---------|--------|---------------|-------|\n")
        for r in results:
            if r["status"] == "PASS":
                f.write(f"| {r['profile']} | ✅ {r['status']} | {r['size']:.2f} | [PDF](file:///{r['path'].replace(chr(92), '/')}) |\n")
            else:
                f.write(f"| {r['profile']} | ❌ {r['status']} | N/A | {r.get('error', 'Failed to generate')} |\n")

if __name__ == "__main__":
    run()
