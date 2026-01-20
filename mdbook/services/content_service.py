"""Content analysis service implementation.

Provides functionality to extract images, mermaid blocks, and validate
content references using constructor injection for dependencies.
"""

import re
from pathlib import Path

from ..domain.content import ImageRef, MermaidBlock
from ..repositories.interfaces import IFileRepository


class ContentService:
    """Service for analyzing and extracting content features.

    Implements image extraction, mermaid block detection, and
    content validation using constructor injection.
    """

    # Pattern for markdown images: ![alt](path)
    IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    # Pattern for mermaid code blocks
    MERMAID_PATTERN = re.compile(
        r"```mermaid\s*\n(.*?)```",
        re.DOTALL | re.MULTILINE,
    )

    def __init__(self, file_repo: IFileRepository) -> None:
        """Initialize the content service with required dependencies.

        Args:
            file_repo: Repository for file system operations.
        """
        self._file_repo = file_repo

    def extract_images(
        self, content: str, chapter_path: Path, validate: bool = True
    ) -> list[ImageRef]:
        """Extract image references from markdown content.

        Finds all ![alt](path) patterns and optionally validates
        that the referenced files exist.

        Args:
            content: The markdown content to analyze.
            chapter_path: Path to the chapter file for relative path resolution.
            validate: If True, check that image files exist.

        Returns:
            List of ImageRef objects with existence status.
        """
        images: list[ImageRef] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for match in self.IMAGE_PATTERN.finditer(line):
                alt_text = match.group(1)
                img_path = match.group(2)

                # Skip external URLs
                if img_path.startswith(("http://", "https://", "//")):
                    images.append(
                        ImageRef(
                            alt_text=alt_text,
                            path=img_path,
                            line_number=line_num,
                            exists=True,  # Assume external URLs exist
                        )
                    )
                    continue

                # Resolve relative path
                exists = True
                if validate:
                    resolved_path = self._resolve_image_path(img_path, chapter_path)
                    exists = self._file_repo.exists(resolved_path)

                images.append(
                    ImageRef(
                        alt_text=alt_text,
                        path=img_path,
                        line_number=line_num,
                        exists=exists,
                    )
                )

        return images

    def extract_mermaid_blocks(self, content: str) -> list[MermaidBlock]:
        """Extract mermaid diagram code blocks from content.

        Finds all ```mermaid ... ``` blocks and extracts their content.

        Args:
            content: The markdown content to analyze.

        Returns:
            List of MermaidBlock objects with content and line info.
        """
        blocks: list[MermaidBlock] = []
        lines = content.split("\n")

        in_mermaid = False
        block_lines: list[str] = []
        start_line = 0

        for line_num, line in enumerate(lines, start=1):
            if line.strip().startswith("```mermaid"):
                in_mermaid = True
                start_line = line_num
                block_lines = []
            elif in_mermaid and line.strip() == "```":
                in_mermaid = False
                blocks.append(
                    MermaidBlock(
                        content="\n".join(block_lines),
                        start_line=start_line,
                        end_line=line_num,
                    )
                )
            elif in_mermaid:
                block_lines.append(line)

        return blocks

    def has_mermaid(self, content: str) -> bool:
        """Check if content contains any mermaid blocks.

        Args:
            content: The markdown content to check.

        Returns:
            True if mermaid blocks are present.
        """
        return bool(self.MERMAID_PATTERN.search(content))

    def validate_images(self, content: str, chapter_path: Path) -> list[ImageRef]:
        """Validate that all referenced images exist.

        Args:
            content: The markdown content to validate.
            chapter_path: Path to the chapter file.

        Returns:
            List of ImageRef objects for missing images only.
        """
        images = self.extract_images(content, chapter_path, validate=True)
        return [img for img in images if not img.exists]

    def _resolve_image_path(self, img_path: str, chapter_path: Path) -> Path:
        """Resolve an image path relative to the chapter.

        Args:
            img_path: The image path from markdown.
            chapter_path: Path to the chapter file.

        Returns:
            Absolute path to the image file.
        """
        # Handle paths starting with ./
        if img_path.startswith("./"):
            img_path = img_path[2:]

        # Resolve relative to chapter directory
        chapter_dir = chapter_path.parent
        return (chapter_dir / img_path).resolve()
