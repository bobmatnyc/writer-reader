"""Domain models for content features.

Provides dataclasses for TOC entries, index terms, image references,
and git version control information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TocEntry:
    """A single entry in a table of contents.

    Represents a heading at any level (##, ###, ####) with support
    for nesting and anchor links.
    """

    title: str
    level: int  # 1 for ##, 2 for ###, 3 for ####
    anchor: str  # URL-friendly slug
    children: list["TocEntry"] = field(default_factory=list)

    @property
    def indent(self) -> str:
        """Get indentation for rendering."""
        return "  " * (self.level - 1)


@dataclass
class ChapterToc:
    """TOC for a single chapter."""

    chapter_number: Optional[int]
    chapter_title: str
    entries: list[TocEntry] = field(default_factory=list)


@dataclass
class BookToc:
    """Full book TOC with nested structure."""

    title: str
    chapters: list[ChapterToc] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the TOC as markdown."""
        lines = [f"# {self.title}", ""]
        for chapter in self.chapters:
            prefix = (
                "Intro" if chapter.chapter_number == 0 else f"{chapter.chapter_number}"
            )
            lines.append(
                f"- [{prefix}. {chapter.chapter_title}](#{_slugify(chapter.chapter_title)})"
            )
            for entry in chapter.entries:
                lines.extend(_render_toc_entry(entry, 1))
        return "\n".join(lines)


@dataclass
class ImageRef:
    """A reference to an image in chapter content."""

    alt_text: str
    path: str
    line_number: int
    exists: bool = True  # Validated during chapter read


@dataclass
class MermaidBlock:
    """A mermaid diagram code block."""

    content: str
    start_line: int
    end_line: int


@dataclass
class IndexTerm:
    """An indexable term with location information."""

    term: str
    chapter_number: Optional[int]
    chapter_title: str
    section_heading: str = ""
    anchor: str = ""


@dataclass
class IndexEntry:
    """A single index entry with all locations."""

    term: str
    locations: list[IndexTerm] = field(default_factory=list)

    @property
    def sort_key(self) -> str:
        """Key for alphabetical sorting."""
        return self.term.lower()


@dataclass
class BookIndex:
    """Complete book index."""

    entries: list[IndexEntry] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the index as markdown."""
        sorted_entries = sorted(self.entries, key=lambda e: e.sort_key)
        lines = ["# Index", ""]
        current_letter = ""

        for entry in sorted_entries:
            first_letter = entry.term[0].upper() if entry.term else ""
            if first_letter != current_letter:
                current_letter = first_letter
                lines.append(f"\n## {current_letter}\n")

            locations = ", ".join(
                f"[{loc.chapter_title}](#{loc.anchor})"
                if loc.anchor
                else loc.chapter_title
                for loc in entry.locations
            )
            lines.append(f"- **{entry.term}**: {locations}")

        return "\n".join(lines)


@dataclass
class CommitInfo:
    """Information about a git commit.

    Represents metadata from a single commit affecting a file.
    """

    hash: str  # Full SHA-1 hash
    short_hash: str  # Abbreviated hash (7 chars)
    author: str
    author_email: str
    date: datetime
    message: str
    subject: str  # First line of commit message


@dataclass
class DiffHunk:
    """A single hunk from a diff.

    Represents a contiguous block of changes.
    """

    old_start: int  # Starting line in old version
    old_count: int  # Number of lines in old version
    new_start: int  # Starting line in new version
    new_count: int  # Number of lines in new version
    content: str  # The actual diff content with +/- prefixes


@dataclass
class FileDiff:
    """Diff information between two versions of a file.

    Contains parsed diff output with statistics and hunks.
    """

    file_path: str
    commit_from: str  # Commit hash or ref for old version
    commit_to: str  # Commit hash or ref for new version
    additions: int  # Lines added
    deletions: int  # Lines removed
    hunks: list[DiffHunk] = field(default_factory=list)
    raw_diff: str = ""  # Full raw diff output

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return self.additions > 0 or self.deletions > 0


@dataclass
class ChapterHistory:
    """Git history for a chapter file.

    Contains list of commits that affected the chapter.
    """

    chapter_path: str
    commits: list[CommitInfo] = field(default_factory=list)

    @property
    def commit_count(self) -> int:
        """Number of commits in history."""
        return len(self.commits)


@dataclass
class RecentChange:
    """A recent change in the book repository.

    Combines commit info with the affected file path.
    """

    file_path: str
    commit: CommitInfo
    change_type: str = "modified"  # added, modified, deleted


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def _render_toc_entry(entry: TocEntry, base_indent: int) -> list[str]:
    """Render a TOC entry and its children."""
    indent = "  " * (base_indent + entry.level - 1)
    lines = [f"{indent}- [{entry.title}](#{entry.anchor})"]
    for child in entry.children:
        lines.extend(_render_toc_entry(child, base_indent))
    return lines
