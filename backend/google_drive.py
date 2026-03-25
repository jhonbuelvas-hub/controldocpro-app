import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

# Ruta a la clave JSON (Render usa variables de entorno)
SERVICE_ACCOUNT_FILE = "service_account.json"

# Folder principal en Drive
DRIVE_ROOT_FOLDER = "1mpnJ5RlKuTXJyIIgGvPSLrhTpNkJAJgJ"  # Carpeta DOCS

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Autenticación con Google Drive
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

drive_service = build("drive", "v3", credentials=credentials)


# ------------------------------------------------------
#   SUBIR ARCHIVOS
# ------------------------------------------------------
def upload_file(local_path, filename, folder_id=DRIVE_ROOT_FOLDER):
    """
    Sube un archivo desde el servidor Render a Google Drive.
    """
    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }

    media = MediaFileUpload(local_path, resumable=True)

    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name"
    ).execute()

    return uploaded


# ------------------------------------------------------
#   DESCARGAR ARCHIVOS
# ------------------------------------------------------
def download_file(file_id, local_path):
    """
    Descarga un archivo de Google Drive al servidor Render.
    """
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, "wb")

    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    return True


# ------------------------------------------------------
#   LISTAR ARCHIVOS EN UNA CARPETA
# ------------------------------------------------------
def list_files(folder_id=DRIVE_ROOT_FOLDER):
    """
    Lista archivos dentro de una carpeta.
    """
    query = f"'{folder_id}' in parents and trashed = false"

    results = drive_service.files().list(
        q=query,
        spaces='drive',
        fields="files(id, name, mimeType)"
    ).execute()

    return results.get("files", [])


# ------------------------------------------------------
#   CREAR SUBCARPETAS
# ------------------------------------------------------
def create_folder(name, parent_id=DRIVE_ROOT_FOLDER):
    """
    Crea subcarpetas para cada contrato, comunicaciones, etc.
    """
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }

    folder = drive_service.files().create(
        body=file_metadata,
        fields="id, name"
    ).execute()

    return folder["id"]
