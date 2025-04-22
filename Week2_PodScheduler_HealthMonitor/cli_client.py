# Week2_PodScheduler_HealthMonitor/cli_client.py
import requests

print("Registering node1...")
requests.post('http://localhost:5000/register_node', json={"node_id": "node1"})

print("Sending heartbeat...")
requests.post('http://localhost:5000/heartbeat', json={"node_id": "node1"})

print("Scheduling pod...")
print(requests.post('http://localhost:5000/schedule_pod', json={"pod_id": "pod1"}).json())
