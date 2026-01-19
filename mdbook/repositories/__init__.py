"""Repository layer for data access abstraction.

This module provides repository interfaces (protocols) and their implementations
for file system and configuration file operations.
"""

from mdbook.repositories.interfaces import IFileRepository, IConfigRepository
from mdbook.repositories.file_repository import FileRepository
from mdbook.repositories.config_repository import ConfigRepository

__all__ = [
    "IFileRepository",
    "IConfigRepository",
    "FileRepository",
    "ConfigRepository",
]
