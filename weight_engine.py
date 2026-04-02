import socket
import struct
import time
import requests

UDP_IP = "0.0.0.0"
UDP_PORT = 5000

API_URL = "http://localhost:8000/api/live-weight"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Weight engine started...")

last_weight = 0
stable_counter = 0

while True:

    data, addr = sock.recvfrom(1024)

    weight = struct.unpack('<f', data[44:48])[0]

    if abs(weight - last_weight) < 3:
        stable_counter += 1
    else:
        stable_counter = 0

    stable = stable_counter > 3

    payload = {
        "weight": round(weight,2),
        "stable": stable
    }

    try:
        requests.post(API_URL, json=payload)
    except:
        pass

    last_weight = weight

    time.sleep(1)
