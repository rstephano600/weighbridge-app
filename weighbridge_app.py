import socket
import struct
import time
import sqlite3
import tkinter as tk
from tkinter import ttk, font
from threading import Thread
import requests

# ========================
# CONFIG
# ========================
UDP_IP = "0.0.0.0"
UDP_PORT = 5000
API_BASE = "http://127.0.0.1:8000/api"

capture_enabled = False
stable_weight = None

# ========================
# THEME PALETTE
# ========================
BG_DARK      = "#0D0F14"
BG_PANEL     = "#141720"
BG_CARD      = "#1C2030"
ACCENT       = "#F5A623"
ACCENT_DIM   = "#C07B10"
SUCCESS      = "#27C87A"
DANGER       = "#E8445A"
TEXT_PRIMARY = "#E8EAF0"
TEXT_MUTED   = "#6B7280"
BORDER       = "#252A3A"
HIGHLIGHT    = "#2A3050"

# ========================
# UDP SETUP
# ========================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT,
            driver TEXT,
            weight REAL,
            direction TEXT,
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
            label = f"{v['truck']['plate_number']}  ·  {v['driver']['name']}"
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
# SEND TO API
# ========================
def send_to_api(weight):
    visit_id = selected_visit_id.get()
    if visit_id == 0:
        set_status("⚠  No truck visit selected.", DANGER)
        return
    try:
        pending = get_pending_transaction(visit_id)
        if not pending:
            payload = {"truck_visit_id": visit_id, "tare_weight": weight}
            res = requests.post(f"{API_BASE}/weigh-in", json=payload, timeout=5)
            print("AUTO IN:", res.json())
            save_weight(weight, "IN", visit_id)
            set_status(f"✔  Tare weight recorded: {weight} kg", SUCCESS)
            append_log(weight, "IN")
        else:
            transaction_id = pending["id"]
            payload = {"gross_weight": weight}
            res = requests.post(f"{API_BASE}/weigh-out/{transaction_id}", json=payload, timeout=5)
            print("AUTO OUT:", res.json())
            save_weight(weight, "OUT", visit_id)
            set_status(f"✔  Gross weight recorded: {weight} kg", SUCCESS)
            append_log(weight, "OUT")
            refresh_visits()
    except Exception as e:
        set_status(f"✘  API Error: {e}", DANGER)

# ========================
# STATUS HELPER
# ========================
def set_status(msg, color=TEXT_MUTED):
    status_label.config(text=msg, fg=color)

# ========================
# LOG HELPER
# ========================
def append_log(weight, direction):
    tag = "in" if direction == "IN" else "out"
    ts = time.strftime("%H:%M:%S")
    label = visit_dropdown.get() or "Unknown"
    log_tree.insert("", 0, values=(ts, label.split("·")[0].strip(), f"{weight} kg", direction), tags=(tag,))

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
            root.after(0, lambda w=weight: weight_var.set(f"{w:,.2f}"))

            if last_weight is None:
                last_weight = weight
                stable_start = time.time()
            elif abs(weight - last_weight) < 2:
                elapsed = time.time() - stable_start
                pct = min(int((elapsed / 4) * 100), 100)
                root.after(0, lambda p=pct: stability_bar.config(value=p))
                if elapsed >= 4:
                    stable_weight = weight
                    root.after(0, lambda w=weight: on_stable(w))
                    capture_enabled = False
            else:
                last_weight = weight
                stable_start = time.time()
                root.after(0, lambda: stability_bar.config(value=0))

def on_stable(weight):
    stable_var.set(f"{weight:,.2f} kg")
    stable_badge.config(text="STABLE", bg=SUCCESS, fg=BG_DARK)
    set_status("✔  Weight is stable. Press 'Store Weight' to save.", ACCENT)
    stability_bar.config(value=100)

# ========================
# BUTTONS
# ========================
def enable_capture():
    global capture_enabled
    capture_enabled = True
    stable_var.set("— — —")
    weight_var.set("0.00")
    stable_badge.config(text="READING", bg=ACCENT, fg=BG_DARK)
    stability_bar.config(value=0)
    set_status("◉  Capturing weight data...", TEXT_PRIMARY)

def store_weight():
    global stable_weight
    if stable_weight is not None:
        send_to_api(stable_weight)
        stable_weight = None
        stable_badge.config(text="STORED", bg=SUCCESS, fg=BG_DARK)
    else:
        set_status("⚠  No stable weight captured yet.", DANGER)

