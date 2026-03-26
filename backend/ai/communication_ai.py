# ai/communication_ai.py

from openai import OpenAI
from backend.ai.utils_ai import extract_text_from_pdf, merge_text_blocks, clean_text

client = OpenAI()

def build_prompt(comm_text, contract_text, history_text):
    """Prompt legal ultra-estricto para evitar alucinaciones y cruce de datos."""
    
    # Limpiamos los textos para evitar basura de PDFs
    clean_comm = clean_text(comm_text)
    clean_contract = clean_text(contract_text)
    clean_history = clean_text(history_text)

    return f"""
Eres un asesor jurídico experto en contratación estatal colombiana y ver desde el punto de vista del contratista. 
Tu objetivo es analizar la comunicación adjunta y proponer una respuesta.

### REGLAS CRÍTICAS:
1. Analiza ÚNICAMENTE la información presente en la "Comunicación Actual".
2. Si el "Contexto del Contrato" o "Historial" mencionan temas (como estampillas, multas anteriores, etc.) que NO están en la comunicación actual, NO los incluyas en la respuesta formal.
3. NO inventes hechos. Si el texto habla de ajustes de precios, mantente en ajustes de precios.

### 1. COMUNICACIÓN ACTUAL A PROCESAR (PRIORIDAD 100%):
{clean_comm}

### 2. CONTEXTO DEL CONTRATO (SOLO SI APLICA):
{clean_contract if clean_contract else "No hay información contractual adicional."}

### 3. ANTECEDENTES RECIENTES (SOLO REFERENCIA):
{clean_history if clean_history else "No hay historial previo."}

---
### TAREAS:
1. Resumen ejecutivo (máximo 8 líneas): Enfocado en el conflicto actual.
2. Puntos clave: ¿Qué pide el contratista y qué responde la entidad?
3. Obligaciones relacionadas: Citar cláusulas si aparecen en el texto.
4. Riesgos: Identificar posibles reclamaciones económicas o retrasos.
5. RESPUESTA FORMAL: Redacta un borrador técnico y profesional. Usa los datos (Radicados, Nombres, Valores) que aparecen en la comunicación actual.
6. Recomendaciones: Pasos a seguir inmediatos.

Usa un tono formal y jurídico.
"""

def generate_ai_response(comm_text, contract_text, history_text): 
    """Genera análisis + borrador de respuesta."""
    
    # Si por algún motivo los textos llegan vacíos, evitamos enviar basura a OpenAI
    if not comm_text or len(comm_text.strip()) < 10:
        return "Error: El contenido de la comunicación está vacío o no se pudo leer el PDF correctamente."

    prompt = build_prompt(comm_text, contract_text, history_text)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto legal que no mezcla casos. Solo respondes basado en el texto principal proporcionado."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1 # Bajamos la temperatura para que sea más preciso y menos creativo
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error en Módulo IA: {str(e)}"


