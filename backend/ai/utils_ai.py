# ai/utils_ai.py
import PyPDF2
import io

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
        
        # Si después de leer todo, el texto sigue vacío, puede ser un PDF escaneado (imagen)
        if not text.strip():
            print("[WARN] El PDF parece no tener texto extraíble (posible imagen).")
            
        return text.strip()

    except Exception as e:
        print(f"[ERROR] extract_text_from_pdf: {e}")
        return ""

def merge_text_blocks(text_list):
    """Une múltiples bloques de texto en uno solo."""
    return "\n\n".join([t for t in text_list if t and t.strip()])

def clean_text(text):
    """Limpia el texto para que la IA lo entienda mejor."""
    if not text:
        return ""
    
    # Eliminar caracteres nulos y limpiar espacios
    text = text.replace("\x00", "").strip()
    
    # Normalizar saltos de línea (máximo 2 seguidos)
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text
