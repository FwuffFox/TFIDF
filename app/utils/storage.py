import logging
import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Union

import aiofiles
from fastapi import UploadFile

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

    def _get_file_path(self, file_id: str, subdir: str = None) -> Path:
        """
        Get the full path for a file.

        Args:
            file_id (str): The unique identifier for the file.
            subdir (str, optional): Subdirectory within the base path.

        Returns:
            Path: The full path to the file.
        """
        if subdir:
            directory = self.base_path / subdir
            os.makedirs(directory, exist_ok=True)
            return directory / file_id
        return self.base_path / file_id

    async def save_file(
        self, file: UploadFile, file_id: str, subdir: str = None
    ) -> str:
        """
        Save an uploaded file to storage.

        Args:
            file (UploadFile): The FastAPI UploadFile object.
            file_id (str): Unique identifier for the file.
            subdir (str, optional): Subdirectory to store the file in.

        Returns:
            str: The path where the file was saved.
        """
        file_path = self._get_file_path(file_id, subdir)

        # Create parent directory if it doesn't exist
        os.makedirs(file_path.parent, exist_ok=True)

        try:
            # Use aiofiles for non-blocking I/O
            async with aiofiles.open(file_path, "wb") as out_file:
                # Read and write in chunks to handle large files efficiently
                content = await file.read()
                await out_file.write(content)

            logger.info(f"File saved: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"Error saving file {file_id}: {str(e)}")
            raise IOError(f"Failed to save file: {str(e)}")

    async def save_bytes(self, content: bytes, file_id: str, subdir: str = None) -> str:
        """
        Save bytes content to storage.

        Args:
            content (bytes): The bytes content to save.
            file_id (str): Unique identifier for the file.
            subdir (str, optional): Subdirectory to store the file in.

        Returns:
            str: The path where the file was saved.
        """
        file_path = self._get_file_path(file_id, subdir)

        # Create parent directory if it doesn't exist
        os.makedirs(file_path.parent, exist_ok=True)

        try:
            # Use aiofiles for non-blocking I/O
            async with aiofiles.open(file_path, "wb") as out_file:
                await out_file.write(content)

            logger.info(f"Content saved: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"Error saving content {file_id}: {str(e)}")
            raise IOError(f"Failed to save content: {str(e)}")

    async def get_file(self, file_id: str) -> Optional[bytes]:
        """
        Retrieve a file from storage.

        Args:
            file_id (str): Unique identifier for the file.

        Returns:
            Optional[bytes]: The file content as bytes, or None if file not found.
        """
        # Try to find the file directly in base path first
        file_path = self.base_path / file_id

        # If not found, search in subdirectories
        if not file_path.exists():
            # Check if file exists in any subdirectory
            for subdir in os.listdir(self.base_path):
                potential_path = self.base_path / subdir / file_id
                if potential_path.exists():
                    file_path = potential_path
                    break

        if not file_path.exists():
            logger.warning(f"File not found: {file_id}")
            return None

        try:
            async with aiofiles.open(file_path, "rb") as file:
                return await file.read()
        except Exception as e:
            logger.error(f"Error reading file {file_id}: {str(e)}")
            raise IOError(f"Failed to read file: {str(e)}")

    def file_exists(self, file_id: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            file_id (str): Unique identifier for the file.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        # Try to find the file directly in base path first
        file_path = self.base_path / file_id

        # If not found, search in subdirectories
        if not file_path.exists():
            # Check if file exists in any subdirectory
            for subdir in os.listdir(self.base_path):
                potential_path = self.base_path / subdir / file_id
                if potential_path.exists():
                    return True

            return False

        return True

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_id (str): Unique identifier for the file.

        Returns:
            bool: True if the file was deleted, False if it didn't exist.
        """
        # Try to find the file directly in base path first
        file_path = self.base_path / file_id

        # If not found, search in subdirectories
        if not file_path.exists():
            # Check if file exists in any subdirectory
            for subdir in os.listdir(self.base_path):
                potential_path = self.base_path / subdir / file_id
                if potential_path.exists():
                    file_path = potential_path
                    break

        if not file_path.exists():
            logger.warning(f"Cannot delete: file not found: {file_id}")
            return False

        try:
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            raise IOError(f"Failed to delete file: {str(e)}")

    def get_file_path(self, file_id: str) -> Optional[str]:
        """
        Get the absolute path to a file.

        Args:
            file_id (str): Unique identifier for the file.

        Returns:
            Optional[str]: The absolute path to the file, or None if not found.
        """
        # Try to find the file directly in base path first
        file_path = self.base_path / file_id

        # If not found, search in subdirectories
        if not file_path.exists():
            # Check if file exists in any subdirectory
            for subdir in os.listdir(self.base_path):
                potential_path = self.base_path / subdir / file_id
                if potential_path.exists():
                    return str(potential_path.absolute())

            return None

        return str(file_path.absolute())
