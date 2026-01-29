from flask import Blueprint, jsonify, render_template 
from . import db, initialize_data
from app.pid_controller import simulation
from app.utils import convert_json_to_meter_reading

bp = Blueprint('api', __name__)

@bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@bp.route('/api/status', methods=['GET'])
def get_status():
    readings = list(db["meter_readings"].values())
    if not readings:
        return jsonify({
            "total_nodes": 0, "tampered_nodes": 0, "avg_confidence": 0, "verified_ratio": 0,
        })
    tampered_nodes = sum(1 for r in readings if r.event_type == 'TAMPER')
    avg_confidence = sum(r.confidence for r in readings) / len(readings) if readings else 0
    verified_ratio = (sum(1 for r in readings if r.verified) / len(readings)) * 100 if readings else 0
    
    return jsonify({
        "total_nodes": len(readings), 
        "tampered_nodes": tampered_nodes,
        "avg_confidence": round(avg_confidence, 1), 
        "verified_ratio": round(verified_ratio, 1),
    })

# API for Latest Status (Cards)
@bp.route('/api/readings', methods=['GET'])
def get_readings():
    readings_list = [reading.__dict__ for reading in db["meter_readings"].values()]
    readings_list.sort(key=lambda x: x['node_id'])
    return jsonify(readings_list)

# NEW API for History (Table)
@bp.route('/api/logs', methods=['GET'])
def get_logs():
    raw_data = db["json_data"]
    # Get last 200 items, reversed (newest first)
    recent = raw_data[-200:][::-1]
    formatted = [convert_json_to_meter_reading(x).__dict__ for x in recent]
    return jsonify(formatted)

@bp.route('/api/predictions', methods=['GET'])
def get_predictions():
    predictions_list = [pred.__dict__ for pred in db["predictions"]]
    return jsonify(predictions_list)

@bp.route('/api/pid_data', methods=['GET'])
def get_pid_data():
    return jsonify(simulation.get_history())

@bp.route('/api/simulate', methods=['POST'])
def simulate_new_data():
    initialize_data()
    return jsonify({"message": "OK"}), 200
    
