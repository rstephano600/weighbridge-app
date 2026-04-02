import socket
import struct
import time
import random

UDP_IP = "127.0.0.1"
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("Starting Weighbridge Simulator...")


def send_weight(weight):

    packet = bytearray(60)
    packet[44:48] = struct.pack('<f', weight)

    sock.sendto(packet, (UDP_IP, UDP_PORT))

    print("Sent:", round(weight,2), "kg")


while True:

    print("\nTruck approaching...")

    # ramp up weight (truck entering scale)
    weight = 0
    target = random.randint(15000, 35000)

    while weight < target:

        weight += random.randint(1000, 3000)
        send_weight(weight)
        time.sleep(1)

    print("Truck fully on scale")

    # stable weight phase
    for i in range(8):

        stable_weight = target + random.uniform(-1, 1)
        send_weight(stable_weight)
        time.sleep(1)

    print("Truck leaving...")

    # ramp down weight
    while weight > 0:

        weight -= random.randint(2000, 4000)
        weight = max(weight, 0)

        send_weight(weight)
        time.sleep(1)

    print("Scale empty\n")

    time.sleep(10)