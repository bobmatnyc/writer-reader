"""Domain models for section-level editing.

Provides Section and Note dataclasses for representing sections within
chapters and timestamped notes stored as HTML comments.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Note:
    """A timestamped note stored as an HTML comment.

    Format: <!-- NOTE: 2024-01-19T15:30:00 - Note text here -->
    """

    timestamp: datetime
    text: str


@dataclass
class Section:
    """A section within a chapter, identified by ## heading.

    Sections are defined by level-2 headings (##) in markdown.
    Content before the first ## heading is treated as section index 0
    with an empty heading.
    """

    heading: str  # Heading text (without ##)
    content: str  # Full content including heading
    start_line: int  # 1-indexed start line
    end_line: int  # 1-indexed end line (exclusive)
    index: int  # 0-indexed position in chapter
    notes: list[Note] = field(default_factory=list)  # Attached notes

    @property
    def slug(self) -> str:
        """Generate a URL-friendly slug from the heading.

        Returns:
            A lowercase, hyphen-separated slug.
        """
        import re

        text = self.heading.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text.strip("-")

    @property
    def body(self) -> str:
        """Get section content without the heading line.

        Returns:
            The section content excluding the ## heading line.
        """
        lines = self.content.split("\n")
        if lines and lines[0].startswith("## "):
            return "\n".join(lines[1:]).lstrip("\n")
        return self.content
