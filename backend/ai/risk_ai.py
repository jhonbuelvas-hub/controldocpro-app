# ai/risk_ai.py

from openai import OpenAI
from ai.utils_ai import clean_text

client = OpenAI()

def risk_prompt(text):
    return f"""
Eres un analista de riesgos en contratación estatal.

Analiza el siguiente texto (comunicaciones, informes, actas, modificatorios):

{text}

Debes identificar:

1. Riesgos contractuales (jurídicos, financieros, técnicos).
2. Causas probables.
3. Posibles consecuencias.
4. Nivel de riesgo (Bajo, Medio, Alto).
5. Recomendaciones de mitigación específicas.

Presenta los resultados en formato claro y profesional.
"""

def analyze_risks(text):
    prompt = risk_prompt(clean_text(text))

    res = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message["content"]
