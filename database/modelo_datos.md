# Modelo de Base de Datos - ControlDocPro

## 1. USERS (usuarios)
- id
- nombre
- email
- password
- rol
- estado
- created_at

## 2. THIRD_PARTIES (terceros)
- id
- tipo
- nombre
- identificacion
- correo
- telefono
- direccion
- ciudad
- created_at

## 3. CONTRACTS (contratos)
- id
- numero_contrato
- objeto
- tipo_contrato
- estado
- valor_inicial
- valor_total
- fecha_inicio
- fecha_fin
- contratista_id (FK)
- supervisor_id (FK)
- created_at

## 4. DOCUMENTS (documentos)
- id
- contrato_id (FK)
- tipo_documento
- nombre_archivo
- url_archivo
- version
- fecha_carga
- usuario_id (FK)

## 5. CORRESPONDENCE (correspondencia)
- id
- numero_radicado
- tipo
- asunto
- fecha_radicado
- remitente
- destinatario
- contrato_id (FK)
- responsable_id (FK)
- fecha_limite_respuesta
- estado

## 6. OBLIGATIONS (obligaciones)
- id
- contrato_id (FK)
- descripcion
- responsable_id (FK)
- fecha_limite
- estado

## 7. CONTROVERSIES (controversias)
- id
- contrato_id (FK)
- tipo
- descripcion
- estado
- fecha_apertura
- created_by

## 8. CONTROVERSY_EVIDENCE (evidencias)
- id
- controversia_id (FK)
- tipo
- descripcion
- archivo_url
- fecha

## 9. PAYMENTS (pagos)
- id
- contrato_id (FK)
- valor
- fecha_pago
- soporte

## 10. ALERTS (alertas)
- id
- tipo
- referencia_id
- fecha_alerta
- estado
