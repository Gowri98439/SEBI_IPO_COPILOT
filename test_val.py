import requests
import time

BASE_URL = "http://localhost:8000/api/v1"
s = requests.Session()

print("Testing Validation API...")

r = s.post(f"{BASE_URL}/auth/login", json={"email": "demo@ipocolpilot.ai", "password": "Demo@1234"})
token = r.json()["access_token"]
s.headers.update({"Authorization": f"Bearer {token}"})

r_companies = s.get(f"{BASE_URL}/companies")
company_id = r_companies.json()[0]["id"]

r = s.post(f"{BASE_URL}/workspaces", json={"name": "API Test Workspace", "company_id": company_id})
workspace_id = r.json()["id"]

with open("backend/test_prospectus.pdf", "rb") as f:
    r = s.post(f"{BASE_URL}/workspaces/{workspace_id}/documents", files={"file": ("test_prospectus.pdf", f, "application/pdf")})
doc_id = r.json()["id"]

print("Doc ID:", doc_id)

r = s.post(f"{BASE_URL}/documents/{doc_id}/validate")
print("Validation Started:", r.status_code)

while True:
    r = s.get(f"{BASE_URL}/workspaces/{workspace_id}")
    docs = r.json().get("documents", [])
    for d in docs:
        if d["id"] == doc_id:
            status = d["status"]
            print("Status:", status)
            if status in ["validated", "failed"]:
                if status == "failed":
                    print("Validation FAILED!")
                else:
                    print("Validation SUCCEEDED!")
                exit(0)
    time.sleep(2)
