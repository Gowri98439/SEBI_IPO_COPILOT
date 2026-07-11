import asyncio
import httpx
import os
import time

BASE_URL = "http://localhost:8000/api/v1"

async def verify_all():
    print("Starting End-to-End Verification...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Register & Login
        email = f"test_{int(time.time())}@example.com"
        print(f"Registering {email}...")
        res = await client.post(f"{BASE_URL}/auth/register", json={
            "email": email, "password": "password123", "full_name": "E2E Tester"
        })
        assert res.status_code == 201, f"Register failed: {res.text}"
        
        print("Logging in...")
        res = await client.post(f"{BASE_URL}/auth/login", json={
            "email": email, "password": "password123"
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Company
        print("Creating company...")
        res = await client.post(f"{BASE_URL}/companies", headers=headers, json={
            "name": "E2E Test Corp", "cin": "U12345MH2024PTC123456", "pan": "ABCDE1234F", "industry": "Technology"
        })
        assert res.status_code == 201, f"Company failed: {res.text}"
        company_id = res.json()["id"]

        # 3. Workspace
        print("Creating workspace...")
        res = await client.post(f"{BASE_URL}/workspaces", json={
            "company_id": company_id, "name": "E2E IPO 2026"
        }, headers=headers)
        assert res.status_code == 201, f"Workspace failed: {res.text}"
        workspace_id = res.json()["id"]

        # 4. Demo Seed
        print("Testing Demo Seeder...")
        res = await client.post(f"{BASE_URL}/workspaces/demo/seed", headers=headers)
        assert res.status_code == 200, f"Demo seed failed: {res.text}"
        demo_workspace_id = res.json()["id"]
        
        # We will run the rest of the tests on the demo workspace as it comes pre-seeded with documents,
        # or we can test upload on our own workspace. Let's test upload on our workspace.
        
        # 5. Upload Document
        print("Uploading document...")
        test_file_content = b"This is a test PDF document for E2E verification."
        files = {"file": ("test.pdf", test_file_content, "application/pdf")}
        data = {"doc_type": "prospectus_draft"}
        res = await client.post(f"{BASE_URL}/workspaces/{workspace_id}/documents", files=files, data=data, headers=headers)
        if res.status_code != 201:
            print(f"Upload failed: {res.text}")
            
        # 6. Dashboard
        print("Fetching dashboard...")
        res = await client.get(f"{BASE_URL}/workspaces/{demo_workspace_id}/dashboard", headers=headers)
        assert res.status_code == 200, f"Dashboard failed: {res.text}"
        assert "audit_events" in res.json(), "audit_events missing in dashboard"

        # 7. Copilot
        print("Testing Copilot...")
        res = await client.post(f"{BASE_URL}/workspaces/{demo_workspace_id}/copilot/sessions", headers=headers)
        assert res.status_code == 201, f"Copilot session failed: {res.text}"
        session_id = res.json()["id"]

        res = await client.post(f"{BASE_URL}/copilot/sessions/{session_id}/message", json={
            "content": "What are the main risks?"
        }, headers=headers)
        if res.status_code != 201:
            print(f"Copilot message failed: {res.text}")
            
        # 8. PDF Export
        print("Testing PDF Export...")
        res = await client.get(f"{BASE_URL}/workspaces/{demo_workspace_id}/export/report.pdf", headers=headers)
        assert res.status_code == 200, f"PDF export failed: {res.text}"
        assert res.headers["content-type"] == "application/pdf", "Not a PDF"
        
        print("All E2E endpoints returned 200 OK successfully!")

if __name__ == "__main__":
    asyncio.run(verify_all())
