import socket
import time
from datetime import datetime
import random

SERVER_IP = "127.0.0.1"   # listener.py PC
SERVER_PORT = 4001        # same port

def generate_weight():
    """
    Simulate real weighbridge behavior:
    - weight fluctuates slightly
    - sometimes unstable (ST=0)
    """
    base_weight = 35640
    fluctuation = random.randint(-20, 20)
    stable = random.choice([0, 1, 1, 1])  # mostly stable
    return base_weight + fluctuation, stable

def start_simulator():
    print("Starting Weighbridge Simulator...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))

    while True:
        weight, stable = generate_weight()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = f"WT={weight};ST={stable};UNIT=KG;TIME={timestamp}"
        sock.sendall((data + "\n").encode())

        print("Sent:", data)
        time.sleep(10)  # 1 second interval

if __name__ == "__main__":
    start_simulator()

