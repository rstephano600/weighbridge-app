#!/usr/bin/env python3
"""
Serial Port Detector & Weighbridge Tester
Finds available serial ports and tests connection to weighbridge
"""

import sys
import time

# Check if pyserial is installed
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("\n" + "="*60)
    print("ERROR: pyserial not installed")
    print("="*60)
    print("\nPlease install it using:")
    print("  pip install pyserial")
    print("\nOr:")
    print("  pip3 install pyserial")
    print("\n" + "="*60 + "\n")
    sys.exit(1)

# Common baud rates for weighbridges
COMMON_BAUDRATES = [9600, 19200, 38400, 4800, 2400, 115200]

# Common serial configurations
SERIAL_CONFIGS = [
    {'bytesize': 8, 'parity': 'N', 'stopbits': 1},  # 8-N-1 (most common)
    {'bytesize': 7, 'parity': 'E', 'stopbits': 1},  # 7-E-1
    {'bytesize': 7, 'parity': 'O', 'stopbits': 1},  # 7-O-1
    {'bytesize': 8, 'parity': 'E', 'stopbits': 1},  # 8-E-1
]

def list_serial_ports():
    """List all available serial ports"""
    print("\n" + "="*60)
    print("STEP 1: Detecting Serial Ports")
    print("="*60 + "\n")
    
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("✗ No serial ports found!")
        print("\nPossible reasons:")
        print("  1. USB-to-Serial adapter not connected")
        print("  2. Drivers not installed")
        print("  3. Device not recognized by OS")
        print("\nOn Windows: Check Device Manager > Ports (COM & LPT)")
        print("On Linux: Check 'ls /dev/tty*' or 'dmesg | grep tty'")
        return []
    
    print(f"Found {len(ports)} serial port(s):\n")
    
    available_ports = []
    
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {port.hwid}")
        
        # Highlight likely weighbridge ports
        desc_lower = port.description.lower()
        if any(keyword in desc_lower for keyword in ['usb', 'serial', 'com', 'ch340', 'cp210', 'ftdi', 'prolific']):
            print(f"   ⭐ Likely USB-Serial adapter")
        
        print()
        available_ports.append(port.device)
    
    return available_ports

