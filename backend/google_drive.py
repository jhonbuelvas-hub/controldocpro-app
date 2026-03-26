import os
import json
import uuid

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ==============================
# CONFIGURACIÓN PRINCIPAL
# ==============================
# El ID de tu unidad compartida (Shared Drive)
SHARED_DRIVE_ID = os.getenv("SHARED_DRIVE_ID", "0ANFiSibcPBDKUk9PVA")
ROOT_FOLDER_NAME = "DOCS"

SCOPES = ["https://www.googleapis.com/auth/drive"]

# ============================================================
# CONSTRUYE CREDENCIALES DESDE REFRESH TOKEN (MODIFICADO)
# ============================================================
def get_user_credentials():
    """
    Crea las credenciales de Google usando el Refresh Token almacenado 
    en las variables de entorno de Render.
    """
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

    if not refresh_token:
        raise Exception(
            "ERROR: No se encontró la variable GOOGLE_OAUTH_REFRESH_TOKEN en Render. "
            "Asegúrate de haberla configurado en el panel de Environment."
        )

    # Creamos el objeto de credenciales directamente en memoria
    creds = Credentials(
        token=None,  # El access token se generará en el refresh()
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )

    # Refrescamos el token de acceso (expira cada hora, por eso refrescamos)
    try:
        creds.refresh(Request())
    except Exception as e:
        raise Exception(f"Error al refrescar el token de Google: {str(e)}")
        
    return creds

# ============================================================
# SERVICIO DRIVE
# ============================================================
def get_drive_service():
    creds = get_user_credentials()
    return build("drive", "v3", credentials=creds)

# ============================================================
# ESCAPAR TEXTO PARA QUERY
# ============================================================
def escape_query_value(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")

# ============================================================
# OBTENER O CREAR CARPETA
# ============================================================
def get_or_create_folder(name, parent_id=None):
    """
    Busca una carpeta por nombre. Si no existe, la crea.
    Ajustado para funcionar con Shared Drives.
    """
    drive = get_drive_service()
    safe_name = escape_query_value(name)

    # Query para buscar la carpeta
    query = (
        f"name = '{safe_name}' and trashed = false and "
        f"mimeType = 'application/vnd.google-apps.folder'"
    )

    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        # Si no hay padre, buscamos en la raíz del Shared Drive
        query += f" and '{SHARED_DRIVE_ID}' in parents"

    try:
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

        if items:
            return items[0]["id"]

        # Si no existe, la creamos
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id if parent_id else SHARED_DRIVE_ID]
        }

        folder = drive.files().create(
            body=metadata,
            fields="id",
            supportsAllDrives=True
        ).execute()

        return folder["id"]

    except HttpError as e:
        raise Exception(f"ERROR en Google Drive (Carpeta): {str(e)}")

# ============================================================
# SUBIR ARCHIVO A DRIVE
# ============================================================
def upload_file_to_drive(local_path, original_name, contract_folder="general", subfolder=None):
    """
    Sube un archivo local a una estructura de carpetas en Drive.
    """
    if not os.path.exists(local_path):
        raise Exception(f"El archivo local no existe en la ruta: {local_path}")

    drive = get_drive_service()

    try:
        # Estructura: DOCS / [ID_CONTRATO] / [SUBFOLDER]
        root_id = get_or_create_folder(ROOT_FOLDER_NAME)
        contract_id = get_or_create_folder(str(contract_folder), root_id)

        if subfolder:
            final_folder_id = get_or_create_folder(subfolder, contract_id)
        else:
            final_folder_id = contract_id

        # Preparar la subida
        media = MediaFileUpload(local_path, resumable=True)

        metadata = {
            "name": original_name,
            "parents": [final_folder_id]
        }

        # Ejecutar subida
        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()

        return uploaded["id"], uploaded.get("webViewLink")

    except HttpError as e:
        raise Exception(f"GOOGLE DRIVE ERROR (Upload): {str(e)}")
    except Exception as e:
        raise Exception(f"ERROR GENERAL SUBIENDO: {str(e)}")

# ============================================================
# ELIMINAR ARCHIVO
# ============================================================
def delete_file_from_drive(file_id):
    try:
        drive = get_drive_service()
        drive.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
        return True
    except Exception:
        return False
