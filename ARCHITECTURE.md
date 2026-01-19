# MD Book Tools - DI/SOA Architecture Design

## Executive Summary

This document defines a Service-Oriented Architecture (SOA) with Dependency Injection (DI) for the MD Book Tools, transforming the current monolithic design into a modular, testable, and extensible system with MCP (Model Context Protocol) server integration for Claude Code.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Proposed Architecture](#proposed-architecture)
3. [Directory Structure](#directory-structure)
4. [Service Layer Design](#service-layer-design)
5. [Dependency Injection Container](#dependency-injection-container)
6. [MCP Server Integration](#mcp-server-integration)
7. [CLI Interface Design](#cli-interface-design)
8. [Migration Plan](#migration-plan)
9. [Testing Strategy](#testing-strategy)

---

## Current State Analysis

### Existing Files

| File | Lines | Responsibility | Issues |
|------|-------|----------------|--------|
| `book_reader.py` | 378 | CLI + UI + Business Logic | Monolithic, tight coupling |
| `book_writer.py` | 260 | CLI + File Operations | Duplicate utilities |
| `structure_detector.py` | 521 | Structure Parsing | Good separation, but creates dependencies |
| `config.py` | 115 | Static Configuration | Class-level state, not injectable |
| `version.py` | 93 | Version Management | Clean, standalone |

### Identified Problems

1. **Tight Coupling**: `BookReader` instantiates `StructureDetector` directly
2. **Global State**: `console = Console()` at module level
3. **Mixed Concerns**: CLI logic interleaved with business logic
4. **Duplicate Code**: Frontmatter parsing exists in both reader and writer
5. **No Testability**: Hard to mock dependencies for unit testing
6. **No MCP Integration**: Cannot expose functionality to Claude Code

---

## Proposed Architecture

### Architecture Diagram

```
                                 +-------------------+
                                 |    CLI Entry      |
                                 |   `mdbook` cmd    |
                                 +--------+----------+
                                          |
                                          v
+------------------+            +-------------------+            +------------------+
|   MCP Server     |<---------->|  Service Layer   |<---------->|  Repository      |
|  (MCPService)    |            |   (Facade)       |            |  Layer           |
+------------------+            +--------+----------+            +------------------+
        ^                                |                               ^
        |                                v                               |
        |                       +--------+----------+                    |
        |                       |  DI Container     |                    |
        |                       | (ServiceRegistry) |                    |
        |                       +-------------------+                    |
        |                                |                               |
        v                                v                               v
+------------------+   +------------------+   +------------------+   +------------------+
|  BookService     |   |  ReaderService   |   |  WriterService   |   | StructureService |
|  (Core Logic)    |   |  (Navigation)    |   |  (Scaffolding)   |   | (Detection)      |
+------------------+   +------------------+   +------------------+   +------------------+
        |                      |                      |                      |
        +----------------------+----------------------+----------------------+
                                          |
                                          v
                               +-------------------+
                               |  Domain Models    |
                               | (Book, Chapter,   |
                               |  BookStructure)   |
                               +-------------------+
```

### Design Principles

1. **Dependency Injection**: All services receive dependencies via constructor
2. **Interface Segregation**: Small, focused service interfaces
3. **Single Responsibility**: Each service has one reason to change
4. **Open/Closed**: Extensible via new services, not modification
5. **Repository Pattern**: Separate data access from business logic

---

## Directory Structure

```
mdbook/
├── __init__.py                    # Package init, exports public API
├── __main__.py                    # Entry point: python -m mdbook
├── cli.py                         # Click CLI commands (thin layer)
├── version.py                     # Version info (unchanged)
│
├── domain/                        # Domain Models (Pure Python, no deps)
│   ├── __init__.py
│   ├── book.py                    # Book, BookMetadata
│   ├── chapter.py                 # Chapter, ChapterMetadata
│   └── structure.py               # BookStructure, FormatType
│
├── services/                      # Business Logic Services
│   ├── __init__.py
│   ├── interfaces.py              # Abstract base classes / Protocols
│   ├── book_service.py            # Core book operations
│   ├── reader_service.py          # Reading / navigation
│   ├── writer_service.py          # Creation / scaffolding
│   ├── structure_service.py       # Detection / parsing
│   └── mcp_service.py             # MCP server interface
│
├── repositories/                  # Data Access Layer
│   ├── __init__.py
│   ├── interfaces.py              # Repository protocols
│   ├── file_repository.py         # Filesystem operations
│   └── config_repository.py       # Configuration loading
│
├── infrastructure/                # Cross-cutting concerns
│   ├── __init__.py
│   ├── container.py               # DI Container
│   ├── config.py                  # Configuration dataclasses
│   └── console.py                 # Rich console wrapper
│
├── mcp/                           # MCP Server Implementation
│   ├── __init__.py
│   ├── server.py                  # MCP server entry point
│   ├── tools.py                   # Tool definitions
│   └── schemas.py                 # JSON schemas for tools
│
└── tests/                         # Test Suite
    ├── __init__.py
    ├── conftest.py                # Pytest fixtures
    ├── unit/
    │   ├── test_book_service.py
    │   ├── test_reader_service.py
    │   ├── test_writer_service.py
    │   └── test_structure_service.py
    └── integration/
        ├── test_cli.py
        └── test_mcp.py
```

---

## Service Layer Design

### 1. Domain Models (`domain/`)

#### `domain/chapter.py`

```python
"""Chapter domain model."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict
from datetime import date


@dataclass(frozen=True)
class ChapterMetadata:
    """Immutable chapter metadata from frontmatter."""
    author: Optional[str] = None
    date: Optional[date] = None
    draft: bool = False
    tags: tuple[str, ...] = ()
    extra: Dict = field(default_factory=dict)


@dataclass
class Chapter:
    """Represents a single chapter in a book."""
    number: int
    title: str
    file_path: Path
    is_intro: bool = False
    metadata: ChapterMetadata = field(default_factory=ChapterMetadata)

    @property
    def is_draft(self) -> bool:
        """Check if chapter is marked as draft."""
        return self.metadata.draft

    @property
    def slug(self) -> str:
        """Generate URL-friendly slug from title."""
        import re
        text = self.title.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        return text.strip('-')
```

#### `domain/book.py`

```python
"""Book domain model."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict
from datetime import date

from .chapter import Chapter


@dataclass
class BookMetadata:
    """Book-level metadata."""
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: str = "en"
    created: Optional[date] = None
    extra: Dict = field(default_factory=dict)


@dataclass
class Book:
    """Represents a complete book."""
    root_path: Path
    metadata: BookMetadata
    chapters: List[Chapter] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def chapter_count(self) -> int:
        """Count of non-intro chapters."""
        return len([c for c in self.chapters if not c.is_intro])

    def get_chapter(self, number: int) -> Optional[Chapter]:
        """Get chapter by number."""
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        return None

    def get_intro(self) -> Optional[Chapter]:
        """Get introduction chapter if exists."""
        for chapter in self.chapters:
            if chapter.is_intro:
                return chapter
        return None
```

#### `domain/structure.py`

```python
"""Book structure domain models."""
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional


class FormatType(Enum):
    """Supported book format types."""
    SUMMARY = auto()    # mdBook/GitBook SUMMARY.md
    LEANPUB = auto()    # Leanpub Book.txt
    BOOKDOWN = auto()   # Bookdown _bookdown.yml
    MDBOOK = auto()     # mdBook book.toml
    AUTO = auto()       # Auto-detected


@dataclass
class BookStructure:
    """Detected book structure information."""
    format_type: FormatType
    root_path: Path
    title: Optional[str] = None
    author: Optional[str] = None
    config_file: Optional[Path] = None
```

### 2. Service Interfaces (`services/interfaces.py`)

```python
"""Service interface definitions using Protocol."""
from abc import abstractmethod
from pathlib import Path
from typing import Protocol, Optional, List

from ..domain.book import Book
from ..domain.chapter import Chapter
from ..domain.structure import BookStructure, FormatType


class IStructureService(Protocol):
    """Interface for book structure detection."""

    @abstractmethod
    def detect(self, root_path: Path) -> BookStructure:
        """Detect book structure from root path."""
        ...

    @abstractmethod
    def supports_format(self, format_type: FormatType) -> bool:
        """Check if this service supports the given format."""
        ...


class IReaderService(Protocol):
    """Interface for book reading operations."""

    @abstractmethod
    def load_book(self, root_path: Path) -> Book:
        """Load book from filesystem."""
        ...

    @abstractmethod
    def read_chapter(self, chapter: Chapter) -> str:
        """Read chapter content."""
        ...

    @abstractmethod
    def list_chapters(self, book: Book) -> List[Chapter]:
        """List all chapters in book."""
        ...


class IWriterService(Protocol):
    """Interface for book writing operations."""

    @abstractmethod
    def initialize_book(
        self,
        path: Path,
        title: str,
        author: str
    ) -> Book:
        """Initialize a new book structure."""
        ...

    @abstractmethod
    def add_chapter(
        self,
        book: Book,
        title: str,
        draft: bool = False
    ) -> Chapter:
        """Add a new chapter to the book."""
        ...

    @abstractmethod
    def update_toc(self, book: Book) -> None:
        """Regenerate table of contents."""
        ...


class IBookService(Protocol):
    """High-level interface for book operations."""

    @abstractmethod
    def get_book_info(self, root_path: Path) -> Book:
        """Get complete book information."""
        ...

    @abstractmethod
    def read_chapter_content(
        self,
        root_path: Path,
        chapter_number: int
    ) -> str:
        """Read specific chapter content."""
        ...

    @abstractmethod
    def create_book(
        self,
        path: Path,
        title: str,
        author: str
    ) -> Book:
        """Create a new book."""
        ...

    @abstractmethod
    def add_chapter_to_book(
        self,
        root_path: Path,
        title: str,
        draft: bool = False
    ) -> Chapter:
        """Add chapter to existing book."""
        ...
```

### 3. Service Implementations

#### `services/structure_service.py`

```python
"""Book structure detection service."""
import re
from pathlib import Path
from typing import Optional, List, Dict

from ..domain.chapter import Chapter, ChapterMetadata
from ..domain.structure import BookStructure, FormatType
from ..repositories.interfaces import IFileRepository, IConfigRepository


class StructureService:
    """Detects and parses book structure from various formats."""

    def __init__(
        self,
        file_repo: IFileRepository,
        config_repo: IConfigRepository
    ):
        """Initialize with injected dependencies."""
        self._file_repo = file_repo
        self._config_repo = config_repo

    def detect(self, root_path: Path) -> BookStructure:
        """Detect book structure in priority order."""
        root = Path(root_path).resolve()

        # Priority order of detection
        detectors = [
            (root / 'SUMMARY.md', FormatType.SUMMARY, self._parse_summary),
            (root / 'Book.txt', FormatType.LEANPUB, self._parse_leanpub),
            (root / '_bookdown.yml', FormatType.BOOKDOWN, self._parse_bookdown),
            (root / 'book.toml', FormatType.MDBOOK, self._parse_mdbook),
        ]

        for config_file, format_type, parser in detectors:
            if self._file_repo.exists(config_file):
                return parser(config_file, root)

        # Fallback to auto-detection
        return self._auto_detect(root)

    def supports_format(self, format_type: FormatType) -> bool:
        """All formats are supported."""
        return True

    def _parse_summary(
        self,
        summary_path: Path,
        root: Path
    ) -> BookStructure:
        """Parse SUMMARY.md format (mdBook/GitBook)."""
        content = self._file_repo.read_text(summary_path)
        structure = BookStructure(
            format_type=FormatType.SUMMARY,
            root_path=root,
            config_file=summary_path
        )
        return structure

    def _parse_leanpub(
        self,
        book_txt: Path,
        root: Path
    ) -> BookStructure:
        """Parse Book.txt format (Leanpub)."""
        # Implementation similar to current structure_detector.py
        return BookStructure(
            format_type=FormatType.LEANPUB,
            root_path=root,
            config_file=book_txt
        )

    def _parse_bookdown(
        self,
        bookdown_yml: Path,
        root: Path
    ) -> BookStructure:
        """Parse _bookdown.yml format."""
        config = self._config_repo.load_yaml(bookdown_yml)
        return BookStructure(
            format_type=FormatType.BOOKDOWN,
            root_path=root,
            title=config.get('book_filename'),
            config_file=bookdown_yml
        )

    def _parse_mdbook(
        self,
        book_toml: Path,
        root: Path
    ) -> BookStructure:
        """Parse book.toml (mdBook)."""
        config = self._config_repo.load_toml(book_toml)
        book_config = config.get('book', {})
        return BookStructure(
            format_type=FormatType.MDBOOK,
            root_path=root,
            title=book_config.get('title'),
            author=book_config.get('authors', [None])[0],
            config_file=book_toml
        )

    def _auto_detect(self, root: Path) -> BookStructure:
        """Auto-detect chapters from file patterns."""
        return BookStructure(
            format_type=FormatType.AUTO,
            root_path=root
        )
```

#### `services/book_service.py`

```python
"""Core book service - facade for all book operations."""
from pathlib import Path
from typing import List

from ..domain.book import Book
from ..domain.chapter import Chapter
from .interfaces import IStructureService, IReaderService, IWriterService


class BookService:
    """
    High-level facade for book operations.

    This service coordinates between reader, writer, and structure services
    to provide a unified API for book operations.
    """

    def __init__(
        self,
        structure_service: IStructureService,
        reader_service: IReaderService,
        writer_service: IWriterService
    ):
        """Initialize with injected services."""
        self._structure = structure_service
        self._reader = reader_service
        self._writer = writer_service

    def get_book_info(self, root_path: Path) -> Book:
        """
        Get complete book information.

        Args:
            root_path: Path to book root directory

        Returns:
            Book object with metadata and chapters
        """
        return self._reader.load_book(root_path)

    def read_chapter_content(
        self,
        root_path: Path,
        chapter_number: int
    ) -> str:
        """
        Read specific chapter content.

        Args:
            root_path: Path to book root directory
            chapter_number: Chapter number (0 for intro)

        Returns:
            Chapter content as markdown string

        Raises:
            ValueError: If chapter not found
        """
        book = self._reader.load_book(root_path)
        chapter = book.get_chapter(chapter_number)

        if not chapter:
            raise ValueError(f"Chapter {chapter_number} not found")

        return self._reader.read_chapter(chapter)

    def list_chapters(self, root_path: Path) -> List[Chapter]:
        """
        List all chapters in a book.

        Args:
            root_path: Path to book root directory

        Returns:
            List of Chapter objects
        """
        book = self._reader.load_book(root_path)
        return self._reader.list_chapters(book)

    def create_book(
        self,
        path: Path,
        title: str,
        author: str
    ) -> Book:
        """
        Create a new book structure.

        Args:
            path: Path where to create the book
            title: Book title
            author: Author name

        Returns:
            Newly created Book object
        """
        return self._writer.initialize_book(path, title, author)

    def add_chapter_to_book(
        self,
        root_path: Path,
        title: str,
        draft: bool = False
    ) -> Chapter:
        """
        Add a new chapter to an existing book.

        Args:
            root_path: Path to book root directory
            title: Chapter title
            draft: Whether to mark as draft

        Returns:
            Newly created Chapter object
        """
        book = self._reader.load_book(root_path)
        chapter = self._writer.add_chapter(book, title, draft)
        self._writer.update_toc(book)
        return chapter

    def regenerate_toc(self, root_path: Path) -> None:
        """
        Regenerate table of contents.

        Args:
            root_path: Path to book root directory
        """
        book = self._reader.load_book(root_path)
        self._writer.update_toc(book)
```

#### `services/reader_service.py`

```python
"""Book reading service."""
import re
from pathlib import Path
from typing import List, Optional

from ..domain.book import Book, BookMetadata
from ..domain.chapter import Chapter, ChapterMetadata
from ..domain.structure import BookStructure
from ..repositories.interfaces import IFileRepository
from .interfaces import IStructureService


class ReaderService:
    """Service for reading and navigating books."""

    def __init__(
        self,
        file_repo: IFileRepository,
        structure_service: IStructureService
    ):
        """Initialize with injected dependencies."""
        self._file_repo = file_repo
        self._structure_service = structure_service

    def load_book(self, root_path: Path) -> Book:
        """Load book from filesystem."""
        root = Path(root_path).resolve()

        # Detect structure
        structure = self._structure_service.detect(root)

        # Build book metadata
        metadata = BookMetadata(
            title=structure.title or self._infer_title(root),
            author=structure.author
        )

        # Load chapters
        chapters = self._load_chapters(structure)

        return Book(
            root_path=root,
            metadata=metadata,
            chapters=chapters
        )

    def read_chapter(self, chapter: Chapter) -> str:
        """Read chapter content, stripping frontmatter."""
        content = self._file_repo.read_text(chapter.file_path)

        # Strip YAML frontmatter from display
        if content.startswith('---'):
            match = re.search(r'\n---\s*\n', content[3:])
            if match:
                content = content[3 + match.end():]

        return content

    def list_chapters(self, book: Book) -> List[Chapter]:
        """List all chapters in order."""
        return sorted(book.chapters, key=lambda c: (c.is_intro, c.number))

    def _infer_title(self, root: Path) -> str:
        """Infer book title from directory name."""
        return root.name.replace('-', ' ').replace('_', ' ').title()

    def _load_chapters(self, structure: BookStructure) -> List[Chapter]:
        """Load chapters based on detected structure."""
        # Implementation depends on format type
        # Delegates to appropriate parser
        return []
```

#### `services/writer_service.py`

```python
"""Book writing service."""
import re
from pathlib import Path
from datetime import date
from typing import Dict, Any

from ..domain.book import Book, BookMetadata
from ..domain.chapter import Chapter, ChapterMetadata
from ..repositories.interfaces import IFileRepository, IConfigRepository


class WriterService:
    """Service for creating and modifying books."""

    def __init__(
        self,
        file_repo: IFileRepository,
        config_repo: IConfigRepository
    ):
        """Initialize with injected dependencies."""
        self._file_repo = file_repo
        self._config_repo = config_repo

    def initialize_book(
        self,
        path: Path,
        title: str,
        author: str
    ) -> Book:
        """Initialize a new book structure."""
        root = Path(path).resolve()

        # Create directories
        chapters_dir = root / 'chapters'
        self._file_repo.mkdir(chapters_dir, parents=True)

        # Create book.yaml
        book_config = {
            'title': title,
            'author': author,
            'description': '',
            'language': 'en',
            'created': date.today().isoformat()
        }
        self._config_repo.save_yaml(root / 'book.yaml', book_config)

        # Create SUMMARY.md
        summary_content = f"# {title}\n\n"
        self._file_repo.write_text(root / 'SUMMARY.md', summary_content)

        # Return Book object
        metadata = BookMetadata(
            title=title,
            author=author,
            created=date.today()
        )
        return Book(root_path=root, metadata=metadata)

    def add_chapter(
        self,
        book: Book,
        title: str,
        draft: bool = False
    ) -> Chapter:
        """Add a new chapter to the book."""
        chapters_dir = book.root_path / 'chapters'

        # Get next chapter number
        chapter_num = self._get_next_chapter_number(chapters_dir)

        # Create filename
        slug = self._slugify(title)
        filename = f"{chapter_num:02d}-{slug}.md"
        chapter_path = chapters_dir / filename

        # Create frontmatter
        frontmatter: Dict[str, Any] = {
            'title': title,
            'chapter': chapter_num,
            'date': date.today().isoformat()
        }
        if draft:
            frontmatter['draft'] = True

        # Create chapter content
        content = self._create_chapter_content(title, frontmatter)
        self._file_repo.write_text(chapter_path, content)

        # Create Chapter object
        metadata = ChapterMetadata(
            date=date.today(),
            draft=draft
        )
        chapter = Chapter(
            number=chapter_num,
            title=title,
            file_path=chapter_path,
            metadata=metadata
        )

        book.chapters.append(chapter)
        return chapter

    def update_toc(self, book: Book) -> None:
        """Regenerate SUMMARY.md from chapters."""
        lines = [f"# {book.title}", ""]

        for chapter in sorted(book.chapters, key=lambda c: c.number):
            prefix = "- " if not chapter.is_draft else "- [DRAFT] "
            rel_path = chapter.file_path.relative_to(book.root_path)
            lines.append(f"{prefix}[{chapter.title}]({rel_path})")

        content = "\n".join(lines) + "\n"
        self._file_repo.write_text(book.root_path / 'SUMMARY.md', content)

    def _get_next_chapter_number(self, chapters_dir: Path) -> int:
        """Find the next available chapter number."""
        max_num = 0
        if self._file_repo.exists(chapters_dir):
            for path in self._file_repo.list_directory(chapters_dir):
                if path.suffix == '.md':
                    match = re.match(r'^(\d+)', path.stem)
                    if match:
                        max_num = max(max_num, int(match.group(1)))
        return max_num + 1

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        return text.strip('-')

    def _create_chapter_content(
        self,
        title: str,
        frontmatter: Dict[str, Any]
    ) -> str:
        """Create chapter content with frontmatter."""
        import yaml
        frontmatter_yaml = yaml.dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True
        )
        return f"---\n{frontmatter_yaml}---\n\n# {title}\n\n"
```

---

## Dependency Injection Container

### `infrastructure/container.py`

```python
"""Dependency Injection Container."""
from pathlib import Path
from typing import TypeVar, Type, Dict, Any, Optional, Callable
from dataclasses import dataclass, field


T = TypeVar('T')


@dataclass
class ServiceRegistration:
    """Registration information for a service."""
    factory: Callable[..., Any]
    singleton: bool = False
    instance: Optional[Any] = None


class ServiceContainer:
    """
    Simple DI container supporting constructor injection.

    Features:
    - Singleton and transient lifetimes
    - Factory-based registration
    - Automatic dependency resolution
    - No global state
    """

    def __init__(self):
        """Initialize empty container."""
        self._registrations: Dict[Type, ServiceRegistration] = {}

    def register(
        self,
        interface: Type[T],
        factory: Callable[..., T],
        singleton: bool = False
    ) -> 'ServiceContainer':
        """
        Register a service.

        Args:
            interface: The interface/protocol type
            factory: Factory function to create instances
            singleton: If True, same instance returned for all resolves

        Returns:
            Self for chaining
        """
        self._registrations[interface] = ServiceRegistration(
            factory=factory,
            singleton=singleton
        )
        return self

    def register_instance(
        self,
        interface: Type[T],
        instance: T
    ) -> 'ServiceContainer':
        """
        Register an existing instance (always singleton).

        Args:
            interface: The interface/protocol type
            instance: The pre-created instance

        Returns:
            Self for chaining
        """
        self._registrations[interface] = ServiceRegistration(
            factory=lambda: instance,
            singleton=True,
            instance=instance
        )
        return self

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a service by interface type.

        Args:
            interface: The interface/protocol type to resolve

        Returns:
            Instance of the requested service

        Raises:
            KeyError: If interface not registered
        """
        if interface not in self._registrations:
            raise KeyError(f"Service not registered: {interface}")

        registration = self._registrations[interface]

        if registration.singleton and registration.instance is not None:
            return registration.instance

        instance = registration.factory()

        if registration.singleton:
            registration.instance = instance

        return instance

    def create_scope(self) -> 'ServiceContainer':
        """
        Create a child scope with inherited registrations.

        Returns:
            New container with same registrations
        """
        child = ServiceContainer()
        child._registrations = self._registrations.copy()
        return child


def configure_services(root_path: Optional[Path] = None) -> ServiceContainer:
    """
    Configure the DI container with all services.

    This is the composition root where all dependencies are wired together.

    Args:
        root_path: Optional default book root path

    Returns:
        Configured ServiceContainer
    """
    container = ServiceContainer()

    # Import implementations
    from ..repositories.file_repository import FileRepository
    from ..repositories.config_repository import ConfigRepository
    from ..services.structure_service import StructureService
    from ..services.reader_service import ReaderService
    from ..services.writer_service import WriterService
    from ..services.book_service import BookService
    from ..services.mcp_service import MCPService
    from ..infrastructure.console import ConsoleWrapper

    # Register repositories
    container.register(
        IFileRepository,
        lambda: FileRepository(),
        singleton=True
    )
    container.register(
        IConfigRepository,
        lambda: ConfigRepository(),
        singleton=True
    )

    # Register services
    container.register(
        IStructureService,
        lambda: StructureService(
            file_repo=container.resolve(IFileRepository),
            config_repo=container.resolve(IConfigRepository)
        ),
        singleton=True
    )

    container.register(
        IReaderService,
        lambda: ReaderService(
            file_repo=container.resolve(IFileRepository),
            structure_service=container.resolve(IStructureService)
        ),
        singleton=True
    )

    container.register(
        IWriterService,
        lambda: WriterService(
            file_repo=container.resolve(IFileRepository),
            config_repo=container.resolve(IConfigRepository)
        ),
        singleton=True
    )

    container.register(
        IBookService,
        lambda: BookService(
            structure_service=container.resolve(IStructureService),
            reader_service=container.resolve(IReaderService),
            writer_service=container.resolve(IWriterService)
        ),
        singleton=True
    )

    container.register(
        IMCPService,
        lambda: MCPService(
            book_service=container.resolve(IBookService)
        ),
        singleton=True
    )

    # Register infrastructure
    container.register(
        ConsoleWrapper,
        lambda: ConsoleWrapper(),
        singleton=True
    )

    return container
```

---

## MCP Server Integration

### `mcp/schemas.py`

```python
"""JSON schemas for MCP tools."""

BOOK_INFO_SCHEMA = {
    "name": "book_info",
    "description": "Get book structure and metadata",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to book root directory"
            }
        },
        "required": ["path"]
    }
}

READ_CHAPTER_SCHEMA = {
    "name": "read_chapter",
    "description": "Read chapter content by number",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to book root directory"
            },
            "chapter": {
                "type": "integer",
                "description": "Chapter number (0 for introduction)"
            }
        },
        "required": ["path", "chapter"]
    }
}

LIST_CHAPTERS_SCHEMA = {
    "name": "list_chapters",
    "description": "List all chapters in a book",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to book root directory"
            }
        },
        "required": ["path"]
    }
}

CREATE_BOOK_SCHEMA = {
    "name": "create_book",
    "description": "Initialize a new book structure",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path where to create the book"
            },
            "title": {
                "type": "string",
                "description": "Book title"
            },
            "author": {
                "type": "string",
                "description": "Author name"
            }
        },
        "required": ["path", "title", "author"]
    }
}

ADD_CHAPTER_SCHEMA = {
    "name": "add_chapter",
    "description": "Add a new chapter to the book",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to book root directory"
            },
            "title": {
                "type": "string",
                "description": "Chapter title"
            },
            "draft": {
                "type": "boolean",
                "description": "Mark as draft",
                "default": False
            }
        },
        "required": ["path", "title"]
    }
}

UPDATE_TOC_SCHEMA = {
    "name": "update_toc",
    "description": "Regenerate table of contents",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to book root directory"
            }
        },
        "required": ["path"]
    }
}

ALL_TOOLS = [
    BOOK_INFO_SCHEMA,
    READ_CHAPTER_SCHEMA,
    LIST_CHAPTERS_SCHEMA,
    CREATE_BOOK_SCHEMA,
    ADD_CHAPTER_SCHEMA,
    UPDATE_TOC_SCHEMA,
]
```

### `mcp/server.py`

```python
"""MCP Server implementation for MD Book Tools."""
import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .schemas import ALL_TOOLS
from ..infrastructure.container import configure_services
from ..services.interfaces import IBookService


class MDBookMCPServer:
    """MCP Server exposing book tools to Claude Code."""

    def __init__(self):
        """Initialize server with DI container."""
        self._container = configure_services()
        self._book_service: IBookService = self._container.resolve(IBookService)
        self._server = Server("mdbook-tools")
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP request handlers."""

        @self._server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name=schema["name"],
                    description=schema["description"],
                    inputSchema=schema["inputSchema"]
                )
                for schema in ALL_TOOLS
            ]

        @self._server.call_tool()
        async def call_tool(
            name: str,
            arguments: Dict[str, Any]
        ) -> list[TextContent]:
            """Handle tool calls."""
            try:
                result = await self._dispatch_tool(name, arguments)
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}),
                    isError=True
                )]

    async def _dispatch_tool(
        self,
        name: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Dispatch tool call to appropriate handler."""
        handlers = {
            "book_info": self._handle_book_info,
            "read_chapter": self._handle_read_chapter,
            "list_chapters": self._handle_list_chapters,
            "create_book": self._handle_create_book,
            "add_chapter": self._handle_add_chapter,
            "update_toc": self._handle_update_toc,
        }

        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(args)

    async def _handle_book_info(self, args: Dict) -> Dict:
        """Handle book_info tool."""
        path = Path(args["path"])
        book = self._book_service.get_book_info(path)
        return {
            "title": book.title,
            "author": book.metadata.author,
            "chapter_count": book.chapter_count,
            "root_path": str(book.root_path),
            "chapters": [
                {
                    "number": c.number,
                    "title": c.title,
                    "is_intro": c.is_intro,
                    "is_draft": c.is_draft
                }
                for c in book.chapters
            ]
        }

    async def _handle_read_chapter(self, args: Dict) -> Dict:
        """Handle read_chapter tool."""
        path = Path(args["path"])
        chapter_num = args["chapter"]
        content = self._book_service.read_chapter_content(path, chapter_num)
        return {
            "chapter": chapter_num,
            "content": content
        }

    async def _handle_list_chapters(self, args: Dict) -> Dict:
        """Handle list_chapters tool."""
        path = Path(args["path"])
        chapters = self._book_service.list_chapters(path)
        return {
            "chapters": [
                {
                    "number": c.number,
                    "title": c.title,
                    "is_intro": c.is_intro,
                    "is_draft": c.is_draft,
                    "file": str(c.file_path.name)
                }
                for c in chapters
            ]
        }

    async def _handle_create_book(self, args: Dict) -> Dict:
        """Handle create_book tool."""
        path = Path(args["path"])
        title = args["title"]
        author = args["author"]
        book = self._book_service.create_book(path, title, author)
        return {
            "created": True,
            "path": str(book.root_path),
            "title": book.title
        }

    async def _handle_add_chapter(self, args: Dict) -> Dict:
        """Handle add_chapter tool."""
        path = Path(args["path"])
        title = args["title"]
        draft = args.get("draft", False)
        chapter = self._book_service.add_chapter_to_book(path, title, draft)
        return {
            "created": True,
            "number": chapter.number,
            "title": chapter.title,
            "file": str(chapter.file_path.name)
        }

    async def _handle_update_toc(self, args: Dict) -> Dict:
        """Handle update_toc tool."""
        path = Path(args["path"])
        self._book_service.regenerate_toc(path)
        return {"updated": True, "path": str(path / "SUMMARY.md")}

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                self._server.create_initialization_options()
            )


async def main():
    """Entry point for MCP server."""
    server = MDBookMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## CLI Interface Design

### `cli.py`

```python
"""CLI entry point for MD Book Tools."""
import click
from pathlib import Path
from typing import Optional

from .version import get_version
from .infrastructure.container import configure_services
from .infrastructure.console import ConsoleWrapper


@click.group()
@click.version_option(version=get_version(), prog_name='mdbook')
@click.pass_context
def cli(ctx):
    """
    MD Book Tools - Read, write, and manage markdown books.

    A unified CLI for markdown book management with MCP server support.
    """
    ctx.ensure_object(dict)
    ctx.obj['container'] = configure_services()


@cli.command()
@click.option('--chapter', '-c', type=int, help='Jump to specific chapter')
@click.option('--toc', is_flag=True, help='Show table of contents')
@click.option('--root', '-r', default='.', help='Book root directory')
@click.option('--info', is_flag=True, help='Show book structure info')
@click.pass_context
def read(ctx, chapter: Optional[int], toc: bool, root: str, info: bool):
    """
    Read a markdown book interactively.

    Examples:
        mdbook read                    # Read book in current directory
        mdbook read --root /path/to/book
        mdbook read --chapter 5        # Jump to chapter 5
        mdbook read --toc              # Show table of contents
    """
    container = ctx.obj['container']
    book_service = container.resolve(IBookService)
    console = container.resolve(ConsoleWrapper)

    root_path = Path(root).resolve()
    book = book_service.get_book_info(root_path)

    if info:
        console.show_book_info(book)
        return

    if toc:
        console.show_toc(book)
        return

    # Interactive reading mode
    from .ui.reader import InteractiveReader
    reader = InteractiveReader(book, console)
    if chapter is not None:
        reader.jump_to(chapter)
    reader.run()


@cli.command()
@click.option('--title', '-t', prompt='Book title', help='Title of the book')
@click.option('--author', '-a', prompt='Author', help='Author name')
@click.option('--path', '-p', default='.', help='Path to create book')
@click.pass_context
def init(ctx, title: str, author: str, path: str):
    """
    Initialize a new book structure.

    Creates:
        - book.yaml (book configuration)
        - SUMMARY.md (table of contents)
        - chapters/ directory

    Examples:
        mdbook init --title "My Book" --author "John Doe"
        mdbook init -t "My Book" -a "John Doe" -p ./my-book
    """
    container = ctx.obj['container']
    book_service = container.resolve(IBookService)
    console = container.resolve(ConsoleWrapper)

    book_path = Path(path).resolve()
    book = book_service.create_book(book_path, title, author)
    console.success(f"Book initialized at {book.root_path}")


@cli.command('new-chapter')
@click.option('--title', '-t', prompt='Chapter title', help='Chapter title')
@click.option('--draft', '-d', is_flag=True, help='Mark as draft')
@click.option('--path', '-p', default='.', help='Book root directory')
@click.pass_context
def new_chapter(ctx, title: str, draft: bool, path: str):
    """
    Add a new chapter to the book.

    Creates a new markdown file with frontmatter and updates SUMMARY.md.

    Examples:
        mdbook new-chapter --title "Introduction to AI"
        mdbook new-chapter -t "Draft Chapter" --draft
    """
    container = ctx.obj['container']
    book_service = container.resolve(IBookService)
    console = container.resolve(ConsoleWrapper)

    root_path = Path(path).resolve()
    chapter = book_service.add_chapter_to_book(root_path, title, draft)
    console.success(f"Created chapter {chapter.number}: {chapter.title}")


@cli.command()
@click.option('--path', '-p', default='.', help='Book root directory')
@click.pass_context
def toc(ctx, path: str):
    """
    Regenerate SUMMARY.md from chapters.

    Scans the chapters/ directory and rebuilds the table of contents.

    Examples:
        mdbook toc
        mdbook toc --path /path/to/book
    """
    container = ctx.obj['container']
    book_service = container.resolve(IBookService)
    console = container.resolve(ConsoleWrapper)

    root_path = Path(path).resolve()
    book_service.regenerate_toc(root_path)
    console.success("Table of contents regenerated")


@cli.command('serve-mcp')
def serve_mcp():
    """
    Start the MCP server for Claude Code integration.

    Exposes book tools via Model Context Protocol:
        - book_info: Get book structure
        - read_chapter: Read chapter content
        - list_chapters: List all chapters
        - create_book: Initialize new book
        - add_chapter: Add new chapter
        - update_toc: Regenerate TOC

    Usage in Claude Desktop config:
        {
            "mcpServers": {
                "mdbook": {
                    "command": "mdbook",
                    "args": ["serve-mcp"]
                }
            }
        }
    """
    import asyncio
    from .mcp.server import main as mcp_main
    asyncio.run(mcp_main())


def main():
    """Entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
```

---

## Migration Plan

### Phase 1: Foundation (Week 1)

**Goal**: Establish domain models and repository layer without breaking existing functionality.

1. **Create package structure**
   ```bash
   mkdir -p mdbook/{domain,services,repositories,infrastructure,mcp,tests/{unit,integration}}
   touch mdbook/{__init__,__main__}.py
   ```

2. **Implement domain models**
   - `domain/chapter.py` - Chapter, ChapterMetadata
   - `domain/book.py` - Book, BookMetadata
   - `domain/structure.py` - BookStructure, FormatType

3. **Implement repository interfaces and implementations**
   - `repositories/interfaces.py` - IFileRepository, IConfigRepository
   - `repositories/file_repository.py` - FileRepository
   - `repositories/config_repository.py` - ConfigRepository

4. **Write unit tests for domain models**

### Phase 2: Service Layer (Week 2)

**Goal**: Implement service layer while maintaining backward compatibility.

1. **Implement service interfaces**
   - `services/interfaces.py` - All Protocol definitions

2. **Migrate structure detection**
   - Extract logic from `structure_detector.py` to `services/structure_service.py`
   - Inject file/config repositories

3. **Implement reader and writer services**
   - `services/reader_service.py` - From `book_reader.py`
   - `services/writer_service.py` - From `book_writer.py`

4. **Implement BookService facade**

5. **Write unit tests for all services**

### Phase 3: DI Container (Week 3)

**Goal**: Wire everything together with dependency injection.

1. **Implement DI container**
   - `infrastructure/container.py`

2. **Configure composition root**
   - `configure_services()` function

3. **Update CLI to use container**
   - Thin CLI layer in `cli.py`

4. **Write integration tests**

### Phase 4: MCP Server (Week 4)

**Goal**: Expose functionality to Claude Code.

1. **Define MCP schemas**
   - `mcp/schemas.py`

2. **Implement MCP server**
   - `mcp/server.py`

3. **Add `serve-mcp` CLI command**

4. **Write MCP integration tests**

5. **Document Claude Desktop configuration**

### Phase 5: Cleanup (Week 5)

**Goal**: Finalize migration and remove legacy code.

1. **Update all imports**
2. **Deprecate old modules**
3. **Update documentation**
4. **Create pyproject.toml for package**
5. **Final integration testing**

### Backward Compatibility Strategy

During migration, maintain backward compatibility via:

```python
# book_reader.py (deprecated, forwards to new implementation)
import warnings
warnings.warn(
    "book_reader.py is deprecated. Use 'mdbook read' instead.",
    DeprecationWarning
)
from mdbook.cli import read
# ... forward calls to new implementation
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_book_service.py
import pytest
from pathlib import Path
from unittest.mock import Mock

from mdbook.services.book_service import BookService
from mdbook.domain.book import Book, BookMetadata
from mdbook.domain.chapter import Chapter


class TestBookService:
    """Unit tests for BookService."""

    @pytest.fixture
    def mock_structure_service(self):
        return Mock()

    @pytest.fixture
    def mock_reader_service(self):
        return Mock()

    @pytest.fixture
    def mock_writer_service(self):
        return Mock()

    @pytest.fixture
    def book_service(
        self,
        mock_structure_service,
        mock_reader_service,
        mock_writer_service
    ):
        return BookService(
            structure_service=mock_structure_service,
            reader_service=mock_reader_service,
            writer_service=mock_writer_service
        )

    def test_get_book_info_delegates_to_reader(
        self,
        book_service,
        mock_reader_service
    ):
        """Test that get_book_info delegates to reader service."""
        # Arrange
        root = Path("/test/book")
        expected_book = Book(
            root_path=root,
            metadata=BookMetadata(title="Test Book")
        )
        mock_reader_service.load_book.return_value = expected_book

        # Act
        result = book_service.get_book_info(root)

        # Assert
        mock_reader_service.load_book.assert_called_once_with(root)
        assert result == expected_book

    def test_read_chapter_raises_for_missing_chapter(
        self,
        book_service,
        mock_reader_service
    ):
        """Test that reading missing chapter raises ValueError."""
        # Arrange
        root = Path("/test/book")
        book = Book(
            root_path=root,
            metadata=BookMetadata(title="Test Book"),
            chapters=[]
        )
        mock_reader_service.load_book.return_value = book

        # Act & Assert
        with pytest.raises(ValueError, match="Chapter 5 not found"):
            book_service.read_chapter_content(root, 5)
```

### Integration Tests

```python
# tests/integration/test_mcp.py
import pytest
import asyncio
from pathlib import Path

from mdbook.mcp.server import MDBookMCPServer


class TestMCPServer:
    """Integration tests for MCP server."""

    @pytest.fixture
    def server(self):
        return MDBookMCPServer()

    @pytest.mark.asyncio
    async def test_book_info_tool(self, server, tmp_path):
        """Test book_info tool returns correct structure."""
        # Arrange: Create test book
        (tmp_path / "SUMMARY.md").write_text("# Test Book\n")
        (tmp_path / "book.yaml").write_text("title: Test Book\nauthor: Test\n")

        # Act
        result = await server._dispatch_tool("book_info", {"path": str(tmp_path)})

        # Assert
        assert result["title"] == "Test Book"
        assert "chapters" in result

    @pytest.mark.asyncio
    async def test_create_book_tool(self, server, tmp_path):
        """Test create_book tool creates correct structure."""
        # Act
        result = await server._dispatch_tool("create_book", {
            "path": str(tmp_path / "new-book"),
            "title": "New Book",
            "author": "Author"
        })

        # Assert
        assert result["created"] is True
        assert (tmp_path / "new-book" / "SUMMARY.md").exists()
        assert (tmp_path / "new-book" / "book.yaml").exists()
```

---

## MCP Tool Specifications

### Tool: `book_info`

**Purpose**: Get complete book structure and metadata.

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to book root directory"
        }
    },
    "required": ["path"]
}
```

**Output Example**:
```json
{
    "title": "The Augmented Programmer",
    "author": "Bob Smith",
    "chapter_count": 12,
    "root_path": "/Users/masa/Writing/Books/book_augmented-programmer",
    "chapters": [
        {"number": 0, "title": "Introduction", "is_intro": true, "is_draft": false},
        {"number": 1, "title": "The Impossible Hire", "is_intro": false, "is_draft": false}
    ]
}
```

### Tool: `read_chapter`

**Purpose**: Read chapter content by number.

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "chapter": {"type": "integer"}
    },
    "required": ["path", "chapter"]
}
```

**Output Example**:
```json
{
    "chapter": 1,
    "content": "# Chapter 1: The Impossible Hire\n\nContent here..."
}
```

### Tool: `list_chapters`

**Purpose**: List all chapters with metadata.

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "path": {"type": "string"}
    },
    "required": ["path"]
}
```

**Output Example**:
```json
{
    "chapters": [
        {"number": 1, "title": "Chapter 1", "is_intro": false, "is_draft": false, "file": "01-chapter-one.md"}
    ]
}
```

### Tool: `create_book`

**Purpose**: Initialize a new book structure.

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "title": {"type": "string"},
        "author": {"type": "string"}
    },
    "required": ["path", "title", "author"]
}
```

**Output Example**:
```json
{
    "created": true,
    "path": "/path/to/new-book",
    "title": "My New Book"
}
```

### Tool: `add_chapter`

**Purpose**: Add a new chapter to existing book.

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "title": {"type": "string"},
        "draft": {"type": "boolean", "default": false}
    },
    "required": ["path", "title"]
}
```

**Output Example**:
```json
{
    "created": true,
    "number": 5,
    "title": "New Chapter Title",
    "file": "05-new-chapter-title.md"
}
```

### Tool: `update_toc`

**Purpose**: Regenerate SUMMARY.md from chapters.

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "path": {"type": "string"}
    },
    "required": ["path"]
}
```

**Output Example**:
```json
{
    "updated": true,
    "path": "/path/to/book/SUMMARY.md"
}
```

---

## Claude Desktop Configuration

To use the MCP server with Claude Desktop, add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "mdbook": {
            "command": "mdbook",
            "args": ["serve-mcp"],
            "env": {
                "PYTHONUNBUFFERED": "1"
            }
        }
    }
}
```

Or with explicit Python path:

```json
{
    "mcpServers": {
        "mdbook": {
            "command": "python",
            "args": ["-m", "mdbook", "serve-mcp"],
            "cwd": "/path/to/mdbook"
        }
    }
}
```

---

## Summary

This architecture provides:

1. **Clean Separation**: Domain, services, repositories, infrastructure
2. **Dependency Injection**: All dependencies injected via constructors
3. **Testability**: Easy to mock any layer for unit testing
4. **Extensibility**: New formats/features via new services
5. **MCP Integration**: Full Claude Code integration via MCP server
6. **Single Entry Point**: Unified `mdbook` CLI with subcommands
7. **Backward Compatibility**: Migration path preserves existing functionality

The design follows the patterns from the loaded skills:
- **DI Pattern**: Constructor injection, no global state
- **SOA Pattern**: Clear service boundaries
- **MCP Pattern**: Tool-based server interface
- **Repository Pattern**: Data access abstraction
