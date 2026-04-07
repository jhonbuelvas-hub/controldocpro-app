# ai/utils_ai.py
import PyPDF2
import io
import re

def extract_text_from_pdf(file_input):
    """
    Extrae texto de un PDF. 
    Soporta rutas de archivos (strings) y objetos en memoria (BytesIO).
    """
    text = ""
    try:
        # Si recibimos bytes directamente, los convertimos a un objeto de memoria
        if isinstance(file_input, bytes):
            file_input = io.BytesIO(file_input)
            
        reader = PyPDF2.PdfReader(file_input)
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        return text.strip()

    except Exception as e:
        print(f"[ERROR] extract_text_from_pdf: {e}")
        return ""

def clean_text(text):
    """Limpia el texto para que la IA lo entienda mejor."""
    if not text:
        return ""
    
    # Eliminar caracteres nulos
    text = text.replace("\x00", "").strip()
    
    # Normalizar saltos de línea excesivos
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def merge_text_blocks(text_list):
    """Une múltiples bloques de texto."""
    return "\n\n".join([t for t in text_list if t and t.strip()])
