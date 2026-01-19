"""Service layer for book operations.

Provides service interfaces (protocols) and implementations for
structure detection, reading, writing, and high-level book management.
"""

from .interfaces import (
    IStructureService,
    IReaderService,
    IWriterService,
    IBookService,
)
from .book_service import BookService
from .reader_service import ReaderService
from .structure_service import StructureService
from .writer_service import WriterService

__all__ = [
    "IStructureService",
    "IReaderService",
    "IWriterService",
    "IBookService",
    "BookService",
    "ReaderService",
    "StructureService",
    "WriterService",
]
