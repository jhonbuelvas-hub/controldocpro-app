from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Server Flask funcionando desde Azure App Service"

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})
