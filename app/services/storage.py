import os
from pathlib import Path
from typing import Optional
import boto3
from botocore.config import Config
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.r2_enabled = bool(
            settings.R2_ACCOUNT_ID and 
            settings.R2_ACCESS_KEY_ID and 
            settings.R2_SECRET_ACCESS_KEY and 
            settings.R2_BUCKET_NAME
        )
        self.s3_client = None
        if self.r2_enabled:
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                    config=Config(signature_version='s3v4')
                )
            except Exception as e:
                print(f"Warning: Cloudflare R2 client initialization failed: {e}")
                self.r2_enabled = False

    def upload_file(self, local_path: str, object_name: Optional[str] = None) -> str:
        """
        Uploads a file to Cloudflare R2 if configured.
        Otherwise returns the local API path for direct streaming.
        """
        filename = os.path.basename(local_path)
        dest_name = object_name or filename

        if self.r2_enabled and self.s3_client:
            try:
                content_type = "video/mp4" if filename.endswith(".mp4") else "text/plain"
                self.s3_client.upload_file(
                    local_path,
                    settings.R2_BUCKET_NAME,
                    dest_name,
                    ExtraArgs={'ContentType': content_type}
                )
                if settings.R2_PUBLIC_URL:
                    base_url = settings.R2_PUBLIC_URL.rstrip("/")
                    return f"{base_url}/{dest_name}"
            except Exception as e:
                print(f"R2 upload failed: {e}. Falling back to local URL.")

        # Local fallback served by FastAPI static router
        return f"/outputs/clips/{filename}"

storage = StorageService()
