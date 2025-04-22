from flask import Flask, request, jsonify
import docker
import threading
import time
from datetime import datetime
import uuid
import sys
import logging

# Configure logging with more details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

try:
    client = docker.from_env()
    client.ping()
    logger.info("Successfully connected to Docker")
    existing_containers = client.containers.list()
    logger.info(f"Found {len(existing_containers)} existing containers")
    for container in existing_containers:
        logger.info(f"Container: {container.name} (ID: {container.short_id})")
except docker.errors.DockerException as e:
    logger.error("Error: Docker is not running or not properly installed.")
    logger.error("Please make sure Docker Desktop is installed and running.")
    logger.error("You can download Docker Desktop from: https://www.docker.com/products/docker-desktop/")
    sys.exit(1)

nodes = {}
pods = {}

class NodeManager:
    @staticmethod
    def add_node(cpu_capacity):
        node_id = str(uuid.uuid4())
        try:
            logger.info(f"Creating new node container with ID: {node_id}")
            logger.info(f"CPU Capacity: {cpu_capacity} cores")
            container = client.containers.run(
                'python:3.9-slim',
                command='tail -f /dev/null',
                detach=True,
                name=f'node-{node_id}'
            )
            logger.info(f"Container created successfully: {container.name} (ID: {container.short_id})")
            nodes[node_id] = {
                'cpu_capacity': cpu_capacity,
                'cpu_available': cpu_capacity,
                'pods': [],
                'last_heartbeat': datetime.now(),
                'status': 'healthy',
                'container_id': container.id,
                'heartbeat_enabled': True
            }
            threading.Thread(target=HealthMonitor.start_heartbeat, args=(node_id,), daemon=True).start()
            logger.info(f"Started heartbeat monitoring for node {node_id}")
            return node_id
        except docker.errors.APIError as e:
            logger.error(f"Docker API error while creating node: {str(e)}")
            return {'error': f'Docker API error: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected error while creating node: {str(e)}")
            return {'error': str(e)}

    @staticmethod
    def remove_node(node_id):
        if node_id in nodes:
            try:
                logger.info(f"Removing node: {node_id}")
                container = client.containers.get(nodes[node_id]['container_id'])
                container.stop()
                container.remove()
                del nodes[node_id]
                logger.info(f"Successfully removed node {node_id} and its container")
                return {'message': f'Node {node_id} removed successfully'}
            except Exception as e:
                logger.error(f"Error removing node {node_id}: {str(e)}")
                return {'error': str(e)}
        logger.error(f"Node not found: {node_id}")
        return {'error': 'Node not found'}

class PodScheduler:
    @staticmethod
    def schedule_pod(cpu_required):
        logger.info(f"Attempting to schedule pod requiring {cpu_required} CPU cores")
        for node_id, node_info in nodes.items():
            if node_info['status'] == 'healthy' and node_info['cpu_available'] >= cpu_required:
                pod_id = str(uuid.uuid4())
                node_info['cpu_available'] -= cpu_required
                node_info['pods'].append(pod_id)
                pods[pod_id] = {
                    'node_id': node_id,
                    'cpu_required': cpu_required,
                    'created_at': datetime.now().isoformat()
                }
                logger.info(f"Successfully scheduled pod {pod_id} on node {node_id}")
                logger.info(f"Node {node_id} now has {node_info['cpu_available']} CPU cores available")
                return pod_id
        logger.error(f"Failed to find suitable node for pod requiring {cpu_required} CPU cores")
        return {'error': 'No suitable node found'}

    @staticmethod
    def reschedule_pods(failed_node_id):
        if failed_node_id not in nodes:
            logger.error(f"Failed node not found: {failed_node_id}")
            return
        failed_pods = nodes[failed_node_id]['pods']
        logger.info(f"Rescheduling {len(failed_pods)} pods from failed node {failed_node_id}")
        for pod_id in failed_pods:
            pod_info = pods[pod_id]
            logger.info(f"Attempting to reschedule pod {pod_id}")
            new_node_id = PodScheduler.schedule_pod(pod_info['cpu_required'])
            if isinstance(new_node_id, dict):
                pods[pod_id]['status'] = 'failed'
                logger.error(f"Failed to reschedule pod {pod_id}")
            else:
                pods[pod_id]['node_id'] = new_node_id
                logger.info(f"Successfully rescheduled pod {pod_id} to node {new_node_id}")

class HealthMonitor:
    @staticmethod
    def start_heartbeat(node_id):
        logger.info(f"Starting heartbeat monitoring for node {node_id}")
        while True:
            if node_id in nodes:
                if nodes[node_id].get('heartbeat_enabled', True):
                    nodes[node_id]['last_heartbeat'] = datetime.now()
                    nodes[node_id]['status'] = 'healthy'
            time.sleep(5)

    @staticmethod
    def check_health():
        while True:
            current_time = datetime.now()
            for node_id, node_info in nodes.items():
                if (current_time - node_info['last_heartbeat']).seconds > 15:
                    if node_info['status'] == 'healthy':
                        logger.warning(f"Node {node_id} marked as unhealthy - missed heartbeats")
                        node_info['status'] = 'unhealthy'
                        PodScheduler.reschedule_pods(node_id)
            time.sleep(5)

@app.route('/nodes', methods=['POST'])
def add_node():
    logger.info("Received request to add node")
    data = request.get_json()
    if not data:
        logger.error("No JSON data received")
        return jsonify({'error': 'No data provided'}), 400
    cpu_capacity = data.get('cpu_capacity')
    if not cpu_capacity:
        logger.error("No CPU capacity specified")
        return jsonify({'error': 'CPU capacity is required'}), 400
    node_id = NodeManager.add_node(cpu_capacity)
    if isinstance(node_id, dict):
        return jsonify(node_id), 400
    return jsonify({'node_id': node_id, 'message': 'Node added successfully'})

@app.route('/nodes/<node_id>', methods=['DELETE'])
def remove_node(node_id):
    logger.info(f"Received request to remove node: {node_id}")
    result = NodeManager.remove_node(node_id)
    if 'error' in result:
        return jsonify(result), 404
    return jsonify(result)

@app.route('/nodes/<node_id>/fail', methods=['POST'])
def fail_node(node_id):
    if node_id in nodes:
        nodes[node_id]['status'] = 'unhealthy'
        nodes[node_id]['heartbeat_enabled'] = False
        logger.warning(f"Node {node_id} marked as unhealthy (failed).")
        PodScheduler.reschedule_pods(node_id)
        return jsonify({"message": f"Node {node_id} marked as failed."}), 200
    else:
        return jsonify({"error": "Node not found"}), 404

@app.route('/pods', methods=['POST'])
def create_pod():
    logger.info("Received request to create pod")
    data = request.get_json()
    if not data:
        logger.error("No JSON data received")
        return jsonify({'error': 'No data provided'}), 400
    cpu_required = data.get('cpu_required')
    if not cpu_required:
        logger.error("No CPU requirement specified")
        return jsonify({'error': 'CPU requirement is required'}), 400
    pod_id = PodScheduler.schedule_pod(cpu_required)
    if isinstance(pod_id, dict):
        return jsonify(pod_id), 400
    return jsonify({'pod_id': pod_id, 'message': 'Pod scheduled successfully'})

@app.route('/cluster/status', methods=['GET'])
def get_cluster_status():
    logger.info("Received request for cluster status")
    orphaned_pods = []
    for pod_id, pod_info in list(pods.items()):
        if pod_info['node_id'] not in nodes:
            orphaned_pods.append(pod_id)

    for orphan_pod_id in orphaned_pods:
        pod_info = pods[orphan_pod_id]
        rescheduled = False
        for node_id, node_info in nodes.items():
            if node_info['status'] == 'healthy' and node_info['cpu_available'] >= pod_info['cpu_required']:
                pod_info['node_id'] = node_id
                pods[orphan_pod_id] = pod_info
                node_info['cpu_available'] -= pod_info['cpu_required']
                node_info['pods'].append(orphan_pod_id)
                logger.info(f"Orphaned pod {orphan_pod_id} successfully rescheduled to node {node_id}")
                rescheduled = True
                break
        if not rescheduled:
            logger.warning(f"Failed to reschedule orphan pod {orphan_pod_id}")

    cluster_status = {
        'nodes': nodes,
        'pods': pods
    }
    return jsonify(cluster_status)

if __name__ == '__main__':
    health_monitor_thread = threading.Thread(target=HealthMonitor.check_health, daemon=True)
    health_monitor_thread.start()
    logger.info("Health monitoring started.")
    app.run(debug=True, host='0.0.0.0', port=5000)
