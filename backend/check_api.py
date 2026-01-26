import requests
import time

try:
    response = requests.get("http://localhost:8001/api/stats", timeout=5)
    print(f"API Check: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"API Check Failed: {e}")
