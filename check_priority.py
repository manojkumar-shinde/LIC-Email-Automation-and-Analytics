import sqlite3
import json
import os

# Path to database
DB_PATH = os.path.join("backend", "data", "emails.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get the last 5 completed emails
cursor.execute("""
    SELECT id, subject, status, analysis 
    FROM emails 
    WHERE status = 'COMPLETED'
    ORDER BY id DESC 
    LIMIT 5
""")

print("Recent Completed Emails with Priority:\n")
print("=" * 80)

for row in cursor.fetchall():
    email_id = row['id']
    subject = row['subject']
    status = row['status']
    analysis_json = row['analysis']
    
    try:
        analysis = json.loads(analysis_json) if analysis_json else {}
        intent = analysis.get('intent', 'N/A')
        sentiment = analysis.get('sentiment', 'N/A')
        priority = analysis.get('priority', 'NOT SET')
        priority_reason = analysis.get('priority_reason', 'N/A')
        
        print(f"\nID: {email_id}")
        print(f"Subject: {subject}")
        print(f"Intent: {intent}")
        print(f"Sentiment: {sentiment}")
        print(f"Priority: {priority}")
        print(f"Reason: {priority_reason}")
        print("-" * 80)
    except json.JSONDecodeError:
        print(f"\nID: {email_id} - Invalid JSON in analysis field")

conn.close()
print("\n✅ Database Check Complete")
