import os
import json

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

DRIVE_ROOT_FOLDER = "1mpnJ5RlKuTXJyIIgGvPSLrhTpNkJAJgJ"

SERVICE_ACCOUNT_FILE = "/tmp/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service():
    """Carga credenciales desde variable y crea cliente."""
    service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_json:
        raise Exception("NO existe la variable GOOGLE_SERVICE_ACCOUNT_JSON en Render")

    # Crear archivo temporal
    with open(SERVICE_ACCOUNT_FILE, "w") as f:
        f.write(service_json)

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds)


def create_folder_if_not_exists(folder_name, parent_folder_id=DRIVE_ROOT_FOLDER):
    """Crea la carpeta si no existe dentro del folder padre."""
    drive = get_drive_service()

    query = (
        f"name = '{folder_name}' and "
        f"'{parent_folder_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )

    results = drive.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])

    if items:
        return items[0]["id"]

    # Crear nueva carpeta
    folder_metadata = {
        "name": folder_name,
        "parents": [parent_folder_id],
        "mimeType": "application/vnd.google-apps.folder",
    }

    folder = drive.files().create(
        body=folder_metadata,
        fields="id"
    ).execute()

    return folder["id"]


def upload_file_to_drive(local_path, original_name, contract_folder, subfolder=None):
    """
    Sube archivo al Drive dentro de:
       DOCS / contract_folder / (subfolder opcional)
    Retorna: (file_id, webViewLink)
    """

    drive = get_drive_service()

    # 1. Carpeta del contrato
    contract_folder_id = create_folder_if_not_exists(contract_folder)

    if not contract_folder_id:
        raise Exception("NO SE PUDO CREAR/OBTENER carpeta del contrato")

    # 2. Subcarpeta dentro del contrato (ej: communications)
    if subfolder:
        final_folder_id = create_folder_if_not_exists(subfolder, contract_folder_id)
    else:
        final_folder_id = contract_folder_id

    if not final_folder_id:
        raise Exception("NO SE PUDO CREAR/OBTENER subcarpeta destino")

    # 3. Subir archivo
    media = MediaFileUpload(local_path, resumable=True)

    metadata = {
        "name": original_name,
        "parents": [final_folder_id]     # ← MUY IMPORTANTE
    }

    try:
        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        return uploaded["id"], uploaded.get("webViewLink")

    except HttpError as e:
        # Este mensaje te mostrará EXACTAMENTE el fallo
        raise Exception(f"GOOGLE DRIVE ERROR: {e.status_code} - {e.error_details}")

    except Exception as e:
        raise Exception(f"ERROR SUBIENDO ARCHIVO: {str(e)}")

# ============================================================
# 🔹 Eliminar archivo por ID
# ============================================================
def delete_file_from_drive(file_id):
    try:
        drive = get_drive_service()
        drive.files().delete(fileId=file_id).execute()
        return True
    except:
        return False
