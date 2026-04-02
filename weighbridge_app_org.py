import socket
import struct
import time
import sqlite3
import tkinter as tk
from threading import Thread
import requests
from tkinter import ttk

# ========================
# CONFIG
# ========================
UDP_IP = "0.0.0.0"
UDP_PORT = 5000
API_BASE = "http://127.0.0.1:8000/api"

capture_enabled = False
stable_weight = None

# ========================
# UDP SETUP
# ========================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for weighbridge data...")

# ========================
# DATABASE INIT
# ========================
def init_db():
    conn = sqlite3.connect("weighbridge.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER,
            direction TEXT,
            weight REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ========================
# SAVE LOCAL
# ========================
def save_weight(weight, direction, visit_id):
    conn = sqlite3.connect("weighbridge.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO weights (visit_id, direction, weight, status)
        VALUES (?, ?, ?, ?)
    """, (visit_id, direction, weight, "saved"))

    conn.commit()
    conn.close()

# ========================
# FETCH VISITS
# ========================
def fetch_truck_visits():
    try:
        res = requests.get(f"{API_BASE}/truck-visits-in", timeout=5)
        data = res.json()

        visits = []
        for v in data:
            label = f"{v['id']} - {v['truck']['plate_number']} ({v['driver']['name']})"
            visits.append((label, v['id']))

        return visits

    except Exception as e:
        print("Error fetching visits:", e)
        return []

# ========================
# CHECK PENDING
# ========================
def get_pending_transaction(visit_id):
    try:
        res = requests.get(f"{API_BASE}/pending-transaction/{visit_id}", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print("Pending check error:", e)

    return None

# ========================
# SEND TO API (AUTO MODE)
# ========================
def send_to_api(weight):
    visit_id = selected_visit_id.get()

    if visit_id == 0:
        print("No visit selected")
        return

    try:
        pending = get_pending_transaction(visit_id)

        # =====================
        # IN (TARE)
        # =====================
        if not pending:

            payload = {
                "truck_visit_id": visit_id,
                "tare_weight": weight
            }

            res = requests.post(f"{API_BASE}/weigh-in", json=payload, timeout=5)
            print("AUTO IN:", res.json())

            save_weight(weight, "IN", visit_id)

        # =====================
        # OUT (GROSS)
        # =====================
        else:

            transaction_id = pending["id"]

            payload = {
                "gross_weight": weight
            }

            res = requests.post(
                f"{API_BASE}/weigh-out/{transaction_id}",
                json=payload,
                timeout=5
            )

            print("AUTO OUT:", res.json())

            save_weight(weight, "OUT", visit_id)

            refresh_visits()

    except Exception as e:
        print("API Error:", e)

# ========================
# UDP LISTENER
# ========================
def weight_listener():
    global capture_enabled, stable_weight

    last_weight = None
    stable_start = None

    while True:
        data, addr = sock.recvfrom(1024)

        try:
            weight = struct.unpack('<f', data[44:48])[0]
            weight = round(weight, 2)
        except:
            continue

        if capture_enabled:
            weight_label.config(text=str(weight) + " kg")

            if last_weight is None:
                last_weight = weight
                stable_start = time.time()

            elif abs(weight - last_weight) < 2:

                if time.time() - stable_start >= 4:
                    stable_weight = weight
                    stable_label.config(text="Stable Weight: " + str(weight) + " kg")
                    capture_enabled = False

            else:
                last_weight = weight
                stable_start = time.time()

# ========================
# BUTTONS
# ========================
def enable_capture():
    global capture_enabled
    stable_label.config(text="Waiting for stable weight...")
    capture_enabled = True

def store_weight():
    global stable_weight

    if stable_weight is not None:
        send_to_api(stable_weight)

        stable_label.config(text="Stored & Sent: " + str(stable_weight) + " kg")
        stable_weight = None

# ========================
# UI
# ========================
root = tk.Tk()
root.title("Weighbridge Capture System")
root.geometry("420x400")

selected_visit_id = tk.IntVar(value=0)

title = tk.Label(root, text="Weighbridge Weight Capture", font=("Arial", 16))
title.pack(pady=10)

weight_label = tk.Label(root, text="0 kg", font=("Arial", 24))
weight_label.pack(pady=10)

stable_label = tk.Label(root, text="Not capturing", font=("Arial", 12))
stable_label.pack(pady=10)

# DROPDOWN
visit_label = tk.Label(root, text="Select Truck Visit")
visit_label.pack()

visits = fetch_truck_visits()

visit_dropdown = ttk.Combobox(root, state="readonly", width=40)
visit_dropdown['values'] = [v[0] for v in visits]
visit_dropdown.pack()

def on_visit_select(event):
    index = visit_dropdown.current()
    if index >= 0:
        selected_visit_id.set(visits[index][1])

visit_dropdown.bind("<<ComboboxSelected>>", on_visit_select)

# BUTTONS
start_btn = tk.Button(root, text="Start Measurement", command=enable_capture)
start_btn.pack(pady=5)

store_btn = tk.Button(root, text="Store Weight", command=store_weight)
store_btn.pack(pady=5)

# REFRESH
def refresh_visits():
    global visits

    visits = fetch_truck_visits()
    visit_dropdown['values'] = [v[0] for v in visits]

    selected_visit_id.set(0)
    visit_dropdown.set('')

    stable_label.config(text="Ready for next truck")

# THREAD
thread = Thread(target=weight_listener)
thread.daemon = True
thread.start()

root.mainloop()