"""Command-line interface for MD Book Tools.

Provides a Click-based CLI for reading and writing markdown books.
This is the single entry point for all command-line operations.
"""

import http.server
import json
import shutil
import socket
import socketserver
import sys
from datetime import datetime
from importlib.metadata import version as get_version
from pathlib import Path

import click

from .infrastructure import configure_services
from .services import IBookService

# Get version from package metadata
try:
    __version__ = get_version("md-book")
except Exception:
    __version__ = "0.0.0"  # Fallback version


# Context keys
BOOK_SERVICE_KEY = "book_service"
BOOK_PATH_KEY = "book_path"


def get_book_service(ctx: click.Context) -> IBookService:
    """Get the book service from click context.

    Args:
        ctx: The click context.

    Returns:
        The configured IBookService instance.
    """
    return ctx.obj[BOOK_SERVICE_KEY]


def resolve_book_path(ctx: click.Context, book_arg: str | None) -> Path:
    """Resolve the book path from argument or global option.

    Args:
        ctx: The click context.
        book_arg: The book path argument from command (overrides global).

    Returns:
        The resolved absolute book path.
    """
    if book_arg is not None:
        return Path(book_arg).resolve()
    return ctx.obj.get(BOOK_PATH_KEY, Path.cwd())


@click.group()
@click.option(
    "--book",
    "-b",
    type=click.Path(),
    help="Path to book directory (default: current directory).",
)
@click.version_option(version=__version__, prog_name="mdbook")
@click.pass_context
def cli(ctx: click.Context, book: str | None) -> None:
    """MD Book Tools - Read and write markdown books.

    A command-line tool for working with markdown-based books.
    Supports multiple formats including mdBook, GitBook, Leanpub,
    and Bookdown.

    Use --book/-b to set a default book path for all commands,
    or pass a BOOK argument to individual commands.
    """
    ctx.ensure_object(dict)
    container = configure_services()
    ctx.obj[BOOK_SERVICE_KEY] = container.resolve(IBookService)
    ctx.obj[BOOK_PATH_KEY] = Path(book).resolve() if book else Path.cwd()


@cli.command()
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.option(
    "--chapter",
    "-c",
    type=int,
    help="Start reading at specific chapter number.",
)
@click.pass_context
def read(ctx: click.Context, book: str | None, chapter: int | None) -> None:
    """Read a markdown book interactively.

    BOOK is the root directory of the book (default: current directory or global --book).

    Displays the book content with simple navigation between chapters.
    """
    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        book_info = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: Invalid book structure - {e}", err=True)
        sys.exit(1)

    if not book_info.chapters:
        click.echo("No chapters found in book.")
        return

    click.echo(f"\n{book_info.metadata.title}")
    if book_info.metadata.author:
        click.echo(f"by {book_info.metadata.author}")
    click.echo("=" * 40)
    click.echo(f"Found {len(book_info.chapters)} chapter(s)\n")

    # Determine starting chapter
    if chapter is not None:
        current_idx = None
        for idx, ch in enumerate(book_info.chapters):
            if ch.number == chapter:
                current_idx = idx
                break
        if current_idx is None:
            click.echo(f"Chapter {chapter} not found.", err=True)
            sys.exit(1)
    else:
        current_idx = 0

    # Simple interactive reader
    while True:
        ch = book_info.chapters[current_idx]
        click.echo(f"\n--- Chapter {ch.number or 'Intro'}: {ch.title} ---\n")

        try:
            content = book_service.read_chapter(book_path, ch.number or 0)
            # Paginate long content
            lines = content.split("\n")
            page_size = 30

            for i in range(0, len(lines), page_size):
                page = "\n".join(lines[i : i + page_size])
                click.echo(page)

                if i + page_size < len(lines):
                    cmd = click.prompt(
                        "\n[Enter=more, n=next, p=prev, q=quit, t=toc]",
                        default="",
                        show_default=False,
                    )
                    if cmd.lower() == "q":
                        return
                    elif cmd.lower() == "n":
                        break
                    elif cmd.lower() == "p":
                        current_idx = max(0, current_idx - 1)
                        break
                    elif cmd.lower() == "t":
                        _show_toc(book_info.chapters)
                        break

        except (FileNotFoundError, KeyError) as e:
            click.echo(f"Error reading chapter: {e}", err=True)

        # Navigation prompt at end of chapter
        cmd = click.prompt(
            "\n[n=next, p=prev, q=quit, t=toc, number=go to chapter]",
            default="n",
            show_default=False,
        )

        if cmd.lower() == "q":
            break
        elif cmd.lower() == "n":
            if current_idx < len(book_info.chapters) - 1:
                current_idx += 1
            else:
                click.echo("End of book.")
        elif cmd.lower() == "p":
            current_idx = max(0, current_idx - 1)
        elif cmd.lower() == "t":
            _show_toc(book_info.chapters)
        elif cmd.isdigit():
            target = int(cmd)
            for idx, ch in enumerate(book_info.chapters):
                if ch.number == target:
                    current_idx = idx
                    break
            else:
                click.echo(f"Chapter {target} not found.")