def refresh_visits():
    global visits
    visits = fetch_truck_visits()
    visit_dropdown['values'] = [v[0] for v in visits]
    selected_visit_id.set(0)
    visit_dropdown.set('')
    set_status("↻  Truck visits refreshed.", TEXT_MUTED)

# ========================
# UI BUILD
# ========================
root = tk.Tk()
root.title("Weighbridge Capture System")
root.geometry("680x720")
root.configure(bg=BG_DARK)
root.resizable(False, False)

selected_visit_id = tk.IntVar(value=0)
weight_var = tk.StringVar(value="0.00")
stable_var = tk.StringVar(value="— — —")

# ── FONTS ──────────────────────────────────────────────
try:
    FONT_MONO    = font.Font(family="Courier New",  size=11)
    FONT_DISPLAY = font.Font(family="Courier New",  size=52, weight="bold")
    FONT_STABLE  = font.Font(family="Courier New",  size=24, weight="bold")
    FONT_TITLE   = font.Font(family="Courier New",  size=13, weight="bold")
    FONT_LABEL   = font.Font(family="Courier New",  size=9)
    FONT_BTN     = font.Font(family="Courier New",  size=10, weight="bold")
    FONT_STATUS  = font.Font(family="Courier New",  size=9)
    FONT_LOG     = font.Font(family="Courier New",  size=9)
except:
    FONT_MONO    = ("Courier New", 11)
    FONT_DISPLAY = ("Courier New", 52, "bold")
    FONT_STABLE  = ("Courier New", 24, "bold")
    FONT_TITLE   = ("Courier New", 13, "bold")
    FONT_LABEL   = ("Courier New", 9)
    FONT_BTN     = ("Courier New", 10, "bold")
    FONT_STATUS  = ("Courier New", 9)
    FONT_LOG     = ("Courier New", 9)

# ── TOP HEADER ─────────────────────────────────────────
header_frame = tk.Frame(root, bg=BG_PANEL, height=54)
header_frame.pack(fill="x")
header_frame.pack_propagate(False)

tk.Label(header_frame, text="⬡  WEIGHBRIDGE CONTROL SYSTEM",
         font=FONT_TITLE, bg=BG_PANEL, fg=ACCENT).pack(side="left", padx=18, pady=14)

version_lbl = tk.Label(header_frame, text="v2.0", font=FONT_LABEL, bg=BG_PANEL, fg=TEXT_MUTED)
version_lbl.pack(side="right", padx=18)

# ── DIVIDER ────────────────────────────────────────────
tk.Frame(root, bg=ACCENT, height=2).pack(fill="x")

# ── MAIN BODY ──────────────────────────────────────────
body = tk.Frame(root, bg=BG_DARK)
body.pack(fill="both", expand=True, padx=20, pady=14)

# ── LEFT COLUMN ────────────────────────────────────────
left = tk.Frame(body, bg=BG_DARK)
left.pack(side="left", fill="both", expand=True, padx=(0, 10))

# Weight display card
weight_card = tk.Frame(left, bg=BG_CARD, bd=0, relief="flat",
                       highlightbackground=BORDER, highlightthickness=1)
weight_card.pack(fill="x", pady=(0, 10))

tk.Label(weight_card, text="LIVE WEIGHT", font=FONT_LABEL, bg=BG_CARD, fg=TEXT_MUTED)\
    .pack(anchor="w", padx=16, pady=(12, 0))

weight_inner = tk.Frame(weight_card, bg=BG_CARD)
weight_inner.pack(fill="x", padx=16, pady=(0, 4))

tk.Label(weight_inner, textvariable=weight_var, font=FONT_DISPLAY,
         bg=BG_CARD, fg=TEXT_PRIMARY).pack(side="left")

tk.Label(weight_inner, text="kg", font=FONT_TITLE, bg=BG_CARD,
         fg=TEXT_MUTED).pack(side="left", anchor="s", pady=(0, 18), padx=6)

stable_badge = tk.Label(weight_inner, text="IDLE", font=FONT_LABEL,
                        bg=HIGHLIGHT, fg=TEXT_MUTED, padx=8, pady=4)
stable_badge.pack(side="right", anchor="n", pady=12)

# Stability progress bar
tk.Label(weight_card, text="STABILITY", font=FONT_LABEL, bg=BG_CARD, fg=TEXT_MUTED)\
    .pack(anchor="w", padx=16)

