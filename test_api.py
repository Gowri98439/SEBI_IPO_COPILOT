import httpx
import json

response = httpx.post(
    "https://sebi-ipo-copilot.onrender.com/api/v1/auth/register",
    json={
        "email": "test4@test.com",
        "password": "Password123!",
        "full_name": "Test User",
        "role": "Administrator"
    }
)
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
