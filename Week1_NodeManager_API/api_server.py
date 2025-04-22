from flask import Flask, request, jsonify
app = Flask(__name__)

nodes = []

@app.route('/add_node', methods=['POST'])
def add_node():
    data = request.get_json()
    node_id = data.get('node_id')
    if node_id and node_id not in nodes:
        nodes.append(node_id)
        return jsonify({'message': 'Node added successfully'}), 200
    return jsonify({'message': 'Invalid or duplicate node'}), 400
