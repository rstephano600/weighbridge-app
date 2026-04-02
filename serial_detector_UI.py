#!/usr/bin/env python3
"""
Serial (RS-232/RS-485) Weighbridge Integration Client
Reads weight data from serial port and sends to Laravel API
"""

import serial
import requests
import re
import time
from datetime import datetime

# ============================================
# CONFIGURATION - EDIT AFTER RUNNING DETECTOR
# ============================================

# Serial Port Settings (from detector results)
SERIAL_PORT = "COM3"          # Windows: COM3, COM4, etc. | Linux: /dev/ttyUSB0
BAUDRATE = 9600               # Common: 9600, 19200, 4800, 38400
BYTESIZE = 8                  # Usually 7 or 8
PARITY = 'N'                  # N=None, E=Even, O=Odd
STOPBITS = 1                  # Usually 1 or 2

# Laravel API Settings
LARAVEL_API_URL = "http://your-domain.com/api/weighbridge/reading"
LARAVEL_API_TOKEN = "your-api-token-here"

# Application Settings
SEND_DUPLICATE_WEIGHTS = False
MIN_WEIGHT = 0
MAX_WEIGHT = 50000
RECONNECT_DELAY = 5

# ============================================
# SERIAL CLIENT CODE
# ============================================

class SerialWeighbridgeClient:
    def __init__(self):
        self.serial = None
        self.last_weight = None
        self.connected = False
        
        # Convert parity and stopbits
        self.parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD,
        }
        
        self.stopbits_map = {
            1: serial.STOPBITS_ONE,
            2: serial.STOPBITS_TWO,
        }
    
    def connect(self):
        """Connect to serial port"""
        try:
            print(f"\n{'='*60}")
            print(f"SERIAL WEIGHBRIDGE INTEGRATION CLIENT")
            print(f"{'='*60}")
            print(f"Connecting to:")
            print(f"  Port:     {SERIAL_PORT}")
            print(f"  Baudrate: {BAUDRATE}")
            print(f"  Format:   {BYTESIZE}-{PARITY}-{STOPBITS}")
            print(f"  Laravel:  {LARAVEL_API_URL}")
            print(f"{'='*60}\n")
            
            self.serial = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUDRATE,
                bytesize=BYTESIZE,
                parity=self.parity_map[PARITY],
                stopbits=self.stopbits_map[STOPBITS],
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            # Wait for port to stabilize
            time.sleep(1)
            
            # Clear any existing data
            self.serial.reset_input_buffer()
            
            self.connected = True
            print(f"✓ Serial port connected successfully")
            print(f"✓ Listening for weight data...\n")
            
            return True
            
        except serial.SerialException as e:
            print(f"✗ Serial port error: {e}")
            print(f"\nTroubleshooting:")
            print(f"  - Check port name (Windows: COM3, Linux: /dev/ttyUSB0)")
            print(f"  - Verify cable is connected")
            print(f"  - Check if port is already in use")
            print(f"  - On Linux, may need: sudo usermod -a -G dialout $USER")
            return False
            
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def parse_weight(self, raw_data):
        """Parse weight data from serial output"""
        try:
            data = raw_data.decode('ascii', errors='ignore').strip()
            
            if not data or len(data) < 3:
                return None
            
            print(f"[RAW] {data}")
            
            # Pattern 1: ST,GS,+01234.5,kg (Structured format)
            match = re.search(r'([A-Z]{2}),([A-Z]{2}),([\+\-]?\d+\.?\d*),(\w+)', data)
            if match:
                status = match.group(1)
                weight_type = match.group(2)
                weight = float(match.group(3))
                unit = match.group(4)
                
                return {
                    'status': status,
                    'weight_type': weight_type,
                    'weight': weight,
                    'unit': unit,
                    'is_stable': (status == 'ST'),
                    'raw_data': data,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Pattern 2: "Weight: 1234.5 kg" or "1234.5 kg"
            match = re.search(r'([\d.]+)\s*(kg|t|lb|g|tons?)', data, re.IGNORECASE)
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
            
            # Pattern 3: Just numbers "1234.5"
            match = re.search(r'([\d.]+)', data)
            if match:
                weight = float(match.group(1))
                
                # Validate range
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
            print(f"[ERROR] Parse error: {e}")
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
        """Main serial listening loop"""
        while self.connected:
            try:
                if self.serial.in_waiting > 0:
                    # Read line from serial port
                    line = self.serial.readline()
                    
                    if line:
                        # Parse weight
                        weight_data = self.parse_weight(line)
                        
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
                
                time.sleep(0.1)  # Small delay to prevent CPU overuse
                
            except serial.SerialException as e:
                print(f"\n[ERROR] Serial connection lost: {e}")
                print(f"Reconnecting in {RECONNECT_DELAY} seconds...")
                self.connected = False
                time.sleep(RECONNECT_DELAY)
                self.connect()
                
            except KeyboardInterrupt:
                print(f"\n{'='*60}")
                print("Stopped by user")
                print(f"{'='*60}\n")
                break
                
            except Exception as e:
                print(f"[ERROR] {e}")
    
    def close(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.connected = False
            print(f"\n✓ Serial connection closed\n")


# ============================================
# MAIN PROGRAM
# ============================================

def main():
    # Check if pyserial is installed
    try:
        import serial
    except ImportError:
        print("\n" + "="*60)
        print("ERROR: pyserial not installed")
        print("="*60)
        print("\nInstall it using:")
        print("  pip install pyserial")
        print("\n" + "="*60 + "\n")
        return
    
    # Check if requests is installed
    try:
        import requests
    except ImportError:
        print("\n" + "="*60)
        print("ERROR: requests not installed")
        print("="*60)
        print("\nInstall it using:")
        print("  pip install requests")
        print("\n" + "="*60 + "\n")
        return
    
    client = SerialWeighbridgeClient()
    
    try:
        if client.connect():
            client.listen()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}\n")
    finally:
        client.close()


if __name__ == "__main__":
    main()


# ============================================
# SETUP INSTRUCTIONS
# ============================================
"""
STEP 1: Install required libraries
  pip install pyserial requests

STEP 2: Run the detector to find your settings
  python3 serial_detector.py

STEP 3: Update configuration at top of this file:
  - SERIAL_PORT: Your COM port or /dev/ttyUSB0
  - BAUDRATE: From detector (usually 9600)
  - BYTESIZE, PARITY, STOPBITS: From detector
  - LARAVEL_API_URL: Your Laravel endpoint
  - LARAVEL_API_TOKEN: Your API token

STEP 4: Run this script
  python3 serial_weighbridge_client.py

LINUX PERMISSIONS:
If you get "Permission denied" error:
  sudo usermod -a -G dialout $USER
  (then logout and login)

Or run with sudo:
  sudo python3 serial_weighbridge_client.py

STOP: Press Ctrl+C
"""