import socket
import struct
import time
import sqlite3
import tkinter as tk
from threading import Thread
import requests
from tkinter import ttk, font

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
            visit_data = {
                'id': v['id'],
                'plate_number': v['truck']['plate_number'],
                'driver_name': v['driver']['name'],
                'driver_phone': v['driver'].get('phone', ''),
                'truck_type': v['truck'].get('type', ''),
                'display_text': f"{v['id']} - {v['truck']['plate_number']} ({v['driver']['name']})"
            }
            visits.append(visit_data)

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
        show_status_message("Please select a truck visit first!", "error")
        return

    try:
        pending = get_pending_transaction(visit_id)

        if not pending:
            payload = {
                "truck_visit_id": visit_id,
                "tare_weight": weight
            }

            res = requests.post(f"{API_BASE}/weigh-in", json=payload, timeout=5)
            print("AUTO IN:", res.json())
            save_weight(weight, "IN", visit_id)
            show_status_message(f"Weight stored: {weight} kg (IN)", "success")

        else:
            transaction_id = pending["id"]
            payload = {"gross_weight": weight}

            res = requests.post(
                f"{API_BASE}/weigh-out/{transaction_id}",
                json=payload,
                timeout=5
            )

            print("AUTO OUT:", res.json())
            save_weight(weight, "OUT", visit_id)
            show_status_message(f"Weight stored: {weight} kg (OUT)", "success")
            refresh_visits()

    except Exception as e:
        print("API Error:", e)
        show_status_message(f"Error sending to API: {str(e)}", "error")

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
            weight_label.config(text=f"{weight:,.2f} kg")
            
            if stable_start and last_weight:
                elapsed = time.time() - stable_start
                progress_bar['value'] = min((elapsed / 4) * 100, 100)
                root.update_idletasks()

            if last_weight is None:
                last_weight = weight
                stable_start = time.time()

            elif abs(weight - last_weight) < 2:
                if time.time() - stable_start >= 4:
                    stable_weight = weight
                    stable_label.config(text=f"✓ Stable: {weight:,.2f} kg")
                    capture_enabled = False
                    progress_bar['value'] = 100
                    show_status_message("Weight stabilized! Click 'Store Weight'", "success")
                    store_btn.config(state="normal")

            else:
                last_weight = weight
                stable_start = time.time()
                progress_bar['value'] = 0

