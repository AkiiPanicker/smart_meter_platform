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
    # This finds the 'smart_meter_platform' folder relative to this file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'sensor_logs.json')

def create_app():
    """Creates and configures the Flask application."""
    global predictive_model
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    CORS(app)
    
    from . import routes
    app.register_blueprint(routes.bp)

    with app.app_context():
        # Setup Paths
        data_path = get_data_path()
        model_path = os.path.join(app.root_path, 'lstm_classifier.h5')

        print(f"------------ SERVER STARTING ------------")
        print(f"Looking for data at: {data_path}")
        print(f"---------------------------------------")

        # Initialize AI
        predictive_model = PredictiveModel(model_path=model_path, data_path=data_path)
        
        # Initial load
        reload_json_data()
        initialize_data()

    # Start background thread
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
        else:
            # Create file if missing
            with open(data_path, 'w') as f:
                f.write("[]")
            print("DISK: Created new empty sensor_logs.json")
    except Exception as e:
        print(f"DISK ERROR: {e}")
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
            update_predictions_and_health(nid)

        # 2. Update pointers
        db["last_processed_index"] = len(db["json_data"])
    except Exception as e:
        print(f"INIT ERROR: {e}")

def update_predictions_and_health(node_id):
    """Updates AI prediction and PID for a specific node."""
    if not predictive_model or not db["json_data"]:
        return

    time_steps = predictive_model.TIME_STEPS
    node_history = [x for x in db["json_data"] if x.get('node_id') == node_id]
    
    if not node_history:
        return

    recent_items = node_history[-time_steps:]
    recent_readings = [convert_json_to_meter_reading(item) for item in recent_items]

    # Defaults
    if node_id in db["meter_readings"]:
        db["meter_readings"][node_id].health_score = 100

    if len(recent_readings) >= time_steps:
        result = predictive_model.get_health_score_and_prediction(node_id, recent_readings)
        
        if node_id in db["meter_readings"]:
            db["meter_readings"][node_id].health_score = result["health_score"]

        if result["prediction"]:
            db["predictions"].insert(0, result["prediction"])
            db["predictions"] = db["predictions"][:50]
            # Trigger PID disturbance
            simulation.trigger_disturbance()

def background_update(app):
    """Real-time data watcher loop."""
    while True:
        time.sleep(1) 
        with app.app_context():
            simulation.step()
            if reload_json_data():
                initialize_data()