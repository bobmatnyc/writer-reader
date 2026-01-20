"""Writer service implementation.

Provides functionality to initialize books, add chapters, and update
the table of contents using constructor injection for dependencies.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .reader_service import ReaderService

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
        chapters_dir = book.root_path / "chapters"
        summary_path = book.root_path / "SUMMARY.md"

        # If we have no chapters in the book object, scan the directory
        if not book.chapters and self._file_repo.exists(chapters_dir):
            from ..domain import FormatType

            book.chapters = self._structure_service.parse_structure(
                book.root_path, FormatType.GITBOOK
            )

        # If preserve_structure and SUMMARY.md exists, merge new files into existing
        if preserve_structure and self._file_repo.exists(summary_path):
            summary_content = self._merge_new_chapters_into_toc(book, summary_path)
        else:
            summary_content = self._generate_flat_toc(book)

        self._file_repo.write_file(summary_path, summary_content)

    def _parse_existing_toc(self, summary_path: Path) -> tuple[list[str], set[str]]:
        """Parse existing SUMMARY.md and extract structure and file paths.

        Args:
            summary_path: Path to the SUMMARY.md file.

        Returns:
            Tuple of (lines as list, set of relative file paths already in TOC).
        """
        content = self._file_repo.read_file(summary_path)
        lines = content.split("\n")

        # Extract all file paths from existing TOC
        existing_paths: set[str] = set()
        link_pattern = re.compile(r"\[.*?\]\(([^)]+)\)")

        for line in lines:
            match = link_pattern.search(line)
            if match:
                path = match.group(1)
                existing_paths.add(path)

        return lines, existing_paths

    def _merge_new_chapters_into_toc(self, book: Book, summary_path: Path) -> str:
        """Merge new chapters into existing SUMMARY.md preserving structure.

        Only adds chapters that are not already present in the TOC.

        Args:
            book: The Book with chapters to check.
            summary_path: Path to the existing SUMMARY.md.

        Returns:
            The updated SUMMARY.md content.
        """
        lines, existing_paths = self._parse_existing_toc(summary_path)

        # Find chapters that are not in the existing TOC
        new_chapters = []
        for chapter in book.chapters:
            try:
                rel_path = str(chapter.file_path.relative_to(book.root_path))
            except ValueError:
                rel_path = str(Path("chapters") / chapter.file_path.name)

            if rel_path not in existing_paths:
                new_chapters.append((chapter, rel_path))

        # If no new chapters, return existing content unchanged
        if not new_chapters:
            return "\n".join(lines)

        # Sort new chapters by number
        new_chapters.sort(key=lambda x: (0 if x[0].is_intro else 1, x[0].number or 0))

        # Append new chapters at the end, before any trailing empty lines
        # Find the position to insert (before trailing empty lines)
        insert_pos = len(lines)
        while insert_pos > 0 and lines[insert_pos - 1].strip() == "":
            insert_pos -= 1

        new_lines = []
        for chapter, rel_path in new_chapters:
            prefix = "- " if not chapter.metadata.draft else "- [DRAFT] "
            new_lines.append(f"{prefix}[{chapter.title}]({rel_path})")

        # Insert new chapters
        result_lines = lines[:insert_pos] + new_lines + [""]

        return "\n".join(result_lines)

    def _generate_flat_toc(self, book: Book) -> str:
        """Generate a flat SUMMARY.md structure.

        Args:
            book: The Book with chapters.

        Returns:
            The SUMMARY.md content as a string.
        """
        summary_lines = [f"# {book.metadata.title}", ""]

        # Sort chapters by number
        sorted_chapters = sorted(
            book.chapters,
            key=lambda c: (0 if c.is_intro else 1, c.number or 0),
        )

        for chapter in sorted_chapters:
            try:
                rel_path = chapter.file_path.relative_to(book.root_path)
            except ValueError:
                rel_path = Path("chapters") / chapter.file_path.name

            prefix = "- " if not chapter.metadata.draft else "- [DRAFT] "
            summary_lines.append(f"{prefix}[{chapter.title}]({rel_path})")

        summary_lines.append("")  # Trailing newline
        return "\n".join(summary_lines)

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

    def update_section(
        self,
        book_path: Path,
        chapter_index: int,
        section_id: str | int,
        new_content: str,
        reader_service: "ReaderService",
    ) -> dict:
        """Replace section content while preserving heading.

        Updates the content of a specific section within a chapter.
        The heading line is preserved; only the body content changes.

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
        book = reader_service.load_book(book_path)
        chapter = book.get_chapter(chapter_index)

        if chapter is None:
            raise KeyError(f"Chapter {chapter_index} not found in book")

        # Read and parse the chapter content
        full_content = self._file_repo.read_file(chapter.file_path)
        content_without_frontmatter = reader_service._strip_frontmatter(full_content)
        sections = reader_service.parse_sections(content_without_frontmatter)

        # Find the section
        section = reader_service.get_section(sections, section_id)
        if section is None:
            raise KeyError(
                f"Section '{section_id}' not found in chapter {chapter_index}"
            )

        # Build the updated section content
        if section.heading:
            updated_section = f"## {section.heading}\n\n{new_content.strip()}"
        else:
            # Section without heading (content before first ##)
            updated_section = new_content.strip()

        # Reconstruct the chapter content
        # Split by frontmatter boundary
        frontmatter = ""
        if full_content.startswith("---"):
            match = re.search(r"\n---\s*\n", full_content[3:])
            if match:
                frontmatter = full_content[: 3 + match.end()]

        # Rebuild content with updated section
        new_sections_content = []
        for s in sections:
            if s.index == section.index:
                new_sections_content.append(updated_section)
            else:
                new_sections_content.append(s.content)

        # Join sections - add blank line between sections with headings
        result_parts = []
        for i, content in enumerate(new_sections_content):
            if i > 0 and sections[i].heading:
                result_parts.append("\n")
            result_parts.append(content)

        new_chapter_content = frontmatter + "\n".join(result_parts)

        # Write back to file
        self._file_repo.write_file(chapter.file_path, new_chapter_content)

        # Re-parse to get updated line numbers
        updated_content = reader_service._strip_frontmatter(new_chapter_content)
        updated_sections = reader_service.parse_sections(updated_content)
        updated_section_obj = reader_service.get_section(
            updated_sections, section.index
        )

        return {
            "success": True,
            "heading": section.heading,
            "start_line": updated_section_obj.start_line if updated_section_obj else 0,
            "end_line": updated_section_obj.end_line if updated_section_obj else 0,
        }

    def add_note(
        self,
        book_path: Path,
        chapter_index: int,
        section_id: str | int,
        note_text: str,
        reader_service: "ReaderService",
    ) -> dict:
        """Add a timestamped note to a section.

        Notes are stored as HTML comments at the end of the section.
        Format: <!-- NOTE: 2024-01-19T15:30:00 - Note text here -->

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
        book = reader_service.load_book(book_path)
        chapter = book.get_chapter(chapter_index)

        if chapter is None:
            raise KeyError(f"Chapter {chapter_index} not found in book")

        # Read and parse the chapter content
        full_content = self._file_repo.read_file(chapter.file_path)
        content_without_frontmatter = reader_service._strip_frontmatter(full_content)
        sections = reader_service.parse_sections(content_without_frontmatter)

        # Find the section
        section = reader_service.get_section(sections, section_id)
        if section is None:
            raise KeyError(
                f"Section '{section_id}' not found in chapter {chapter_index}"
            )

        # Create timestamped note
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        note_comment = f"<!-- NOTE: {timestamp_str} - {note_text} -->"

        # Add note at the end of the section content
        section_content = section.content.rstrip()
        updated_section = f"{section_content}\n\n{note_comment}"

        # Extract frontmatter
        frontmatter = ""
        if full_content.startswith("---"):
            match = re.search(r"\n---\s*\n", full_content[3:])
            if match:
                frontmatter = full_content[: 3 + match.end()]

        # Rebuild content with updated section
        new_sections_content = []
        for s in sections:
            if s.index == section.index:
                new_sections_content.append(updated_section)
            else:
                new_sections_content.append(s.content)

        # Join sections
        result_parts = []
        for i, content in enumerate(new_sections_content):
            if i > 0 and sections[i].heading:
                result_parts.append("\n")
            result_parts.append(content)

        new_chapter_content = frontmatter + "\n".join(result_parts)

        # Write back to file
        self._file_repo.write_file(chapter.file_path, new_chapter_content)

        return {
            "success": True,
            "timestamp": timestamp_str,
            "text": note_text,
        }
