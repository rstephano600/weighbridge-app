#!/usr/bin/env python3
"""
UDP Weighbridge Listener
Listens for UDP broadcasts/unicasts from weighbridge
"""

import socket
import sys
import time
from datetime import datetime

# Configuration
WEIGHBRIDGE_IP = "192.168.1.100"
COMMON_UDP_PORTS = [13805, 4001, 4002, 3000, 8000, 8001, 9001, 10001, 50000]

def listen_udp_port(port, duration=15):
    """Listen for UDP data on a specific port"""
    print(f"\n{'='*60}")
    print(f"Listening on UDP port {port} for {duration} seconds")
    print(f"{'='*60}")
    
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to all interfaces on this port
        sock.bind(('', port))
        sock.settimeout(1)
        
        print(f"✓ Listening on 0.0.0.0:{port}")
        print(f"  Put weight on scale to trigger data...\n")
        print("-" * 60)
        
        start_time = time.time()
        data_received = False
        
        while (time.time() - start_time) < duration:
            try:
                data, addr = sock.recvfrom(1024)
                
                if data:
                    data_received = True
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    
                    print(f"\n[{timestamp}] ✓ Data received from {addr[0]}:{addr[1]}")
                    print(f"RAW BYTES: {repr(data)}")
                    print(f"TEXT:      {data.decode('ascii', errors='ignore').strip()}")
                    print("-" * 60)
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error receiving: {e}")
        
        sock.close()
        return data_received
        
    except PermissionError:
        print(f"✗ Permission denied on port {port}")
        print(f"  Try running with sudo/administrator privileges")
        return False
    except OSError as e:
        print(f"✗ Cannot bind to port {port}: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def listen_broadcast(duration=15):
    """Listen for UDP broadcast messages"""
    print(f"\n{'='*60}")
    print(f"Listening for UDP BROADCAST messages")
    print(f"{'='*60}")
    
    try:
        # Create UDP socket for broadcast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Bind to all interfaces
        sock.bind(('', 0))  # Bind to any available port
        sock.settimeout(1)
        
        print(f"✓ Listening for broadcasts on all ports")
        print(f"  Duration: {duration} seconds")
        print(f"  Put weight on scale...\n")
        print("-" * 60)
        
        start_time = time.time()
        data_received = False
        
        while (time.time() - start_time) < duration:
            try:
                data, addr = sock.recvfrom(1024)
                
                if data:
                    data_received = True
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    
                    print(f"\n[{timestamp}] ✓ Broadcast from {addr[0]}:{addr[1]}")
                    print(f"RAW BYTES: {repr(data)}")
                    print(f"TEXT:      {data.decode('ascii', errors='ignore').strip()}")
                    print("-" * 60)
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error: {e}")
        
        sock.close()
        return data_received
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def sniff_all_udp(duration=20):
    """Try to capture any UDP traffic (requires admin/root)"""
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE UDP SNIFFER")
    print(f"{'='*60}")
    print(f"Monitoring ALL UDP traffic for {duration} seconds")
    print(f"This helps identify which port the weighbridge is using\n")
    print("-" * 60)
    
    try:
        import threading
        
        # Listen on multiple common ports simultaneously
        threads = []
        results = {}
        
        for port in COMMON_UDP_PORTS:
            def listen_thread(p):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('', p))
                    sock.settimeout(1)
                    
                    start = time.time()
                    while (time.time() - start) < duration:
                        try:
                            data, addr = sock.recvfrom(1024)
                            if addr[0] == WEIGHBRIDGE_IP:
                                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                                decoded = data.decode('ascii', errors='ignore').strip()
                                print(f"\n[{timestamp}] ✓✓✓ FOUND on port {p} from {addr[0]}")
                                print(f"TEXT: {decoded}")
                                print("-" * 60)
                                results[p] = decoded
                        except socket.timeout:
                            continue
                    
                    sock.close()
                except:
                    pass
            
            t = threading.Thread(target=listen_thread, args=(port,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        print(f"Listening on ports: {COMMON_UDP_PORTS}")
        print(f"Put weight on scale now...\n")
        
        # Wait for threads
        for t in threads:
            t.join()
        
        return results
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return {}

def main():
    print("\n" + "="*60)
    print("UDP WEIGHBRIDGE DETECTOR")
    print("="*60)
    print(f"Target: {WEIGHBRIDGE_IP}")
    print(f"\nThis tool will detect UDP traffic from your weighbridge")
    print("="*60)
    
    print(f"\n📋 INSTRUCTIONS:")
    print(f"   1. Make sure weighbridge is powered on")
    print(f"   2. When prompted, put weight on the scale")
    print(f"   3. Or trigger a reading from the weighbridge display")
    print(f"   4. Watch for data to appear")
    
    input("\nPress ENTER to start listening...")
    
    # Method 1: Comprehensive multi-port listener
    print(f"\n{'='*60}")
    print("METHOD 1: Multi-Port UDP Listener")
    print("="*60)
    
    results = sniff_all_udp(duration=20)
    
    if results:
        print(f"\n{'='*60}")
        print("✅ SUCCESS! Found UDP data on these ports:")
        print("="*60)
        for port, data in results.items():
            print(f"\nPort {port}: {data}")
        
        print(f"\n{'='*60}")
        print("CONFIGURATION FOR YOUR INTEGRATION:")
        print("="*60)
        best_port = list(results.keys())[0]
        print(f"WEIGHBRIDGE_IP = '{WEIGHBRIDGE_IP}'")
        print(f"WEIGHBRIDGE_PORT = {best_port}")
        print(f"PROTOCOL = 'UDP'")
        print("="*60)
        return
    
    # Method 2: Try each port individually
    print(f"\n{'='*60}")
    print("METHOD 2: Individual Port Testing")
    print("="*60)
    
    found_ports = []
    
    for port in COMMON_UDP_PORTS:
        if listen_udp_port(port, duration=10):
            found_ports.append(port)
            break  # Found data, stop searching
    
    if found_ports:
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS! Found data on UDP port {found_ports[0]}")
        print("="*60)
    else:
        print(f"\n{'='*60}")
        print("❌ NO UDP DATA DETECTED")
        print("="*60)
        print("\nPossible reasons:")
        print("1. Weighbridge not configured to send UDP data")
        print("2. Using a different protocol (RS-232/RS-485)")
        print("3. Need to enable 'Auto Print' or 'Continuous Output'")
        print("4. Firewall blocking UDP traffic")
        print("\nNext steps:")
        print("→ Check weighbridge manual for UDP configuration")
        print("→ Access device menu and look for:")
        print("  - Communication Mode: UDP / Ethernet / Network")
        print("  - Data Output: Continuous / Auto")
        print("  - Port Number setting")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user\n")
        sys.exit(0)