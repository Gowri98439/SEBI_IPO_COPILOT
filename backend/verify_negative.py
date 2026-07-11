import sys
import httpx
import time
import os

BASE_URL = "http://localhost:8000/api/v1"
client = httpx.Client(timeout=10.0)

def print_result(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"{name}: {status} {detail}")
    if not passed:
        sys.exit(1)

def run_tests():
    print("Running Negative Tests...")
    
    # 1. Unauthorized Access
    resp = client.get(f"{BASE_URL}/workspaces")
    print_result("Unauthorized Access", resp.status_code == 401, f"Expected 401, got {resp.status_code}")
    
    # 2. Invalid Token
    headers = {"Authorization": "Bearer invalid.token.value"}
    resp = client.get(f"{BASE_URL}/workspaces", headers=headers)
    print_result("Invalid Token", resp.status_code == 401, f"Expected 401, got {resp.status_code}")

    # Login to get token
    resp = client.post(f"{BASE_URL}/auth/login", json={"email": "demo@ipocolpilot.ai", "password": "Demo@1234"})
    if resp.status_code != 200:
        resp = client.post(f"{BASE_URL}/auth/login", json={"email": "demo@ipocolpilot.ai", "password": "password"})
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    # Create workspace
    resp = client.get(f"{BASE_URL}/companies")
    if resp.status_code != 200 or not resp.json():
        print(f"Failed to get companies: {resp.status_code} {resp.text}")
        sys.exit(1)
    company_id = resp.json()[0]["id"]
    resp = client.post(f"{BASE_URL}/workspaces", json={"company_id": company_id, "name": "Negative Test Workspace"})
    if resp.status_code != 201:
        print(f"Failed to create workspace: {resp.status_code} {resp.text}")
        sys.exit(1)
    workspace_id = resp.json()["id"]

    # 3. Empty PDF
    with open("empty.pdf", "wb") as f:
        pass
    with open("empty.pdf", "rb") as f:
        resp = client.post(f"{BASE_URL}/workspaces/{workspace_id}/documents", data={"doc_type": "drhp"}, files={"file": ("empty.pdf", f, "application/pdf")})
    # Might be 400 or 422 for empty file, but definitely not 500
    print_result("Empty PDF", resp.status_code in [400, 422, 500] == False or resp.status_code != 500, f"Got {resp.status_code}")

    # 4. Invalid PDF (Text file renamed)
    with open("invalid.pdf", "w") as f:
        f.write("This is not a PDF")
    with open("invalid.pdf", "rb") as f:
        resp = client.post(f"{BASE_URL}/workspaces/{workspace_id}/documents", data={"doc_type": "drhp"}, files={"file": ("invalid.pdf", f, "application/pdf")})
    print_result("Invalid PDF format", resp.status_code != 500, f"Got {resp.status_code}")
    
    # 5. Missing File
    resp = client.post(f"{BASE_URL}/workspaces/{workspace_id}/documents", data={"doc_type": "drhp"})
    print_result("Missing File Field", resp.status_code == 422, f"Expected 422, got {resp.status_code}")

    # 6. Empty Workspace Compliance
    resp = client.post(f"{BASE_URL}/workspaces/{workspace_id}/compliance/run")
    print_result("Empty Workspace Compliance", resp.status_code != 500, f"Got {resp.status_code}")

    # 7. Valid File Upload
    with open("dummy.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(This is a valid PDF.) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000222 00000 n \n0000000310 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n403\n%%EOF")
    with open("dummy.pdf", "rb") as f:
        resp = client.post(f"{BASE_URL}/workspaces/{workspace_id}/documents", data={"doc_type": "drhp"}, files={"file": ("dummy.pdf", f, "application/pdf")})
    doc_id = resp.json()["id"]
    
    # 8. Repeated Validation
    resp1 = client.post(f"{BASE_URL}/documents/{doc_id}/validate")
    resp2 = client.post(f"{BASE_URL}/documents/{doc_id}/validate")
    print_result("Repeated Validation", resp1.status_code != 500 and resp2.status_code != 500, f"Got {resp1.status_code}, {resp2.status_code}")

    # 9. Repeated Compliance
    resp1 = client.post(f"{BASE_URL}/workspaces/{workspace_id}/compliance/run")
    resp2 = client.post(f"{BASE_URL}/workspaces/{workspace_id}/compliance/run")
    print_result("Repeated Compliance", resp1.status_code != 500 and resp2.status_code != 500, f"Got {resp1.status_code}, {resp2.status_code}")
    
    # 10. Repeated Export
    resp1 = client.get(f"{BASE_URL}/workspaces/{workspace_id}/export/report.pdf")
    resp2 = client.get(f"{BASE_URL}/workspaces/{workspace_id}/export/report.pdf")
    print_result("Repeated Export", resp1.status_code != 500 and resp2.status_code != 500, f"Got {resp1.status_code}, {resp2.status_code}")

    # Clean up
    os.remove("empty.pdf")
    os.remove("invalid.pdf")
    os.remove("dummy.pdf")
    
    print("ALL NEGATIVE TESTS PASSED")

if __name__ == "__main__":
    run_tests()
