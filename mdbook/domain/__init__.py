"""Domain layer for book representation."""

from .chapter import Chapter, ChapterMetadata
from .book import Book, BookMetadata
from .structure import FormatType
from .section import Section, Note
from .content import (
    TocEntry,
    ChapterToc,
    BookToc,
    ImageRef,
    MermaidBlock,
    IndexTerm,
    IndexEntry,
    BookIndex,
)

__all__ = [
    "Chapter",
    "ChapterMetadata",
    "Book",
    "BookMetadata",
    "FormatType",
    "Section",
    "Note",
    "TocEntry",
    "ChapterToc",
    "BookToc",
    "ImageRef",
    "MermaidBlock",
    "IndexTerm",
    "IndexEntry",
    "BookIndex",
]
