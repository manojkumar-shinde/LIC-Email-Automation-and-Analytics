import sqlite3
import json

conn = sqlite3.connect("backend/data/emails.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT id, subject, status, analysis 
    FROM emails 
    ORDER BY id DESC 
    LIMIT 5
""")

print("\n" + "="*80)
print("LATEST 5 EMAILS - PRIORITY VERIFICATION")
print("="*80 + "\n")

for row in c.fetchall():
    analysis = json.loads(row['analysis']) if row['analysis'] else {}
    
    print(f"ID: {row['id']}")
    print(f"Subject: {row['subject']}")
    print(f"Status: {row['status']}")
    
    if row['status'] == 'COMPLETED':
        print(f"  Intent: {analysis.get('intent', 'N/A')}")
        print(f"  Sentiment: {analysis.get('sentiment', 'N/A')}")
        print(f"  Priority: {analysis.get('priority', '❌ MISSING')}")
        print(f"  Reason: {analysis.get('priority_reason', '❌ MISSING')}")
    else:
        print(f"  (Not yet processed)")
    
    print("-" * 80)

conn.close()
