import logging
import os
from pathlib import Path
from typing import Optional, Union

import aiofiles

logger = logging.getLogger(__name__)


class FileStorage:
    """
    Utility for handling file storage operations.
    """

    def __init__(self, base_path: str = "./storage") -> None:
        """
        Initialize the file storage utility.

        Args:
            base_path (str, optional): Base directory for file storage.
                Defaults to './storage' if not provided.
        """
        self.base_path = Path(base_path)
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure the storage directory exists."""
        os.makedirs(self.base_path, exist_ok=True)

    def _get_file_path(self, path: Union[str, Path], create_missing: bool = False) -> Path:
        """
        Get the full file path for a given file identifier.

        Args:
            path (Union[str, Path]): The file identifier or path.
            create_missing (bool): Whether to create the directory if it doesn't exist.

        Returns:
            Path: The full path to the file.
        """
        if not path.is_absolute():
            path = self.base_path / path
            
        if create_missing:
            path.parent.mkdir(parents=True, exist_ok=True)
            
        return path

    async def get_file_by_path(self, path: Union[Path, str]) -> Optional[bytes]:
        """
        Retrieve a file from storage.

        Args:
            path (Union[Path, str]): The file path.

        Returns:
            Optional[bytes]: The file content as bytes, or None if file not found.
        """
        file_path = self._get_file_path(path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            async with aiofiles.open(file_path, "rb") as file:
                return await file.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise IOError(f"Failed to read file: {str(e)}")
    
    async def delete_file_by_path(self, path: Union[Path, str]) -> bool:
        """
        Delete a file from storage.

        Args:
            path (Union[Path, str]): The file path.

        Returns:
            bool: True if the file was deleted, False if it didn't exist.
        """
        # Try to find the file directly in base path first
        file_path = self._get_file_path(path)

        if not file_path.exists():
            logger.warning(f"Cannot delete: file not found: {file_path}")
            return False

        try:
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            raise IOError(f"Failed to delete file: {str(e)}")

    async def save_bytes_by_path(self, bytes: bytes, path: Union[str, Path]) -> Path:
        """
        Save bytes to a file at the specified path.

        Args:
            path (Union[str, Path]): The file path where bytes should be saved.
            bytes (bytes): The bytes content to save.

        Returns:
            bool: True if the file was saved successfully, False otherwise.
        """
        file_path = self._get_file_path(path, create_missing=True)
        try:
            async with aiofiles.open(file_path, "wb") as out_file:
                await out_file.write(bytes)
            logger.info(f"Bytes saved to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving bytes to {file_path}: {str(e)}")
            raise IOError(f"Failed to save bytes to {file_path}: {str(e)}")
