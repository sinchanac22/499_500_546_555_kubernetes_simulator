#WEEK2-PodScheduler and HeartMonitoring/api_server.py
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

if __name__ == '__main__':
    health_monitor_thread = threading.Thread(target=HealthMonitor.check_health, daemon=True)
    health_monitor_thread.start()
    logger.info("Health monitoring started.")
    app.run(debug=True, host='0.0.0.0', port=5000)
