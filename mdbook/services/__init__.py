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
from .content_service import ContentService
from .render_service import RenderService
from .toc_service import TocService
from .index_service import IndexService
from .git_service import GitService

__all__ = [
    "IStructureService",
    "IReaderService",
    "IWriterService",
    "IBookService",
    "BookService",
    "ReaderService",
    "StructureService",
    "WriterService",
    "ContentService",
    "RenderService",
    "TocService",
    "IndexService",
    "GitService",
]
