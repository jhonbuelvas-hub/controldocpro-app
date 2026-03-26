import os
import json

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# ==============================
# CONFIGURACIÓN PRINCIPAL
# ==============================
SHARED_DRIVE_ID = os.getenv("SHARED_DRIVE_ID", "0ANFiSibcPBDKUk9PVA")
ROOT_FOLDER_NAME = "DOCS"

SCOPES = ["https://www.googleapis.com/auth/drive"]


# ============================================================
# CONFIG OAUTH DESDE VARIABLES DE ENTORNO
# ============================================================
def get_client_config():
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        raise Exception(
            "Faltan variables GOOGLE_OAUTH_CLIENT_ID, "
            "GOOGLE_OAUTH_CLIENT_SECRET o GOOGLE_OAUTH_REDIRECT_URI"
        )

    return {
        "web": {
            "client_id": client_id,
            "project_id": "controldocpro",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri]
        }
    }


# ============================================================
# CREA FLOW OAUTH
# ============================================================
def create_oauth_flow(state=None):
    client_config = get_client_config()
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = redirect_uri
    return flow


# ============================================================
# URL DE AUTORIZACIÓN
# ============================================================
def get_authorization_url():
    flow = create_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return authorization_url, state


# ============================================================
# INTERCAMBIA CODE POR TOKENS
# ============================================================
def fetch_tokens_from_response(full_request_url, state):
    flow = create_oauth_flow(state=state)
    flow.fetch_token(authorization_response=full_request_url)
    creds = flow.credentials

    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }


# ============================================================
# CONSTRUYE CREDENCIALES DESDE REFRESH TOKEN
# ============================================================
def get_user_credentials():
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

    if not refresh_token:
        raise Exception(
            "No existe GOOGLE_OAUTH_REFRESH_TOKEN. "
            "Primero debes autorizar la cuenta por OAuth."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )

    # Fuerza renovación del access token
    creds.refresh(Request())
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
    drive = get_drive_service()
    safe_name = escape_query_value(name)

    query = (
        f"name = '{safe_name}' and trashed = false and "
        f"mimeType = 'application/vnd.google-apps.folder'"
    )

    if parent_id:
        query += f" and '{parent_id}' in parents"

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

        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder"
        }

        if parent_id:
            metadata["parents"] = [parent_id]
        else:
            metadata["parents"] = [SHARED_DRIVE_ID]

        folder = drive.files().create(
            body=metadata,
            fields="id",
            supportsAllDrives=True
        ).execute()

        return folder["id"]

    except HttpError as e:
        status = getattr(e.resp, "status", "N/A")
        raise Exception(f"ERROR creando/buscando carpeta: {status} - {str(e)}")


# ============================================================
# SUBIR ARCHIVO A DRIVE
# ============================================================
def upload_file_to_drive(local_path, original_name, contract_folder, subfolder=None):
    if not os.path.exists(local_path):
        raise Exception(f"El archivo local no existe: {local_path}")

    drive = get_drive_service()

    try:
        root_id = get_or_create_folder(ROOT_FOLDER_NAME)
        contract_id = get_or_create_folder(str(contract_folder), root_id)

        if subfolder:
            final_folder_id = get_or_create_folder(subfolder, contract_id)
        else:
            final_folder_id = contract_id

        media = MediaFileUpload(local_path, resumable=True)

        metadata = {
            "name": original_name,
            "parents": [final_folder_id]
        }

        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()

        return uploaded["id"], uploaded.get("webViewLink")

    except HttpError as e:
        status = getattr(e.resp, "status", "N/A")
        raise Exception(f"GOOGLE DRIVE ERROR: {status} - {str(e)}")
    except Exception as e:
        raise Exception(f"ERROR SUBIENDO ARCHIVO: {str(e)}")


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
