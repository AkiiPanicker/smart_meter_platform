import threading
import time
import os
import logging
from flask import Flask
from flask_cors import CORS
from app.utils import load_sensor_logs, convert_json_to_meter_reading
from app.models import AIPrediction, MeterReading
from app.ai_model import PredictiveModel
from app.pid_controller import simulation 

# Configure logging
logging.basicConfig(level=logging.INFO)

# Global in-memory database
db = {
    "meter_readings": {},
    "predictions": [],
    "json_data": [],
    "last_processed_index": 0,
    "last_file_size": 0
}
predictive_model = None

def get_data_path():
    """Returns the absolute path to sensor_logs.json in the project root."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'sensor_logs.json')

def create_app():
    global predictive_model
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    CORS(app)
    
    from . import routes
    app.register_blueprint(routes.bp)

    with app.app_context():
        # Setup Paths
        data_path = get_data_path()
        model_path = os.path.join(app.root_path, 'lstm_classifier.h5')

        predictive_model = PredictiveModel(model_path=model_path, data_path=data_path)
        
        # Initial load
        reload_json_data()
        initialize_data()

    thread = threading.Thread(target=background_update, args=(app,), daemon=True)
    thread.start()
    
    return app

def reload_json_data():
    """Reloads sensor data from the JSON file."""
    data_path = get_data_path()
    try:
        if os.path.exists(data_path):
            file_size = os.path.getsize(data_path)
            # Reload if file changed OR if memory is empty
            if file_size != db["last_file_size"] or not db["json_data"]:
                data = load_sensor_logs(data_path)
                if data:
                    db["json_data"] = data
                    db["last_file_size"] = file_size
                    print(f"DISK: Loaded {len(db['json_data'])} entries from log file.")
                    return True
    except Exception: pass
    return False

def initialize_data():
    """Processes loaded JSON data to set initial state."""
    if not db["json_data"]:
        return

    # Sort data chronologically
    try:
        sorted_data = sorted(db["json_data"], key=lambda x: x.get('timestamp', ''))
        
        # 1. Update Latest State (For Dashboard Cards)
        node_latest = {}
        for entry in sorted_data:
            nid = entry.get('node_id')
            if nid:
                node_latest[nid] = entry
        
        for nid, entry in node_latest.items():
            reading = convert_json_to_meter_reading(entry)
            db["meter_readings"][nid] = reading

        # 2. POPULATE HISTORICAL ALERTS (Fix for the "0" issue)
        # We clear old predictions and scan history for tampers
        db["predictions"] = []
        for entry in sorted_data:
            if entry.get('tamperFlag') == 1 or entry.get('event_type') == 'TAMPER':
                nid = entry.get('node_id', 'UNKNOWN')
                # Generate a mock prediction based on stored data
                conf = 80.0 + (float(entry.get('current', 0)) * 1.5)
                if conf > 100: conf = 99.9
                
                pred = AIPrediction(
                    timestamp=entry.get('timestamp'),
                    node_id=nid,
                    event_type='TAMPER',
                    confidence=conf,
                    severity='high' if conf > 90 else 'medium',
                    explanation="Historical Analysis: Sensor patterns indicate physical manipulation."
                )
                db["predictions"].append(pred)
        
        # Reverse to show newest first and limit to 50
        db["predictions"].reverse()
        db["predictions"] = db["predictions"][:50]

        db["last_processed_index"] = len(db["json_data"])
    except Exception as e:
        print(f"INIT ERROR: {e}")

def update_predictions_and_health(node_id):
    """Updates AI prediction and PID for a specific node."""
    if not predictive_model or not db["json_data"]:
        return

    time_steps = predictive_model.TIME_STEPS
    node_history = [x for x in db["json_data"] if x.get('node_id') == node_id]
    
    if not node_history: return

    recent_items = node_history[-time_steps:]
    recent_readings = [convert_json_to_meter_reading(item) for item in recent_items]

    # Set Default
    if node_id in db["meter_readings"]:
        db["meter_readings"][node_id].health_score = 100

    if len(recent_readings) >= time_steps:
        result = predictive_model.get_health_score_and_prediction(node_id, recent_readings)
        
        if node_id in db["meter_readings"]:
            db["meter_readings"][node_id].health_score = result["health_score"]

        if result["prediction"]:
            db["predictions"].insert(0, result["prediction"])
            db["predictions"] = db["predictions"][:50]
            # Trigger PID disturbance whenever AI detects a threat
            simulation.trigger_disturbance()

def background_update(app):
    """Real-time data watcher loop."""
    while True:
        time.sleep(1) 
        with app.app_context():
            simulation.step()
            if reload_json_data():
                # Process only new data if needed, for now full re-init is safer
                initialize_data()
