"""Repository interface protocols.

Defines the contracts for repository implementations using Python's Protocol
for structural subtyping (duck typing with type hints).
"""

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IFileRepository(Protocol):
    """Protocol for file system operations.

    Provides an abstraction over file system access, enabling
    easier testing and potential alternative implementations
    (e.g., in-memory, remote storage).
    """

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
        ...

    def write_file(self, path: Path, content: str) -> None:
        """Write content to a file, creating it if it doesn't exist.

        Args:
            path: Path to the file to write.
            content: The string content to write.

        Raises:
            PermissionError: If write permission is denied.
            IsADirectoryError: If the path points to a directory.
        """
        ...

    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory matching a glob pattern.

        Args:
            directory: The directory to search in.
            pattern: Glob pattern for filtering files (default: "*").

        Returns:
            A list of Path objects for matching files.

        Raises:
            NotADirectoryError: If the path is not a directory.
        """
        ...

    def exists(self, path: Path) -> bool:
        """Check if a path exists.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        ...

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
        ...


@runtime_checkable
class IConfigRepository(Protocol):
    """Protocol for configuration file operations.

    Provides an abstraction for loading and saving configuration
    files in various formats (YAML, TOML).
    """

    def load_yaml(self, path: Path) -> dict[str, Any]:
        """Load and parse a YAML configuration file.

        Args:
            path: Path to the YAML file.

        Returns:
            A dictionary containing the parsed YAML data.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the YAML is invalid.
        """
        ...

    def load_toml(self, path: Path) -> dict[str, Any]:
        """Load and parse a TOML configuration file.

        Args:
            path: Path to the TOML file.

        Returns:
            A dictionary containing the parsed TOML data.

        Raises:
            FileNotFoundError: If the file does not exist.
            tomli.TOMLDecodeError: If the TOML is invalid.
        """
        ...

    def save_yaml(self, path: Path, data: dict[str, Any]) -> None:
        """Save data to a YAML configuration file.

        Args:
            path: Path to the YAML file to write.
            data: The dictionary data to serialize as YAML.

        Raises:
            PermissionError: If write permission is denied.
        """
        ...
