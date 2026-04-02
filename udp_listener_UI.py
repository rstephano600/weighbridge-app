#!/usr/bin/env python3
"""
UDP Weighbridge Integration Client
Receives UDP data from weighbridge and sends to Laravel API
"""

import socket
import requests
import re
import time
from datetime import datetime

# ============================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================

WEIGHBRIDGE_IP = "192.168.1.100"      # Your weighbridge IP
UDP_PORT = 4001                        # UDP port (will be detected)
LISTEN_ALL_IPS = True                  # True = listen from any IP, False = only from WEIGHBRIDGE_IP

LARAVEL_API_URL = "http://your-domain.com/api/weighbridge/reading"
LARAVEL_API_TOKEN = "your-api-token-here"

# Settings
SEND_DUPLICATE_WEIGHTS = False
MIN_WEIGHT = 0
MAX_WEIGHT = 50000

# ============================================
# UDP CLIENT CODE
# ============================================

class UDPWeighbridgeClient:
    def __init__(self):
        self.socket = None
        self.last_weight = None
        self.connected = False
        
    def start_listening(self):
        """Start UDP listener"""
        try:
            print(f"\n{'='*60}")
            print(f"UDP WEIGHBRIDGE INTEGRATION CLIENT")
            print(f"{'='*60}")
            print(f"Listening for UDP data:")
            print(f"  From IP: {WEIGHBRIDGE_IP if not LISTEN_ALL_IPS else 'Any IP'}")
            print(f"  On Port: {UDP_PORT}")
            print(f"  Laravel API: {LARAVEL_API_URL}")
            print(f"{'='*60}\n")
            
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to port (listen on all interfaces)
            self.socket.bind(('', UDP_PORT))
            self.socket.settimeout(1)
            
            self.connected = True
            print(f"✓ UDP listener started on port {UDP_PORT}")
            print(f"✓ Waiting for weight data...\n")
            
            return True
            
        except PermissionError:
            print(f"✗ Permission denied on port {UDP_PORT}")
            print(f"  Try running with: sudo python3 {__file__}")
            return False
            
        except OSError as e:
            print(f"✗ Cannot bind to port {UDP_PORT}: {e}")
            print(f"  Port may already be in use")
            return False
            
        except Exception as e:
            print(f"✗ Error starting listener: {e}")
            return False
    
    def parse_weight(self, raw_data):
        """Parse weight data from UDP packet"""
        try:
            data = raw_data.decode('ascii', errors='ignore').strip()
            
            if not data or len(data) < 3:
                return None
            
            print(f"[RAW] {data}")
            
            # Pattern 1: ST,GS,+01234.5,kg
            match = re.search(r'([A-Z]{2}),([A-Z]{2}),([\+\-]?\d+\.?\d*),(\w+)', data)
            if match:
                return {
                    'status': match.group(1),
                    'weight_type': match.group(2),
                    'weight': float(match.group(3)),
                    'unit': match.group(4),
                    'is_stable': (match.group(1) == 'ST'),
                    'raw_data': data,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Pattern 2: Simple "1234.5 kg"
            match = re.search(r'([\d.]+)\s*(kg|t|lb|g)', data, re.IGNORECASE)
            if match:
                weight = float(match.group(1))
                unit = match.group(2).lower()
                
                return {
                    'status': 'ST',
                    'weight_type': 'GS',
                    'weight': weight,
                    'unit': unit,
                    'is_stable': True,
                    'raw_data': data,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Pattern 3: Just numbers
            match = re.search(r'([\d.]+)', data)
            if match:
                weight = float(match.group(1))
                
                if MIN_WEIGHT <= weight <= MAX_WEIGHT:
                    return {
                        'status': 'ST',
                        'weight_type': 'GS',
                        'weight': weight,
                        'unit': 'kg',
                        'is_stable': True,
                        'raw_data': data,
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Parse failed: {e}")
            return None
    
    def send_to_laravel(self, weight_data):
        """Send weight data to Laravel API"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {LARAVEL_API_TOKEN}',
                'Accept': 'application/json'
            }
            
            response = requests.post(
                LARAVEL_API_URL,
                json=weight_data,
                headers=headers,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                print(f"[SUCCESS] ✓ Sent: {weight_data['weight']} {weight_data['unit']}")
                return True
            else:
                print(f"[ERROR] ✗ API error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"[ERROR] ✗ Laravel API timeout")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] ✗ Cannot reach Laravel API")
            return False
        except Exception as e:
            print(f"[ERROR] ✗ Send failed: {e}")
            return False
    
    def should_send_weight(self, weight):
        """Check if weight should be sent"""
        if SEND_DUPLICATE_WEIGHTS:
            return True
        
        if weight == self.last_weight:
            return False
        
        return True
    
    def listen(self):
        """Main UDP listening loop"""
        while self.connected:
            try:
                # Receive UDP packet
                data, addr = self.socket.recvfrom(1024)
                
                # Filter by IP if configured
                if not LISTEN_ALL_IPS and addr[0] != WEIGHBRIDGE_IP:
                    continue
                
                if data:
                    print(f"[UDP] Received from {addr[0]}:{addr[1]}")
                    
                    # Parse weight
                    weight_data = self.parse_weight(data)
                    
                    if weight_data:
                        # Only send stable weights
                        if weight_data['is_stable']:
                            if self.should_send_weight(weight_data['weight']):
                                success = self.send_to_laravel(weight_data)
                                
                                if success:
                                    self.last_weight = weight_data['weight']
                            else:
                                print(f"[SKIP] Duplicate: {weight_data['weight']} {weight_data['unit']}")
                        else:
                            print(f"[SKIP] Unstable: {weight_data['weight']} {weight_data['unit']}")
                    
                    print()  # Blank line for readability
                
            except socket.timeout:
                # Timeout is normal for UDP
                continue
                
            except KeyboardInterrupt:
                print(f"\n{'='*60}")
                print("Stopped by user")
                print(f"{'='*60}\n")
                break
                
            except Exception as e:
                print(f"[ERROR] {e}")
    
    def close(self):
        """Close UDP socket"""
        if self.socket:
            self.socket.close()
            self.connected = False
            print(f"✓ UDP listener closed\n")


# ============================================
# MAIN PROGRAM
# ============================================

def main():
    client = UDPWeighbridgeClient()
    
    try:
        if client.start_listening():
            client.listen()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}\n")
    finally:
        client.close()


if __name__ == "__main__":
    main()


# ============================================
# QUICK START
# ============================================
"""
SETUP:
1. First run the UDP detector to find the port:
   python3 udp_listener.py

2. Update configuration at top of this file:
   - UDP_PORT: Port number found by detector
   - LARAVEL_API_URL: Your Laravel API endpoint
   - LARAVEL_API_TOKEN: Your API token

3. Install requests:
   pip install requests

4. Run this script:
   python3 weighbridge_udp_client.py

5. May need sudo/admin on Linux:
   sudo python3 weighbridge_udp_client.py

STOP: Press Ctrl+C
"""