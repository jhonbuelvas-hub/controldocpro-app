import os
import json

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# ==============================
# CONFIGURACIÓN PRINCIPAL
# ==============================

# Shared Drive donde se guardan todos los archivos
SHARED_DRIVE_ID = "0ANFiSibcPBDKUk9PVA"

# Carpeta raíz dentro del Shared Drive
ROOT_FOLDER_NAME = "DOCS"

# Archivo temporal donde reconstruimos el JSON
SERVICE_ACCOUNT_FILE = "/tmp/service_account.json"

# Permisos completos sobre Drive
SCOPES = ["https://www.googleapis.com/auth/drive"]


# ============================================================
# 🔹 Construye credenciales desde Render
# ============================================================
def get_drive_service():
    service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not service_json:
        raise Exception("ERROR: No existe GOOGLE_SERVICE_ACCOUNT_JSON en Render")

    # Escribir JSON temporal
    with open(SERVICE_ACCOUNT_FILE, "w") as f:
        f.write(service_json)

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds)


# ============================================================
# 🔹 Obtiene o crea carpeta dentro del Shared Drive
# ============================================================
def get_or_create_folder(name, parent_id=None):
    drive = get_drive_service()

    # Uso del Shared Drive para búsquedas
    query = (
        f"name = '{name}' and trashed = false and "
        f"mimeType = 'application/vnd.google-apps.folder'"
    )

    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = drive.files().list(
        q=query,
        spaces="drive",
        corpora="drive",
        driveId=SHARED_DRIVE_ID,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name)"
    ).execute()

    items = results.get("files", [])

    # Si existe → usamos ese ID
    if items:
        return items[0]["id"]

    # Si no existe → creamos
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id] if parent_id else [SHARED_DRIVE_ID]
    }

    folder = drive.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True
    ).execute()

    return folder["id"]


# ============================================================
# 🔹 Sube archivo dentro de:  SharedDrive / DOCS / contrato / subcarpeta
# ============================================================
def upload_file_to_drive(local_path, original_name, contract_folder, subfolder=None):

    drive = get_drive_service()

    # 1. Carpeta raíz DOCS en el Shared Drive
    root_id = get_or_create_folder(ROOT_FOLDER_NAME)

    # 2. Carpeta del contrato
    contract_id = get_or_create_folder(str(contract_folder), root_id)

    # 3. Subcarpeta (ej: communications)
    if subfolder:
        final_folder_id = get_or_create_folder(subfolder, contract_id)
    else:
        final_folder_id = contract_id

    # 4. Preparar archivo
    media = MediaFileUpload(local_path, resumable=True)

    metadata = {
        "name": original_name,
        "parents": [final_folder_id]
    }

    try:
        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()

        return uploaded["id"], uploaded.get("webViewLink")

    except HttpError as e:
        raise Exception(f"GOOGLE DRIVE ERROR: {e.status_code} - {e.error_details}")

    except Exception as e:
        raise Exception(f"ERROR SUBIENDO ARCHIVO: {str(e)}")


# ============================================================
# 🔹 Eliminar archivo por ID
# ============================================================
def delete_file_from_drive(file_id):
    try:
        drive = get_drive_service()
        drive.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
        return True
    except:
        return False
