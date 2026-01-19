"""Structure detection service implementation.

Provides book structure detection and parsing for various formats:
- SUMMARY.md (mdBook / GitBook)
- Book.txt (Leanpub)
- _bookdown.yml (Bookdown)
- book.toml (mdBook)
- Auto-detection via filename patterns
"""

import re
from datetime import date
from pathlib import Path
from typing import Any

from ..domain import Chapter, ChapterMetadata, FormatType
from ..repositories.interfaces import IConfigRepository, IFileRepository


class StructureService:
    """Detects and parses book structure from various formats.

    Implements IStructureService protocol using constructor injection
    for file and configuration repositories.
    """

    # Files that indicate an introduction/preface chapter
    INTRO_FILES = frozenset({
        "readme.md",
        "index.md",
        "introduction.md",
        "preface.md",
        "foreword.md",
    })

    # Files to skip during auto-detection
    SKIP_FILES = frozenset({
        "SUMMARY.md",
        "Book.txt",
        "_bookdown.yml",
        "book.toml",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE.md",
    })

    # Patterns for chapter file naming
    CHAPTER_FILE_PATTERNS = (
        r"chapter[-_]?(\d+)",
        r"ch[-_]?(\d+)",
        r"(\d+)[-_]",
    )

    # Priority patterns for selecting best content file
    PRIORITY_PATTERNS = (
        r".*complete\.md$",
        r".*enhanced\.md$",
        r".*revised\.md$",
        r".*final\.md$",
    )

    def __init__(
        self,
        file_repo: IFileRepository,
        config_repo: IConfigRepository,
    ) -> None:
        """Initialize the structure service.

        Args:
            file_repo: Repository for file system operations.
            config_repo: Repository for configuration file operations.
        """
        self._file_repo = file_repo
        self._config_repo = config_repo

    def detect_format(self, root: Path) -> FormatType:
        """Detect the book format type from directory structure.

        Examines the directory for format-specific files and conventions
        to determine the book format (mdBook, GitBook, Leanpub, etc.).

        Priority order:
        1. SUMMARY.md (mdBook/GitBook)
        2. Book.txt (Leanpub)
        3. _bookdown.yml (Bookdown)
        4. book.toml (mdBook)
        5. AUTO (fallback)

        Args:
            root: Root directory of the book project.

        Returns:
            The detected FormatType, or FormatType.AUTO if unable to determine.

        Raises:
            NotADirectoryError: If root is not a directory.
        """
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")

        # Check for SUMMARY.md (could be mdBook or GitBook)
        if self._file_repo.exists(root / "SUMMARY.md"):
            # If book.toml also exists, it's mdBook
            if self._file_repo.exists(root / "book.toml"):
                return FormatType.MDBOOK
            return FormatType.GITBOOK

        # Check for src/SUMMARY.md (mdBook structure)
        if self._file_repo.exists(root / "src" / "SUMMARY.md"):
            return FormatType.MDBOOK

        # Check for Book.txt (Leanpub)
        if self._file_repo.exists(root / "Book.txt"):
            return FormatType.LEANPUB

        # Check for _bookdown.yml (Bookdown)
        if self._file_repo.exists(root / "_bookdown.yml"):
            return FormatType.BOOKDOWN

        # Check for book.toml without SUMMARY.md
        if self._file_repo.exists(root / "book.toml"):
            return FormatType.MDBOOK

        return FormatType.AUTO

    def parse_structure(self, root: Path, format_type: FormatType) -> list[Chapter]:
        """Parse the book structure and return ordered chapters.

        Reads the table of contents or directory structure to build
        a list of chapters with their metadata and file paths.

        Args:
            root: Root directory of the book project.
            format_type: The book format type to use for parsing.

        Returns:
            A list of Chapter objects in reading order.

        Raises:
            FileNotFoundError: If required structure files are missing.
            ValueError: If the structure cannot be parsed.
        """
        if format_type == FormatType.MDBOOK:
            return self._parse_mdbook(root)
        elif format_type == FormatType.GITBOOK:
            return self._parse_summary_md(root, root / "SUMMARY.md")
        elif format_type == FormatType.LEANPUB:
            return self._parse_leanpub(root)
        elif format_type == FormatType.BOOKDOWN:
            return self._parse_bookdown(root)
        else:
            return self._auto_detect(root)

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
        frontmatter = self._extract_frontmatter_dict(content)

        if frontmatter is None:
            # No frontmatter, try to extract title from first heading
            title = self._extract_heading_title(content) or "Untitled"
            return ChapterMetadata(title=title)

        # Extract and validate title
        title = frontmatter.get("title")
        if title is None:
            title = self._extract_heading_title(content) or "Untitled"

        # Extract chapter number
        number = None
        if "chapter" in frontmatter:
            try:
                number = int(frontmatter["chapter"])
            except (ValueError, TypeError):
                pass

        # Extract author
        author = frontmatter.get("author")

        # Extract date
        chapter_date = None
        raw_date = frontmatter.get("date")
        if raw_date is not None:
            if isinstance(raw_date, date):
                chapter_date = raw_date
            else:
                try:
                    chapter_date = date.fromisoformat(str(raw_date))
                except ValueError:
                    pass

        # Extract draft status
        draft = bool(frontmatter.get("draft", False))

        # Collect extra fields
        known_keys = {"title", "chapter", "author", "date", "draft"}
        extra = {k: v for k, v in frontmatter.items() if k not in known_keys}

        return ChapterMetadata(
            title=title,
            number=number,
            author=author,
            date=chapter_date,
            draft=draft,
            extra=extra,
        )

    def _extract_frontmatter_dict(self, content: str) -> dict[str, Any] | None:
        """Extract frontmatter as a dictionary from content.

        Args:
            content: The full markdown content.

        Returns:
            Dictionary of frontmatter values, or None if no frontmatter.

        Raises:
            ValueError: If frontmatter is malformed YAML.
        """
        if not content.startswith("---"):
            return None

        # Find end of frontmatter
        end_match = re.search(r"\n---\s*\n", content[3:])
        if not end_match:
            return None

        frontmatter_text = content[3 : 3 + end_match.start()]

        try:
            # Build path to a temporary pseudo-file for YAML parsing
            # We use the config_repo's load_yaml indirectly via yaml
            import yaml

            data = yaml.safe_load(frontmatter_text)
            return data if isinstance(data, dict) else None
        except Exception as e:
            raise ValueError(f"Malformed frontmatter YAML: {e}") from e

    def _extract_heading_title(self, content: str) -> str | None:
        """Extract title from first markdown heading.

        Args:
            content: The markdown content.

        Returns:
            The heading text, or None if no heading found.
        """
        # Skip frontmatter if present
        if content.startswith("---"):
            end_match = re.search(r"\n---\s*\n", content[3:])
            if end_match:
                content = content[3 + end_match.end() :]

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        return None

    def _parse_mdbook(self, root: Path) -> list[Chapter]:
        """Parse mdBook format structure.

        Args:
            root: Root directory of the book project.

        Returns:
            List of chapters in reading order.
        """
        # mdBook uses src/SUMMARY.md by default
        src_summary = root / "src" / "SUMMARY.md"
        if self._file_repo.exists(src_summary):
            return self._parse_summary_md(root, src_summary)

        # Try SUMMARY.md in root
        root_summary = root / "SUMMARY.md"
        if self._file_repo.exists(root_summary):
            return self._parse_summary_md(root, root_summary)

        # Fall back to auto-detection
        return self._auto_detect(root)

    def _parse_summary_md(self, root: Path, summary_path: Path) -> list[Chapter]:
        """Parse SUMMARY.md format (mdBook/GitBook).

        Args:
            root: Root directory of the book project.
            summary_path: Path to the SUMMARY.md file.

        Returns:
            List of chapters in reading order.
        """
        try:
            content = self._file_repo.read_file(summary_path)
        except FileNotFoundError:
            return self._auto_detect(root)

        chapters = []
        chapter_num = 0

        # Parse markdown links: [Title](path/to/file.md)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")

        for line in content.split("\n"):
            match = link_pattern.search(line)
            if match:
                title = match.group(1).strip()
                rel_path = match.group(2).strip()

                # Resolve the path relative to book root
                file_path = root / rel_path
                if not self._file_repo.exists(file_path):
                    # Try relative to SUMMARY.md location
                    file_path = summary_path.parent / rel_path

                if self._file_repo.exists(file_path):
                    is_intro = rel_path.lower() in {
                        "readme.md",
                        "index.md",
                        "introduction.md",
                    }

                    # Enrich with frontmatter
                    metadata = self._get_chapter_metadata(file_path, title)

                    if is_intro:
                        metadata = ChapterMetadata(
                            title=metadata.title,
                            number=0,
                            author=metadata.author,
                            date=metadata.date,
                            draft=metadata.draft,
                            extra=metadata.extra,
                        )
                        chapter = Chapter(
                            file_path=file_path,
                            metadata=metadata,
                            is_intro=True,
                        )
                    else:
                        chapter_num += 1
                        metadata = ChapterMetadata(
                            title=metadata.title,
                            number=chapter_num,
                            author=metadata.author,
                            date=metadata.date,
                            draft=metadata.draft,
                            extra=metadata.extra,
                        )
                        chapter = Chapter(
                            file_path=file_path,
                            metadata=metadata,
                            is_intro=False,
                        )

                    chapters.append(chapter)

        return chapters

    def _parse_leanpub(self, root: Path) -> list[Chapter]:
        """Parse Book.txt format (Leanpub).

        Args:
            root: Root directory of the book project.

        Returns:
            List of chapters in reading order.
        """
        book_txt_path = root / "Book.txt"

        try:
            content = self._file_repo.read_file(book_txt_path)
        except FileNotFoundError:
            return self._auto_detect(root)

        chapters = []
        chapter_num = 0

        # Leanpub Book.txt is a simple list of file paths
        manuscript_dir = root / "manuscript"
        base_dir = manuscript_dir if self._file_repo.exists(manuscript_dir) else root

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Handle frontmatter, mainmatter, backmatter markers
            if line in ("frontmatter:", "mainmatter:", "backmatter:"):
                continue

            file_path = base_dir / line
            if not self._file_repo.exists(file_path):
                file_path = root / line

            if self._file_repo.exists(file_path) and file_path.suffix == ".md":
                is_intro = line.lower() in {
                    "introduction.md",
                    "preface.md",
                    "foreword.md",
                }

                # Get metadata from file
                metadata = self._get_chapter_metadata(file_path)

                if is_intro:
                    metadata = ChapterMetadata(
                        title=metadata.title,
                        number=0,
                        author=metadata.author,
                        date=metadata.date,
                        draft=metadata.draft,
                        extra=metadata.extra,
                    )
                    chapter = Chapter(
                        file_path=file_path,
                        metadata=metadata,
                        is_intro=True,
                    )
                else:
                    chapter_num += 1
                    metadata = ChapterMetadata(
                        title=metadata.title,
                        number=chapter_num,
                        author=metadata.author,
                        date=metadata.date,
                        draft=metadata.draft,
                        extra=metadata.extra,
                    )
                    chapter = Chapter(
                        file_path=file_path,
                        metadata=metadata,
                        is_intro=False,
                    )

                chapters.append(chapter)

        return chapters

    def _parse_bookdown(self, root: Path) -> list[Chapter]:
        """Parse _bookdown.yml format.

        Args:
            root: Root directory of the book project.

        Returns:
            List of chapters in reading order.
        """
        bookdown_path = root / "_bookdown.yml"

        try:
            config = self._config_repo.load_yaml(bookdown_path)
        except FileNotFoundError:
            return self._auto_detect(root)

        chapters = []
        chapter_num = 0

        # Get chapter files from rmd_files or chapter_name pattern
        rmd_files = config.get("rmd_files", [])

        for idx, file_name in enumerate(rmd_files):
            # Bookdown uses .Rmd files, but we support .md too
            file_path = root / file_name
            if not self._file_repo.exists(file_path):
                # Try .md extension
                md_path = file_path.with_suffix(".md")
                if self._file_repo.exists(md_path):
                    file_path = md_path
                else:
                    continue

            is_intro = "index" in file_name.lower() or idx == 0

            # Get metadata from file
            metadata = self._get_chapter_metadata(file_path)

            if is_intro and chapter_num == 0:
                metadata = ChapterMetadata(
                    title=metadata.title,
                    number=0,
                    author=metadata.author,
                    date=metadata.date,
                    draft=metadata.draft,
                    extra=metadata.extra,
                )
                chapter = Chapter(
                    file_path=file_path,
                    metadata=metadata,
                    is_intro=True,
                )
            else:
                chapter_num += 1
                metadata = ChapterMetadata(
                    title=metadata.title,
                    number=chapter_num,
                    author=metadata.author,
                    date=metadata.date,
                    draft=metadata.draft,
                    extra=metadata.extra,
                )
                chapter = Chapter(
                    file_path=file_path,
                    metadata=metadata,
                    is_intro=False,
                )

            chapters.append(chapter)

        return chapters

    def _auto_detect(self, root: Path) -> list[Chapter]:
        """Auto-detect chapters from file patterns.

        - Sort .md files alphanumerically
        - Skip underscore-prefixed files
        - Recognize standard chapter patterns

        Args:
            root: Root directory of the book project.

        Returns:
            List of chapters in reading order.
        """
        chapters = []
        chapter_num = 0

        # First, check for intro files
        for intro_file in self.INTRO_FILES:
            intro_path = root / intro_file
            if self._file_repo.exists(intro_path):
                metadata = self._get_chapter_metadata(intro_path, "Introduction")
                metadata = ChapterMetadata(
                    title=metadata.title,
                    number=0,
                    author=metadata.author,
                    date=metadata.date,
                    draft=metadata.draft,
                    extra=metadata.extra,
                )
                chapter = Chapter(
                    file_path=intro_path,
                    metadata=metadata,
                    is_intro=True,
                )
                chapters.append(chapter)
                break

        # Collect all markdown files
        md_files = self._collect_markdown_files(root)

        # Sort alphanumerically
        md_files.sort(key=lambda p: (self._extract_sort_key(p), p.name.lower()))

        for file_path in md_files:
            # Skip files we've already added as intro
            if any(c.file_path == file_path for c in chapters):
                continue

            # Skip files in skip list
            if file_path.name in self.SKIP_FILES:
                continue

            metadata = self._get_chapter_metadata(file_path)
            chapter_num += 1
            metadata = ChapterMetadata(
                title=metadata.title,
                number=chapter_num,
                author=metadata.author,
                date=metadata.date,
                draft=metadata.draft,
                extra=metadata.extra,
            )
            chapter = Chapter(
                file_path=file_path,
                metadata=metadata,
                is_intro=False,
            )
            chapters.append(chapter)

        return chapters

    def _collect_markdown_files(self, root: Path) -> list[Path]:
        """Collect markdown files, respecting skip patterns.

        Args:
            root: Root directory to search.

        Returns:
            List of markdown file paths.
        """
        md_files = []

        # Check for chapter directories (chapter-01, etc.)
        chapter_dirs = sorted(
            [
                d
                for d in self._file_repo.list_files(root, "chapter-*")
                if d.is_dir()
            ],
            key=lambda p: p.name,
        )

        # Try glob pattern for directories
        try:
            chapter_dirs = sorted(root.glob("chapter-*"))
            chapter_dirs = [d for d in chapter_dirs if d.is_dir()]
        except Exception:
            chapter_dirs = []

        if chapter_dirs:
            for chapter_dir in chapter_dirs:
                # Look in content subdirectory first
                content_dir = chapter_dir / "content"
                if content_dir.is_dir():
                    content_files = self._file_repo.list_files(content_dir, "*.md")
                    if content_files:
                        # Pick best file from content directory
                        best_file = self._pick_best_content_file(content_files)
                        if best_file:
                            md_files.append(best_file)
                        continue

                # Otherwise look for .md files directly in chapter dir
                direct_files = [
                    f
                    for f in self._file_repo.list_files(chapter_dir, "*.md")
                    if not f.name.startswith("_")
                ]
                if direct_files:
                    best_file = self._pick_best_content_file(direct_files)
                    if best_file:
                        md_files.append(best_file)

            return md_files

        # No chapter directories, look for flat structure
        for md_file in self._file_repo.list_files(root, "*.md"):
            # Skip underscore-prefixed files
            if md_file.name.startswith("_"):
                continue

            # Skip common non-content files
            if md_file.name.upper() in {"SUMMARY.MD", "BOOK.TXT"}:
                continue

            # Skip intro files (handled separately)
            if md_file.name.lower() in self.INTRO_FILES:
                continue

            # Skip files in skip list
            if md_file.name in self.SKIP_FILES:
                continue

            md_files.append(md_file)

        return md_files

    def _pick_best_content_file(self, files: list[Path]) -> Path | None:
        """Pick the best content file from a list based on priority patterns.

        Args:
            files: List of candidate files.

        Returns:
            The best file, or None if list is empty.
        """
        if not files:
            return None

        for pattern in self.PRIORITY_PATTERNS:
            for f in files:
                if re.match(pattern, f.name, re.IGNORECASE):
                    return f

        # Return first file if no priority match
        return files[0]

    def _extract_sort_key(self, file_path: Path) -> tuple[int, str]:
        """Extract a sort key from filename for proper ordering.

        Args:
            file_path: The file path to extract sort key from.

        Returns:
            Tuple of (numeric_key, name) for sorting.
        """
        name = file_path.stem

        # Try to extract leading numbers
        match = re.match(r"^(\d+)", name)
        if match:
            return (int(match.group(1)), name)

        # Try chapter patterns
        for pattern in self.CHAPTER_FILE_PATTERNS:
            match = re.match(pattern, file_path.name, re.IGNORECASE)
            if match:
                return (int(match.group(1)), name)

        # No number found, sort alphabetically at the end
        return (999999, name)

    def _get_chapter_metadata(
        self, file_path: Path, default_title: str | None = None
    ) -> ChapterMetadata:
        """Get chapter metadata from file content.

        Args:
            file_path: Path to the chapter file.
            default_title: Default title if none found.

        Returns:
            ChapterMetadata populated from file content.
        """
        try:
            content = self._file_repo.read_file(file_path)
            metadata = self.parse_frontmatter(content)

            # Use default title if metadata title is "Untitled"
            if metadata.title == "Untitled" and default_title:
                metadata = ChapterMetadata(
                    title=default_title,
                    number=metadata.number,
                    author=metadata.author,
                    date=metadata.date,
                    draft=metadata.draft,
                    extra=metadata.extra,
                )
            elif metadata.title == "Untitled":
                # Generate title from filename
                title = self._title_from_filename(file_path.stem)
                metadata = ChapterMetadata(
                    title=title,
                    number=metadata.number,
                    author=metadata.author,
                    date=metadata.date,
                    draft=metadata.draft,
                    extra=metadata.extra,
                )

            return metadata
        except Exception:
            title = default_title or self._title_from_filename(file_path.stem)
            return ChapterMetadata(title=title)

    def _title_from_filename(self, stem: str) -> str:
        """Convert filename stem to title.

        Args:
            stem: The filename without extension.

        Returns:
            Human-readable title.
        """
        # Remove leading numbers and separators
        title = re.sub(r"^\d+[-_]?", "", stem)
        # Replace separators with spaces
        title = re.sub(r"[-_]+", " ", title)
        # Title case
        return title.title()
