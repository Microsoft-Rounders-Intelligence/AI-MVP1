# upload_to_blob.py
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

AZURE_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER")
BLOB_CONN_STR = os.getenv("AZURE_BLOB_CONN_STRING")
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)

def upload_pdf_to_blob(local_path: str, user_id: int) -> str:
    filename = f"user_{user_id}_{os.path.basename(local_path)}"
    blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER, blob=filename)
    with open(local_path, "rb") as f:
        blob_client.upload_blob(f, overwrite=True)
    return f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER}/{filename}"
