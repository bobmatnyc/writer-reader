"""Command-line interface for MD Book Tools.

Provides a Click-based CLI for reading and writing markdown books.
This is the single entry point for all command-line operations.
"""

import sys
from importlib.metadata import version as get_version
from pathlib import Path

import click

from .infrastructure import configure_services
from .services import IBookService


# Get version from package metadata
try:
    __version__ = get_version("mdbook")
except Exception:
    __version__ = "3.0.0"  # Fallback version


# Context key for book service
BOOK_SERVICE_KEY = "book_service"


def get_book_service(ctx: click.Context) -> IBookService:
    """Get the book service from click context.

    Args:
        ctx: The click context.

    Returns:
        The configured IBookService instance.
    """
    return ctx.obj[BOOK_SERVICE_KEY]


@click.group()
@click.version_option(version=__version__, prog_name="mdbook")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """MD Book Tools - Read and write markdown books.

    A command-line tool for working with markdown-based books.
    Supports multiple formats including mdBook, GitBook, Leanpub,
    and Bookdown.
    """
    ctx.ensure_object(dict)
    container = configure_services()
    ctx.obj[BOOK_SERVICE_KEY] = container.resolve(IBookService)


@cli.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option(
    "--chapter", "-c",
    type=int,
    help="Start reading at specific chapter number.",
)
@click.pass_context
def read(ctx: click.Context, path: str, chapter: int | None) -> None:
    """Read a markdown book interactively.

    PATH is the root directory of the book (default: current directory).

    Displays the book content with simple navigation between chapters.
    """
    book_service = get_book_service(ctx)
    book_path = Path(path).resolve()

    try:
        book = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: Invalid book structure - {e}", err=True)
        sys.exit(1)

    if not book.chapters:
        click.echo("No chapters found in book.")
        return

    click.echo(f"\n{book.metadata.title}")
    if book.metadata.author:
        click.echo(f"by {book.metadata.author}")
    click.echo("=" * 40)
    click.echo(f"Found {len(book.chapters)} chapter(s)\n")

    # Determine starting chapter
    if chapter is not None:
        current_idx = None
        for idx, ch in enumerate(book.chapters):
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
        ch = book.chapters[current_idx]
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
                        _show_toc(book.chapters)
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
            if current_idx < len(book.chapters) - 1:
                current_idx += 1
            else:
                click.echo("End of book.")
        elif cmd.lower() == "p":
            current_idx = max(0, current_idx - 1)
        elif cmd.lower() == "t":
            _show_toc(book.chapters)
        elif cmd.isdigit():
            target = int(cmd)
            for idx, ch in enumerate(book.chapters):
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
@click.argument("path", type=click.Path())
@click.option(
    "--title", "-t",
    required=True,
    help="The book title.",
)
@click.option(
    "--author", "-a",
    required=True,
    help="The book author.",
)
@click.pass_context
def init(ctx: click.Context, path: str, title: str, author: str) -> None:
    """Initialize a new book project.

    PATH is the directory where the book will be created.

    Creates the directory structure, configuration files, and
    an empty SUMMARY.md for a new markdown book.
    """
    book_service = get_book_service(ctx)
    book_path = Path(path).resolve()

    try:
        book = book_service.create_book(book_path, title, author)
        click.echo(f"Created new book: {book.metadata.title}")
        click.echo(f"  Location: {book.root_path}")
        click.echo(f"  Author: {book.metadata.author}")
        click.echo("\nNext steps:")
        click.echo(f"  cd {path}")
        click.echo("  mdbook new-chapter -t 'Introduction'")
    except FileExistsError:
        click.echo(f"Error: A book already exists at {book_path}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Error: Permission denied - {e}", err=True)
        sys.exit(1)


@cli.command("new-chapter")
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option(
    "--title", "-t",
    required=True,
    help="The chapter title.",
)
@click.option(
    "--draft", "-d",
    is_flag=True,
    help="Mark chapter as draft.",
)
@click.pass_context
def new_chapter(
    ctx: click.Context,
    path: str,
    title: str,
    draft: bool,
) -> None:
    """Add a new chapter to a book.

    PATH is the root directory of the book (default: current directory).

    Creates a new chapter file with frontmatter and updates SUMMARY.md.
    """
    book_service = get_book_service(ctx)
    book_path = Path(path).resolve()

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
@click.argument("path", type=click.Path(exists=True), default=".")
@click.pass_context
def toc(ctx: click.Context, path: str) -> None:
    """Regenerate table of contents.

    PATH is the root directory of the book (default: current directory).

    Scans the chapters directory and regenerates SUMMARY.md based on
    the current chapter files.
    """
    book_service = get_book_service(ctx)
    book_path = Path(path).resolve()

    try:
        book_service.update_toc(book_path)
        click.echo(f"Updated SUMMARY.md in {book_path}")
    except FileNotFoundError as e:
        click.echo(f"Error: No book found - {e}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Error: Permission denied - {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.pass_context
def info(ctx: click.Context, path: str) -> None:
    """Show book information.

    PATH is the root directory of the book (default: current directory).

    Displays the book metadata and chapter list.
    """
    book_service = get_book_service(ctx)
    book_path = Path(path).resolve()

    try:
        book = book_service.get_book_info(book_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: Invalid book structure - {e}", err=True)
        sys.exit(1)

    click.echo(f"\nTitle: {book.metadata.title}")
    if book.metadata.author:
        click.echo(f"Author: {book.metadata.author}")
    if book.metadata.description:
        click.echo(f"Description: {book.metadata.description}")
    click.echo(f"Language: {book.metadata.language}")
    click.echo(f"Location: {book.root_path}")

    click.echo(f"\nChapters ({len(book.chapters)}):")
    for ch in book.chapters:
        prefix = "Intro" if ch.is_intro else f"{ch.number:4}"
        draft = " [DRAFT]" if ch.metadata.draft else ""
        click.echo(f"  {prefix}. {ch.title}{draft}")


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


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