# ========================
# SEARCH FUNCTIONALITY
# ========================
class SearchableTruckSelection:
    def __init__(self, parent, visits, on_select_callback):
        self.parent = parent
        self.visits = visits
        self.on_select = on_select_callback
        self.filtered_visits = visits.copy()
        
        # ========================
        # MAIN CONTAINER FRAME
        # ========================
        # Create main frame that holds all search components
        # bg="#ffffff" = White background for clean look
        # relief=tk.FLAT = No border for modern flat design
        # bd=0 = No border width
        self.frame = tk.Frame(parent, bg="#ffffff", relief=tk.FLAT, bd=0)
        self.frame.pack(fill="both", expand=True)  # Expand to fill available space
        
        # ========================
        # SEARCH SECTION HEADER
        # ========================
        # Label for search section with emoji icon for visual cue
        # font: 11pt bold Segoe UI for emphasis
        # bg="#ffffff" matches parent background
        # fg="#2c3e50" = dark blue-gray for text
        # anchor="w" = left-align text
        # pady=(0, 5) = 0px top padding, 5px bottom padding for spacing
        search_label = tk.Label(
            self.frame,
            text="🔍 Search Trucks",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg="#2c3e50"
        )
        search_label.pack(anchor="w", pady=(0, 5))
        
        # ========================
        # SEARCH INPUT CONTAINER
        # ========================
        # Frame to hold search entry with gray background for contrast
        # bg="#f0f0f0" = light gray background
        # relief=tk.FLAT = flat style
        search_frame = tk.Frame(self.frame, bg="#f0f0f0", relief=tk.FLAT, bd=0)
        search_frame.pack(fill="x", pady=(0, 10))  # fill="x" = stretch horizontally, 10px bottom padding
        
        # Inner frame for search entry with white background and border
        # bg="white" = white background for input field
        # relief=tk.SOLID = solid border
        # bd=1 = 1 pixel border width
        search_entry_frame = tk.Frame(search_frame, bg="white", relief=tk.SOLID, bd=1)
        search_entry_frame.pack(fill="x", padx=5, pady=5)  # padx=5 = 5px horizontal padding, pady=5 = 5px vertical padding
        
        # ========================
        # SEARCH INPUT FIELD
        # ========================
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search)  # Trigger search on every keystroke
        
        self.search_entry = tk.Entry(
            search_entry_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 10),  # 10pt font for input text
            bg="white",  # White background
            fg="#2c3e50",  # Dark text color
            insertbackground="#2c3e50",  # Cursor color
            relief=tk.FLAT  # Flat style for entry
        )
        # pack with side="left" to allow other elements to be on right
        # expand=True allows it to take remaining space
        # fill="x" stretches horizontally
        # padx=10 = 10px left/right internal padding
        # pady=8 = 8px top/bottom internal padding for comfortable height
        self.search_entry.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        
        # ========================
        # CLEAR BUTTON
        # ========================
        # Button to clear search text with "✖" (X) symbol
        # font: 10pt for appropriate size
        # bg="white" matches entry background
        # fg="#7f8c8d" = gray color for less emphasis
        # relief=tk.FLAT = flat button style
        # cursor="hand2" = hand cursor on hover
        # bd=0 = no border for clean look
        clear_btn = tk.Button(
            search_entry_frame,
            text="✖",
            font=("Segoe UI", 10),
            bg="white",
            fg="#7f8c8d",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.clear_search,
            bd=0
        )
        clear_btn.pack(side="right", padx=10)  # padx=10 = 10px horizontal padding from right edge
        
        # ========================
        # RESULTS COUNTER
        # ========================
        # Label showing number of trucks found
        # font: 9pt for secondary information
        # bg="#ffffff" matches main background
        # fg="#7f8c8d" = gray for subtle text
        # anchor="w" = left align
        # pady=(0, 5) = 5px bottom padding for spacing
        self.count_label = tk.Label(
            self.frame,
            text=f"Showing {len(self.filtered_visits)} trucks",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#7f8c8d"
        )
        self.count_label.pack(anchor="w", pady=(0, 5))
        
        # ========================
        # LISTBOX CONTAINER
        # ========================
        # Frame to hold listbox and scrollbar
        # bg="#ffffff" matches main background
        list_frame = tk.Frame(self.frame, bg="#ffffff")
        list_frame.pack(fill="both", expand=True)  # fill="both" = stretch both directions, expand=True = take available space
        
        # ========================
        # SCROLLBAR
        # ========================
        # Scrollbar for listbox
        # pack(side="right", fill="y") = place on right side, fill vertically
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        # ========================
        # TRUCK LISTBOX - MAIN DISPLAY
        # ========================
        # This is the actual widget that shows the list of trucks
        # STYLING OPTIONS:
        # - font: ("Segoe UI", 10) = 10pt Segoe UI font for readability
        # - bg="#f8f9fa" = very light gray background (almost white)
        # - fg="#2c3e50" = dark blue-gray text color
        # - selectbackground="#3498db" = blue highlight when selected
        # - selectforeground="white" = white text when selected
        # - height=10 = show 10 items at once (adjust this for more/less visible items)
        # - relief=tk.FLAT = flat border style
        # - bd=1 = 1 pixel border width
        # - highlightthickness=0 = remove focus highlight for cleaner look
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,  # Connect scrollbar
            font=("Segoe UI", 10),  # Font for list items
            bg="#f8f9fa",  # Light gray background
            fg="#2c3e50",  # Dark text color
            selectbackground="#3498db",  # Blue selection color
            selectforeground="white",  # White text when selected
            height=7,  # Number of visible items (adjust as needed)
            relief=tk.FLAT,  # Flat style
            bd=1,  # 1 pixel border
            highlightthickness=0  # Remove focus ring
        )
        # pack with side="left" to allow scrollbar on right
        # fill="both" = fill both directions
        # expand=True = expand to fill space
        self.listbox.pack(side="left", fill="both", expand=True)
        
        # Connect scrollbar to listbox
        scrollbar.config(command=self.listbox.yview)
        
        # ========================
        # LISTBOX EVENT BINDING
        # ========================
        # Bind selection event to handle when user clicks on a truck
        self.listbox.bind('<<ListboxSelect>>', self.on_listbox_select)
        
        # ========================
        # POPULATE LISTBOX
        # ========================
        # Initial population of listbox with all trucks
        self.update_listbox(self.filtered_visits)
        
        # ========================
        # SELECTED TRUCK DETAILS SECTION
        # ========================
        # LabelFrame with title "Selected Truck Details"
        # font: 10pt bold for header
        # bg="#ffffff" white background
        # fg="#2c3e50" dark text
        # padx=10, pady=10 = 10px internal padding
        self.info_frame = tk.LabelFrame(
            self.frame,
            text="📋 Selected Truck Details",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#2c3e50",
            padx=10,  # 10px horizontal internal padding
            pady=10   # 10px vertical internal padding
        )
        self.info_frame.pack(fill="x", pady=(15, 0))  # pady=(15,0) = 15px top padding, 0 bottom padding
        
        # ========================
        # DETAILS TEXT WIDGET
        # ========================
        # Text widget to display selected truck details
        # height=6 = show 6 lines of text
        # font: 9pt for details
        # bg="#f8f9fa" light gray background
        # fg="#2c3e50" dark text
        # relief=tk.FLAT flat style
        # wrap=tk.WORD wrap text at word boundaries
        # padx=10, pady=10 = 10px internal padding for comfortable reading
        self.info_text = tk.Text(
            self.info_frame,
            height=6,
            font=("Segoe UI", 9),
            bg="#f8f9fa",
            fg="#2c3e50",
            relief=tk.FLAT,
            wrap=tk.WORD,
            padx=10,  # 10px horizontal internal padding
            pady=10   # 10px vertical internal padding
        )
        self.info_text.pack(fill="x")  # fill="x" = stretch horizontally
    
    # ========================
    # SEARCH METHOD
    # ========================
    def on_search(self, *args):
        """Filter truck list based on search term"""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            # If search is empty, show all trucks
            self.filtered_visits = self.visits.copy()
        else:
            # Filter trucks based on multiple fields
            self.filtered_visits = []
            for visit in self.visits:
                # Search in ID, plate number, driver name, phone, and truck type
                if (search_term in str(visit['id']).lower() or
                    search_term in visit['plate_number'].lower() or
                    search_term in visit['driver_name'].lower() or
                    search_term in visit.get('driver_phone', '').lower() or
                    search_term in visit.get('truck_type', '').lower()):
                    self.filtered_visits.append(visit)
        
        # Update UI with filtered results
        self.update_listbox(self.filtered_visits)
        # Update counter label
        self.count_label.config(text=f"Showing {len(self.filtered_visits)} trucks")
    
    # ========================
    # CLEAR SEARCH METHOD
    # ========================
    def clear_search(self):
        """Clear search input and reset to full list"""
        self.search_var.set("")  # Clear search text
        self.search_entry.focus()  # Return focus to search box
    
    # ========================
    # UPDATE LISTBOX METHOD
    # ========================
    def update_listbox(self, visits):
        """Populate listbox with truck data"""
        self.listbox.delete(0, tk.END)  # Clear existing items
        
        # Add each truck to the listbox
        for visit in visits:
            # Insert display_text into listbox
            # display_text format: "ID - PLATE_NUMBER (DRIVER_NAME)"
            self.listbox.insert(tk.END, visit['display_text'])
        
        # Handle empty results
        if len(visits) == 0:
            self.listbox.insert(tk.END, "  No results found")
            # Style the "no results" message in red
            self.listbox.itemconfig(0, fg="#e74c3c")
    
    # ========================
    # LISTBOX SELECTION HANDLER
    # ========================
    def on_listbox_select(self, event):
        """Handle when user selects a truck from the list"""
        selection = self.listbox.curselection()
        if selection and self.filtered_visits:
            index = selection[0]
            if index < len(self.filtered_visits):
                selected = self.filtered_visits[index]
                # Call callback with selected truck ID
                self.on_select(selected['id'])
                # Show detailed information
                self.show_truck_details(selected)
    
    # ========================
    # DISPLAY TRUCK DETAILS
    # ========================
    def show_truck_details(self, visit):
        """Display detailed information about selected truck"""
        self.info_text.delete(1.0, tk.END)  # Clear existing text
        
        # Format details with sections and spacing
        # Using emoji icons for visual appeal
        details = f"""
🚛 Truck Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ID: {visit['id']}
Plate Number: {visit['plate_number']}
Truck Type: {visit.get('truck_type', 'N/A')}

👤 Driver Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {visit['driver_name']}
Phone: {visit.get('driver_phone', 'N/A')}
        """
        self.info_text.insert(1.0, details.strip())
    
    # ========================
    # REFRESH VISITS METHOD
    # ========================
    def refresh_visits(self, new_visits):
        """Update the truck list with fresh data"""
        self.visits = new_visits
        self.filtered_visits = new_visits.copy()
        self.search_var.set("")  # Clear search
        self.update_listbox(self.filtered_visits)  # Update listbox
        self.count_label.config(text=f"Showing {len(self.filtered_visits)} trucks")  # Update counter
        self.info_text.delete(1.0, tk.END)  # Clear details
        self.info_text.insert(1.0, "Select a truck to view details")  # Reset message

