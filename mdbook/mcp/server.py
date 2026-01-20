"""MCP server for MD Book Tools.

Provides Model Context Protocol tools for interacting with markdown books.
Exposes book operations (info, read, create, modify) as MCP tools.
"""

import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from ..infrastructure import configure_services
from ..services import IBookService

# Initialize MCP server
server = Server("mdbook")

# Lazy service container initialization
_book_service: IBookService | None = None


def get_book_service() -> IBookService:
    """Get or create the book service singleton.

    Returns:
        The configured IBookService instance.
    """
    global _book_service
    if _book_service is None:
        container = configure_services()
        _book_service = container.resolve(IBookService)
    return _book_service


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools for book operations.

    Returns:
        List of Tool definitions with names, descriptions, and schemas.
    """
    return [
        Tool(
            name="book_info",
            description="Get information about a markdown book including title, author, and chapter list.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="read_chapter",
            description="Read the content of a specific chapter from a book.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "chapter": {
                        "type": "integer",
                        "description": "Chapter number to read (0 for intro, 1+ for numbered chapters)",
                    },
                },
                "required": ["path", "chapter"],
            },
        ),
        Tool(
            name="list_chapters",
            description="List all chapters in a book with their metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="create_book",
            description="Create a new book project with the specified title and author.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path where the book will be created",
                    },
                    "title": {
                        "type": "string",
                        "description": "The book title",
                    },
                    "author": {
                        "type": "string",
                        "description": "The book author",
                    },
                },
                "required": ["path", "title", "author"],
            },
        ),
        Tool(
            name="add_chapter",
            description="Add a new chapter to an existing book.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "title": {
                        "type": "string",
                        "description": "The chapter title",
                    },
                    "draft": {
                        "type": "boolean",
                        "description": "Mark chapter as draft (default: false)",
                        "default": False,
                    },
                },
                "required": ["path", "title"],
            },
        ),
        Tool(
            name="update_toc",
            description="Update the table of contents (SUMMARY.md). By default preserves existing hierarchy.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "preserve_structure": {
                        "type": "boolean",
                        "description": "Preserve existing SUMMARY.md hierarchy and only add new files (default: true). Set to false to regenerate flat structure.",
                        "default": True,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="list_sections",
            description="List all sections (## headings) in a chapter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "chapter": {
                        "type": "integer",
                        "description": "Chapter number (0 for intro, 1+ for numbered chapters)",
                    },
                },
                "required": ["path", "chapter"],
            },
        ),
        Tool(
            name="read_section",
            description="Get section content by heading or index.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "chapter": {
                        "type": "integer",
                        "description": "Chapter number (0 for intro, 1+ for numbered chapters)",
                    },
                    "section": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ],
                        "description": "Section identifier: heading text (partial match) or 0-based index",
                    },
                },
                "required": ["path", "chapter", "section"],
            },
        ),
        Tool(
            name="update_section",
            description="Replace section content (preserves heading).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "chapter": {
                        "type": "integer",
                        "description": "Chapter number (0 for intro, 1+ for numbered chapters)",
                    },
                    "section": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ],
                        "description": "Section identifier: heading text (partial match) or 0-based index",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for the section body (heading is preserved)",
                    },
                },
                "required": ["path", "chapter", "section", "content"],
            },
        ),
        Tool(
            name="add_note",
            description="Add timestamped HTML comment note to section.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "chapter": {
                        "type": "integer",
                        "description": "Chapter number (0 for intro, 1+ for numbered chapters)",
                    },
                    "section": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ],
                        "description": "Section identifier: heading text (partial match) or 0-based index",
                    },
                    "note": {
                        "type": "string",
                        "description": "The note text to add",
                    },
                },
                "required": ["path", "chapter", "section", "note"],
            },
        ),
        Tool(
            name="list_notes",
            description="List all notes in a chapter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "chapter": {
                        "type": "integer",
                        "description": "Chapter number (0 for intro, 1+ for numbered chapters)",
                    },
                },
                "required": ["path", "chapter"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle MCP tool calls.

    Routes tool calls to the appropriate book service methods.

    Args:
        name: The tool name being called.
        arguments: The tool arguments.

    Returns:
        List containing a TextContent response.
    """
    book_service = get_book_service()

    try:
        if name == "book_info":
            result = await handle_book_info(book_service, arguments)
        elif name == "read_chapter":
            result = await handle_read_chapter(book_service, arguments)
        elif name == "list_chapters":
            result = await handle_list_chapters(book_service, arguments)
        elif name == "create_book":
            result = await handle_create_book(book_service, arguments)
        elif name == "add_chapter":
            result = await handle_add_chapter(book_service, arguments)
        elif name == "update_toc":
            result = await handle_update_toc(book_service, arguments)
        elif name == "list_sections":
            result = await handle_list_sections(book_service, arguments)
        elif name == "read_section":
            result = await handle_read_section(book_service, arguments)
        elif name == "update_section":
            result = await handle_update_section(book_service, arguments)
        elif name == "add_note":
            result = await handle_add_note(book_service, arguments)
        elif name == "list_notes":
            result = await handle_list_notes(book_service, arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}
    except FileNotFoundError as e:
        result = {"error": f"Not found: {e}"}
    except FileExistsError as e:
        result = {"error": f"Already exists: {e}"}
    except PermissionError as e:
        result = {"error": f"Permission denied: {e}"}
    except ValueError as e:
        result = {"error": f"Invalid value: {e}"}
    except KeyError as e:
        result = {"error": f"Not found: {e}"}
    except Exception as e:
        result = {"error": f"Unexpected error: {type(e).__name__}: {e}"}

    # Format result as JSON-like string for readability
    import json

    text = json.dumps(result, indent=2, default=str)

    return [TextContent(type="text", text=text)]


