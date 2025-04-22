import streamlit as st
import requests
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5000'

st.set_page_config(page_title="Kubernetes-like Simulator", layout="centered")
st.title("🚀 Kubernetes-like Cluster Simulator")
st.markdown("Manage your cluster nodes and pods using a friendly interface!")

# Check API server status
def is_api_running():
    try:
        requests.get(f'{BASE_URL}/cluster/status')
        return True
    except:
        return False

if not is_api_running():
    st.error("❌ Cannot connect to the API server. Please start it using `python api_server.py`.")
    st.stop()

# Section: Add Node
st.subheader("🧱 Add Node")
cpu_capacity = st.slider("Select CPU capacity", min_value=1, max_value=16, value=4)
if st.button("Add Node"):
    res = requests.post(f"{BASE_URL}/nodes", json={"cpu_capacity": cpu_capacity})
    if res.status_code == 200:
        st.session_state["node_added"] = True
        st.rerun()
    else:
        st.error(f"❌ Failed to add node: {res.text}")

if "node_added" in st.session_state:
    st.success("✅ Node added successfully!")
    del st.session_state["node_added"]

# Section: Create Pod
st.subheader("📦 Create Pod")
cpu_required = st.slider("CPU required for pod", min_value=1, max_value=8, value=2)
if st.button("Create Pod"):
    res = requests.post(f"{BASE_URL}/pods", json={"cpu_required": cpu_required})
    if res.status_code == 200:
        st.session_state["pod_created"] = True
        st.rerun()
    else:
        st.error(f"❌ Failed to create pod: {res.text}")

if "pod_created" in st.session_state:
    st.success("✅ Pod created successfully!")
    del st.session_state["pod_created"]

# Refresh Button
refresh_clicked = st.button("🔄 Refresh Cluster Status")

# Get Cluster Status
status_res = requests.get(f"{BASE_URL}/cluster/status")
cluster_data = status_res.json() if status_res.status_code == 200 else {}

# Display Nodes
st.subheader("📊 Cluster Status")
nodes = cluster_data.get("nodes", {})
pods = cluster_data.get("pods", {})

if not nodes:
    st.warning("⚠️ No nodes available in the cluster.")
else:
    st.markdown(f"🧮 Total Nodes: **{len(nodes)}**")
    for node_id, info in nodes.items():
        status = info['status']
        status_icon = "🟢" if status == 'healthy' else "🔴"
        heartbeat_time = datetime.fromisoformat(info["last_heartbeat"]).strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"""
        {status_icon} **Node ID**: `{node_id[:8]}`
        - **Status**: `{status.capitalize()}`
        - **CPU Availability**: `{info['cpu_available']} / {info['cpu_capacity']}`
        - **Last Heartbeat**: `{heartbeat_time}`
        - **Pods Running**: `{len(info['pods'])}`
        """)
        st.markdown("---")

# Display Pods
st.subheader("📦 Pods Overview")
orphaned_pods = []  # Define orphaned_pods list

if pods:
    st.markdown(f"🧮 Total Pods: **{len(pods)}**")
    
    # Check for orphaned pods
    for pod_id, pod_info in pods.items():
        if pod_info['node_id'] not in nodes:
            orphaned_pods.append(pod_id)
            continue  # Skip orphaned pods in the normal list display
    
    # Display normal pods
    for pod_id, pod_info in pods.items():
        if pod_id not in orphaned_pods:
            st.markdown(f"""
            🔹 **Pod ID**: `{pod_id[:8]}`
            - Assigned to Node: `{pod_info['node_id'][:8]}`
            - CPU Required: `{pod_info['cpu_required']}`
            - Created At: `{pod_info['created_at']}`
            """)
            st.markdown("----")
else:
    st.info("No pods are currently scheduled.")

if orphaned_pods:
    st.info(f"ℹ️ {len(orphaned_pods)} pod(s) were reassigned to new nodes after their original node(s) went offline.")


# Remove Node
st.subheader("🗑️ Remove Node")
node_ids = list(nodes.keys())
if node_ids:
    node_to_remove = st.selectbox("Select Node to remove", node_ids)
    if st.button("Remove Node"):
        res = requests.delete(f"{BASE_URL}/nodes/{node_to_remove}")
        if res.status_code == 200:
            st.session_state["node_removed"] = True
            st.rerun()
        else:
            st.error(f"❌ Failed to remove node: {res.text}")
else:
    st.info("No nodes to remove.")

if "node_removed" in st.session_state:
    st.success("✅ Node removed successfully!")
    del st.session_state["node_removed"]

# Simulate Node Failure
st.subheader("💥 Simulate Node Failure")
if node_ids:
    node_to_fail = st.selectbox("Select Node to simulate failure", node_ids, key="fail_node_select")
    if st.button("Simulate Failure"):
        res = requests.post(f"{BASE_URL}/nodes/{node_to_fail}/fail")
        if res.status_code == 200:
            st.session_state["node_failed"] = True
            st.rerun()
        else:
            st.error(f"❌ Failed to simulate node failure: {res.text}")
else:
    st.info("No nodes available to simulate failure.")

if "node_failed" in st.session_state:
    st.warning("⚠️ Node failure simulated. Cluster will now try to recover pods!")
    del st.session_state["node_failed"]
