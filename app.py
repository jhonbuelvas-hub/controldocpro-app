import os
import sys

# Asegura que la raíz del proyecto esté en el PYTHONPATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, jsonify, request
from ai.utils_ai import extract_text_from_pdf

app = Flask(__name__)

# -------------------------
# Ruta de verificación
# -------------------------
@app.route("/")
def home():
    return "✅ API Avalora IA funcionando desde Azure App Service"

# -------------------------
# Ruta de prueba de imports
# -------------------------
@app.route("/ping")
def ping():
    try:
        test_text = extract_text_from_pdf(b"")
        return jsonify({
            "status": "ok",
            "import_utils": True,
            "test_text_length": len(test_text)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# -------------------------
# Ruta principal (PDF)
# -------------------------
@app.route("/analizar", methods=["POST"])
def analizar():
    if "archivo" not in request.files:
        return jsonify({"error": "No se envió archivo PDF"}), 400

    archivo = request.files["archivo"]
    instruccion = request.form.get("instruccion", "")

    pdf_bytes = archivo.read()

    texto_pdf = extract_text_from_pdf(pdf_bytes)

    # Por ahora solo devolvemos el texto (IA se integra después)
    return jsonify({
        "texto_extraido": texto_pdf[:3000],  # limitamos tamaño por seguridad
        "longitud_texto": len(texto_pdf),
        "instruccion": instruccion
    })

# NO usar app.run() en Azure
``
