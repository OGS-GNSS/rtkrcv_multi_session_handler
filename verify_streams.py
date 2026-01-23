import socket
import yaml
import time
import binascii
from pathlib import Path

def check_stream(name, ip, port, timeout=5):
    print(f"--- Checking {name} ({ip}:{port}) ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        start = time.time()
        s.connect((ip, int(port)))
        print(f"Connected in {time.time()-start:.2f}s")
        
        # Try to read data
        print("Waiting for data...")
        data = s.recv(1024)
        
        if not data:
            print("❌ Connection closed by remote host (No data)")
        else:
            print(f"✅ Received {len(data)} bytes")
            hex_data = binascii.hexlify(data[:32]).decode('utf-8')
            spaced_hex = " ".join(hex_data[i:i+2] for i in range(0, len(hex_data), 2))
            print(f"Header (hex): {spaced_hex}")
            
            # Format guess
            if data.startswith(b'\xb5\x62'):
                print("Detected Format: UBX (u-blox)")
            elif data.startswith(b'\xd3'):
                print("Detected Format: RTCM3")
            elif any(c in data for c in b'$G'):
                print("Detected Format: NMEA (ASCII)")
            else:
                print("Detected Format: Unknown Binary/Text")
                
        s.close()
        return True
    except socket.timeout:
        print("❌ Timeout: No data received (Stream is silent)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def verify_all():
    try:
        with open("list.yaml", 'r') as f:
            config = yaml.safe_load(f)
            
        receivers = config.get('receivers', {})
        results = {}
        
        print(f"Found {len(receivers)} receivers to verify.\n")
        
        for serial, rcv in receivers.items():
            success = check_stream(serial, rcv['ip'], rcv['port'])
            results[serial] = success
            print("")
            
        print("=== Summary ===")
        for serial, success in results.items():
            status = "OK" if success else "FAIL"
            print(f"{serial}: {status}")
            
    except Exception as e:
        print(f"Failed to load configuration: {e}")

if __name__ == "__main__":
    verify_all()
