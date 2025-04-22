# Week3_NodeList_Testing/api_server.py
from flask import Flask, jsonify
from Week2_PodScheduler_HealthMonitor.api_server import nodes

app = Flask(__name__)

@app.route('/nodes', methods=['GET'])
def get_nodes():
    return jsonify(nodes), 200
