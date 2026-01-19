"""Domain layer for book representation."""

from .chapter import Chapter, ChapterMetadata
from .book import Book, BookMetadata
from .structure import FormatType

__all__ = [
    "Chapter",
    "ChapterMetadata",
    "Book",
    "BookMetadata",
    "FormatType",
]
