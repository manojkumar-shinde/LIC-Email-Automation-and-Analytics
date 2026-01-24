import sqlite3
import json

conn = sqlite3.connect("backend/data/emails.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Get last 10 completed emails
c.execute("""
    SELECT id, subject, sender, status, analysis 
    FROM emails 
    WHERE status = 'COMPLETED'
    ORDER BY id DESC 
    LIMIT 10
""")

print("="*80)
print("LAST 10 COMPLETED EMAILS - INTENT/SENTIMENT CHECK")
print("="*80)

results = []
for row in c.fetchall():
    try:
        analysis = json.loads(row['analysis']) if row['analysis'] else {}
        
        result = {
            'id': row['id'],
            'subject': row['subject'][:50],
            'intent': analysis.get('intent', 'MISSING'),
            'sentiment': analysis.get('sentiment', 'MISSING'),
            'priority': analysis.get('priority', 'MISSING'),
            'summary': analysis.get('summary', 'MISSING')[:60]
        }
        results.append(result)
        
        print(f"\nID: {result['id']}")
        print(f"Subject: {result['subject']}")
        print(f"Intent: {result['intent']}")
        print(f"Sentiment: {result['sentiment']}")
        print(f"Priority: {result['priority']}")
        print(f"Summary: {result['summary']}...")
        print("-"*80)
    except Exception as e:
        print(f"\nID: {row['id']} - Error parsing: {e}")

# Check if all intents are the same
intents = [r['intent'] for r in results]
sentiments = [r['sentiment'] for r in results]

print("\n" + "="*80)
print("ANALYSIS SUMMARY")
print("="*80)
print(f"Total emails checked: {len(results)}")
print(f"Unique intents: {set(intents)}")
print(f"Unique sentiments: {set(sentiments)}")

if len(set(intents)) == 1:
    print(f"\n⚠️  WARNING: All emails have the SAME intent: {intents[0]}")
    
if len(set(sentiments)) == 1:
    print(f"⚠️  WARNING: All emails have the SAME sentiment: {sentiments[0]}")

conn.close()
