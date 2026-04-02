import socket
import logging
from datetime import datetime
import requests

LARAVEL_API = "http://127.0.0.1:8000/api/weighbridge/ingest"

HOST = "192.168.1.100"
PORT = 4001

# Setup logging
logging.basicConfig(
    filename="C:\\weighbridge\\logs\\listener.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

def start_listener():
    print("Starting Weighbridge TCP Listener...")
    logging.info("Listener started")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    while True:
        conn, addr = server.accept()
        print(f"Connected from {addr}")
        logging.info(f"Connected from {addr}")

        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                raw = data.decode(errors="ignore").strip()
                print(raw)
                logging.info(raw)

                # Send to Laravel API
                try:
                    response = requests.post(
                        LARAVEL_API,
                        json={"raw": raw},
                        timeout=2
                    )
                    logging.info(f"API response: {response.status_code}")
                except requests.RequestException as e:
                    logging.error(f"API error: {e}")

        except Exception as e:
            logging.error(str(e))

        finally:
            conn.close()
            logging.info("Connection closed")

if __name__ == "__main__":
    start_listener()
