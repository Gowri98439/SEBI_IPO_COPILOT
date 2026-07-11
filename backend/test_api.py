import requests, json, time

BASE = 'http://localhost:8000/api/v1'
r = requests.post(f'{BASE}/auth/login', json={'email': 'test@ipoco.com', 'password': 'Password123'})
token = r.json()['access_token']
H = {'Authorization': f'Bearer {token}'}
ws_id = requests.get(f'{BASE}/workspaces', headers=H).json()[0]['id']
print(f'[OK] Login, workspace={ws_id}')

# Test 1: SEBI Advisor Chat
print('\n--- Test 1: Copilot Chat (SEBI Advisor) ---')
r1 = requests.post(f'{BASE}/workspaces/{ws_id}/copilot/chat', headers=H, json={
    'message': 'What is the minimum net tangible assets required for SME IPO?',
    'history': []
}, timeout=30)
print(f'Status: {r1.status_code}')
if r1.status_code == 200:
    resp = r1.json()
    answer = resp.get('response', '')
    sources = resp.get('rag_sources', 0)
    print(f'RAG sources used: {sources}')
    print(f'Answer (first 300 chars): {answer[:300]}')
else:
    print(f'Error: {r1.text[:300]}')

# Test 2: Compliance Run + Check
print('\n--- Test 2: Compliance Engine ---')
r2 = requests.post(f'{BASE}/workspaces/{ws_id}/compliance/run', headers=H, timeout=10)
print(f'Run triggered: {r2.status_code}')
time.sleep(5)
r2b = requests.get(f'{BASE}/workspaces/{ws_id}/compliance', headers=H, timeout=10)
checks = r2b.json()
print(f'Checks in DB: {len(checks)}')
if checks:
    c = checks[0]
    print(f'Sample: {c.get("check_type")} => {c.get("status")}')

# Test 3: Dashboard Stats
print('\n--- Test 3: Dashboard ---')
r3 = requests.get(f'{BASE}/workspaces/{ws_id}/dashboard', headers=H, timeout=10)
d = r3.json()
readiness = d.get('readiness_score', 0)
docs = d.get('documents_uploaded', 0)
docs_req = d.get('documents_required', 5)
compliance_pct = d.get('compliance_pass_rate_percent', 0)
audit_count = len(d.get('audit_events', []))
print(f'Readiness: {readiness}%')
print(f'Docs: {docs}/{docs_req}')
print(f'Compliance pass rate: {compliance_pct}%')
print(f'Audit events: {audit_count}')

print('\n[ALL TESTS COMPLETE]')
