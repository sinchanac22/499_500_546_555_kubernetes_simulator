# Week3_NodeList_Testing/web_interface.py
from flask import Flask, render_template
import requests

app = Flask(__name__)

@app.route('/')
def home():
    response = requests.get("http://localhost:5000/nodes")
    nodes = response.json()
    return render_template('index.html', nodes=nodes)
