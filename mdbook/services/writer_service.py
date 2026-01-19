"""Writer service implementation.

Provides functionality to initialize books, add chapters, and update
the table of contents using constructor injection for dependencies.
"""

import re
from datetime import date
from pathlib import Path

from ..domain import Book, BookMetadata, Chapter, ChapterMetadata
from ..repositories.interfaces import IConfigRepository, IFileRepository
from .interfaces import IStructureService


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: The text to convert.

    Returns:
        A lowercase, hyphen-separated slug.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class WriterService:
    """Service for writing and modifying books.

    Implements IWriterService protocol using constructor injection
    for all dependencies, enabling easy testing and flexibility.
    """

    def __init__(
        self,
        file_repo: IFileRepository,
        config_repo: IConfigRepository,
        structure_service: IStructureService,
    ) -> None:
        """Initialize the writer service with required dependencies.

        Args:
            file_repo: Repository for file system operations.
            config_repo: Repository for configuration file operations.
            structure_service: Service for detecting format and parsing structure.
        """
        self._file_repo = file_repo
        self._config_repo = config_repo
        self._structure_service = structure_service

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
        root = Path(root).resolve()

        # Check if book already exists
        book_yaml_path = root / "book.yaml"
        if self._file_repo.exists(book_yaml_path):
            raise FileExistsError(f"Book already exists at {root}")

        # Create directories
        chapters_dir = root / "chapters"
        self._file_repo.mkdir(root, parents=True, exist_ok=True)
        self._file_repo.mkdir(chapters_dir, parents=True, exist_ok=True)

        # Create book.yaml configuration
        today = date.today()
        book_config = {
            "title": title,
            "author": author,
            "description": "",
            "language": "en",
            "created": today.isoformat(),
        }
        self._config_repo.save_yaml(book_yaml_path, book_config)

        # Create empty SUMMARY.md
        summary_path = root / "SUMMARY.md"
        summary_content = f"# {title}\n\n"
        self._file_repo.write_file(summary_path, summary_content)

        # Build and return Book object
        metadata = BookMetadata(
            title=title,
            author=author,
            description="",
            language="en",
            created=today,
        )

        return Book(
            root_path=root,
            metadata=metadata,
            chapters=[],
        )

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
        chapters_dir = book.root_path / "chapters"

        # Ensure chapters directory exists
        if not self._file_repo.exists(chapters_dir):
            self._file_repo.mkdir(chapters_dir, parents=True, exist_ok=True)

        # Calculate next chapter number
        chapter_num = self._get_next_chapter_number(chapters_dir)

        # Create filename from title
        slug = _slugify(title)
        filename = f"{chapter_num:02d}-{slug}.md"
        chapter_path = chapters_dir / filename

        # Create frontmatter
        today = date.today()
        frontmatter = {
            "title": title,
            "chapter": chapter_num,
            "date": today.isoformat(),
        }
        if draft:
            frontmatter["draft"] = True

        # Build chapter content with frontmatter
        frontmatter_lines = ["---"]
        frontmatter_lines.append(f"title: {title}")
        frontmatter_lines.append(f"chapter: {chapter_num}")
        frontmatter_lines.append(f"date: {today.isoformat()}")
        if draft:
            frontmatter_lines.append("draft: true")
        frontmatter_lines.append("---")
        frontmatter_lines.append("")
        frontmatter_lines.append(f"# {title}")
        frontmatter_lines.append("")

        content = "\n".join(frontmatter_lines)
        self._file_repo.write_file(chapter_path, content)

        # Create Chapter object
        chapter_metadata = ChapterMetadata(
            title=title,
            number=chapter_num,
            date=today,
            draft=draft,
        )
        chapter = Chapter(
            file_path=chapter_path,
            metadata=chapter_metadata,
            is_intro=False,
        )

        # Add to book's chapter list
        book.chapters.append(chapter)

        # Update table of contents
        self.update_toc(book)

        return chapter

    def update_toc(self, book: Book) -> None:
        """Update the book's table of contents.

        Regenerates the SUMMARY.md file based on the
        current chapter list in the book.

        Args:
            book: The Book whose TOC should be updated.

        Raises:
            PermissionError: If unable to write the TOC file.
        """
        chapters_dir = book.root_path / "chapters"

        # If we have no chapters in the book object, scan the directory
        if not book.chapters and self._file_repo.exists(chapters_dir):
            # Use structure service to parse existing chapters
            from ..domain import FormatType

            book.chapters = self._structure_service.parse_structure(
                book.root_path, FormatType.GITBOOK
            )

        # Generate SUMMARY.md content
        summary_lines = [f"# {book.metadata.title}", ""]

        # Sort chapters by number
        sorted_chapters = sorted(
            book.chapters,
            key=lambda c: (0 if c.is_intro else 1, c.number or 0),
        )

        for chapter in sorted_chapters:
            # Calculate relative path from book root to chapter file
            try:
                rel_path = chapter.file_path.relative_to(book.root_path)
            except ValueError:
                # File is not under book root, use just the name
                rel_path = Path("chapters") / chapter.file_path.name

            prefix = "- " if not chapter.metadata.draft else "- [DRAFT] "
            summary_lines.append(f"{prefix}[{chapter.title}]({rel_path})")

        summary_lines.append("")  # Trailing newline
        summary_content = "\n".join(summary_lines)

        summary_path = book.root_path / "SUMMARY.md"
        self._file_repo.write_file(summary_path, summary_content)

    def _get_next_chapter_number(self, chapters_dir: Path) -> int:
        """Find the next available chapter number.

        Args:
            chapters_dir: Path to the chapters directory.

        Returns:
            The next sequential chapter number.
        """
        if not self._file_repo.exists(chapters_dir):
            return 1

        max_num = 0
        try:
            files = self._file_repo.list_files(chapters_dir, "*.md")
            for file_path in files:
                match = re.match(r"^(\d+)", file_path.stem)
                if match:
                    max_num = max(max_num, int(match.group(1)))
        except Exception:
            # If listing fails, start at 1
            pass

        return max_num + 1
