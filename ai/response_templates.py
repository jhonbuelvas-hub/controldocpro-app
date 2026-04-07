# ai/response_templates.py

def template_respuesta_requerimiento(entity, contract_number):
    return f"""
{entity}
Asunto: Respuesta a requerimiento relacionado con el contrato {contract_number}

Respetados señores,

En atención a su comunicación, nos permitimos informar lo siguiente:
[PARÁGRAFOS AUTOMÁTICOS GENERADOS POR IA]

Quedamos atentos a cualquier información adicional.

Atentamente,
[Nombre del Supervisor]
[Cargo]
"""

def template_respuesta_derecho_peticion(entity):
    return f"""
{entity}
Asunto: Respuesta a Derecho de Petición

Respetado(a) ciudadano(a),

Dando respuesta a su Derecho de Petición, nos permitimos indicar:
[RESPUESTA AUTOMÁTICA GENERADA POR IA]

Cordialmente,
[Dependencia]
"""
