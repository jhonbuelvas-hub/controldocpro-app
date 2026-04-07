# ai/utils_ai.py
from PyPDF2 import PdfReader
import io
import re
from typing import Union

def extract_text_from_pdf(file_input: Union[bytes, io.BytesIO]) -> str:
    """
    Extrae texto de un PDF.
    Acepta bytes o BytesIO.
    Nunca lanza excepción hacia Flask (seguro para Azure).
    """
    if not file_input:
        return ""

    try:
        # Convertir bytes a BytesIO si es necesario
        if isinstance(file_input, bytes):
            file_input = io.BytesIO(file_input)

        # Asegurar puntero al inicio
        try:
            file_input.seek(0)
        except Exception:
            pass

        reader = PdfReader(file_input)
        text_chunks = []

        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text_chunks.append(page_text)
            except Exception:
                # Nunca romper por una página dañada
                continue

        return "\n".join(text_chunks).strip()

    except Exception:
        # En Azure NUNCA imprimir ni lanzar error
        return ""

def clean_text(text: str) -> str:
    """Limpia el texto para que la IA lo entienda mejor."""
    if not text:
        return ""

    text = text.replace("\x00", "").strip()
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text

def merge_text_blocks(text_list):
    """Une múltiples bloques de texto sin valores vacíos."""
    if not text_list:
        return ""

    return "\n\n".join(t for t in text_list if t and t.strip())
``
