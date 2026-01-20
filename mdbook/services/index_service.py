"""Index service implementation.

Provides functionality to extract indexable terms from chapters and
build a complete book index with alphabetical ordering.
"""

import re
from collections import defaultdict

from ..domain import Book, Chapter
from ..domain.content import IndexTerm, IndexEntry, BookIndex
from .interfaces import IReaderService


class IndexService:
    """Service for building book indices.

    Extracts indexable terms from chapters using explicit markers
    and builds an alphabetically sorted index.
    """

    # Pattern for explicit index markers: {{index: term}}
    INDEX_MARKER_PATTERN = re.compile(r"\{\{index:\s*([^}]+)\}\}")

    # Pattern for headings (for context)
    HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

    def __init__(self, reader_service: IReaderService) -> None:
        """Initialize the index service with required dependencies.

        Args:
            reader_service: Service for reading chapter content.
        """
        self._reader_service = reader_service

    def extract_terms(
        self, chapter: Chapter, content: str | None = None
    ) -> list[IndexTerm]:
        """Extract indexable terms from a chapter.

        Finds all {{index: term}} markers and extracts terms
        with their location context.

        Args:
            chapter: The chapter to extract terms from.
            content: Optional pre-loaded content.

        Returns:
            List of IndexTerm objects found in the chapter.
        """
        if content is None:
            content = self._reader_service.get_chapter_content(chapter)
            content = self._strip_frontmatter(content)

        terms: list[IndexTerm] = []
        lines = content.split("\n")

        current_section = ""
        current_anchor = ""

        for line_num, line in enumerate(lines, start=1):
            # Track current section heading
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                current_section = heading_match.group(2).strip()
                current_anchor = self._slugify(current_section)

            # Find index markers
            for match in self.INDEX_MARKER_PATTERN.finditer(line):
                term = match.group(1).strip()

                terms.append(
                    IndexTerm(
                        term=term,
                        chapter_number=chapter.number,
                        chapter_title=chapter.title,
                        section_heading=current_section,
                        anchor=current_anchor,
                    )
                )

        return terms

    def build_index(self, book: Book) -> BookIndex:
        """Build a complete index for the entire book.

        Extracts terms from all chapters and consolidates them
        into a single alphabetically sorted index.

        Args:
            book: The book to build index for.

        Returns:
            BookIndex with consolidated, sorted entries.
        """
        # Collect all terms by term text
        terms_by_text: dict[str, list[IndexTerm]] = defaultdict(list)

        for chapter in book.chapters:
            chapter_terms = self.extract_terms(chapter)
            for term in chapter_terms:
                terms_by_text[term.term].append(term)

        # Build index entries
        entries: list[IndexEntry] = []
        for term_text, locations in terms_by_text.items():
            entries.append(
                IndexEntry(
                    term=term_text,
                    locations=locations,
                )
            )

        # Sort alphabetically
        entries.sort(key=lambda e: e.sort_key)

        return BookIndex(entries=entries)

    def generate_index_markdown(self, book: Book) -> str:
        """Generate markdown index for the book.

        Args:
            book: The book to generate index for.

        Returns:
            Markdown formatted index string.
        """
        index = self.build_index(book)
        return index.to_markdown()

    def strip_index_markers(self, content: str) -> str:
        """Remove index markers from content for rendering.

        Removes {{index: term}} markers while preserving
        the rest of the content.

        Args:
            content: The markdown content with markers.

        Returns:
            Content with markers removed.
        """
        return self.INDEX_MARKER_PATTERN.sub("", content)

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug.

        Args:
            text: The heading text.

        Returns:
            URL-friendly anchor string.
        """
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text.strip("-")

    def _strip_frontmatter(self, content: str) -> str:
        """Strip YAML frontmatter from content.

        Args:
            content: The markdown content.

        Returns:
            Content with frontmatter removed.
        """
        if not content.startswith("---"):
            return content

        match = re.search(r"\n---\s*\n", content[3:])
        if match:
            return content[3 + match.end() :].lstrip()
        return content
