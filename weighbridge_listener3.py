import socket
import struct
import time

UDP_IP = "0.0.0.0"
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for weighbridge data...")

last_capture = 0
capture_interval = 3   # seconds

while True:
    data, addr = sock.recvfrom(1024)

    current_time = time.time()

    # only process every 2 seconds
    if current_time - last_capture < capture_interval:
        continue

    last_capture = current_time

    print("\n--- Packet Received ---")

    # search for possible float values
    for i in range(0, len(data)-4):

        try:
            value = struct.unpack('<f', data[i:i+4])[0]

            # realistic weighbridge range
            if 0 < value < 200000:
                print("Offset:", i, "Value:", round(value,2))

        except:
            pass