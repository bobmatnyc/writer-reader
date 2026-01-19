"""Book service facade implementation.

Provides a simplified high-level interface for book operations by
delegating to reader and writer services.
"""

from pathlib import Path

from ..domain import Book, Chapter
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

    def update_toc(self, root: Path) -> None:
        """Update the book's table of contents.

        Regenerates the TOC based on current chapters.

        Args:
            root: Root directory of the book project.

        Raises:
            FileNotFoundError: If no book exists at root.
            PermissionError: If unable to write the TOC.
        """
        book = self._reader.load_book(root)
        self._writer.update_toc(book)
