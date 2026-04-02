import sqlite3

conn = sqlite3.connect("weighbridge.db")
cursor = conn.cursor()

def add_column(column_name, column_type):

    try:
        cursor.execute(f"ALTER TABLE weights ADD COLUMN {column_name} {column_type}")
        print(f"{column_name} column added")
    except sqlite3.OperationalError:
        print(f"{column_name} already exists")

# Add new fields
add_column("truck", "TEXT")
add_column("driver", "TEXT")
add_column("direction", "TEXT")

conn.commit()
conn.close()

print("Database alteration completed.")