import sqlite3
import os

DB_PATH = os.path.join("backend", "data", "emails.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get count before deletion
cursor.execute("SELECT COUNT(*) FROM emails")
before_count = cursor.fetchone()[0]

print(f"Emails in database before deletion: {before_count}")

# Delete all emails
cursor.execute("DELETE FROM emails")
conn.commit()

# Verify deletion
cursor.execute("SELECT COUNT(*) FROM emails")
after_count = cursor.fetchone()[0]

conn.close()

print(f"Emails in database after deletion: {after_count}")
print(f"\n✅ Successfully deleted {before_count} emails!")
print("\nDatabase is now empty and ready for fresh ingestion.")
print("New emails will be properly analyzed with AI (Ollama is running).")
