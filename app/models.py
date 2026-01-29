import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, List, Optional

# Type definitions similar to TypeScript
EventType = Literal['NORMAL', 'TAMPER']
TamperReason = Literal['Abnormal Voltage', 'Overcurrent', 'Light Tamper', 'Switch Tampering', None]
Severity = Literal['low', 'medium', 'high']

@dataclass
class MeterReading:
    node_id: str
    timestamp: str
    voltage: float
    current: float
    light: float
    event_type: EventType
    tamper_reason: Optional[TamperReason] = None  # Added this field
    confidence: float = 0.0
    ciphertext: str = ""
    hmac: str = ""
    verified: bool = True
    health_score: int = 100

@dataclass
class AIPrediction:
    timestamp: str
    node_id: str
    event_type: EventType
    confidence: float
    explanation: str
    severity: Severity