# ========================
# BUTTONS
# ========================
def enable_capture():
    global capture_enabled
    if selected_visit_id.get() == 0:
        show_status_message("Please select a truck visit first!", "error")
        return
    
    stable_label.config(text="⚡ Waiting for stable weight...")
    weight_label.config(text="--- kg")
    capture_enabled = True
    progress_bar['value'] = 0
    store_btn.config(state="disabled")
    show_status_message("Measuring... Please wait for stable weight", "info")

def store_weight():
    global stable_weight

    if stable_weight is not None:
        send_to_api(stable_weight)
        stable_weight = None
        weight_label.config(text="0 kg")
        store_btn.config(state="disabled")
        capture_btn.config(state="normal")

def show_status_message(message, msg_type="info"):
    status_label.config(text=message)
    if msg_type == "error":
        status_label.config(fg="#e74c3c")
    elif msg_type == "success":
        status_label.config(fg="#27ae60")
    else:
        status_label.config(fg="#3498db")
    
    root.after(3000, lambda: status_label.config(text="✓ Ready", fg="#7f8c8d"))

# ========================
# UI STYLING
# ========================
class StyledButton(tk.Button):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=12
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def on_enter(self, e):
        self.configure(background=self['activebackground'])
    
    def on_leave(self, e):
        self.configure(background=self['background'])

