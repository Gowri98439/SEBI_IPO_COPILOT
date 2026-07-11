import requests, json, time, sys

BASE = 'http://localhost:8000/api/v1'

# 1. Login
r = requests.post(f'{BASE}/auth/login', json={'email': 'test@ipoco.com', 'password': 'Password123'})
if r.status_code != 200:
    print('LOGIN FAILED:', r.text)
    sys.exit(1)
token = r.json()['access_token']
H = {'Authorization': f'Bearer {token}'}
print('[OK] Login')

# 2. Get workspace
ws_list = requests.get(f'{BASE}/workspaces', headers=H).json()
ws_id = ws_list[0]['id'] if ws_list else None
print(f'[OK] Workspace: {ws_id}')

# 3. Upload a valid PDF
pdf = (
    b'%PDF-1.4\n'
    b'1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n'
    b'2 0 obj\n<</Type/Pages/Count 1/Kids[3 0 R]>>\nendobj\n'
    b'3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>\nendobj\n'
    b'xref\n0 4\n'
    b'0000000000 65535 f \n'
    b'0000000009 00000 n \n'
    b'0000000058 00000 n \n'
    b'0000000115 00000 n \n'
    b'trailer\n<</Size 4/Root 1 0 R>>\n'
    b'startxref\n190\n%%EOF\n'
)
r3 = requests.post(
    f'{BASE}/workspaces/{ws_id}/documents',
    headers=H,
    files={'file': ('financial_statements.pdf', pdf, 'application/pdf')},
    data={'doc_type': 'financial'}
)
print(f'[UPLOAD] Status={r3.status_code} Response={r3.text[:300]}')

# 4. Check audit logs
r4 = requests.get(f'{BASE}/workspaces/{ws_id}/audit-logs', headers=H)
count = len(r4.json()) if r4.status_code == 200 else 'ERROR'
print(f'[AUDIT] {r4.status_code}: {count} events')

# 5. Start DRHP generation
drhp_payload = {
    'company': {
        'name': 'Acme Technologies Private Limited',
        'cin': 'U72900MH2020PTC123456',
        'pan': 'AABCT1234A',
        'incorporation_date': '2020-01-15',
        'registered_address': '123 Business Park, Andheri East, Mumbai 400069',
        'sector': 'Technology & IT',
        'sub_sector': 'Cloud Software & SaaS',
        'website': 'https://www.acme.com',
        'description': 'Acme Technologies Private Limited is a Mumbai-based technology company specialising in cloud-native enterprise software solutions, API integration platforms, and managed SaaS services. The Company serves clients across BFSI, retail, and logistics sectors.'
    },
    'promoters': [
        {'name': 'Rahul Sharma', 'designation': 'Managing Director', 'qualification': 'B.Tech IIT Bombay', 'holding_pct': 55.0},
        {'name': 'Priya Singh', 'designation': 'Executive Director', 'qualification': 'FCA', 'holding_pct': 20.0}
    ],
    'financials': [
        {'year': '2021-22', 'revenue': 3200.0, 'net_profit': 180.0, 'total_assets': 5500.0, 'total_equity': 2800.0, 'ebitda': 480.0},
        {'year': '2022-23', 'revenue': 4800.0, 'net_profit': 380.0, 'total_assets': 7200.0, 'total_equity': 3600.0, 'ebitda': 820.0},
        {'year': '2023-24', 'revenue': 6500.0, 'net_profit': 620.0, 'total_assets': 9800.0, 'total_equity': 4800.0, 'ebitda': 1180.0},
    ],
    'issue': {
        'issue_size_cr': 18.0, 'fresh_issue_cr': 12.0, 'ofs_cr': 6.0,
        'price_band_low': 120.0, 'price_band_high': 128.0,
        'face_value': 10.0, 'lot_size': 1000,
        'objects_of_issue': '1. Expansion of technology infrastructure\n2. Working capital requirements\n3. General corporate purposes',
        'use_of_proceeds': 'INR 8 Cr - Technology infrastructure\nINR 2 Cr - Working capital\nINR 2 Cr - Corporate purposes',
        'merchant_banker': 'Axis Capital Limited'
    }
}
r5 = requests.post(f'{BASE}/workspaces/{ws_id}/drhp/generate', headers=H, json=drhp_payload)
print(f'[DRHP_START] {r5.status_code}: {r5.text[:200]}')

if r5.status_code == 202:
    job_id = r5.json()['job_id']
    print(f'  Job ID: {job_id}')
    for i in range(30):
        time.sleep(5)
        rs = requests.get(f'{BASE}/workspaces/{ws_id}/drhp/status/{job_id}', headers=H)
        st = rs.json()
        pct = st.get('progress_pct', 0)
        status = st.get('status', '?')
        msg = st.get('message', '')
        print(f'  Poll {i+1}: status={status} progress={pct}% msg={msg[:60]}')
        if status in ('done', 'error'):
            break
    if st.get('status') == 'done':
        rd = requests.get(f'{BASE}/workspaces/{ws_id}/drhp/download/{job_id}', headers=H)
        size_kb = len(rd.content) / 1024
        # Save locally for inspection
        with open('test_drhp_output.pdf', 'wb') as f:
            f.write(rd.content)
        print(f'[DRHP_DONE] PDF size={size_kb:.1f} KB, saved to test_drhp_output.pdf')
    else:
        print(f'[DRHP_ERROR]', st)
else:
    print('[DRHP FAILED]', r5.text[:300])