def _show_toc(chapters: list) -> None:
    """Display table of contents."""
    click.echo("\n--- Table of Contents ---")
    for ch in chapters:
        prefix = "  " if ch.is_intro else f"{ch.number:2}."
        draft = " [DRAFT]" if ch.metadata.draft else ""
        click.echo(f"  {prefix} {ch.title}{draft}")
    click.echo()


@cli.command()
@click.argument("book", type=click.Path(), default=None, required=False)
@click.option(
    "--title",
    "-t",
    required=True,
    help="The book title.",
)
@click.option(
    "--author",
    "-a",
    required=True,
    help="The book author.",
)
@click.pass_context
def init(ctx: click.Context, book: str | None, title: str, author: str) -> None:
    """Initialize a new book project.

    BOOK is the directory where the book will be created
    (default: current directory or global --book).

    Creates the directory structure, configuration files, and
    an empty SUMMARY.md for a new markdown book.
    """
    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        new_book = book_service.create_book(book_path, title, author)
        click.echo(f"Created new book: {new_book.metadata.title}")
        click.echo(f"  Location: {new_book.root_path}")
        click.echo(f"  Author: {new_book.metadata.author}")
        click.echo("\nNext steps:")
        click.echo(f"  cd {book_path}")
        click.echo("  mdbook new-chapter -t 'Introduction'")
    except FileExistsError:
        click.echo(f"Error: A book already exists at {book_path}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Error: Permission denied - {e}", err=True)
        sys.exit(1)


