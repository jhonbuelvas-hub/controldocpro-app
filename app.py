from flask import Flask, request, jsonify
from ai.communication_ai import generate_ai_response
from ai.utils_ai import extract_text_from_pdf

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ API Avalora IA funcionando desde Azure App Service"

@app.route("/analizar", methods=["POST"])
def analizar():
    if "archivo" not in request.files:
        return jsonify({"error": "No se envió archivo PDF"}), 400

    archivo = request.files["archivo"]
    instruccion = request.form.get("instruccion", "")

    pdf_bytes = archivo.read()
    comm_text = extract_text_from_pdf(pdf_bytes)

    respuesta = generate_ai_response(
        comm_text,
        contract_text="",
        history_text=""
    )

    return jsonify({"respuesta": respuesta})
