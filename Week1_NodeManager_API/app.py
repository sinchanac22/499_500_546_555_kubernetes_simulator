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
