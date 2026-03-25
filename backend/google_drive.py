import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ID de la carpeta raíz "DOCS"
DRIVE_ROOT_FOLDER = "1mpnJ5RlKuTXJyIIgGvPSLrhTpNkJAJgJ"

# Archivo temporal donde se crea la credencial
SERVICE_ACCOUNT_FILE = "/tmp/service_account.json"

# Permisos necesarios
SCOPES = ["https://www.googleapis.com/auth/drive"]


# ============================================================
#  🔹 Servicio autenticado
# ============================================================
def get_drive_service():
    """Crea una credencial temporal desde la variable de entorno."""
    service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not service_json:
        raise Exception("ERROR: Falta la variable GOOGLE_SERVICE_ACCOUNT_JSON.")

    # Crear archivo temporal con la clave
    with open(SERVICE_ACCOUNT_FILE, "w") as tmp_file:
        tmp_file.write(service_json)

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    drive = build("drive", "v3", credentials=creds)
    return drive


# ============================================================
# 🔹 Crear carpeta si no existe
# ============================================================
def create_folder_if_not_exists(folder_name, parent_folder_id=DRIVE_ROOT_FOLDER):
    """Crea una carpeta dentro del parent si no existe."""
    try:
        drive = get_drive_service()

        query = (
            f"name = '{folder_name}' and "
            f"'{parent_folder_id}' in parents and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )

        results = drive.files().list(
            q=query,
            fields="files(id, name)"
        ).execute()

        items = results.get("files", [])

        if items:
            return items[0]["id"]  # Ya existe

        # Crear carpeta
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
# 🔹 Subir archivo a Drive
# ============================================================
def upload_file_to_drive(local_path, original_name, subfolder):
    """
    Sube archivo a Google Drive dentro de DOCS/{subfolder}.
    Retorna: file_id, link pública
    """
    try:
        drive = get_drive_service()

        # Crear (o verificar) subcarpeta dentro de DOCS
        folder_id = create_folder_if_not_exists(subfolder)

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

        return uploaded["id"], uploaded.get("webViewLink")

    except HttpError as e:
        raise Exception(f"Error en Google Drive API: {e}")
    except Exception as e:
        raise Exception(f"Error subiendo archivo: {str(e)}")


# ============================================================
# 🔹 Wrapper: función con la firma EXACTA que usas en app.py
# ============================================================
def upload_file(contract_id, filename, tmp_path, subfolder="communications"):
    """
    Wrapper compatible con app.py.
    Crea carpeta por contrato y subcarpeta interna.
    
    Estructura:
        DOCS/
            {contract_id}/
                communications/
                    archivo.pdf
    """
    # Crear carpeta del contrato
    contract_folder_id = create_folder_if_not_exists(str(contract_id))

    # Crear subcarpeta dentro del contrato
    subfolder_id = create_folder_if_not_exists(subfolder, parent_folder_id=contract_folder_id)

    drive = get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [subfolder_id]
    }

    media = MediaFileUpload(tmp_path, resumable=True)

    uploaded = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    return uploaded["id"], uploaded.get("webViewLink")


# ============================================================
# 🔹 Eliminar archivo de Drive
# ============================================================
def delete_file_from_drive(file_id):
    try:
        drive = get_drive_service()
        drive.files().delete(fileId=file_id).execute()
        return True
    except:
        return False
