import serial
import json
import os
import random
from datetime import datetime

SERIAL_PORT = 'COM6' # Change if needed
BAUD_RATE = 115200

# FIX: Get path to 'smart_meter_platform/sensor_logs.json'
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sensor_logs.json')

# Config
NUM_NODES = 6
node_ids = [f"NODE-{str(i+1).zfill(2)}" for i in range(NUM_NODES)]
current_node_index = 0

def initialize_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT}")
        return ser
    except:
        print(f"Cannot connect to {SERIAL_PORT}")
        return None

def save_reading(voltage, current, light, tamper, node_id):
    # Ensure event_type string is correct
    event_type = "TAMPER" if tamper == 1 else "NORMAL"
    
    reading = {
        "node_id": node_id,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "voltage": voltage,
        "current": current,
        "lightIntensity": light,
        "tamperFlag": tamper
    }
    
    # Read existing
    all_readings = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                content = f.read()
                if content: all_readings = json.loads(content)
        except: pass
    
    # Append
    all_readings.append(reading)
    
    # Write back
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_readings, f, indent=2)
    
    print(f"LOGGED: {node_id} - {event_type} | V:{voltage} I:{current}")

def get_next_node_id():
    global current_node_index
    nid = node_ids[current_node_index]
    current_node_index = (current_node_index + 1) % NUM_NODES
    return nid

def main():
    ser = initialize_serial()
    if not ser: return

    print(f"Writing to: {OUTPUT_FILE}")
    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        data = json.loads(line)
                        node_id = get_next_node_id()
                        save_reading(
                            data.get('voltage',0), 
                            data.get('current',0), 
                            data.get('lightIntensity',0), 
                            data.get('tamperFlag',0), 
                            node_id
                        )
                    except: pass
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        if ser: ser.close()

if __name__ == "__main__":
    main()
    