@cli.command("new-chapter")
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.option(
    "--title",
    "-t",
    required=True,
    help="The chapter title.",
)
@click.option(
    "--draft",
    "-d",
    is_flag=True,
    help="Mark chapter as draft.",
)
@click.pass_context
def new_chapter(
    ctx: click.Context,
    book: str | None,
    title: str,
    draft: bool,
) -> None:
    """Add a new chapter to a book.

    BOOK is the root directory of the book (default: current directory or global --book).

    Creates a new chapter file with frontmatter and updates SUMMARY.md.
    """
    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        chapter = book_service.add_chapter(book_path, title, draft)
        status = " (draft)" if draft else ""
        click.echo(f"Created chapter {chapter.number}: {chapter.title}{status}")
        click.echo(f"  File: {chapter.file_path}")
    except FileNotFoundError as e:
        click.echo(f"Error: No book found - {e}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Error: Permission denied - {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.option(
    "--preserve-structure/-P",
    "--no-preserve-structure",
    "preserve_structure",
    default=True,
    help="Preserve existing SUMMARY.md hierarchy (default). Use -P to regenerate flat.",
)
@click.pass_context
def toc(ctx: click.Context, book: str | None, preserve_structure: bool) -> None:
    """Regenerate table of contents.

    BOOK is the root directory of the book (default: current directory or global --book).

    By default, preserves existing SUMMARY.md hierarchy (Part headers, nesting)
    and only adds new files. Use --no-preserve-structure/-P to regenerate flat.
    """
    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        book_service.update_toc(book_path, preserve_structure)
        mode = "preserved structure" if preserve_structure else "flat structure"
        click.echo(f"Updated SUMMARY.md in {book_path} ({mode})")
    except FileNotFoundError as e:
        click.echo(f"Error: No book found - {e}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Error: Permission denied - {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.pass_context
def info(ctx: click.Context, book: str | None) -> None:
    """Show book information.

    BOOK is the root directory of the book (default: current directory or global --book).

    Displays the book metadata and chapter list.
    """
    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        book_info = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: Invalid book structure - {e}", err=True)
        sys.exit(1)

    click.echo(f"\nTitle: {book_info.metadata.title}")
    if book_info.metadata.author:
        click.echo(f"Author: {book_info.metadata.author}")
    if book_info.metadata.description:
        click.echo(f"Description: {book_info.metadata.description}")
    click.echo(f"Language: {book_info.metadata.language}")
    click.echo(f"Location: {book_info.root_path}")

    click.echo(f"\nChapters ({len(book_info.chapters)}):")
    for ch in book_info.chapters:
        prefix = "Intro" if ch.is_intro else f"{ch.number:4}"
        draft = " [DRAFT]" if ch.metadata.draft else ""
        click.echo(f"  {prefix}. {ch.title}{draft}")


def _find_available_port(start_port: int = 3500, max_port: int = 3509) -> int | None:
    """Find an available port in the specified range.

    Args:
        start_port: The first port to try.
        max_port: The last port to try.

    Returns:
        An available port number, or None if no ports are available.
    """
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            if result != 0:
                # Port is available (connection failed)
                return port
    return None


class _QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that suppresses console output."""

    def log_message(self, format: str, *args) -> None:
        """Suppress log messages by default."""
        pass


@cli.command()
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.option(
    "--port",
    "-p",
    type=int,
    default=None,
    help="Port to serve on (default: 3500, with fallback to 3501-3509 if busy).",
)
@click.pass_context
def serve(ctx: click.Context, book: str | None, port: int | None) -> None:
    """Serve the book locally via HTTP.

    BOOK is the root directory of the book (default: current directory or global --book).

    Starts a local HTTP server to preview the book. By default uses port 3500,
    with automatic fallback to ports 3501-3509 if the port is in use.

    Press Ctrl+C to stop the server.
    """
    book_path = resolve_book_path(ctx, book)

    # Verify the book exists
    if not book_path.exists():
        click.echo(f"Error: Book directory not found: {book_path}", err=True)
        sys.exit(1)

    # Determine port to use
    if port is not None:
        # User specified a port, use it directly
        actual_port = port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("localhost", actual_port)) == 0:
                click.echo(f"Error: Port {actual_port} is already in use.", err=True)
                sys.exit(1)
    else:
        # Find an available port in the default range
        actual_port = _find_available_port(3500, 3509)
        if actual_port is None:
            click.echo(
                "Error: All ports in range 3500-3509 are in use. "
                "Specify a different port with --port.",
                err=True,
            )
            sys.exit(1)

    # Create a handler that serves from the book directory
    class BookHTTPHandler(_QuietHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(book_path), **kwargs)

    # Start the server
    click.echo(f"Serving book at http://localhost:{actual_port}")
    click.echo(f"Book directory: {book_path}")
    click.echo("Press Ctrl+C to stop the server.")

    try:
        with socketserver.TCPServer(("", actual_port), BookHTTPHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")
    except OSError as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


@cli.command("serve-mcp")
def serve_mcp() -> None:
    """Start MCP server for Claude Code.

    Launches the Model Context Protocol server that exposes
    book operations as tools for AI assistants.

    The server communicates over stdio and provides tools for:
    - book_info: Get book metadata and chapter list
    - read_chapter: Read chapter content
    - list_chapters: List all chapters
    - create_book: Create a new book project
    - add_chapter: Add a chapter to a book
    - update_toc: Regenerate the table of contents
    """
    from .mcp import run_server

    run_server()


def _get_mdbook_install_path() -> Path:
    """Get the installation path of the mdbook package.

    Returns:
        Path to the directory containing the mdbook package.
    """
    # Get the path to this module's package directory
    package_path = Path(__file__).parent.parent.resolve()
    return package_path


def _build_mcp_config() -> dict:
    """Build the MCP server configuration for mdbook.

    Returns:
        Dict with the mdbook MCP server configuration.
    """
    install_path = _get_mdbook_install_path()
    return {
        "mdbook": {
            "command": "uv",
            "args": ["run", "--directory", str(install_path), "mdbook", "serve-mcp"],
        }
    }


def _load_mcp_config(config_path: Path) -> dict:
    """Load existing MCP configuration from file.

    Args:
        config_path: Path to the MCP config file.

    Returns:
        The parsed config dict, or empty structure if file doesn't exist.
    """
    if not config_path.exists():
        return {"mcpServers": {}}

    try:
        with open(config_path) as f:
            config = json.load(f)
            # Ensure mcpServers key exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            return config
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in {config_path}: {e}")


def _backup_config(config_path: Path) -> Path | None:
    """Create a backup of the config file if it exists.

    Args:
        config_path: Path to the config file.

    Returns:
        Path to the backup file, or None if no backup was needed.
    """
    if not config_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.with_suffix(f".{timestamp}.backup")
    shutil.copy2(config_path, backup_path)
    return backup_path


def _save_mcp_config(config_path: Path, config: dict) -> None:
    """Save MCP configuration to file.

    Args:
        config_path: Path to the MCP config file.
        config: The config dict to save.
    """
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")  # Add trailing newline


@cli.command()
@click.option(
    "--global",
    "-g",
    "global_config",
    is_flag=True,
    help="Install to global ~/.claude/mcp.json",
)
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(),
    help="Install to project .mcp.json",
)
@click.pass_context
def setup(ctx: click.Context, global_config: bool, project_path: str | None) -> None:
    """Auto-configure MCP integration with Claude Code.

    Adds mdbook MCP server to Claude Code configuration.

    Examples:
        mdbook setup              # Auto-detect (project if exists, else global)
        mdbook setup --global     # Install to ~/.claude/mcp.json
        mdbook setup -p /path     # Install to specific project's .mcp.json
    """
    # Determine which config file to update
    if global_config and project_path:
        raise click.ClickException("Cannot specify both --global and --project")

    if global_config:
        config_path = Path.home() / ".claude" / "mcp.json"
        location_type = "global"
    elif project_path:
        config_path = Path(project_path).resolve() / ".mcp.json"
        location_type = "project"
    else:
        # Auto-detect: use project config if it exists, otherwise global
        cwd_config = Path.cwd() / ".mcp.json"
        if cwd_config.exists():
            config_path = cwd_config
            location_type = "project"
        else:
            config_path = Path.home() / ".claude" / "mcp.json"
            location_type = "global"

    # Build the mdbook MCP server config
    mdbook_config = _build_mcp_config()

    # Backup existing config if present
    backup_path = _backup_config(config_path)
    if backup_path:
        click.echo(f"Backed up existing config to: {backup_path}")

    # Load existing config (or create empty structure)
    config = _load_mcp_config(config_path)

    # Check if mdbook is already configured
    existing_mdbook = config["mcpServers"].get("mdbook")
    if existing_mdbook:
        click.echo("Note: Updating existing mdbook configuration")

    # Merge the mdbook config
    config["mcpServers"].update(mdbook_config)

    # Save the updated config
    _save_mcp_config(config_path, config)

    # Display success message
    click.echo("\nSuccessfully configured mdbook MCP server!")
    click.echo(f"  Location: {config_path} ({location_type})")
    click.echo("\nAdded configuration:")
    click.echo(json.dumps(mdbook_config, indent=2))

    click.echo("\nClaude Code will now have access to mdbook tools.")
    click.echo("Restart Claude Code to load the new configuration.")


@cli.command()
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory for HTML files (default: book/html).",
)
@click.pass_context
def build(ctx: click.Context, book: str | None, output: str | None) -> None:
    """Build book to HTML with all features.

    BOOK is the root directory of the book (default: current directory or global --book).

    Renders all chapters to HTML with:
    - Syntax highlighting
    - Tables and footnotes
    - Task lists
    - Mermaid diagrams (client-side rendering)
    - Navigation between chapters
    """
    from .services import RenderService

    container = ctx.obj.get("_container")
    if container is None:
        from .infrastructure import configure_services

        container = configure_services()
        ctx.obj["_container"] = container

    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        book_info = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Determine output directory
    if output:
        output_dir = Path(output).resolve()
    else:
        output_dir = book_path / "html"

    # Get render service
    render_service = container.resolve(RenderService)

    click.echo(f"Building book: {book_info.metadata.title}")
    click.echo(f"Output directory: {output_dir}")

    try:
        generated = render_service.render_book(book_info, output_dir)
        click.echo(f"\nGenerated {len(generated)} HTML files:")
        for path in generated:
            click.echo(f"  {path.name}")
        click.echo(f"\nOpen {output_dir / 'index.html'} to view the book.")
    except PermissionError as e:
        click.echo(f"Error: Permission denied - {e}", err=True)
        sys.exit(1)


@cli.command("toc-gen")
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for TOC (default: stdout).",
)
@click.option(
    "--full",
    "-f",
    is_flag=True,
    help="Include intra-chapter headings in TOC.",
)
@click.pass_context
def toc_gen(
    ctx: click.Context, book: str | None, output: str | None, full: bool
) -> None:
    """Generate hierarchical table of contents.

    BOOK is the root directory of the book (default: current directory or global --book).

    Extracts all headings (##, ###, ####) from chapters and generates
    a hierarchical markdown TOC.
    """
    from .services import TocService

    container = ctx.obj.get("_container")
    if container is None:
        from .infrastructure import configure_services

        container = configure_services()
        ctx.obj["_container"] = container

    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        book_info = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Get TOC service
    toc_service = container.resolve(TocService)

    toc_md = toc_service.generate_toc_markdown(book_info, include_chapter_tocs=full)

    if output:
        output_path = Path(output).resolve()
        output_path.write_text(toc_md)
        click.echo(f"TOC written to {output_path}")
    else:
        click.echo(toc_md)


@cli.command("index-gen")
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for index (default: stdout).",
)
@click.pass_context
def index_gen(ctx: click.Context, book: str | None, output: str | None) -> None:
    """Generate alphabetical index from markers.

    BOOK is the root directory of the book (default: current directory or global --book).

    Extracts terms marked with {{index: term}} and generates
    an alphabetically sorted index with chapter/section references.
    """
    from .services import IndexService

    container = ctx.obj.get("_container")
    if container is None:
        from .infrastructure import configure_services

        container = configure_services()
        ctx.obj["_container"] = container

    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        book_info = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Get index service
    index_service = container.resolve(IndexService)

    index_md = index_service.generate_index_markdown(book_info)

    if output:
        output_path = Path(output).resolve()
        output_path.write_text(index_md)
        click.echo(f"Index written to {output_path}")
    else:
        click.echo(index_md)


@cli.command("validate-images")
@click.argument("book", type=click.Path(exists=True), default=None, required=False)
@click.pass_context
def validate_images(ctx: click.Context, book: str | None) -> None:
    """Validate that all referenced images exist.

    BOOK is the root directory of the book (default: current directory or global --book).

    Checks all ![alt](path) image references and reports any missing files.
    """
    from .services import ContentService

    container = ctx.obj.get("_container")
    if container is None:
        from .infrastructure import configure_services

        container = configure_services()
        ctx.obj["_container"] = container

    book_service = get_book_service(ctx)
    book_path = resolve_book_path(ctx, book)

    try:
        book_info = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Get services
    content_service = container.resolve(ContentService)
    from .services import IReaderService

    reader_service = container.resolve(IReaderService)

    missing_count = 0
    for chapter in book_info.chapters:
        content = reader_service.get_chapter_content(chapter)
        missing = content_service.validate_images(content, chapter.file_path)

        if missing:
            click.echo(f"\nChapter {chapter.number or 'Intro'}: {chapter.title}")
            for img in missing:
                click.echo(f"  Line {img.line_number}: {img.path}")
                missing_count += 1

    if missing_count == 0:
        click.echo("All image references are valid.")
    else:
        click.echo(f"\nFound {missing_count} missing image(s).")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