bar_style = ttk.Style()
bar_style.theme_use("clam")
bar_style.configure("Stab.Horizontal.TProgressbar",
                    troughcolor=BORDER, background=ACCENT,
                    bordercolor=BG_CARD, lightcolor=ACCENT, darkcolor=ACCENT_DIM,
                    thickness=8)

stability_bar = ttk.Progressbar(weight_card, orient="horizontal",
                                 mode="determinate", maximum=100,
                                 style="Stab.Horizontal.TProgressbar")
stability_bar.pack(fill="x", padx=16, pady=(4, 14))

# Stable weight card
stable_card = tk.Frame(left, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
stable_card.pack(fill="x", pady=(0, 10))

tk.Label(stable_card, text="STABLE WEIGHT", font=FONT_LABEL,
         bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=16, pady=(12, 0))

tk.Label(stable_card, textvariable=stable_var, font=FONT_STABLE,
         bg=BG_CARD, fg=SUCCESS).pack(anchor="w", padx=16, pady=(4, 14))

# Truck Visit selector card
visit_card = tk.Frame(left, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
visit_card.pack(fill="x", pady=(0, 10))

visit_header = tk.Frame(visit_card, bg=BG_CARD)
visit_header.pack(fill="x", padx=16, pady=(12, 4))
tk.Label(visit_header, text="TRUCK VISIT", font=FONT_LABEL,
         bg=BG_CARD, fg=TEXT_MUTED).pack(side="left")

# Search entry
search_var = tk.StringVar()
search_entry = tk.Entry(visit_card, textvariable=search_var,
                        font=FONT_MONO, bg=HIGHLIGHT, fg=TEXT_PRIMARY,
                        insertbackground=ACCENT, relief="flat", bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
search_entry.pack(fill="x", padx=16, pady=(0, 6), ipady=6)

# Placeholder logic
def on_search_focus_in(e):
    if search_var.get() == "Search plate or driver...":
        search_var.set("")
        search_entry.config(fg=TEXT_PRIMARY)

def on_search_focus_out(e):
    if not search_var.get():
        search_var.set("Search plate or driver...")
        search_entry.config(fg=TEXT_MUTED)

search_var.set("Search plate or driver...")
search_entry.config(fg=TEXT_MUTED)
search_entry.bind("<FocusIn>", on_search_focus_in)
search_entry.bind("<FocusOut>", on_search_focus_out)

visits = fetch_truck_visits()
all_visits = visits[:]

def filter_visits(*args):
    term = search_var.get().lower()
    if term == "search plate or driver...":
        term = ""
    filtered = [v[0] for v in all_visits if term in v[0].lower()] if term else [v[0] for v in all_visits]
    visit_dropdown['values'] = filtered

search_var.trace_add("write", filter_visits)

combo_style = ttk.Style()
combo_style.theme_use("clam")
combo_style.configure("Dark.TCombobox",
                       fieldbackground=HIGHLIGHT,
                       background=HIGHLIGHT,
                       foreground=TEXT_PRIMARY,
                       arrowcolor=ACCENT,
                       bordercolor=BORDER,
                       lightcolor=BG_CARD,
                       darkcolor=BG_CARD,
                       selectbackground=HIGHLIGHT,
                       selectforeground=TEXT_PRIMARY)
combo_style.map("Dark.TCombobox",
                fieldbackground=[("readonly", HIGHLIGHT)],
                selectbackground=[("readonly", HIGHLIGHT)],
                background=[("active", BG_CARD)])

visit_dropdown = ttk.Combobox(visit_card, state="readonly",
                               font=FONT_MONO, style="Dark.TCombobox")
visit_dropdown['values'] = [v[0] for v in visits]
visit_dropdown.pack(fill="x", padx=16, pady=(0, 12), ipady=5)

def on_visit_select(event):
    idx = visit_dropdown.current()
    sel_text = visit_dropdown.get()
    for v in all_visits:
        if v[0] == sel_text:
            selected_visit_id.set(v[1])
            return
    if idx >= 0 and idx < len(visits):
        selected_visit_id.set(visits[idx][1])

visit_dropdown.bind("<<ComboboxSelected>>", on_visit_select)

# ── BUTTONS ────────────────────────────────────────────
btn_frame = tk.Frame(left, bg=BG_DARK)
btn_frame.pack(fill="x", pady=(0, 8))

def make_btn(parent, text, cmd, color, hover_color, text_color=BG_DARK):
    btn = tk.Button(parent, text=text, command=cmd,
                    font=FONT_BTN, bg=color, fg=text_color,
                    activebackground=hover_color, activeforeground=BG_DARK,
                    relief="flat", bd=0, cursor="hand2",
                    padx=12, pady=10)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_color))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn

start_btn = make_btn(btn_frame, "▶  START MEASUREMENT", enable_capture, ACCENT, "#FFB84D")
start_btn.pack(fill="x", pady=(0, 6))

store_btn = make_btn(btn_frame, "⬇  STORE WEIGHT", store_weight, SUCCESS, "#35E88A")
store_btn.pack(fill="x", pady=(0, 6))

refresh_btn = make_btn(btn_frame, "↻  REFRESH VISITS", refresh_visits,
                       HIGHLIGHT, BG_CARD, TEXT_PRIMARY)
refresh_btn.pack(fill="x")

# Status bar
status_label = tk.Label(left, text="System ready.", font=FONT_STATUS,
                         bg=BG_DARK, fg=TEXT_MUTED, anchor="w")
status_label.pack(fill="x", pady=(8, 0))

# ── RIGHT COLUMN: LOG ──────────────────────────────────
right = tk.Frame(body, bg=BG_DARK, width=220)
right.pack(side="right", fill="both")
right.pack_propagate(False)

log_card = tk.Frame(right, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
log_card.pack(fill="both", expand=True)

tk.Label(log_card, text="SESSION LOG", font=FONT_LABEL,
         bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(10, 4))

tk.Frame(log_card, bg=BORDER, height=1).pack(fill="x", padx=12)

log_style = ttk.Style()
log_style.configure("Log.Treeview",
                     background=BG_CARD,
                     foreground=TEXT_PRIMARY,
                     fieldbackground=BG_CARD,
                     bordercolor=BORDER,
                     rowheight=26,
                     font=("Courier New", 8))
log_style.configure("Log.Treeview.Heading",
                     background=BG_PANEL,
                     foreground=TEXT_MUTED,
                     font=("Courier New", 8, "bold"),
                     relief="flat")
log_style.map("Log.Treeview",
              background=[("selected", HIGHLIGHT)],
              foreground=[("selected", TEXT_PRIMARY)])

log_tree = ttk.Treeview(log_card, columns=("time", "plate", "weight", "dir"),
                         show="headings", style="Log.Treeview", height=22)
log_tree.heading("time",   text="TIME",   anchor="w")
log_tree.heading("plate",  text="PLATE",  anchor="w")
log_tree.heading("weight", text="WEIGHT", anchor="w")
log_tree.heading("dir",    text="DIR",    anchor="w")
log_tree.column("time",   width=54,  stretch=False)
log_tree.column("plate",  width=72,  stretch=False)
log_tree.column("weight", width=60,  stretch=False)
log_tree.column("dir",    width=32,  stretch=False)

log_tree.tag_configure("in",  foreground=ACCENT)
log_tree.tag_configure("out", foreground=SUCCESS)

scroll = ttk.Scrollbar(log_card, orient="vertical", command=log_tree.yview)
log_tree.configure(yscrollcommand=scroll.set)

log_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(4, 8))
scroll.pack(side="right", fill="y", pady=4, padx=(0, 4))

# ── BOTTOM STATUS STRIP ────────────────────────────────
tk.Frame(root, bg=BORDER, height=1).pack(fill="x")
foot = tk.Frame(root, bg=BG_PANEL, height=28)
foot.pack(fill="x")
foot.pack_propagate(False)

tk.Label(foot, text=f"UDP  {UDP_IP}:{UDP_PORT}",
         font=FONT_LABEL, bg=BG_PANEL, fg=TEXT_MUTED).pack(side="left", padx=16, pady=6)
tk.Label(foot, text=f"API  {API_BASE}",
         font=FONT_LABEL, bg=BG_PANEL, fg=TEXT_MUTED).pack(side="left", padx=0, pady=6)

conn_dot = tk.Label(foot, text="●  CONNECTED", font=FONT_LABEL,
                    bg=BG_PANEL, fg=SUCCESS)
conn_dot.pack(side="right", padx=16, pady=6)

# ── THREAD ─────────────────────────────────────────────
thread = Thread(target=weight_listener)
thread.daemon = True
thread.start()

root.mainloop()