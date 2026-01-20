"""Render service implementation.

Provides markdown to HTML rendering using the markdown library with
pymdown-extensions for enhanced features like tables, footnotes,
task lists, and code highlighting.
"""

import re
from pathlib import Path
from typing import Optional

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension

from ..domain import Book, Chapter
from ..repositories.interfaces import IFileRepository
from .interfaces import IReaderService


# Mermaid.js CDN URL
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.esm.min.mjs"

# HTML template for rendered chapters
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }}
        h1, h2, h3, h4 {{ color: #2c3e50; }}
        pre {{ background: #f5f5f5; padding: 1rem; overflow-x: auto; border-radius: 4px; }}
        code {{ background: #f5f5f5; padding: 0.2em 0.4em; border-radius: 3px; }}
        pre code {{ background: none; padding: 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #ddd; padding: 0.75rem; text-align: left; }}
        th {{ background: #f5f5f5; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 1rem; color: #666; }}
        .task-list {{ list-style: none; padding-left: 0; }}
        .task-list-item input {{ margin-right: 0.5rem; }}
        .mermaid {{ background: #fff; padding: 1rem; margin: 1rem 0; }}
        .footnote {{ font-size: 0.9em; }}
        nav {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #eee; }}
        nav a {{ margin-right: 1rem; }}
        .toc {{ background: #f9f9f9; padding: 1rem; border-radius: 4px; margin-bottom: 2rem; }}
        .toc ul {{ margin: 0.5rem 0; padding-left: 1.5rem; }}
        img {{ max-width: 100%; height: auto; }}
        .highlight {{ background: #ffffcc; }}
    </style>
    {extra_head}
</head>
<body>
    {nav}
    <article>
        {content}
    </article>
    {scripts}
</body>
</html>"""

# Mermaid initialization script
MERMAID_SCRIPT = """
<script type="module">
    import mermaid from '{mermaid_cdn}';
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
</script>
"""


class RenderService:
    """Service for rendering markdown to HTML.

    Uses the markdown library with pymdown-extensions for:
    - Tables
    - Footnotes
    - Task lists
    - Code highlighting with Pygments
    - Mermaid diagram support
    """

    def __init__(
        self,
        file_repo: IFileRepository,
        reader_service: IReaderService,
    ) -> None:
        """Initialize the render service with required dependencies.

        Args:
            file_repo: Repository for file system operations.
            reader_service: Service for reading chapter content.
        """
        self._file_repo = file_repo
        self._reader_service = reader_service
        self._md = self._create_markdown_processor()

    def _create_markdown_processor(self) -> markdown.Markdown:
        """Create configured markdown processor with extensions."""
        try:
            import pymdownx  # noqa: F401 - verify package available

            extensions = [
                TableExtension(),
                TocExtension(permalink=True, slugify=self._slugify),
                FencedCodeExtension(),
                CodeHiliteExtension(css_class="highlight", guess_lang=True),
                "footnotes",
                "pymdownx.tasklist",
                "pymdownx.superfences",
            ]
            extension_configs = {
                "pymdownx.tasklist": {"custom_checkbox": True},
                "pymdownx.superfences": {
                    "custom_fences": [
                        {
                            "name": "mermaid",
                            "class": "mermaid",
                            "format": self._mermaid_format,
                        }
                    ]
                },
            }
        except ImportError:
            # Fallback without pymdownx
            extensions = [
                TableExtension(),
                TocExtension(permalink=True, slugify=self._slugify),
                FencedCodeExtension(),
                CodeHiliteExtension(css_class="highlight", guess_lang=True),
                "footnotes",
            ]
            extension_configs = {}

        return markdown.Markdown(
            extensions=extensions,
            extension_configs=extension_configs,
            output_format="html5",
        )

    def _mermaid_format(
        self,
        source: str,
        language: str,
        css_class: str,
        options: dict,
        md: markdown.Markdown,
        **kwargs,
    ) -> str:
        """Custom formatter for mermaid code blocks."""
        return f'<div class="mermaid">\n{source}\n</div>'

    def _slugify(self, value: str, separator: str = "-") -> str:
        """Convert heading text to URL-friendly slug."""
        value = re.sub(r"[^\w\s-]", "", value.lower().strip())
        return re.sub(r"[\s_-]+", separator, value).strip(separator)

    def render_chapter(
        self,
        chapter: Chapter,
        content: Optional[str] = None,
        include_toc: bool = True,
    ) -> str:
        """Render a chapter's markdown content to HTML.

        Args:
            chapter: The chapter to render.
            content: Optional pre-loaded content (otherwise reads from file).
            include_toc: Whether to include a table of contents.

        Returns:
            The rendered HTML content (body only, not full document).
        """
        if content is None:
            content = self._reader_service.get_chapter_content(chapter)
            # Strip frontmatter
            content = self._strip_frontmatter(content)

        # Expand [TOC] markers
        if "[TOC]" in content:
            content = content.replace("[TOC]", "[TOC]")  # TocExtension handles this

        # Reset markdown processor state
        self._md.reset()

        # Render markdown to HTML
        html_content = self._md.convert(content)

        # Get TOC if available
        toc_html = ""
        if include_toc and hasattr(self._md, "toc"):
            toc_html = f'<nav class="toc">\n<h2>Contents</h2>\n{self._md.toc}\n</nav>'

        return f"{toc_html}\n{html_content}"

    def render_chapter_full(
        self,
        chapter: Chapter,
        book: Book,
        content: Optional[str] = None,
        include_nav: bool = True,
    ) -> str:
        """Render a chapter as a complete HTML document.

        Args:
            chapter: The chapter to render.
            book: The book containing the chapter.
            content: Optional pre-loaded content.
            include_nav: Whether to include navigation links.

        Returns:
            Complete HTML document string.
        """
        html_content = self.render_chapter(chapter, content)

        # Check for mermaid content
        has_mermaid = self._has_mermaid(
            content or self._reader_service.get_chapter_content(chapter)
        )
        scripts = MERMAID_SCRIPT.format(mermaid_cdn=MERMAID_CDN) if has_mermaid else ""

        # Build navigation
        nav = ""
        if include_nav:
            nav = self._build_nav(chapter, book)

        return HTML_TEMPLATE.format(
            lang=book.metadata.language,
            title=f"{chapter.title} - {book.metadata.title}",
            extra_head="",
            nav=nav,
            content=html_content,
            scripts=scripts,
        )

    def render_book(
        self,
        book: Book,
        output_dir: Path,
    ) -> list[Path]:
        """Render all chapters of a book to HTML files.

        Args:
            book: The book to render.
            output_dir: Directory to write HTML files to.

        Returns:
            List of paths to generated HTML files.
        """
        self._file_repo.mkdir(output_dir, parents=True, exist_ok=True)

        generated_files: list[Path] = []

        for chapter in book.chapters:
            html = self.render_chapter_full(chapter, book)

            # Generate output filename
            if chapter.is_intro:
                filename = "index.html"
            else:
                filename = f"chapter-{chapter.number:02d}.html"

            output_path = output_dir / filename
            self._file_repo.write_file(output_path, html)
            generated_files.append(output_path)

        # Generate index page if no intro chapter
        if not any(ch.is_intro for ch in book.chapters):
            index_html = self._generate_index_page(book)
            index_path = output_dir / "index.html"
            self._file_repo.write_file(index_path, index_html)
            generated_files.append(index_path)

        return generated_files

    def _build_nav(self, chapter: Chapter, book: Book) -> str:
        """Build navigation HTML for a chapter."""
        nav_items = []

        # Find chapter index
        chapter_idx = None
        for idx, ch in enumerate(book.chapters):
            if ch.file_path == chapter.file_path:
                chapter_idx = idx
                break

        if chapter_idx is None:
            return ""

        # Previous link
        if chapter_idx > 0:
            prev_ch = book.chapters[chapter_idx - 1]
            prev_file = (
                "index.html"
                if prev_ch.is_intro
                else f"chapter-{prev_ch.number:02d}.html"
            )
            nav_items.append(f'<a href="{prev_file}">&larr; {prev_ch.title}</a>')

        # Index link
        nav_items.append('<a href="index.html">Contents</a>')

        # Next link
        if chapter_idx < len(book.chapters) - 1:
            next_ch = book.chapters[chapter_idx + 1]
            next_file = (
                "index.html"
                if next_ch.is_intro
                else f"chapter-{next_ch.number:02d}.html"
            )
            nav_items.append(f'<a href="{next_file}">{next_ch.title} &rarr;</a>')

        return f'<nav>{"".join(nav_items)}</nav>'

    def _generate_index_page(self, book: Book) -> str:
        """Generate index page listing all chapters."""
        chapters_html = ["<ul>"]
        for ch in book.chapters:
            filename = "index.html" if ch.is_intro else f"chapter-{ch.number:02d}.html"
            prefix = "Intro" if ch.is_intro else f"{ch.number}"
            chapters_html.append(
                f'<li><a href="{filename}">{prefix}. {ch.title}</a></li>'
            )
        chapters_html.append("</ul>")

        content = f"<h1>{book.metadata.title}</h1>\n"
        if book.metadata.author:
            content += f"<p>by {book.metadata.author}</p>\n"
        if book.metadata.description:
            content += f"<p>{book.metadata.description}</p>\n"
        content += "\n<h2>Chapters</h2>\n" + "\n".join(chapters_html)

        return HTML_TEMPLATE.format(
            lang=book.metadata.language,
            title=book.metadata.title,
            extra_head="",
            nav="",
            content=content,
            scripts="",
        )

    def _has_mermaid(self, content: str) -> bool:
        """Check if content contains mermaid blocks."""
        return "```mermaid" in content

    def _strip_frontmatter(self, content: str) -> str:
        """Strip YAML frontmatter from content."""
        if not content.startswith("---"):
            return content

        match = re.search(r"\n---\s*\n", content[3:])
        if match:
            return content[3 + match.end() :].lstrip()
        return content
