import random
import string
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from app.models import MeterReading, TamperReason

def generate_hex_string(length: int) -> str:
    """Generates a random hex string of a given length."""
    return ''.join(random.choices(string.hexdigits.lower(), k=length))

def generate_mock_reading(node_id: str, force_tamper: bool = False) -> MeterReading:
    """Generates a single mock meter reading."""
    is_tamper = force_tamper or random.random() < 0.15
    tamper_reasons: list[TamperReason] = ['Abnormal Voltage', 'Overcurrent', 'Light Tamper', 'Switch Tampering']
    
    return MeterReading(
        node_id=node_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        voltage=220 + random.uniform(25, 50) if is_tamper else 220 + random.uniform(-5, 5),
        current=15 + random.uniform(5, 20) if is_tamper else 5 + random.uniform(0, 5),
        light=random.uniform(0, 200) if is_tamper else random.uniform(800, 1000),
        event_type='TAMPER' if is_tamper else 'NORMAL',
        tamper_reason=random.choice(tamper_reasons) if is_tamper else None,
        confidence=random.uniform(75, 100) if is_tamper else random.uniform(50, 80),
        ciphertext=generate_hex_string(32), 
        hmac=generate_hex_string(64), 
        verified=random.random() > 0.1
    )

def load_sensor_logs(filepath: str) -> List[Dict]:
    """Load sensor data from JSON file."""
    # Use the passed filepath argument, DO NOT default to a C:\Users path
    try:
        print(f"DEBUG: Attempting to load JSON from: {filepath}")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                result = data if isinstance(data, list) else []
                print(f"DEBUG: Loaded {len(result)} items.")
                return result
        else:
            print(f"Warning: {filepath} not found. Returning empty list.")
            return []
    except json.JSONDecodeError as e:
        print(f"Error reading JSON: {e}")
        return []
    except Exception as e:
        print(f"Error loading sensor logs: {e}")
        return []

def convert_json_to_meter_reading(json_data: Dict) -> MeterReading:
    """Convert JSON data format to MeterReading object."""
    event_type = 'TAMPER' if json_data.get('tamperFlag', 0) == 1 else 'NORMAL'
    
    tamper_reason = None
    if event_type == 'TAMPER':
        voltage = json_data.get('voltage', 0)
        current = json_data.get('current', 0)
        light = json_data.get('lightIntensity', 0)
        
        if voltage > 240 or voltage < 200:
            tamper_reason = 'Abnormal Voltage'
        elif current > 15:
            tamper_reason = 'Overcurrent'
        elif light < 500:
            tamper_reason = 'Light Tamper'
        else:
            tamper_reason = 'Switch Tampering'
    
    # Check key mappings carefully
    confidence = random.uniform(75, 95) if event_type == 'TAMPER' else random.uniform(50, 80)
    
    return MeterReading(
        node_id=json_data.get('node_id', 'UNKNOWN'),
        timestamp=json_data.get('timestamp', datetime.utcnow().isoformat() + "Z"),
        voltage=float(json_data.get('voltage', 220)),
        current=float(json_data.get('current', 5)),
        # Mapping 'lightIntensity' from JSON to 'light' in dataclass
        light=float(json_data.get('lightIntensity', 900)),
        event_type=event_type,
        tamper_reason=tamper_reason,
        confidence=confidence,
        ciphertext=generate_hex_string(32),
        hmac=generate_hex_string(64),
        verified=True,
        # Default health score, overwritten in __init__.py logic usually
        health_score=100
    )
    
