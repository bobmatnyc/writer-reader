"""
Table of Contents (SUMMARY.md) Management

Updates SUMMARY.md while preserving existing hierarchy structure.
Supports mdBook format with Part headers and nested entries.

Structure example:
    # Summary

    ## Part I: Basics

    - [Introduction](chapters/intro.md)
      - [Getting Started](chapters/getting-started.md)

    ## Part II: Advanced

    - [Deep Dive](chapters/deep-dive.md)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TocEntry:
    """Represents a single entry in the table of contents."""

    title: str
    path: str | None
    indent_level: int = 0
    children: list["TocEntry"] = field(default_factory=list)
    is_part_header: bool = False
    raw_line: str = ""

    def to_markdown(self) -> str:
        """Convert entry back to markdown format."""
        if self.is_part_header:
            return f"\n{self.raw_line}\n"
        indent = "  " * self.indent_level
        if self.path:
            return f"{indent}- [{self.title}]({self.path})"
        return f"{indent}- {self.title}"


@dataclass
class TocStructure:
    """Represents the complete table of contents structure."""

    title: str = "Summary"
    entries: list[TocEntry] = field(default_factory=list)
    raw_header: str = "# Summary"

    def get_all_paths(self) -> set[str]:
        """Get all file paths referenced in the TOC."""
        paths = set()

        def collect_paths(entries: list[TocEntry]) -> None:
            for entry in entries:
                if entry.path:
                    paths.add(entry.path)
                collect_paths(entry.children)

        collect_paths(self.entries)
        return paths

    def to_markdown(self) -> str:
        """Convert structure back to markdown format."""
        lines = [self.raw_header, ""]

        def render_entries(entries: list[TocEntry]) -> None:
            for entry in entries:
                lines.append(entry.to_markdown())
                render_entries(entry.children)

        render_entries(self.entries)
        return "\n".join(lines) + "\n"


def parse_summary_structure(content: str) -> TocStructure:
    """
    Parse existing SUMMARY.md preserving hierarchy.

    Args:
        content: Raw SUMMARY.md content

    Returns:
        TocStructure with parsed entries maintaining hierarchy
    """
    structure = TocStructure()
    lines = content.split("\n")

    # Find and parse header
    for i, line in enumerate(lines):
        if line.startswith("# "):
            structure.raw_header = line
            structure.title = line[2:].strip()
            lines = lines[i + 1 :]
            break

    # Stack to track parent entries at each indent level
    entry_stack: list[tuple[int, TocEntry]] = []

    # Regex patterns
    link_pattern = re.compile(r"^(\s*)-\s*\[([^\]]+)\]\(([^)]+)\)\s*$")
    text_pattern = re.compile(r"^(\s*)-\s*(.+)\s*$")
    part_pattern = re.compile(r"^##\s+(.+)$")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for Part header (## Part I, etc.)
        part_match = part_pattern.match(stripped)
        if part_match:
            entry = TocEntry(
                title=part_match.group(1),
                path=None,
                indent_level=0,
                is_part_header=True,
                raw_line=stripped,
            )
            structure.entries.append(entry)
            entry_stack = []  # Reset stack for new part
            continue

        # Check for link entry
        link_match = link_pattern.match(line)
        if link_match:
            indent_str = link_match.group(1)
            indent_level = len(indent_str) // 2
            title = link_match.group(2)
            path = link_match.group(3)

            entry = TocEntry(
                title=title,
                path=path,
                indent_level=indent_level,
                raw_line=line,
            )

            _add_entry_to_structure(structure, entry_stack, entry, indent_level)
            continue

        # Check for text-only entry (no link)
        text_match = text_pattern.match(line)
        if text_match:
            indent_str = text_match.group(1)
            indent_level = len(indent_str) // 2
            title = text_match.group(2)

            # Skip if it looks like a link that didn't match
            if "[" in title:
                continue

            entry = TocEntry(
                title=title,
                path=None,
                indent_level=indent_level,
                raw_line=line,
            )

            _add_entry_to_structure(structure, entry_stack, entry, indent_level)

    return structure


def _add_entry_to_structure(
    structure: TocStructure,
    entry_stack: list[tuple[int, TocEntry]],
    entry: TocEntry,
    indent_level: int,
) -> None:
    """Add an entry to the structure at the correct hierarchy level."""
    # Pop entries from stack that are at same or deeper level
    while entry_stack and entry_stack[-1][0] >= indent_level:
        entry_stack.pop()

    if entry_stack:
        # Add as child of parent
        parent = entry_stack[-1][1]
        parent.children.append(entry)
    else:
        # Add as top-level entry
        structure.entries.append(entry)

    # Push current entry onto stack
    entry_stack.append((indent_level, entry))


def discover_markdown_files(book_dir: Path) -> list[str]:
    """
    Find all .md files in chapters/src directory.

    Args:
        book_dir: Root directory of the book

    Returns:
        List of relative paths to markdown files
    """
    files = []

    # Check common locations for mdBook content
    search_dirs = [
        book_dir / "src",
        book_dir / "chapters",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for md_file in sorted(search_dir.rglob("*.md")):
            # Skip SUMMARY.md itself
            if md_file.name == "SUMMARY.md":
                continue

            # Get relative path from book_dir
            try:
                rel_path = md_file.relative_to(book_dir)
                files.append(str(rel_path))
            except ValueError:
                # File not under book_dir, skip
                continue

    return files


def update_summary(book_dir: Path, preserve_structure: bool = True) -> dict:
    """
    Update SUMMARY.md table of contents.

    Args:
        book_dir: Root directory of the book
        preserve_structure: If True, preserve existing hierarchy and add new files.
                           If False, generate fresh flat structure.

    Returns:
        Dict with 'added', 'existing', 'summary_path' keys
    """
    # Find SUMMARY.md location
    summary_path = _find_summary_path(book_dir)
    existing_content = ""

    if summary_path.exists():
        existing_content = summary_path.read_text(encoding="utf-8")

    # Discover all markdown files
    discovered_files = discover_markdown_files(book_dir)

    if preserve_structure and existing_content:
        result = _update_preserving_structure(summary_path, existing_content, discovered_files)
    else:
        result = _generate_flat_structure(summary_path, discovered_files)

    result["summary_path"] = str(summary_path)
    return result


def _find_summary_path(book_dir: Path) -> Path:
    """Find the correct location for SUMMARY.md."""
    # Check common locations
    candidates = [
        book_dir / "src" / "SUMMARY.md",
        book_dir / "SUMMARY.md",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Default to src/SUMMARY.md for mdBook convention
    src_dir = book_dir / "src"
    if src_dir.exists():
        return src_dir / "SUMMARY.md"

    return book_dir / "SUMMARY.md"


def _update_preserving_structure(
    summary_path: Path, existing_content: str, discovered_files: list[str]
) -> dict:
    """Update SUMMARY.md while preserving existing structure."""
    structure = parse_summary_structure(existing_content)
    existing_paths = structure.get_all_paths()

    # Normalize paths for comparison
    normalized_existing = {_normalize_path(p) for p in existing_paths}

    # Find new files not in existing structure
    added = []
    existing = []

    for file_path in discovered_files:
        normalized = _normalize_path(file_path)
        if normalized in normalized_existing:
            existing.append(file_path)
        else:
            added.append(file_path)

    # Add new files at the end of structure
    for file_path in added:
        title = _path_to_title(file_path)
        entry = TocEntry(title=title, path=file_path, indent_level=0)
        structure.entries.append(entry)

    # Write updated structure
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(structure.to_markdown(), encoding="utf-8")

    return {"added": added, "existing": existing}


def _generate_flat_structure(summary_path: Path, discovered_files: list[str]) -> dict:
    """Generate a fresh flat SUMMARY.md structure."""
    structure = TocStructure()

    for file_path in discovered_files:
        title = _path_to_title(file_path)
        entry = TocEntry(title=title, path=file_path, indent_level=0)
        structure.entries.append(entry)

    # Write new structure
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(structure.to_markdown(), encoding="utf-8")

    return {"added": discovered_files, "existing": []}


def _normalize_path(path: str) -> str:
    """Normalize a path for comparison."""
    # Remove leading ./ and normalize separators
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lower()


def _path_to_title(path: str) -> str:
    """Convert a file path to a readable title."""
    name = Path(path).stem

    # Remove common prefixes like ch01-, chapter-01-, etc.
    name = re.sub(r"^(ch(apter)?[-_]?)?\d+[-_]?", "", name, flags=re.IGNORECASE)

    # Convert kebab-case and snake_case to title case
    name = re.sub(r"[-_]", " ", name)

    # Title case
    if name:
        return name.title()

    # Fallback to filename
    return Path(path).stem.title()
