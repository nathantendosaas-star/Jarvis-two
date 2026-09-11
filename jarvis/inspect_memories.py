import sqlite3
import os

db_path = r"E:\nate\GEMINI AGENT\JARVIS\.storage\jarvis.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", tables)
        
        # Query memories table
        cursor.execute("PRAGMA table_info(memories);")
        columns = cursor.fetchall()
        print("Memories Table Columns:", [col[1] for col in columns])
        
        cursor.execute("SELECT * FROM memories LIMIT 50;")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} memories:")
        for r in rows:
            print(r)
    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()
