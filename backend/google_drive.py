import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Ruta donde guardaremos el JSON interno en Render
SERVICE_ACCOUNT_FILE = "/tmp/google_sa.json"

# ID de carpeta raíz donde guardas todo
ROOT_FOLDER_ID = "1mpnJ5RlKuTXJyIIgGvPSLrhTpNkJAJgJ"


def load_service_account():
    """Crea archivo JSON en /tmp a partir de variable de entorno."""
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not sa_json:
        raise Exception("ERROR: Variable GOOGLE_SERVICE_ACCOUNT_JSON no configurada.")

    with open(SERVICE_ACCOUNT_FILE, "w") as f:
        f.write(sa_json)

    return SERVICE_ACCOUNT_FILE


def get_drive_service():
    """Inicializa cliente Google Drive."""
    json_path = load_service_account()

    creds = Credentials.from_service_account_file(
        json_path,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    return build("drive", "v3", credentials=creds)


def create_contract_folder(contract_id):
    """Crea carpeta de contrato dentro de DOCS."""
    service = get_drive_service()

    metadata = {
        "name": f"CONTRACT_{contract_id}",
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [ROOT_FOLDER_ID]
    }

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_file_to_drive(contract_id, filename, local_path, subfolder="communications"):
    """Sube archivo a Drive dentro de su subcarpeta."""
    service = get_drive_service()

    # 1. Crear carpeta del contrato si no existe
    contract_folder_id = create_contract_folder(contract_id)

    # 2. Crear subcarpeta si no existe
    sub_metadata = {
        "name": subfolder,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [contract_folder_id]
    }
    sub = service.files().create(body=sub_metadata, fields="id").execute()

    file_metadata = {
        "name": filename,
        "parents": [sub["id"]]
    }

    media = MediaFileUpload(local_path, resumable=True)

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    return {
        "file_id": uploaded["id"],
        "view_url": uploaded["webViewLink"]
    }
