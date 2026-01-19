"""File repository implementation using pathlib.

Provides concrete file system operations through Python's pathlib module.
"""

from pathlib import Path


class FileRepository:
    """File system repository using pathlib.

    Implements IFileRepository protocol for standard file system operations.
    All operations use pathlib.Path for cross-platform compatibility.
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        """Initialize the file repository.

        Args:
            encoding: Default text encoding for read/write operations.
        """
        self._encoding = encoding

    def read_file(self, path: Path) -> str:
        """Read and return the contents of a file as a string.

        Args:
            path: Path to the file to read.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If read permission is denied.
        """
        return path.read_text(encoding=self._encoding)

    def write_file(self, path: Path, content: str) -> None:
        """Write content to a file, creating it if it doesn't exist.

        Creates parent directories if they don't exist.

        Args:
            path: Path to the file to write.
            content: The string content to write.

        Raises:
            PermissionError: If write permission is denied.
            IsADirectoryError: If the path points to a directory.
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=self._encoding)

    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory matching a glob pattern.

        Args:
            directory: The directory to search in.
            pattern: Glob pattern for filtering files (default: "*").
                     Use "**/*" for recursive matching.

        Returns:
            A sorted list of Path objects for matching files (files only).

        Raises:
            NotADirectoryError: If the path is not a directory.
        """
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        # Use glob and filter to only include files
        matches = [p for p in directory.glob(pattern) if p.is_file()]
        return sorted(matches)

    def exists(self, path: Path) -> bool:
        """Check if a path exists.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        return path.exists()

    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Create a directory.

        Args:
            path: The directory path to create.
            parents: If True, create parent directories as needed.
            exist_ok: If True, don't raise an error if directory exists.

        Raises:
            FileExistsError: If exist_ok is False and directory exists.
            PermissionError: If permission is denied.
        """
        path.mkdir(parents=parents, exist_ok=exist_ok)
