import sqlite3

conn = sqlite3.connect("trading.db")

cursor = conn.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""")

print("Tables:", [row[0] for row in cursor.fetchall()])

conn.close()
