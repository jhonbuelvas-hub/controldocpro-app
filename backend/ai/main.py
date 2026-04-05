from fastapi import FastAPI, UploadFile, File, Form
from backend.ai.communication_ai import generate_ai_response
from backend.ai.utils_ai import extract_text_from_pdf

app = FastAPI()

@app.post("/analizar")
async def analizar(
    archivo: UploadFile = File(...),
    instruccion: str = Form("")
):
    pdf_bytes = await archivo.read()

    # Extrae texto del PDF
    comm_text = extract_text_from_pdf(pdf_bytes)

    # Llama tu módulo principal de IA
    respuesta = generate_ai_response(
        comm_text,
        contract_text="",  
        history_text=""
    )

    return {"respuesta": respuesta}
