import socket
import struct
import time
import sqlite3

UDP_IP = "0.0.0.0"
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for weighbridge data...")

last_capture = 0
capture_interval = 2


def detect_direction(weight):

    if weight < 100:
        return "EMPTY"
    elif weight > 1000:
        return "IN"
    else:
        return "OUT"


def save_weight(weight):

    direction = detect_direction(weight)

    conn = sqlite3.connect("weighbridge.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO weights (weight, direction, status)
        VALUES (?, ?, ?)
    """, (weight, direction, "unused"))

    conn.commit()
    conn.close()


while True:

    data, addr = sock.recvfrom(1024)
    now = time.time()

    if now - last_capture >= capture_interval:

        weight = struct.unpack('<f', data[44:48])[0]

        if weight > 1:

            weight = round(weight, 2)

            print("Captured Weight:", weight, "kg")

            save_weight(weight)

        last_capture = now