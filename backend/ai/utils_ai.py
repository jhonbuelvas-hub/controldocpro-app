# ai/utils_ai.py

import fitz  # PyMuPDF

def extract_text_from_pdf(path):
    """Extrae texto plano desde un PDF usando PyMuPDF."""
    try:
        doc = fitz.open(path)
        return "\n".join([page.get_text() for page in doc])
    except Exception as e:
        print(f"[ERROR] extract_text_from_pdf: {e}")
        return ""


def merge_text_blocks(text_list):
    """Une múltiples bloques de texto en uno solo, separando por dobles saltos."""
    return "\n\n".join([t for t in text_list if t.strip()])


def clean_text(text):
    """Limpia texto eliminando espacios, saltos repetidos y caracteres raros."""
    if not text:
        return ""
    
    text = text.replace("\x00", "").strip()
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text

def extract_text_from_pdf(file_input):
    """
    file_input puede ser una ruta de archivo (string) 
    o un objeto BytesIO (archivo en memoria)
    """
    import PyPDF2
    reader = PyPDF2.PdfReader(file_input)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text
