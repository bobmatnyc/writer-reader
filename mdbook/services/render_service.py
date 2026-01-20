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

# Theme CSS with CSS custom properties for light/dark modes
THEME_CSS = """
        /* Theme initialization - prevent flash of wrong theme */
        :root {
            color-scheme: light dark;
        }

        /* Light theme (default) */
        :root, [data-theme="light"] {
            --bg-primary: #ffffff;
            --bg-secondary: #f5f5f5;
            --bg-tertiary: #f9f9f9;
            --text-primary: #333333;
            --text-secondary: #666666;
            --text-heading: #2c3e50;
            --border-color: #dddddd;
            --border-light: #eeeeee;
            --link-color: #0066cc;
            --link-hover: #004499;
            --code-bg: #f5f5f5;
            --code-text: #333333;
            --highlight-bg: #ffffcc;
            --blockquote-border: #dddddd;
            --mermaid-bg: #ffffff;
        }

        /* Dark theme */
        [data-theme="dark"] {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-tertiary: #0f0f23;
            --text-primary: #e4e4e7;
            --text-secondary: #a1a1aa;
            --text-heading: #f4f4f5;
            --border-color: #3f3f46;
            --border-light: #27272a;
            --link-color: #60a5fa;
            --link-hover: #93c5fd;
            --code-bg: #0f0f23;
            --code-text: #e4e4e7;
            --highlight-bg: #422006;
            --blockquote-border: #3f3f46;
            --mermaid-bg: #1a1a2e;
        }

        /* System theme - follows OS preference */
        @media (prefers-color-scheme: dark) {
            [data-theme="system"] {
                --bg-primary: #1a1a2e;
                --bg-secondary: #16213e;
                --bg-tertiary: #0f0f23;
                --text-primary: #e4e4e7;
                --text-secondary: #a1a1aa;
                --text-heading: #f4f4f5;
                --border-color: #3f3f46;
                --border-light: #27272a;
                --link-color: #60a5fa;
                --link-hover: #93c5fd;
                --code-bg: #0f0f23;
                --code-text: #e4e4e7;
                --highlight-bg: #422006;
                --blockquote-border: #3f3f46;
                --mermaid-bg: #1a1a2e;
            }
        }

        /* Smooth theme transitions */
        body, body * {
            transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
        }

        /* Base styles using CSS variables */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            background-color: var(--bg-primary);
            color: var(--text-primary);
        }

        h1, h2, h3, h4 { color: var(--text-heading); }

        a { color: var(--link-color); }
        a:hover { color: var(--link-hover); }

        pre {
            background: var(--code-bg);
            color: var(--code-text);
            padding: 1rem;
            overflow-x: auto;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }

        code {
            background: var(--code-bg);
            color: var(--code-text);
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }

        pre code { background: none; padding: 0; border: none; }

        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }

        th, td {
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            text-align: left;
        }

        th { background: var(--bg-secondary); }
        tr:nth-child(even) { background: var(--bg-tertiary); }

        blockquote {
            border-left: 4px solid var(--blockquote-border);
            margin: 0;
            padding-left: 1rem;
            color: var(--text-secondary);
            background: var(--bg-tertiary);
            padding: 0.5rem 1rem;
            border-radius: 0 4px 4px 0;
        }

        .task-list { list-style: none; padding-left: 0; }
        .task-list-item input { margin-right: 0.5rem; }

        .mermaid {
            background: var(--mermaid-bg);
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }

        .footnote { font-size: 0.9em; color: var(--text-secondary); }

        nav.page-nav {
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-light);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        nav.page-nav .nav-links { display: flex; align-items: center; flex-wrap: wrap; }
        nav.page-nav .nav-links a { margin-right: 1rem; }

        .toc {
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 2rem;
            border: 1px solid var(--border-light);
        }

        .toc ul { margin: 0.5rem 0; padding-left: 1.5rem; }

        img { max-width: 100%; height: auto; border-radius: 4px; }

        .highlight { background: var(--highlight-bg); }

        /* Theme switcher styles */
        .theme-switcher {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem;
            background: var(--bg-secondary);
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }

        .theme-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border: none;
            background: transparent;
            cursor: pointer;
            border-radius: 4px;
            color: var(--text-secondary);
            font-size: 1rem;
            transition: all 0.15s ease;
        }

        .theme-btn:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .theme-btn.active {
            background: var(--bg-primary);
            color: var(--text-heading);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .theme-btn[title]::after {
            content: attr(title);
            position: absolute;
            bottom: -1.5rem;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.7rem;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.15s;
        }

        /* Pygments/CodeHilite dark theme overrides */
        [data-theme="dark"] .highlight .hll { background-color: #49483e; }
        [data-theme="dark"] .highlight .c { color: #75715e; } /* Comment */
        [data-theme="dark"] .highlight .k { color: #66d9ef; } /* Keyword */
        [data-theme="dark"] .highlight .n { color: #f8f8f2; } /* Name */
        [data-theme="dark"] .highlight .o { color: #f92672; } /* Operator */
        [data-theme="dark"] .highlight .p { color: #f8f8f2; } /* Punctuation */
        [data-theme="dark"] .highlight .s { color: #e6db74; } /* String */
        [data-theme="dark"] .highlight .m { color: #ae81ff; } /* Number */
        [data-theme="dark"] .highlight .na { color: #a6e22e; } /* Name.Attribute */
        [data-theme="dark"] .highlight .nb { color: #f8f8f2; } /* Name.Builtin */
        [data-theme="dark"] .highlight .nc { color: #a6e22e; } /* Name.Class */
        [data-theme="dark"] .highlight .nf { color: #a6e22e; } /* Name.Function */
        [data-theme="dark"] .highlight .nn { color: #f8f8f2; } /* Name.Namespace */

        @media (prefers-color-scheme: dark) {
            [data-theme="system"] .highlight .hll { background-color: #49483e; }
            [data-theme="system"] .highlight .c { color: #75715e; }
            [data-theme="system"] .highlight .k { color: #66d9ef; }
            [data-theme="system"] .highlight .n { color: #f8f8f2; }
            [data-theme="system"] .highlight .o { color: #f92672; }
            [data-theme="system"] .highlight .p { color: #f8f8f2; }
            [data-theme="system"] .highlight .s { color: #e6db74; }
            [data-theme="system"] .highlight .m { color: #ae81ff; }
            [data-theme="system"] .highlight .na { color: #a6e22e; }
            [data-theme="system"] .highlight .nb { color: #f8f8f2; }
            [data-theme="system"] .highlight .nc { color: #a6e22e; }
            [data-theme="system"] .highlight .nf { color: #a6e22e; }
            [data-theme="system"] .highlight .nn { color: #f8f8f2; }
        }
"""

