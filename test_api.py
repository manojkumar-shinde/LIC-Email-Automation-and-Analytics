import requests
import json

# Test API connectivity
print("Testing API at http://localhost:8000...")

# Test 1: Stats
try:
    response = requests.get("http://localhost:8000/api/stats")
    print(f"\n✅ Stats API: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\n❌ Stats API failed: {e}")

# Test 2: Ingest
try:
    data = {
        "subject": "Death Claim Request",
        "body": "My father passed away last month. I need help filing the death claim for his LIC policy."
    }
    response = requests.post("http://localhost:8000/api/ingest", json=data)
    print(f"\n✅ Ingest API: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\n❌ Ingest API failed: {e}")

# Test 3: Check stats again
import time
time.sleep(2)
try:
    response = requests.get("http://localhost:8000/api/stats")
    print(f"\n✅ Stats After Ingest: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\n❌ Stats API failed: {e}")
