"""Service interface protocols.

Defines the contracts for service implementations using Python's Protocol
for structural subtyping (duck typing with type hints).
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..domain import Book, Chapter, ChapterMetadata, FormatType, Section


@runtime_checkable
class IStructureService(Protocol):
    """Protocol for book structure detection and parsing.

    Provides functionality to detect book formats, parse table of contents,
    and extract chapter metadata from frontmatter.
    """

    def detect_format(self, root: Path) -> FormatType:
        """Detect the book format type from directory structure.

        Examines the directory for format-specific files and conventions
        to determine the book format (mdBook, GitBook, Leanpub, etc.).

        Args:
            root: Root directory of the book project.

        Returns:
            The detected FormatType, or FormatType.AUTO if unable to determine.

        Raises:
            NotADirectoryError: If root is not a directory.
        """
        ...

    def parse_structure(self, root: Path, format: FormatType) -> list[Chapter]:
        """Parse the book structure and return ordered chapters.

        Reads the table of contents or directory structure to build
        a list of chapters with their metadata and file paths.

        Args:
            root: Root directory of the book project.
            format: The book format type to use for parsing.

        Returns:
            A list of Chapter objects in reading order.

        Raises:
            FileNotFoundError: If required structure files are missing.
            ValueError: If the structure cannot be parsed.
        """
        ...

    def parse_frontmatter(self, content: str) -> ChapterMetadata:
        """Parse YAML frontmatter from chapter content.

        Extracts metadata from the YAML frontmatter block at the
        beginning of a markdown file (between --- delimiters).

        Args:
            content: The full markdown content of a chapter.

        Returns:
            ChapterMetadata populated from frontmatter, or defaults
            if no frontmatter is present.

        Raises:
            ValueError: If frontmatter is malformed.
        """
        ...


@runtime_checkable
class IReaderService(Protocol):
    """Protocol for reading book content.

    Provides functionality to load books and read chapter content.
    """

    def load_book(self, root: Path) -> Book:
        """Load a book from a directory.

        Detects the format, parses structure, and loads metadata
        to create a complete Book object.

        Args:
            root: Root directory of the book project.

        Returns:
            A fully populated Book object.

        Raises:
            FileNotFoundError: If the book directory or config doesn't exist.
            ValueError: If the book structure is invalid.
        """
        ...

    def read_chapter(self, book: Book, number: int) -> str:
        """Read the content of a specific chapter by number.

        Args:
            book: The Book object to read from.
            number: The chapter number (1-indexed for numbered chapters).

        Returns:
            The full markdown content of the chapter.

        Raises:
            KeyError: If no chapter with that number exists.
            FileNotFoundError: If the chapter file is missing.
        """
        ...

    def get_chapter_content(self, chapter: Chapter) -> str:
        """Read the content of a specific chapter.

        Args:
            chapter: The Chapter object to read.

        Returns:
            The full markdown content of the chapter.

        Raises:
            FileNotFoundError: If the chapter file doesn't exist.
        """
        ...

    def parse_sections(self, content: str) -> list[Section]:
        """Parse markdown content into sections by ## headings.

        Args:
            content: The full markdown content of a chapter.

        Returns:
            A list of Section objects in document order.
        """
        ...

    def get_section(
        self, sections: list[Section], identifier: str | int
    ) -> Section | None:
        """Get a section by heading or index.

        Args:
            sections: List of Section objects to search.
            identifier: Either an integer index (0-based) or a string
                for case-insensitive partial match on heading.

        Returns:
            The matching Section, or None if not found.
        """
        ...

    def list_sections(self, book_path: Path, chapter_index: int) -> list[Section]:
        """List all sections in a specific chapter.

        Args:
            book_path: Root directory of the book project.
            chapter_index: The chapter number.

        Returns:
            A list of Section objects in the chapter.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If no chapter with that index exists.
        """
        ...


@runtime_checkable
class IWriterService(Protocol):
    """Protocol for writing and modifying books.

    Provides functionality to initialize books, add chapters,
    and update the table of contents.
    """

    def init_book(self, root: Path, title: str, author: str) -> Book:
        """Initialize a new book project.

        Creates the directory structure, configuration files,
        and initial content for a new book.

        Args:
            root: Root directory for the new book project.
            title: The book title.
            author: The book author.

        Returns:
            A Book object representing the newly created book.

        Raises:
            FileExistsError: If a book already exists at root.
            PermissionError: If unable to create directories/files.
        """
        ...

    def add_chapter(self, book: Book, title: str, draft: bool = False) -> Chapter:
        """Add a new chapter to an existing book.

        Creates the chapter file with appropriate frontmatter
        and updates the book's table of contents.

        Args:
            book: The Book to add the chapter to.
            title: The title for the new chapter.
            draft: If True, mark the chapter as a draft.

        Returns:
            The newly created Chapter object.

        Raises:
            PermissionError: If unable to create the chapter file.
        """
        ...

    def update_toc(self, book: Book, preserve_structure: bool = True) -> None:
        """Update the book's table of contents.

        When preserve_structure=True (default), preserves existing hierarchy
        in SUMMARY.md (Part headers, nesting levels) and only adds new files.
        When preserve_structure=False, regenerates flat structure.

        Args:
            book: The Book whose TOC should be updated.
            preserve_structure: If True, preserve existing SUMMARY.md hierarchy
                and only add new files. If False, generate flat structure.

        Raises:
            PermissionError: If unable to write the TOC file.
        """
        ...

    def update_section(
        self,
        book_path: Path,
        chapter_index: int,
        section_id: str | int,
        new_content: str,
        reader_service: "IReaderService",
    ) -> dict:
        """Replace section content while preserving heading.

        Args:
            book_path: Root directory of the book project.
            chapter_index: The chapter number.
            section_id: Section identifier (index or heading match).
            new_content: The new content for the section body.
            reader_service: ReaderService for parsing sections.

        Returns:
            Dictionary with success status and section info.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If the chapter or section is not found.
        """
        ...

    def add_note(
        self,
        book_path: Path,
        chapter_index: int,
        section_id: str | int,
        note_text: str,
        reader_service: "IReaderService",
    ) -> dict:
        """Add a timestamped note to a section.

        Args:
            book_path: Root directory of the book project.
            chapter_index: The chapter number.
            section_id: Section identifier (index or heading match).
            note_text: The text of the note to add.
            reader_service: ReaderService for parsing sections.

        Returns:
            Dictionary with success status and note info.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If the chapter or section is not found.
        """
        ...


@runtime_checkable
class IBookService(Protocol):
    """Facade protocol for high-level book operations.

    Provides a simplified interface that combines structure detection,
    reading, and writing operations for common use cases.
    """

    def get_book_info(self, root: Path) -> Book:
        """Get information about a book.

        Loads and returns the book with all its metadata and chapters.

        Args:
            root: Root directory of the book project.

        Returns:
            A fully populated Book object.

        Raises:
            FileNotFoundError: If no book exists at root.
            ValueError: If the book structure is invalid.
        """
        ...

    def read_chapter(self, root: Path, number: int) -> str:
        """Read the content of a specific chapter.

        Args:
            root: Root directory of the book project.
            number: The chapter number to read.

        Returns:
            The full markdown content of the chapter.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If no chapter with that number exists.
        """
        ...

    def list_chapters(self, root: Path) -> list[Chapter]:
        """List all chapters in a book.

        Args:
            root: Root directory of the book project.

        Returns:
            A list of Chapter objects in reading order.

        Raises:
            FileNotFoundError: If no book exists at root.
        """
        ...

    def create_book(self, root: Path, title: str, author: str) -> Book:
        """Create a new book project.

        Initializes the directory structure and configuration
        for a new book.

        Args:
            root: Root directory for the new book.
            title: The book title.
            author: The book author.

        Returns:
            A Book object representing the new book.

        Raises:
            FileExistsError: If a book already exists at root.
            PermissionError: If unable to create the book.
        """
        ...

    def add_chapter(self, root: Path, title: str, draft: bool = False) -> Chapter:
        """Add a new chapter to a book.

        Args:
            root: Root directory of the book project.
            title: The title for the new chapter.
            draft: If True, mark the chapter as a draft.

        Returns:
            The newly created Chapter object.

        Raises:
            FileNotFoundError: If no book exists at root.
            PermissionError: If unable to create the chapter.
        """
        ...

    def update_toc(self, root: Path, preserve_structure: bool = True) -> None:
        """Update the book's table of contents.

        When preserve_structure=True (default), preserves existing hierarchy
        in SUMMARY.md (Part headers, nesting levels) and only adds new files.
        When preserve_structure=False, regenerates flat structure.

        Args:
            root: Root directory of the book project.
            preserve_structure: If True, preserve existing SUMMARY.md hierarchy
                and only add new files. If False, generate flat structure.

        Raises:
            FileNotFoundError: If no book exists at root.
            PermissionError: If unable to write the TOC.
        """
        ...

    def list_sections(self, root: Path, chapter_index: int) -> list[Section]:
        """List all sections in a specific chapter.

        Args:
            root: Root directory of the book project.
            chapter_index: The chapter number.

        Returns:
            A list of Section objects in the chapter.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If no chapter with that index exists.
        """
        ...

    def read_section(
        self, root: Path, chapter_index: int, section_id: str | int
    ) -> Section | None:
        """Get a section by heading or index.

        Args:
            root: Root directory of the book project.
            chapter_index: The chapter number.
            section_id: Section identifier (index or heading match).

        Returns:
            The matching Section, or None if not found.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If no chapter with that index exists.
        """
        ...

    def update_section(
        self,
        root: Path,
        chapter_index: int,
        section_id: str | int,
        new_content: str,
    ) -> dict:
        """Replace section content while preserving heading.

        Args:
            root: Root directory of the book project.
            chapter_index: The chapter number.
            section_id: Section identifier (index or heading match).
            new_content: The new content for the section body.

        Returns:
            Dictionary with success status and section info.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If the chapter or section is not found.
        """
        ...

    def add_note(
        self,
        root: Path,
        chapter_index: int,
        section_id: str | int,
        note_text: str,
    ) -> dict:
        """Add a timestamped note to a section.

        Args:
            root: Root directory of the book project.
            chapter_index: The chapter number.
            section_id: Section identifier (index or heading match).
            note_text: The text of the note to add.

        Returns:
            Dictionary with success status and note info.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If the chapter or section is not found.
        """
        ...

    def list_notes(self, root: Path, chapter_index: int) -> list[dict]:
        """List all notes in a chapter.

        Args:
            root: Root directory of the book project.
            chapter_index: The chapter number.

        Returns:
            A list of note dictionaries with section info.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If no chapter with that index exists.
        """
        ...