# Theme initialization script - runs before body renders to prevent flash
THEME_INIT_SCRIPT = """
    <script>
        (function() {
            const stored = localStorage.getItem('mdbook-theme');
            const theme = stored || 'system';
            document.documentElement.setAttribute('data-theme', theme);
        })();
    </script>
"""

# Theme switcher JavaScript
THEME_SWITCHER_JS = """
<script>
(function() {
    const STORAGE_KEY = 'mdbook-theme';

    function getStoredTheme() {
        return localStorage.getItem(STORAGE_KEY) || 'system';
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(STORAGE_KEY, theme);
        updateButtons(theme);
        updateMermaid(theme);
    }

    function updateButtons(theme) {
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === theme);
        });
    }

    function getEffectiveTheme(theme) {
        if (theme === 'system') {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return theme;
    }

    function updateMermaid(theme) {
        if (typeof mermaid !== 'undefined' && mermaid.initialize) {
            const effectiveTheme = getEffectiveTheme(theme);
            const mermaidTheme = effectiveTheme === 'dark' ? 'dark' : 'default';
            mermaid.initialize({ startOnLoad: false, theme: mermaidTheme });
            // Re-render existing diagrams
            document.querySelectorAll('.mermaid').forEach(el => {
                if (el.dataset.processed) {
                    const code = el.dataset.code || el.textContent;
                    el.removeAttribute('data-processed');
                    el.innerHTML = code;
                }
            });
            mermaid.run();
        }
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        const currentTheme = getStoredTheme();
        updateButtons(currentTheme);

        // Add click handlers
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', () => setTheme(btn.dataset.theme));
        });

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (getStoredTheme() === 'system') {
                updateMermaid('system');
            }
        });
    });
})();
</script>
"""

# Theme switcher HTML component
THEME_SWITCHER_HTML = """
<div class="theme-switcher">
    <button class="theme-btn" data-theme="light" title="Light">&#9728;</button>
    <button class="theme-btn" data-theme="dark" title="Dark">&#9790;</button>
    <button class="theme-btn" data-theme="system" title="System">&#128187;</button>
</div>
"""

# HTML template for rendered chapters
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {theme_init}
    <style>
{theme_css}
    </style>
    {extra_head}
</head>
<body>
    {nav}
    <article>
        {content}
    </article>
    {scripts}
    {theme_js}
</body>
</html>"""

# Mermaid initialization script - theme-aware
MERMAID_SCRIPT = """
<script type="module">
    import mermaid from '{mermaid_cdn}';

    function getEffectiveTheme() {{
        const stored = localStorage.getItem('mdbook-theme') || 'system';
        if (stored === 'system') {{
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }}
        return stored;
    }}

    const effectiveTheme = getEffectiveTheme();
    const mermaidTheme = effectiveTheme === 'dark' ? 'dark' : 'default';

    mermaid.initialize({{ startOnLoad: true, theme: mermaidTheme }});

    // Store mermaid module globally for theme switcher
    window.mermaid = mermaid;
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

        # Build navigation with theme switcher
        nav = ""
        if include_nav:
            nav = self._build_nav(chapter, book)

        return HTML_TEMPLATE.format(
            lang=book.metadata.language,
            title=f"{chapter.title} - {book.metadata.title}",
            theme_init=THEME_INIT_SCRIPT,
            theme_css=THEME_CSS,
            extra_head="",
            nav=nav,
            content=html_content,
            scripts=scripts,
            theme_js=THEME_SWITCHER_JS,
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
        """Build navigation HTML for a chapter with theme switcher."""
        nav_items = []

        # Find chapter index
        chapter_idx = None
        for idx, ch in enumerate(book.chapters):
            if ch.file_path == chapter.file_path:
                chapter_idx = idx
                break

        if chapter_idx is None:
            return THEME_SWITCHER_HTML

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

        nav_links = f'<div class="nav-links">{"".join(nav_items)}</div>'
        return f'<nav class="page-nav">{nav_links}{THEME_SWITCHER_HTML}</nav>'

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

        # Build nav with just the theme switcher
        nav = f'<nav class="page-nav">{THEME_SWITCHER_HTML}</nav>'

        return HTML_TEMPLATE.format(
            lang=book.metadata.language,
            title=book.metadata.title,
            theme_init=THEME_INIT_SCRIPT,
            theme_css=THEME_CSS,
            extra_head="",
            nav=nav,
            content=content,
            scripts="",
            theme_js=THEME_SWITCHER_JS,
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
