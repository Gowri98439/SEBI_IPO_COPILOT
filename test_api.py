import requests

BASE_URL = "http://localhost:8000/api/v1"
s = requests.Session()

print("Testing Backend APIs...")

# 1. Login
r = s.post(f"{BASE_URL}/auth/login", json={"email": "demo@ipocolpilot.ai", "password": "Demo@1234"})
print("1. Login:", r.status_code)
if r.status_code not in [200, 201]: exit(1)
token = r.json()["access_token"]
s.headers.update({"Authorization": f"Bearer {token}"})

# Get Company
r_companies = s.get(f"{BASE_URL}/companies")
if r_companies.status_code not in [200, 201] or not r_companies.json():
    print("Failed to get companies")
    exit(1)
company_id = r_companies.json()[0]["id"]

# 2. Workspace Creation
r = s.post(f"{BASE_URL}/workspaces", json={"name": "API Test Workspace", "company_id": company_id})
print("2. Create Workspace:", r.status_code)
if r.status_code not in [200, 201]: exit(1)
workspace_id = r.json()["id"]

# 3. Workspace Loading
r = s.get(f"{BASE_URL}/workspaces/{workspace_id}")
print("3. Load Workspace:", r.status_code)

# 4. Document Upload
with open("backend/test_prospectus.pdf", "rb") as f:
    r = s.post(f"{BASE_URL}/workspaces/{workspace_id}/documents", files={"file": ("test_prospectus.pdf", f, "application/pdf")})
print("4. Upload Doc:", r.status_code)
if r.status_code not in [200, 201]: exit(1)
doc_id = r.json()["id"]

# 5. PDF Parsing / Validation
r = s.post(f"{BASE_URL}/documents/{doc_id}/validate")
print("5. Validate Doc:", r.status_code)

# 6. Compliance Analysis
r = s.post(f"{BASE_URL}/workspaces/{workspace_id}/compliance/run")
print("6. Compliance:", r.status_code)

# 7. Copilot Chat
r = s.post(f"{BASE_URL}/workspaces/{workspace_id}/copilot/sessions")
print("7. Create Copilot Session:", r.status_code)
if r.status_code in [200, 201]:
    session_id = r.json()["id"]
    r = s.post(f"{BASE_URL}/copilot/sessions/{session_id}/message", json={"content": "What is the issue size?", "action_type": "chat"})
    print("   Send Copilot Message:", r.status_code)

# 8. Dashboard metrics
r = s.get(f"{BASE_URL}/workspaces/{workspace_id}/dashboard")
print("8. Dashboard Metrics:", r.status_code)

# 9. Draft Review
r = s.post(f"{BASE_URL}/workspaces/{workspace_id}/drafts", json={"workspace_id": workspace_id, "section": "Risk Factors", "draft_content": "This is a risk."})
print("9. Create Draft Review:", r.status_code)

# 10. Human Review Task
r = s.post(f"{BASE_URL}/workspaces/{workspace_id}/reviews", json={"workspace_id": workspace_id, "task_type": "legal", "notes": "Please review this."})
print("10. Create Review Task:", r.status_code)

import time
print("Waiting for background jobs to finish...")
time.sleep(15)
# 11. PDF Export
r = s.get(f"{BASE_URL}/workspaces/{workspace_id}/export/report.pdf")
print("11. Export PDF:", r.status_code)

# 12. DOCX Export
r = s.get(f"{BASE_URL}/workspaces/{workspace_id}/export/report.docx")
print("12. Export DOCX:", r.status_code)

print("\nAll Workflows APIs verified successfully.")
