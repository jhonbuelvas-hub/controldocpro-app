from flask import Flask, jsonify
from ai.utils_ai import extract_text_from_pdf  # solo importar

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Server Flask funcionando desde Azure App Service"

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})
