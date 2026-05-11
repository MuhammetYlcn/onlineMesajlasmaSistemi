import sqlite3

db_path = r'c:\Users\apota\OneDrive\Desktop\bilgisayar ağları proje\data\database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables:")
for table in tables:
    print(f"\nTable: {table[0]}")
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  Column: {col[1]} ({col[2]})")

conn.close()
