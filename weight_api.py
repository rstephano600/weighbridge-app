from fastapi import FastAPI
import sqlite3

app = FastAPI()


def get_db():
    conn = sqlite3.connect("weighbridge.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def home():
    return {"message": "Weighbridge API running"}


@app.get("/weight/latest")
def latest_weight():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM weights
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    return {"message": "No weight found"}


@app.get("/weights/unused")
def unused_weights():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM weights
        WHERE status='unused'
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]


@app.post("/weights/mark-used/{weight_id}")
def mark_used(weight_id: int):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE weights
        SET status='used'
        WHERE id=?
    """, (weight_id,))

    conn.commit()
    conn.close()

    return {"message": "Weight marked as used"}