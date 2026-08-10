import requests, time

BASE = 'http://localhost:8000/api/v1'

r = requests.post(f'{BASE}/auth/login', json={'email': 'test@ipoco.com', 'password': 'Password123'})
token = r.json()['access_token']
H = {'Authorization': f'Bearer {token}'}

ws = requests.get(f'{BASE}/workspaces', headers=H).json()
ws_id = ws[0]['id']

req = requests.post(f'{BASE}/workspaces/{ws_id}/drhp/v2/generate', headers=H, json={
    'company': {'name': 'Sunrise Specialty Chemicals Ltd', 'cin': 'L12345MH2000PLC123456', 'pan': 'ABCDE1234F', 'incorporation_date': '2000-01-01', 'registered_address': 'Mumbai', 'sector': 'Chemicals', 'sub_sector': 'Specialty', 'website': 'http://example.com', 'description': 'Dummy company description'*20},
    'promoters': [{'name': 'Alpha', 'designation': 'MD', 'holding_pct': 50.0}],
    'financials': [{'year': '2023-24', 'revenue': 1000, 'net_profit': 100, 'total_assets': 500, 'total_equity': 200, 'ebitda': 150}],
    'issue': {'issue_size_cr': 50, 'fresh_issue_cr': 25, 'ofs_cr': 25, 'price_band_low': 100, 'price_band_high': 120, 'face_value': 10, 'lot_size': 1200, 'objects_of_issue': 'Expansion', 'use_of_proceeds': 'Capex', 'merchant_banker': 'Banker A'},
    'use_llm_generation': False,
    'generate_intelligence_report': False
})

job_id = req.json().get('job_id')
if not job_id:
    print("Error:", req.text)
    exit(1)

print('Job ID:', job_id)

for i in range(30):
    time.sleep(1)
    status_req = requests.get(f'{BASE}/workspaces/{ws_id}/drhp/v2/status/{job_id}', headers=H)
    status_data = status_req.json()
    print(f"Status: {status_data.get('status')} - Progress: {status_data.get('progress_pct')}%")
    if status_data.get('status') == 'done':
        break
    if status_data.get('status') == 'error':
        print('Error generated')
        break

print("Testing DRHP PDF Download Header:")
dl = requests.get(f'{BASE}/workspaces/{ws_id}/drhp/v2/download/{job_id}', headers=H)
print(f"Status Code: {dl.status_code}")
print('Content-Disposition:', dl.headers.get('Content-Disposition', 'None'))
