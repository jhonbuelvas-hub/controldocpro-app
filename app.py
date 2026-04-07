from flask import Flask, request, jsonify
from backend.ai.communication_ai import generate_ai_response
from backend.ai.utils_ai import extract_text_from_pdf

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

    # Leer PDF enviado
    pdf_bytes = archivo.read()

    # Extraer texto del PDF (tu propia función)
    comm_text = extract_text_from_pdf(pdf_bytes)

    # Llamar tu módulo de IA (resumen, análisis técnico, contractual, etc.)
    respuesta = generate_ai_response(
        comm_text,
        contract_text="",
        history_text=""
    )

    return jsonify({"respuesta": respuesta})

