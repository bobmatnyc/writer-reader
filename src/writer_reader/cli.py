#!/usr/bin/env python3
"""
Writer-Reader CLI

Commands:
    serve       Start the editor server
    segment     Segment chapters into individual files
    assemble    Assemble segments back into chapter files
    init        Initialize a new manuscript project
"""

from pathlib import Path

import click

from . import __version__


@click.group()
@click.version_option(version=__version__, prog_name="writer-reader")
def main():
    """Segment-based book manuscript editor with git integration."""
    pass


@main.command()
@click.option("--port", "-p", default=5555, help="Port to run the server on")
@click.option("--host", "-h", default="localhost", help="Host to bind to")
@click.option("--book-dir", "-d", type=click.Path(exists=True), help="Book directory path")
@click.option("--debug/--no-debug", default=True, help="Run in debug mode")
def serve(port: int, host: str, book_dir: str, debug: bool):
    """Start the editor server."""
    from .server import create_app

    book_path = Path(book_dir) if book_dir else Path.cwd()

    click.echo(f"Writer-Reader v{__version__}")
    click.echo(f"  Book directory: {book_path}")
    click.echo(f"  Server: http://{host}:{port}")
    click.echo()

    app = create_app(book_path)
    app.run(host=host, port=port, debug=debug)


@main.command()
@click.argument("book_dir", type=click.Path(exists=True), default=".")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing segments")
def segment(book_dir: str, force: bool):
    """Segment chapters into individual markdown files."""
    from .segmenter import segment_book

    book_path = Path(book_dir)
    click.echo(f"Segmenting chapters in {book_path}...")

    result = segment_book(book_path, force=force)

    click.echo(
        f"  Created {result['total_segments']} segments across {result['chapters']} chapters"
    )
    click.echo(f"  Output: {result['segments_dir']}")


@main.command()
@click.argument("book_dir", type=click.Path(exists=True), default=".")
@click.option("--chapter", "-c", type=int, help="Assemble specific chapter only")
def assemble(book_dir: str, chapter: int):
    """Assemble segments back into chapter files."""
    from .segmenter import assemble_chapters

    book_path = Path(book_dir)

    if chapter:
        click.echo(f"Assembling chapter {chapter}...")
        result = assemble_chapters(book_path, chapter_num=chapter)
    else:
        click.echo("Assembling all chapters...")
        result = assemble_chapters(book_path)

    click.echo(f"  Assembled {result['chapters_assembled']} chapters")


@main.command()
@click.argument("book_dir", type=click.Path(), default=".")
@click.option("--title", "-t", prompt="Book title", help="Title of the book")
@click.option("--author", "-a", prompt="Author name", help="Author name")
def init(book_dir: str, title: str, author: str):
    """Initialize a new manuscript project."""
    from .project import init_project

    book_path = Path(book_dir)
    click.echo(f"Initializing manuscript project in {book_path}...")

    result = init_project(book_path, title=title, author=author)

    click.echo(f"  Created: {result['created']}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Add chapter files to chapters/")
    click.echo("  2. Run: writer-reader segment")
    click.echo("  3. Run: writer-reader serve")


@main.command("update-toc")
@click.argument("book_dir", type=click.Path(exists=True), default=".")
@click.option(
    "--preserve-structure/--no-preserve-structure",
    "-p/-P",
    default=True,
    help="Preserve existing SUMMARY.md hierarchy (default: True)",
)
def update_toc(book_dir: str, preserve_structure: bool):
    """Update SUMMARY.md table of contents."""
    from .toc import update_summary

    book_path = Path(book_dir)
    click.echo(f"Updating SUMMARY.md in {book_path}...")

    result = update_summary(book_path, preserve_structure=preserve_structure)

    if preserve_structure:
        click.echo("  Mode: preserving existing structure")
    else:
        click.echo("  Mode: generating flat structure")

    click.echo(f"  Added: {len(result['added'])} new files")
    click.echo(f"  Existing: {len(result['existing'])} files")
    click.echo(f"  Output: {result['summary_path']}")

    if result["added"]:
        click.echo()
        click.echo("New files added:")
        for path in result["added"]:
            click.echo(f"    - {path}")


if __name__ == "__main__":
    main()
