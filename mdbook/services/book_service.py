"""Book service facade implementation.

Provides a simplified high-level interface for book operations by
delegating to reader and writer services.
"""

from pathlib import Path

from ..domain import Book, Chapter, Section
from .interfaces import IReaderService, IWriterService


class BookService:
    """Facade service for high-level book operations.

    Implements IBookService protocol by delegating to specialized
    reader and writer services. Provides a simplified interface
    for common book operations.
    """

    def __init__(
        self,
        reader: IReaderService,
        writer: IWriterService,
    ) -> None:
        """Initialize the book service with required dependencies.

        Args:
            reader: Service for reading book content.
            writer: Service for writing and modifying books.
        """
        self._reader = reader
        self._writer = writer

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
        return self._reader.load_book(root)

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
        book = self._reader.load_book(root)
        return self._reader.read_chapter(book, number)

    def list_chapters(self, root: Path) -> list[Chapter]:
        """List all chapters in a book.

        Args:
            root: Root directory of the book project.

        Returns:
            A list of Chapter objects in reading order.

        Raises:
            FileNotFoundError: If no book exists at root.
        """
        book = self._reader.load_book(root)
        return book.chapters

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
        return self._writer.init_book(root, title, author)

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
        book = self._reader.load_book(root)
        return self._writer.add_chapter(book, title, draft)

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
        book = self._reader.load_book(root)
        self._writer.update_toc(book, preserve_structure)

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
        return self._reader.list_sections(root, chapter_index)

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
        sections = self._reader.list_sections(root, chapter_index)
        return self._reader.get_section(sections, section_id)

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
        return self._writer.update_section(
            root, chapter_index, section_id, new_content, self._reader
        )

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
        return self._writer.add_note(
            root, chapter_index, section_id, note_text, self._reader
        )

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
        sections = self._reader.list_sections(root, chapter_index)
        notes = []
        for section in sections:
            for note in section.notes:
                notes.append(
                    {
                        "section_heading": section.heading,
                        "section_index": section.index,
                        "timestamp": note.timestamp.isoformat(),
                        "text": note.text,
                    }
                )
        return notes
