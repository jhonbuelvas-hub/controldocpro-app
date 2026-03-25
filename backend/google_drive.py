import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Carpeta raíz DOCS en tu Drive
DRIVE_ROOT_FOLDER = "1mpnJ5RlKuTXJyIIgGvPSLrhTpNkJAJgJ"

# Archivo temporal donde se guardan las credenciales
SERVICE_ACCOUNT_FILE = "/tmp/service_account.json"

# Permisos para Drive
SCOPES = ["https://www.googleapis.com/auth/drive"]


# ============================================================
# 🔹 Crear cliente autenticado de Google Drive
# ============================================================
def get_drive_service():
    """Crea cliente Drive usando la credencial JSON almacenada en variables de entorno."""
    try:
        service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not service_json:
            raise Exception("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON no existe en Render.")

        # Crear archivo temporal con el JSON
        with open(SERVICE_ACCOUNT_FILE, "w") as tmp_file:
            tmp_file.write(service_json)

        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        return build("drive", "v3", credentials=creds)

    except Exception as e:
        raise Exception(f"Error creando servicio de Google Drive: {str(e)}")


# ============================================================
# 🔹 Crear carpeta si no existe
# ============================================================
def create_folder_if_not_exists(folder_name, parent_folder_id=DRIVE_ROOT_FOLDER):
    """Crea una carpeta dentro de otra si no existe y devuelve su ID."""
    try:
        drive = get_drive_service()

        query = (
            f"name = '{folder_name}' and "
            f"'{parent_folder_id}' in parents and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )

        result = drive.files().list(q=query, fields="files(id, name)").execute()
        files = result.get("files", [])

        if files:
            return files[0]["id"]

        # Crear nueva carpeta
        metadata = {
            "name": folder_name,
            "parents": [parent_folder_id],
            "mimeType": "application/vnd.google-apps.folder"
        }

        folder = drive.files().create(body=metadata, fields="id").execute()

        return folder["id"]

    except Exception as e:
        raise Exception(f"Error creando carpeta '{folder_name}': {str(e)}")


# ============================================================
# 🔹 Subir archivo a Drive (compatible con app.py)
# ============================================================
def upload_file_to_drive(contract_id, filename, tmp_path, subfolder="communications"):
    """
    Sube archivo a Drive usando estructura:

        DOCS/
            {contract_id}/
                {subfolder}/
                    archivo.pdf

    Retorna:
        file_id, webViewLink
    """
    try:
        drive = get_drive_service()

        # 1. Crear carpeta del contrato
        contract_folder_id = create_folder_if_not_exists(str(contract_id))

        # 2. Crear subcarpeta interna (comunicaciones, documentos, etc.)
        subfolder_id = create_folder_if_not_exists(
            subfolder,
            parent_folder_id=contract_folder_id
        )

        # 3. Metadata del archivo
        metadata = {
            "name": filename,
            "parents": [subfolder_id]
        }

        media = MediaFileUpload(tmp_path, resumable=True)

        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        return uploaded["id"], uploaded.get("webViewLink")

    except HttpError as e:
    raise Exception(f"GOOGLE ERROR: {e.status_code} - {e.error_details}")

    except Exception as e:
        raise Exception(f"Error subiendo archivo: {str(e)}")


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
