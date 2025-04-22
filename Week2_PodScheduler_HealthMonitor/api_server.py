#WEEK2-PodScheduler and HeartMonitoring/api_server.py
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
