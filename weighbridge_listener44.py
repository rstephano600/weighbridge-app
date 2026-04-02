import socket
import struct
import time

UDP_IP = "0.0.0.0"
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for weighbridge data...")

last_capture = 0
capture_interval = 2

while True:

    data, addr = sock.recvfrom(1024)
    now = time.time()

    if now - last_capture >= capture_interval:

        weight = struct.unpack('<f', data[44:48])[0]

        if weight > 1:
            print("Captured Weight:", round(weight,2), "kg")

        last_capture = now