# ========================
# MAIN UI
# ========================
root = tk.Tk()
root.title("Weighbridge Capture System")
root.geometry("1200x700")
root.configure(bg="#f5f6fa")

# Configure custom fonts
title_font = font.Font(family="Segoe UI", size=24, weight="bold")
label_font = font.Font(family="Segoe UI", size=11)
weight_font = font.Font(family="Segoe UI", size=48, weight="bold")

# Main container
main_container = tk.Frame(root, bg="#f5f6fa")
main_container.pack(fill="both", expand=True, padx=20, pady=20)

# Header
header_frame = tk.Frame(main_container, bg="#f5f6fa")
header_frame.pack(fill="x", pady=(0, 20))

title = tk.Label(
    header_frame,
    text="WEIGHBRIDGE CAPTURE SYSTEM",
    font=title_font,
    bg="#f5f6fa",
    fg="#2c3e50"
)
title.pack()

subtitle = tk.Label(
    header_frame,
    text="Real-time Weight Measurement & Truck Management",
    font=("Segoe UI", 10),
    bg="#f5f6fa",
    fg="#7f8c8d"
)
subtitle.pack()

# Two-column layout
columns_frame = tk.Frame(main_container, bg="#f5f6fa")
columns_frame.pack(fill="both", expand=True)

# Left column - Weight Measurement
left_column = tk.Frame(columns_frame, bg="#ffffff", relief=tk.RAISED, bd=0)
left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))

# Weight card
weight_card = tk.Frame(left_column, bg="white")
weight_card.pack(fill="both", expand=True, padx=20, pady=20)

weight_label_title = tk.Label(
    weight_card,
    text="Current Weight",
    font=("Segoe UI", 14, "bold"),
    bg="white",
    fg="#7f8c8d"
)
weight_label_title.pack(pady=(0, 10))