async def handle_book_info(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle book_info tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path'.

    Returns:
        Dictionary with book information.
    """
    path = Path(arguments["path"]).resolve()
    book = book_service.get_book_info(path)

    return {
        "title": book.metadata.title,
        "author": book.metadata.author,
        "description": book.metadata.description,
        "language": book.metadata.language,
        "chapter_count": len(book.chapters),
        "chapters": [
            {
                "number": ch.number,
                "title": ch.title,
                "is_intro": ch.is_intro,
                "draft": ch.metadata.draft,
                "file_path": str(ch.file_path),
            }
            for ch in book.chapters
        ],
    }


async def handle_read_chapter(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle read_chapter tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path' and 'chapter'.

    Returns:
        Dictionary with chapter content.
    """
    path = Path(arguments["path"]).resolve()
    chapter_num = arguments["chapter"]

    content = book_service.read_chapter(path, chapter_num)

    # Also get chapter metadata for context
    book = book_service.get_book_info(path)
    chapter = book.get_chapter(chapter_num)

    result: dict[str, Any] = {"content": content}
    if chapter:
        result["title"] = chapter.title
        result["number"] = chapter.number
        result["is_intro"] = chapter.is_intro
        result["draft"] = chapter.metadata.draft

    return result


async def handle_list_chapters(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle list_chapters tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path'.

    Returns:
        Dictionary with chapters list.
    """
    path = Path(arguments["path"]).resolve()
    chapters = book_service.list_chapters(path)

    return {
        "count": len(chapters),
        "chapters": [
            {
                "number": ch.number,
                "title": ch.title,
                "is_intro": ch.is_intro,
                "draft": ch.metadata.draft,
                "file_path": str(ch.file_path),
            }
            for ch in chapters
        ],
    }


async def handle_create_book(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle create_book tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'title', 'author'.

    Returns:
        Dictionary with creation status and book info.
    """
    path = Path(arguments["path"]).resolve()
    title = arguments["title"]
    author = arguments["author"]

    book = book_service.create_book(path, title, author)

    return {
        "success": True,
        "message": f"Created book: {title}",
        "path": str(book.root_path),
        "title": book.metadata.title,
        "author": book.metadata.author,
    }


async def handle_add_chapter(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle add_chapter tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'title', optional 'draft'.

    Returns:
        Dictionary with chapter creation info.
    """
    path = Path(arguments["path"]).resolve()
    title = arguments["title"]
    draft = arguments.get("draft", False)

    chapter = book_service.add_chapter(path, title, draft)

    return {
        "success": True,
        "message": f"Added chapter: {title}",
        "number": chapter.number,
        "title": chapter.title,
        "draft": chapter.metadata.draft,
        "file_path": str(chapter.file_path),
    }


async def handle_update_toc(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle update_toc tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path' and optional 'preserve_structure'.

    Returns:
        Dictionary with update status.
    """
    path = Path(arguments["path"]).resolve()
    preserve_structure = arguments.get("preserve_structure", True)

    book_service.update_toc(path, preserve_structure)

    # Get updated book info to confirm
    book = book_service.get_book_info(path)

    return {
        "success": True,
        "message": "Table of contents updated",
        "path": str(path),
        "chapter_count": len(book.chapters),
        "preserve_structure": preserve_structure,
    }


async def handle_list_sections(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle list_sections tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path' and 'chapter'.

    Returns:
        Dictionary with sections list.
    """
    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]

    sections = book_service.list_sections(path, chapter)

    return {
        "sections": [
            {
                "index": s.index,
                "heading": s.heading,
                "slug": s.slug,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "note_count": len(s.notes),
            }
            for s in sections
        ],
    }


async def handle_read_section(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle read_section tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'chapter', and 'section'.

    Returns:
        Dictionary with section content.
    """
    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]
    section_id = arguments["section"]

    section = book_service.read_section(path, chapter, section_id)

    if section is None:
        return {"error": f"Section '{section_id}' not found in chapter {chapter}"}

    return {
        "heading": section.heading,
        "content": section.content,
        "body": section.body,
        "notes": [
            {"timestamp": n.timestamp.isoformat(), "text": n.text}
            for n in section.notes
        ],
    }


async def handle_update_section(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle update_section tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'chapter', 'section', 'content'.

    Returns:
        Dictionary with update status.
    """
    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]
    section_id = arguments["section"]
    content = arguments["content"]

    result = book_service.update_section(path, chapter, section_id, content)

    return result


async def handle_add_note(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle add_note tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'chapter', 'section', 'note'.

    Returns:
        Dictionary with note info.
    """
    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]
    section_id = arguments["section"]
    note_text = arguments["note"]

    result = book_service.add_note(path, chapter, section_id, note_text)

    return result


async def handle_list_notes(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle list_notes tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path' and 'chapter'.

    Returns:
        Dictionary with notes list.
    """
    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]

    notes = book_service.list_notes(path, chapter)

    return {"notes": notes}


async def run_server_async() -> None:
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_server() -> None:
    """Entry point for running the MCP server.

    Starts the async event loop and runs the server.
    """
    asyncio.run(run_server_async())


if __name__ == "__main__":
    run_server()
