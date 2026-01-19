# mdbook - Book reader infrastructure
"""MD Book Tools - A library for reading and writing markdown books.

This package provides:
- Domain models for books and chapters
- Repository abstractions for file system and configuration
- Services for structure detection, reading, and writing
- Dependency injection infrastructure
- CLI entry point for command-line usage
"""

from .cli import cli, main

__all__ = ["cli", "main"]
