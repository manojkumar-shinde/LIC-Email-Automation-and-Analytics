import requests
import json
import uuid
import time

BASE_URL = "http://localhost:8000"

def generate_dummy_emails(count=10):
    emails = []
    for i in range(count):
        emails.append({
            "google_id": str(uuid.uuid4()),
            "sender": f"sender_{i}@example.com",
            "subject": f"Bulk Email {i}",
            "body": f"This is the body of bulk email {i}. It contains some potential PII like 123-456-7890."
        })
    return emails

def verify_bulk_ingest():
    print("Generating 10 dummy emails...")
    emails = generate_dummy_emails(10)
    
    # Save to json file
    with open("temp_bulk_emails.json", "w") as f:
        json.dump(emails, f)
        
    print("Uploading file to /api/ingest/bulk...")
    with open("temp_bulk_emails.json", "rb") as f:
        files = {'file': ('temp_bulk_emails.json', f, 'application/json')}
        try:
            response = requests.post(f"{BASE_URL}/api/ingest/bulk", files=files)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("SUCCESS: Bulk ingest returned 200 OK")
            else:
                print("FAILURE: Bulk ingest failed")
                return
        except Exception as e:
            print(f"ERROR: Could not connect to backend. Is it running? {e}")
            return

    # Check stats
    time.sleep(1) # Wait a bit for stats to reflect if async (though saving is synchronous here)
    try:
        stats = requests.get(f"{BASE_URL}/api/stats").json()
        print(f"Current Stats: {stats}")
        if stats.get('pending', 0) >= 10:
             print("SUCCESS: Stats reflect pending emails.")
        else:
             print("WARNING: Stats might not reflect count yet or database is empty.")
    except Exception as e:
        print(f"ERROR getting stats: {e}")

if __name__ == "__main__":
    verify_bulk_ingest()
