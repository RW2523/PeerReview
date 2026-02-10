"""
MinIO storage client for file uploads
"""

import logging
from typing import BinaryIO, Optional

from minio import Minio
from minio.error import S3Error
from src.config import settings

logger = logging.getLogger(__name__)


class StorageClient:
    """MinIO S3-compatible storage client"""
    
    def __init__(self):
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket
    
    def ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            # Avoid breaking app import / startup if MinIO isn't reachable yet.
            logger.warning("MinIO bucket ensure failed (bucket=%s): %s", self.bucket_name, e)
    
    def upload_file(self, file_key: str, file_data: BinaryIO, file_size: int, content_type: str) -> str:
        """
        Upload file to MinIO
        
        Args:
            file_key: Object key/path in bucket
            file_data: File-like object
            file_size: Size in bytes
            content_type: MIME type
        
        Returns:
            file_key on success
        
        Raises:
            S3Error on upload failure
        """
        try:
            self.ensure_bucket_exists()
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=file_key,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            return file_key
        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}")
    
    def download_file(self, file_key: str) -> bytes:
        """
        Download file from MinIO
        
        Args:
            file_key: Object key/path in bucket
        
        Returns:
            File contents as bytes
        
        Raises:
            S3Error if file not found or download fails
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=file_key
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise Exception(f"Failed to download file: {e}")
    
    def delete_file(self, file_key: str) -> None:
        """
        Delete file from MinIO
        
        Args:
            file_key: Object key/path in bucket
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=file_key
            )
        except S3Error as e:
            logger.warning("Error deleting MinIO object (key=%s): %s", file_key, e)
    
    def file_exists(self, file_key: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=file_key
            )
            return True
        except S3Error:
            return False


_storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """
    Lazy singleton: avoids MinIO network calls at import time.
    """
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
