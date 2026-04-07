from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ API Avalora IA funcionando desde Azure"

@app.route("/analizar", methods=["POST"])
def analizar():
    return jsonify({"respuesta": "La IA funciona"})
