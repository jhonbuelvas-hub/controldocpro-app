import os
import json
import io

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Carpeta raíz en tu Google Drive
DRIVE_ROOT_FOLDER = "1mpnJ5RlKuTXJyIIgGvPSLrhTpNkJAJgJ"

# Archivo temporal donde se crea la credencial
SERVICE_ACCOUNT_FILE = "/tmp/service_account.json"

# Permisos necesarios
SCOPES = ["https://www.googleapis.com/auth/drive"]


# ============================================================
#  🔹 Obtiene servicio autenticado de Google Drive
# ============================================================
def get_drive_service():
    """Crea archivo temporal con las credenciales y retorna cliente de Drive."""

    service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not service_json:
        raise Exception("ERROR: No existe la variable GOOGLE_SERVICE_ACCOUNT_JSON en Render")

    # Crear archivo temporal
    with open(SERVICE_ACCOUNT_FILE, "w") as tmp_file:
        tmp_file.write(service_json)

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    drive = build("drive", "v3", credentials=creds)
    return drive


# ============================================================
# 🔹 Crear una subcarpeta dentro de la carpeta raíz DOCS
# ============================================================
def create_folder_if_not_exists(folder_name, parent_folder_id=DRIVE_ROOT_FOLDER):
    """Crea una carpeta si no existe. Retorna su ID."""
    try:
        drive = get_drive_service()

        query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        results = drive.files().list(q=query, fields="files(id, name)").execute()
        items = results.get("files", [])

        if items:
            return items[0]["id"]  # Ya existe

        # Crear nueva carpeta
        folder_metadata = {
            "name": folder_name,
            "parents": [parent_folder_id],
            "mimeType": "application/vnd.google-apps.folder"
        }

        folder = drive.files().create(
            body=folder_metadata,
            fields="id"
        ).execute()

        return folder["id"]

    except Exception as e:
        raise Exception(f"Error creando carpeta '{folder_name}': {str(e)}")


# ============================================================
# 🔹 Subir archivo a Drive en carpeta del contrato
# ============================================================
def upload_file_to_drive(local_path, original_name, contract_folder):
    """
    Sube un archivo a Drive dentro de la subcarpeta del contrato.
    Retorna: (file_id, web_view_link)
    """

    try:
        drive = get_drive_service()

        # 1. Asegurar carpeta por contrato
        folder_id = create_folder_if_not_exists(contract_folder)

        # 2. Preparar metadata
        file_metadata = {
            "name": original_name,
            "parents": [folder_id]
        }

        media = MediaFileUpload(local_path, resumable=True)

        uploaded = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        file_id = uploaded["id"]
        link = uploaded.get("webViewLink")

        return file_id, link

    except HttpError as e:
        raise Exception(f"Error en Google Drive API: {e}")
    except Exception as e:
        raise Exception(f"Error subiendo archivo: {str(e)}")


# ============================================================
# 🔹 Eliminar archivo de Drive
# ============================================================
def delete_file_from_drive(file_id):
    try:
        drive = get_drive_service()
        drive.files().delete(fileId=file_id).execute()
        return True
    except HttpError as e:
        return False
