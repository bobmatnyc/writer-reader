"""Configuration repository implementation.

Provides concrete configuration file operations using pyyaml and tomli/tomllib.
"""

import sys
from pathlib import Path
from typing import Any

# Python 3.11+ has tomllib built-in, older versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import yaml


class ConfigRepository:
    """Configuration file repository using pyyaml and tomli.

    Implements IConfigRepository protocol for loading and saving
    configuration files in YAML and TOML formats.
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        """Initialize the configuration repository.

        Args:
            encoding: Default text encoding for file operations.
        """
        self._encoding = encoding

    def load_yaml(self, path: Path) -> dict[str, Any]:
        """Load and parse a YAML configuration file.

        Uses safe_load to prevent arbitrary code execution.

        Args:
            path: Path to the YAML file.

        Returns:
            A dictionary containing the parsed YAML data.
            Returns an empty dict if the file is empty.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the YAML is invalid.
        """
        with open(path, "r", encoding=self._encoding) as f:
            data = yaml.safe_load(f)
            # safe_load returns None for empty files
            return data if data is not None else {}

    def load_toml(self, path: Path) -> dict[str, Any]:
        """Load and parse a TOML configuration file.

        Args:
            path: Path to the TOML file.

        Returns:
            A dictionary containing the parsed TOML data.

        Raises:
            FileNotFoundError: If the file does not exist.
            tomllib.TOMLDecodeError: If the TOML is invalid.
        """
        with open(path, "rb") as f:
            return tomllib.load(f)

    def save_yaml(self, path: Path, data: dict[str, Any]) -> None:
        """Save data to a YAML configuration file.

        Uses default_flow_style=False for human-readable output.
        Creates parent directories if they don't exist.

        Args:
            path: Path to the YAML file to write.
            data: The dictionary data to serialize as YAML.

        Raises:
            PermissionError: If write permission is denied.
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding=self._encoding) as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
