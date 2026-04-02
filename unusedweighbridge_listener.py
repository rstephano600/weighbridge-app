import socket

UDP_IP = "0.0.0.0"
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for weighbridge data...")

while True:
    data, addr = sock.recvfrom(1024)

    print("RAW:", data)

    message = data.decode('utf-8', errors='ignore').strip()

    print("Decoded:", message)