def test_serial_port(port_name, baudrate, config, duration=10):
    """Test a serial port with specific settings"""
    try:
        # Convert parity letter to pyserial constant
        parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD,
        }
        
        stopbits_map = {
            1: serial.STOPBITS_ONE,
            2: serial.STOPBITS_TWO,
        }
        
        print(f"\nTesting: {port_name} @ {baudrate} baud, {config['bytesize']}-{config['parity']}-{config['stopbits']}")
        print(f"Listening for {duration} seconds...", end=" ")
        
        # Open serial port
        ser = serial.Serial(
            port=port_name,
            baudrate=baudrate,
            bytesize=config['bytesize'],
            parity=parity_map[config['parity']],
            stopbits=stopbits_map[config['stopbits']],
            timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        
        # Wait for port to stabilize
        time.sleep(0.5)
        
        # Clear any existing data
        ser.reset_input_buffer()
        
        print("✓")
        
        start_time = time.time()
        data_received = False
        
        while (time.time() - start_time) < duration:
            if ser.in_waiting > 0:
                data = ser.readline()
                
                if data:
                    data_received = True
                    timestamp = time.strftime('%H:%M:%S')
                    decoded = data.decode('ascii', errors='ignore').strip()
                    
                    print(f"\n  [{timestamp}] ✓✓✓ DATA RECEIVED!")
                    print(f"  RAW BYTES: {repr(data)}")
                    print(f"  TEXT:      {decoded}")
                    print(f"  LENGTH:    {len(data)} bytes")
                    print()
            
            time.sleep(0.1)
        
        ser.close()
        return data_received
        
    except serial.SerialException as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def auto_detect_settings(port_name):
    """Try to auto-detect correct serial settings"""
    print("\n" + "="*60)
    print(f"STEP 2: Auto-Detecting Settings for {port_name}")
    print("="*60)
    print("\nTrying common configurations...")
    print("Put weight on scale or trigger reading now!\n")
    print("-" * 60)
    
    for baudrate in COMMON_BAUDRATES:
        for config in SERIAL_CONFIGS:
            if test_serial_port(port_name, baudrate, config, duration=5):
                print("\n" + "="*60)
                print("✅ SUCCESS! Found working configuration:")
                print("="*60)
                print(f"Port:     {port_name}")
                print(f"Baudrate: {baudrate}")
                print(f"Format:   {config['bytesize']}-{config['parity']}-{config['stopbits']}")
                print("="*60)
                return {
                    'port': port_name,
                    'baudrate': baudrate,
                    'config': config
                }
    
    return None

def manual_test(port_name, baudrate=9600):
    """Manually test a port with user-specified settings"""
    print("\n" + "="*60)
    print(f"MANUAL TEST: {port_name} @ {baudrate} baud")
    print("="*60)
    
    config = SERIAL_CONFIGS[0]  # 8-N-1
    
    print(f"\nConfiguration: {config['bytesize']}-{config['parity']}-{config['stopbits']}")
    print("Listening for 15 seconds...")
    print("\n⚠ Put weight on scale NOW!\n")
    print("-" * 60)
    
    if test_serial_port(port_name, baudrate, config, duration=15):
        print("\n✅ Data received successfully!")
    else:
        print("\n❌ No data received")
        print("\nTroubleshooting:")
        print("  1. Check cable connection")
        print("  2. Verify weighbridge is powered on")
        print("  3. Enable 'Auto Print' or 'Continuous Output' on device")
        print("  4. Try different baud rate (common: 9600, 19200, 4800)")

def interactive_menu():
    """Interactive menu for testing"""
    ports = list_serial_ports()
    
    if not ports:
        print("\n⚠ No serial ports available!")
        print("\nConnect USB-to-Serial adapter and try again.")
        return
    
    print("\n" + "="*60)
    print("CHOOSE AN OPTION:")
    print("="*60)
    print("\n1. Auto-detect settings (Recommended)")
    print("2. Manual test with specific settings")
    print("3. Refresh port list")
    print("4. Exit")
    
    try:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            print("\nWhich port to test?")
            for i, port in enumerate(ports, 1):
                print(f"{i}. {port}")
            
            port_choice = input(f"\nEnter port number (1-{len(ports)}): ").strip()
            try:
                port_idx = int(port_choice) - 1
                if 0 <= port_idx < len(ports):
                    result = auto_detect_settings(ports[port_idx])
                    
                    if result:
                        print("\n" + "="*60)
                        print("SAVE THIS CONFIGURATION:")
                        print("="*60)
                        print(f"PORT = '{result['port']}'")
                        print(f"BAUDRATE = {result['baudrate']}")
                        print(f"BYTESIZE = {result['config']['bytesize']}")
                        print(f"PARITY = '{result['config']['parity']}'")
                        print(f"STOPBITS = {result['config']['stopbits']}")
                        print("="*60)
                    else:
                        print("\n❌ Could not auto-detect settings")
                        print("Try manual test or check device configuration")
            except ValueError:
                print("Invalid choice")
        
        elif choice == '2':
            print("\nWhich port to test?")
            for i, port in enumerate(ports, 1):
                print(f"{i}. {port}")
            
            port_choice = input(f"\nEnter port number (1-{len(ports)}): ").strip()
            baudrate = input("Enter baud rate (default 9600): ").strip() or "9600"
            
            try:
                port_idx = int(port_choice) - 1
                if 0 <= port_idx < len(ports):
                    manual_test(ports[port_idx], int(baudrate))
            except ValueError:
                print("Invalid input")
        
        elif choice == '3':
            interactive_menu()
        
        elif choice == '4':
            print("\nExiting...\n")
            sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\nExiting...\n")
        sys.exit(0)

def main():
    print("\n" + "="*60)
    print("SERIAL PORT WEIGHBRIDGE DETECTOR")
    print("="*60)
    print("\nThis tool will help you:")
    print("  ✓ Find available serial ports")
    print("  ✓ Auto-detect correct settings")
    print("  ✓ Test connection to weighbridge")
    print("="*60)
    
    interactive_menu()

if __name__ == "__main__":
    main()


# ============================================
# INSTALLATION INSTRUCTIONS
# ============================================
"""
REQUIRED LIBRARY:
pip install pyserial

Or:
pip3 install pyserial

HARDWARE NEEDED:
- USB-to-Serial adapter (USB to RS-232)
- Serial cable connecting weighbridge PRINT port to adapter

WINDOWS:
- Check Device Manager > Ports (COM & LPT) for COM port number
- May need to install CH340, CP2102, or FTDI drivers

LINUX:
- Port will be /dev/ttyUSB0 or /dev/ttyACM0
- May need to add user to dialout group:
  sudo usermod -a -G dialout $USER
  (then logout and login)

RUN:
python3 serial_detector.py
"""