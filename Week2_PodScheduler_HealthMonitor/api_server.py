# Week2_PodScheduler_HealthMonitor/api_server.py
from flask import Flask, request, jsonify
import time

app = Flask(__name__)

nodes = {}
pods = {}

@app.route('/register_node', methods=['POST'])
def register_node():
    data = request.get_json()
    node_id = data.get('node_id')
    nodes[node_id] = {'last_heartbeat': time.time()}
    return jsonify({'message': 'Node registered'}), 200

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    node_id = data.get('node_id')
    if node_id in nodes:
        nodes[node_id]['last_heartbeat'] = time.time()
        return jsonify({'message': 'Heartbeat received'}), 200
    return jsonify({'message': 'Node not found'}), 404

@app.route('/schedule_pod', methods=['POST'])
def schedule_pod():
    data = request.get_json()
    pod_id = data.get('pod_id')
    for node_id in nodes:
        if time.time() - nodes[node_id]['last_heartbeat'] < 10:
            pods[pod_id] = node_id
            return jsonify({'message': f'Pod scheduled on {node_id}'}), 200
    return jsonify({'message': 'No healthy node found'}), 503
