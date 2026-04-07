import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, jsonify
from ai.utils_ai import extract_text_from_pdf

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Flask base funcionando"

@app.route("/ping")
def ping():
    texto = extract_text_from_pdf(b"test")
    return jsonify({
        "status": "ok",
        "utils_response": texto
    })
