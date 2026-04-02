import sqlite3

def create_database():

    conn = sqlite3.connect("weighbridge.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        weight REAL,
        direction TEXT DEFAULT 'UNKNOWN',
        status TEXT DEFAULT 'unused',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

create_database()

print("Database and table created successfully.")