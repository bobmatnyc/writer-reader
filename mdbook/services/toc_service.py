"""TOC (Table of Contents) service implementation.

Provides functionality to extract hierarchical table of contents from
chapters and books, supporting multiple heading levels.
"""

import re

from ..domain import Book, Chapter
from ..domain.content import TocEntry, ChapterToc, BookToc
from .interfaces import IReaderService


class TocService:
    """Service for extracting and building table of contents.

    Extracts hierarchical TOC from markdown headings (##, ###, ####)
    and builds both chapter-level and book-level TOCs.
    """

    # Pattern for markdown headings
    HEADING_PATTERN = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)

    def __init__(self, reader_service: IReaderService) -> None:
        """Initialize the TOC service with required dependencies.

        Args:
            reader_service: Service for reading chapter content.
        """
        self._reader_service = reader_service

    def extract_chapter_toc(
        self, chapter: Chapter, content: str | None = None
    ) -> ChapterToc:
        """Extract TOC entries from a single chapter.

        Parses all ##, ###, and #### headings and builds a
        hierarchical structure.

        Args:
            chapter: The chapter to extract TOC from.
            content: Optional pre-loaded content.

        Returns:
            ChapterToc with hierarchical entries.
        """
        if content is None:
            content = self._reader_service.get_chapter_content(chapter)
            content = self._strip_frontmatter(content)

        entries = self._parse_headings(content)

        return ChapterToc(
            chapter_number=chapter.number,
            chapter_title=chapter.title,
            entries=entries,
        )

    def build_book_toc(self, book: Book) -> BookToc:
        """Build a complete TOC for the entire book.

        Extracts TOC from all chapters and combines them into
        a unified book-level TOC.

        Args:
            book: The book to build TOC for.

        Returns:
            BookToc with all chapter TOCs.
        """
        chapters: list[ChapterToc] = []

        for chapter in book.chapters:
            chapter_toc = self.extract_chapter_toc(chapter)
            chapters.append(chapter_toc)

        return BookToc(
            title=f"{book.metadata.title} - Table of Contents",
            chapters=chapters,
        )

    def expand_toc_marker(self, content: str) -> str:
        """Expand [TOC] markers in content with generated TOC.

        Replaces [TOC] markers with markdown TOC generated from
        the headings in the content.

        Args:
            content: The markdown content with [TOC] markers.

        Returns:
            Content with [TOC] replaced by actual TOC markdown.
        """
        if "[TOC]" not in content:
            return content

        entries = self._parse_headings(content)
        toc_md = self._entries_to_markdown(entries)

        return content.replace("[TOC]", toc_md)

    def _parse_headings(self, content: str) -> list[TocEntry]:
        """Parse headings from content into TOC entries.

        Args:
            content: The markdown content.

        Returns:
            List of TocEntry objects (flat, with level info).
        """
        entries: list[TocEntry] = []

        for match in self.HEADING_PATTERN.finditer(content):
            hashes = match.group(1)
            title = match.group(2).strip()

            # Level: ## = 1, ### = 2, #### = 3
            level = len(hashes) - 1

            # Generate anchor
            anchor = self._slugify(title)

            entries.append(
                TocEntry(
                    title=title,
                    level=level,
                    anchor=anchor,
                )
            )

        # Build hierarchy
        return self._build_hierarchy(entries)

    def _build_hierarchy(self, entries: list[TocEntry]) -> list[TocEntry]:
        """Build hierarchical structure from flat entries.

        Nests entries based on their level, with lower-level entries
        becoming children of higher-level ones.

        Args:
            entries: Flat list of TocEntry objects with level info.

        Returns:
            Hierarchical list with children populated.
        """
        if not entries:
            return []

        # Simple approach: return flat list with level info preserved
        # More complex nesting can be added if needed
        result: list[TocEntry] = []
        stack: list[TocEntry] = []

        for entry in entries:
            # Find parent at lower level
            while stack and stack[-1].level >= entry.level:
                stack.pop()

            if stack:
                # Add as child of parent
                stack[-1].children.append(entry)
            else:
                # Top-level entry
                result.append(entry)

            stack.append(entry)

        return result

    def _entries_to_markdown(self, entries: list[TocEntry], indent: int = 0) -> str:
        """Convert TOC entries to markdown list.

        Args:
            entries: List of TocEntry objects.
            indent: Current indentation level.

        Returns:
            Markdown formatted TOC string.
        """
        lines: list[str] = []

        for entry in entries:
            prefix = "  " * indent
            lines.append(f"{prefix}- [{entry.title}](#{entry.anchor})")

            if entry.children:
                child_md = self._entries_to_markdown(entry.children, indent + 1)
                lines.append(child_md)

        return "\n".join(lines)

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

    def generate_toc_markdown(
        self, book: Book, include_chapter_tocs: bool = True
    ) -> str:
        """Generate markdown TOC for the entire book.

        Args:
            book: The book to generate TOC for.
            include_chapter_tocs: If True, include intra-chapter headings.

        Returns:
            Markdown formatted TOC string.
        """
        book_toc = self.build_book_toc(book)

        lines = [f"# {book.metadata.title}", "", "## Table of Contents", ""]

        for chapter_toc in book_toc.chapters:
            prefix = (
                "Intro"
                if chapter_toc.chapter_number == 0
                else f"{chapter_toc.chapter_number}"
            )
            chapter_anchor = self._slugify(chapter_toc.chapter_title)
            lines.append(
                f"- [{prefix}. {chapter_toc.chapter_title}](#{chapter_anchor})"
            )

            if include_chapter_tocs:
                for entry in chapter_toc.entries:
                    lines.append(f"  - [{entry.title}](#{entry.anchor})")

        return "\n".join(lines)
