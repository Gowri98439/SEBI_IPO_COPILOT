from google import genai
import os

key = "AQ.Ab8RN6LQCiI6tRxn8LGErx3CISmUlFid7IzDPvf4q6wCmOSjUg"
client = genai.Client(api_key=key)

for m in client.models.list():
    print(m.name)
