from flask import Flask, request, jsonify
from backend.ai.communication_ai import generate_ai_response
from backend.ai.utils_ai import extract_text_from_pdf

app = Flask(__name__)

@app.route("/analizar", methods=["POST"])
def analizar():
    if "archivo" not in request.files:
        return jsonify({"error": "No se envió archivo PDF"}), 400

    archivo = request.files["archivo"]
    instruccion = request.form.get("instruccion", "")

    # Leer PDF
    pdf_bytes = archivo.read()

    # Extraer texto del PDF
    comm_text = extract_text_from_pdf(pdf_bytes)

    # Llamar tu motor de IA
    respuesta = generate_ai_response(
        comm_text,
        contract_text="",  
        history_text=""
    )

    return jsonify({"respuesta": respuesta})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
