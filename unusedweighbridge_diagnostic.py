#!/usr/bin/env python3
"""
Weighbridge Diagnostic Tool
Tests connection and displays raw data from weighbridge
"""

import socket
import sys
import time

# Configuration
WEIGHBRIDGE_IP = "192.168.1.100"
COMMON_PORTS = [4001, 4002, 8001, 9001, 23, 502, 10001]

def test_ping():
    """Test basic network connectivity"""
    print("\n" + "="*60)
    print("STEP 1: Testing Network Connection (PING)")
    print("="*60)
    
    import platform
    import subprocess
    
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', WEIGHBRIDGE_IP]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ Ping successful to {WEIGHBRIDGE_IP}")
            return True
        else:
            print(f"✗ Ping failed to {WEIGHBRIDGE_IP}")
            return False
    except Exception as e:
        print(f"✗ Ping test error: {e}")
        return False

def test_port(ip, port, timeout=3):
    """Test if a specific port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def scan_ports():
    """Scan common weighbridge ports"""
    print("\n" + "="*60)
    print("STEP 2: Scanning Common Weighbridge Ports")
    print("="*60)
    
    open_ports = []
    
    for port in COMMON_PORTS:
        print(f"Testing port {port}...", end=" ")
        if test_port(WEIGHBRIDGE_IP, port):
            print(f"✓ OPEN")
            open_ports.append(port)
        else:
            print(f"✗ Closed")
    
    return open_ports

def read_data_from_port(ip, port, duration=10):
    """Connect to port and read data"""
    print("\n" + "="*60)
    print(f"STEP 3: Reading Data from {ip}:{port}")
    print("="*60)
    print(f"Listening for {duration} seconds...\n")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        print(f"Connecting...", end=" ")
        sock.connect((ip, port))
        print(f"✓ Connected!\n")
        
        start_time = time.time()
        data_received = False
        
        print("Waiting for data (put weight on scale):\n")
        print("-" * 60)
        
        while (time.time() - start_time) < duration:
            try:
                data = sock.recv(1024)
                if data:
                    data_received = True
                    decoded = data.decode('ascii', errors='ignore')
                    print(f"[{time.strftime('%H:%M:%S')}] RAW: {repr(data)}")
                    print(f"[{time.strftime('%H:%M:%S')}] TXT: {decoded.strip()}")
                    print("-" * 60)
            except socket.timeout:
                continue
        
        sock.close()
        
        if not data_received:
            print("\n⚠ No data received during test period")
            print("   Possible reasons:")
            print("   - Data output not enabled on weighbridge")
            print("   - Wrong port number")
            print("   - Need to trigger reading manually")
            print("   - Device in command-response mode (not continuous)")
        
        return data_received
        
    except ConnectionRefusedError:
        print(f"✗ Connection refused on port {port}")
        return False
    except socket.timeout:
        print(f"✗ Connection timeout on port {port}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def try_commands(ip, port):
    """Try common commands to trigger weight reading"""
    print("\n" + "="*60)
    print(f"STEP 4: Testing Common Commands")
    print("="*60)
    
    commands = [
        (b'P\r\n', 'Print/Poll'),
        (b'W\r\n', 'Weight'),
        (b'S\r\n', 'Send'),
        (b'R\r\n', 'Read'),
        (b'\x05', 'ENQ (Enquiry)'),
        (b'G\r\n', 'Get'),
    ]
    
    for cmd, name in commands:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((ip, port))
            
            print(f"\nTrying command: {name} ({repr(cmd)})")
            sock.send(cmd)
            
            time.sleep(0.5)
            
            try:
                response = sock.recv(1024)
                if response:
                    print(f"  ✓ Response: {response.decode('ascii', errors='ignore').strip()}")
            except socket.timeout:
                print(f"  ✗ No response")
            
            sock.close()
            
        except Exception as e:
            print(f"  ✗ Error: {e}")

def main():
    print("\n" + "="*60)
    print("WEIGHBRIDGE DIAGNOSTIC TOOL")
    print("="*60)
    print(f"Target Device: {WEIGHBRIDGE_IP}")
    print("="*60)
    
    # Step 1: Test ping
    if not test_ping():
        print("\n❌ Cannot reach device. Check network connection.")
        sys.exit(1)
    
    # Step 2: Scan ports
    open_ports = scan_ports()
    
    if not open_ports:
        print("\n❌ No open ports found.")
        print("\nNext steps:")
        print("1. Access weighbridge menu (SETUP/MENU button)")
        print("2. Enable TCP/IP or Ethernet communication")
        print("3. Set IP address and port number")
        print("4. Save settings and reboot device")
        sys.exit(1)
    
    print(f"\n✓ Found {len(open_ports)} open port(s): {open_ports}")
    
    # Step 3: Try to read data from each open port
    for port in open_ports:
        data_received = read_data_from_port(WEIGHBRIDGE_IP, port, duration=10)
        
        if data_received:
            print(f"\n✅ SUCCESS! Port {port} is sending data.")
            print(f"\nUse this configuration in your integration:")
            print(f"  WEIGHBRIDGE_IP = '{WEIGHBRIDGE_IP}'")
            print(f"  WEIGHBRIDGE_PORT = {port}")
            break
        
        # If no data, try commands
        if not data_received:
            try_commands(WEIGHBRIDGE_IP, port)
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic stopped by user\n")
        sys.exit(0)