# ai/contract_ai.py

from openai import OpenAI
from backend.ai.utils_ai import clean_text

client = OpenAI()

def build_contract_prompt(contract_text):
    return f"""
Eres un experto en contratación estatal en Colombia.

Analiza el siguiente contrato y sus documentos anexos:

---
{clean_text(contract_text)}
---

Debes entregar:

1. Resumen general del contrato.
2. Matriz de obligaciones (contratista, supervisor, entidad).
3. Riesgos jurídicos, financieros y técnicos.
4. Hallazgos importantes (inconsistencias, vacíos, cláusulas críticas).
5. Puntos clave para vigilancia contractual.
6. Recomendaciones profesionales para la entidad.

Responde de forma estructurada y profesional.
"""

def analyze_contract(contract_text):
    prompt = build_contract_prompt(contract_text)

    res = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message["content"]
