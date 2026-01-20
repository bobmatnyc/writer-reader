"""Domain layer for book representation."""

from .chapter import Chapter, ChapterMetadata
from .book import Book, BookMetadata
from .structure import FormatType
from .section import Section, Note

__all__ = [
    "Chapter",
    "ChapterMetadata",
    "Book",
    "BookMetadata",
    "FormatType",
    "Section",
    "Note",
]
