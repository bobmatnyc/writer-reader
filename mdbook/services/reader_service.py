"""Reader service implementation.

Provides functionality to load books and read chapter content using
constructor injection for dependencies.
"""

import re
from datetime import datetime
from pathlib import Path

from ..domain import Book, BookMetadata, Chapter, FormatType, Note, Section
from ..repositories.interfaces import IFileRepository, IConfigRepository
from .interfaces import IStructureService


class ReaderService:
    """Service for reading book content.

    Implements IReaderService protocol using constructor injection
    for all dependencies, enabling easy testing and flexibility.
    """

    def __init__(
        self,
        file_repo: IFileRepository,
        config_repo: IConfigRepository,
        structure_service: IStructureService,
    ) -> None:
        """Initialize the reader service with required dependencies.

        Args:
            file_repo: Repository for file system operations.
            config_repo: Repository for configuration file operations.
            structure_service: Service for detecting format and parsing structure.
        """
        self._file_repo = file_repo
        self._config_repo = config_repo
        self._structure_service = structure_service

    def load_book(self, root: Path) -> Book:
        """Load a book from a directory.

        Detects the format, parses structure, and loads metadata
        to create a complete Book object.

        Args:
            root: Root directory of the book project.

        Returns:
            A fully populated Book object.

        Raises:
            FileNotFoundError: If the book directory doesn't exist.
            ValueError: If the book structure is invalid.
        """
        root = Path(root).resolve()

        if not root.exists():
            raise FileNotFoundError(f"Book directory not found: {root}")

        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")

        # Detect the book format
        format_type = self._structure_service.detect_format(root)

        # Parse chapters from the structure
        chapters = self._structure_service.parse_structure(root, format_type)

        # Load book metadata from config files
        metadata = self._load_metadata(root, format_type)

        return Book(
            root_path=root,
            metadata=metadata,
            chapters=chapters,
        )

    def read_chapter(self, book: Book, number: int) -> str:
        """Read the content of a specific chapter by number.

        Retrieves the chapter content and strips YAML frontmatter
        for clean display.

        Args:
            book: The Book object to read from.
            number: The chapter number (1-indexed for numbered chapters,
                    0 for intro chapters).

        Returns:
            The markdown content of the chapter with frontmatter stripped.

        Raises:
            KeyError: If no chapter with that number exists.
            FileNotFoundError: If the chapter file is missing.
        """
        chapter = book.get_chapter(number)

        if chapter is None:
            raise KeyError(f"Chapter {number} not found in book")

        content = self.get_chapter_content(chapter)

        # Strip YAML frontmatter from content
        return self._strip_frontmatter(content)

    def get_chapter_content(self, chapter: Chapter) -> str:
        """Read the raw content of a specific chapter.

        Args:
            chapter: The Chapter object to read.

        Returns:
            The full markdown content of the chapter including frontmatter.

        Raises:
            FileNotFoundError: If the chapter file doesn't exist.
        """
        if not self._file_repo.exists(chapter.file_path):
            raise FileNotFoundError(f"Chapter file not found: {chapter.file_path}")

        return self._file_repo.read_file(chapter.file_path)

    def _strip_frontmatter(self, content: str) -> str:
        """Strip YAML frontmatter from markdown content.

        Removes the YAML frontmatter block delimited by --- markers
        at the beginning of the content.

        Args:
            content: The full markdown content.

        Returns:
            Content with frontmatter removed.
        """
        if not content.startswith("---"):
            return content

        # Find the closing --- delimiter
        match = re.search(r"\n---\s*\n", content[3:])
        if match:
            # Return content after the frontmatter block
            return content[3 + match.end() :].lstrip()

        return content

    def _load_metadata(self, root: Path, format_type: FormatType) -> BookMetadata:
        """Load book metadata from configuration files.

        Attempts to load metadata from format-specific config files
        (book.toml, book.yaml, etc.) and falls back to directory name.

        Args:
            root: Root directory of the book.
            format_type: The detected book format.

        Returns:
            BookMetadata populated from config or defaults.
        """
        # Try mdBook format (book.toml)
        toml_path = root / "book.toml"
        if self._file_repo.exists(toml_path):
            return self._load_toml_metadata(toml_path)

        # Try YAML config (book.yaml or book.yml)
        for yaml_name in ["book.yaml", "book.yml"]:
            yaml_path = root / yaml_name
            if self._file_repo.exists(yaml_path):
                return self._load_yaml_metadata(yaml_path)

        # Try Leanpub format (Book.txt directory often has metadata)
        # Try Bookdown format (_bookdown.yml)
        bookdown_path = root / "_bookdown.yml"
        if self._file_repo.exists(bookdown_path):
            return self._load_yaml_metadata(bookdown_path)

        # Fall back to directory name as title
        title = self._format_title_from_path(root)
        return BookMetadata(title=title)

    def _load_toml_metadata(self, path: Path) -> BookMetadata:
        """Load metadata from a TOML config file.

        Args:
            path: Path to the TOML file.

        Returns:
            BookMetadata populated from TOML data.
        """
        try:
            data = self._config_repo.load_toml(path)
            book_section = data.get("book", {})

            return BookMetadata(
                title=book_section.get("title", path.parent.name),
                author=self._extract_author(book_section.get("authors", [])),
                description=book_section.get("description"),
                language=book_section.get("language", "en"),
            )
        except Exception:
            # Fall back to directory name if config parsing fails
            return BookMetadata(title=self._format_title_from_path(path.parent))

    def _load_yaml_metadata(self, path: Path) -> BookMetadata:
        """Load metadata from a YAML config file.

        Args:
            path: Path to the YAML file.

        Returns:
            BookMetadata populated from YAML data.
        """
        try:
            data = self._config_repo.load_yaml(path)

            return BookMetadata(
                title=data.get("title", path.parent.name),
                author=self._extract_author(data.get("author") or data.get("authors")),
                description=data.get("description"),
                language=data.get("language", "en"),
            )
        except Exception:
            # Fall back to directory name if config parsing fails
            return BookMetadata(title=self._format_title_from_path(path.parent))

    def _extract_author(self, author_data: str | list | None) -> str | None:
        """Extract author string from various config formats.

        Args:
            author_data: Author field from config (string or list).

        Returns:
            Author as a string, or None if not available.
        """
        if author_data is None:
            return None

        if isinstance(author_data, str):
            return author_data

        if isinstance(author_data, list) and author_data:
            # Join multiple authors
            return ", ".join(str(a) for a in author_data)

        return None

    def _format_title_from_path(self, path: Path) -> str:
        """Format a book title from a directory path.

        Converts directory name to a human-readable title by
        replacing separators and title-casing.

        Args:
            path: Path to format as title.

        Returns:
            Formatted title string.
        """
        name = path.name
        # Replace common separators with spaces
        name = name.replace("-", " ").replace("_", " ")
        # Title case
        return name.title()

    def parse_sections(self, content: str) -> list[Section]:
        """Parse markdown content into sections by ## headings.

        Splits content on level-2 headings (##) and creates Section objects.
        Content before the first ## heading becomes section 0 with empty heading.

        Args:
            content: The full markdown content of a chapter.

        Returns:
            A list of Section objects in document order.
        """
        lines = content.split("\n")
        sections: list[Section] = []
        current_lines: list[str] = []
        current_heading = ""
        current_start = 1
        section_index = 0

        for line_num, line in enumerate(lines, start=1):
            # Check for ## heading (but not ### or more)
            if line.startswith("## ") and not line.startswith("### "):
                # Save previous section if we have content
                if current_lines or section_index == 0:
                    section_content = "\n".join(current_lines)
                    notes = self._parse_notes(section_content)
                    sections.append(
                        Section(
                            heading=current_heading,
                            content=section_content,
                            start_line=current_start,
                            end_line=line_num,
                            index=section_index,
                            notes=notes,
                        )
                    )
                    section_index += 1

                # Start new section
                current_heading = line[3:].strip()
                current_start = line_num
                current_lines = [line]
            else:
                current_lines.append(line)

        # Don't forget the last section
        if current_lines or section_index == 0:
            section_content = "\n".join(current_lines)
            notes = self._parse_notes(section_content)
            sections.append(
                Section(
                    heading=current_heading,
                    content=section_content,
                    start_line=current_start,
                    end_line=len(lines) + 1,
                    index=section_index,
                    notes=notes,
                )
            )

        return sections

    def _parse_notes(self, content: str) -> list[Note]:
        """Parse notes from HTML comments in content.

        Notes have the format: <!-- NOTE: 2024-01-19T15:30:00 - Note text here -->

        Args:
            content: The content to parse for notes.

        Returns:
            A list of Note objects found in the content.
        """
        notes: list[Note] = []
        # Match <!-- NOTE: timestamp - text -->
        pattern = (
            r"<!--\s*NOTE:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*-\s*(.*?)\s*-->"
        )
        for match in re.finditer(pattern, content, re.DOTALL):
            try:
                timestamp = datetime.fromisoformat(match.group(1))
                text = match.group(2).strip()
                notes.append(Note(timestamp=timestamp, text=text))
            except ValueError:
                # Skip invalid timestamps
                continue
        return notes

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
        if isinstance(identifier, int):
            if 0 <= identifier < len(sections):
                return sections[identifier]
            return None

        # String identifier - case-insensitive partial match
        identifier_lower = identifier.lower()
        for section in sections:
            if identifier_lower in section.heading.lower():
                return section
        return None

    def list_sections(self, book_path: Path, chapter_index: int) -> list[Section]:
        """List all sections in a specific chapter.

        Args:
            book_path: Root directory of the book project.
            chapter_index: The chapter number (0 for intro, 1+ for chapters).

        Returns:
            A list of Section objects in the chapter.

        Raises:
            FileNotFoundError: If the book or chapter doesn't exist.
            KeyError: If no chapter with that index exists.
        """
        book = self.load_book(book_path)
        chapter = book.get_chapter(chapter_index)

        if chapter is None:
            raise KeyError(f"Chapter {chapter_index} not found in book")

        content = self.get_chapter_content(chapter)
        content = self._strip_frontmatter(content)
        return self.parse_sections(content)
