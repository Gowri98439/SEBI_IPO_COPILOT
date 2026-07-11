import os
import sys
import httpx
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_outputs():
    # 1. Login
    print("Logging in...")
    client = httpx.Client(timeout=30.0)
    resp = client.post(f"{BASE_URL}/auth/login", json={"email": "demo@ipocolpilot.ai", "password": "password"})
    
    if resp.status_code != 200:
        print("Failed to login, trying demo user password...")
        resp = client.post(f"{BASE_URL}/auth/login", json={"email": "demo@ipocolpilot.ai", "password": "Demo@1234"})
    
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.headers.update(headers)

    # 2. Create Workspace
    print("Creating workspace...")
    resp = client.post(f"{BASE_URL}/workspaces", json={"company_id": "00000000-0000-0000-0000-000000000000", "name": "QA Test Workspace"})
    if resp.status_code != 201:
        # We need a valid company ID
        resp = client.get(f"{BASE_URL}/companies")
        company_id = resp.json()[0]["id"]
        resp = client.post(f"{BASE_URL}/workspaces", json={"company_id": company_id, "name": "QA Test Workspace"})
    
    workspace_id = resp.json()["id"]

    # Create dummy PDF
    with open("dummy.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(This is a test DRHP document for IPO Copilot.) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000222 00000 n \n0000000310 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n403\n%%EOF")

    print("Uploading document...")
    with open("dummy.pdf", "rb") as f:
        resp = client.post(
            f"{BASE_URL}/workspaces/{workspace_id}/documents",
            data={"doc_type": "drhp"},
            files={"file": ("dummy.pdf", f, "application/pdf")}
        )
    doc_id = resp.json()["id"]

    print("Triggering Validation...")
    client.post(f"{BASE_URL}/documents/{doc_id}/validate")
    
    print("Waiting for Validation to finish...")
    for _ in range(30):
        resp = client.get(f"{BASE_URL}/workspaces/{workspace_id}/documents")
        docs = resp.json()
        if docs[0]["status"] == "validated":
            print("Validation finished.")
            break
        time.sleep(2)
    else:
        print("FAIL: Validation timeout.")
        sys.exit(1)

    print("Triggering Compliance...")
    client.post(f"{BASE_URL}/workspaces/{workspace_id}/compliance/run")

    print("Waiting for Compliance and others (30s)...")
    time.sleep(30)

    # 3. Verify Validation
    print("Checking Validation Results...")
    resp = client.get(f"{BASE_URL}/documents/{doc_id}/validation-result")
    if resp.status_code == 200:
        val_data = resp.json()
        if not val_data.get("issues") and not val_data.get("summary"):
            print("FAIL: Validation has NO issues or summary!")
            sys.exit(1)
        if val_data.get("issues") and val_data["issues"][0].get("description") in ["Placeholder", "Loading...", ""]:
            print("FAIL: Validation finding is a placeholder!")
            sys.exit(1)
        print("Validation: PASS (Generated actual findings)")
    else:
        print(f"FAIL: Could not fetch validation: {resp.status_code}")
        sys.exit(1)

    # 4. Verify Compliance
    print("Checking Compliance Results...")
    resp = client.get(f"{BASE_URL}/workspaces/{workspace_id}/compliance")
    if resp.status_code == 200:
        comp_data = resp.json()
        if not comp_data:
            print("FAIL: Compliance is empty!")
            sys.exit(1)
        if not comp_data[0].get("evidence") and not comp_data[0].get("ai_reasoning"):
            print("FAIL: Compliance check has NO issues!")
            sys.exit(1)
        print("Compliance: PASS (Generated actual issues)")
    else:
        print(f"FAIL: Could not fetch compliance: {resp.status_code}")
        sys.exit(1)
        
    # 5. Verify Copilot
    print("Checking Copilot...")
    resp = client.post(f"{BASE_URL}/workspaces/{workspace_id}/copilot/sessions", json={"name": "Test Session"})
    session_id = resp.json()["id"]
    
    resp = client.post(
        f"{BASE_URL}/copilot/sessions/{session_id}/message", 
        json={"content": "What is the purpose of this DRHP?", "action_type": "chat", "context_filters": {}}
    )
    if resp.status_code != 201:
        print(f"FAIL: Copilot message failed: {resp.status_code} {resp.text}")
        sys.exit(1)
        
    print("Reading Copilot stream...")
    # Add SSE query param token
    with client.stream("GET", f"{BASE_URL}/copilot/sessions/{session_id}/stream", params={"token": token}) as response:
        content = ""
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                content += data
                
        if len(content) < 10:
            print(f"FAIL: Copilot response too short: {content}")
            sys.exit(1)
        
    print("Copilot: PASS (Generated actual answer)")

    print("ALL OUTPUTS VERIFIED SUCCESSFULLY")

if __name__ == "__main__":
    test_outputs()