weight_label = tk.Label(
    weight_card,
    text="0 kg",
    font=weight_font,
    bg="white",
    fg="#2c3e50"
)
weight_label.pack(pady=20)

# Progress bar
progress_frame = tk.Frame(weight_card, bg="white")
progress_frame.pack(fill="x", pady=20)

progress_label = tk.Label(
    progress_frame,
    text="Stability Progress",
    font=("Segoe UI", 10),
    bg="white",
    fg="#7f8c8d"
)
progress_label.pack()

progress_bar = ttk.Progressbar(
    progress_frame,
    length=300,
    mode='determinate',
    style="green.Horizontal.TProgressbar"
)
progress_bar.pack(pady=10)

stable_label = tk.Label(
    weight_card,
    text="⚡ Not capturing",
    font=("Segoe UI", 12),
    bg="white",
    fg="#7f8c8d"
)
stable_label.pack(pady=10)

# Buttons
button_frame = tk.Frame(weight_card, bg="white")
button_frame.pack(fill="x", pady=20)

capture_btn = StyledButton(
    button_frame,
    text="🎯 START MEASUREMENT",
    command=enable_capture,
    bg="#3498db",
    fg="white",
    activebackground="#2980b9"
)
capture_btn.pack(side="left", padx=5, expand=True, fill="x")

store_btn = StyledButton(
    button_frame,
    text="💾 STORE WEIGHT",
    command=store_weight,
    bg="#27ae60",
    fg="white",
    activebackground="#229954",
    state="disabled"
)
store_btn.pack(side="left", padx=5, expand=True, fill="x")

# Status
status_frame = tk.Frame(weight_card, bg="white")
status_frame.pack(fill="x", pady=10)

status_label = tk.Label(
    status_frame,
    text="✓ Ready",
    font=("Segoe UI", 10),
    bg="white",
    fg="#7f8c8d"
)
status_label.pack()

# Right column - Truck Management
right_column = tk.Frame(columns_frame, bg="#ffffff", relief=tk.RAISED, bd=0)
right_column.pack(side="right", fill="both", expand=True, padx=(10, 0))

# Truck management header
truck_header = tk.Frame(right_column, bg="white")
truck_header.pack(fill="x", padx=20, pady=20)

truck_title = tk.Label(
    truck_header,
    text="🚛 TRUCK MANAGEMENT",
    font=("Segoe UI", 14, "bold"),
    bg="white",
    fg="#2c3e50"
)
truck_title.pack(side="left")

refresh_btn = StyledButton(
    truck_header,
    text="↻ REFRESH",
    command=lambda: refresh_visits(),
    bg="#95a5a6",
    fg="white",
    activebackground="#7f8c8d",
    padx=15,
    pady=5
)
refresh_btn.pack(side="right")

# Separator
separator = ttk.Separator(right_column, orient='horizontal')
separator.pack(fill='x', padx=20)

# Truck selection content
truck_content = tk.Frame(right_column, bg="white")
truck_content.pack(fill="both", expand=True, padx=20, pady=20)

selected_visit_id = tk.IntVar(value=0)

# Fetch initial visits
visits = fetch_truck_visits()

def on_truck_selected(visit_id):
    selected_visit_id.set(visit_id)
    for visit in visits:
        if visit['id'] == visit_id:
            show_status_message(f"Selected: {visit['display_text']}", "info")
            break

search_selection = SearchableTruckSelection(truck_content, visits, on_truck_selected)

# Configure styles for ttk widgets
style = ttk.Style()
style.theme_use('clam')
style.configure("green.Horizontal.TProgressbar",
                background='#27ae60',
                troughcolor='#ecf0f1',
                bordercolor='#ecf0f1',
                lightcolor='#27ae60',
                darkcolor='#27ae60',
                thickness=10)

# ========================
# FUNCTIONS
# ========================
def refresh_visits():
    global visits
    
    visits = fetch_truck_visits()
    search_selection.refresh_visits(visits)
    
    selected_visit_id.set(0)
    show_status_message(f"Loaded {len(visits)} trucks!", "success")

# ========================
# START THREAD
# ========================
thread = Thread(target=weight_listener)
thread.daemon = True
thread.start()

root.mainloop()