# ai/communication_ai.py

from openai import OpenAI
from backend.ai.utils_ai import extract_text_from_pdf, merge_text_blocks, clean_text

client = OpenAI()

def build_prompt(comm_text, contract_text, history_text):
    """Prompt legal especializado para comunicaciones."""
    return f"""
Eres un asesor jurídico experto en contratación estatal de Colombia y comunicaciones formales.

### Comunicación recibida:
{clean_text(comm_text)}

### Información contractual relevante:
{clean_text(contract_text)}

### Historial de comunicaciones previas:
{clean_text(history_text)}

---

Con base en estos insumos, realiza lo siguiente:

1. Resumen ejecutivo (máximo 8 líneas).
2. Puntos clave de la comunicación.
3. Identifique obligaciones contractuales relacionadas.
4. Riesgos jurídicos o contractuales.
5. Redacta una RESPUESTA FORMAL completa y profesional lista para enviar.
6. Recomendaciones adicionales.

Usa un estilo claro, jurídico y profesional.
"""

def generate_ai_response(comm_text, contract_text, history_text): 
    """Genera análisis + borrador de respuesta."""
    prompt = build_prompt(comm_text, contract_text, history_text)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto en contratación estatal colombiana."},
                {"role": "user", "content": prompt}
            ]
        )

        # ✔ ACCESO CORRECTO AL TEXTO DE LA RESPUESTA
        return response.choices[0].message.content

    except Exception as e:
        return f"Error en Módulo IA: {str(e)}"
