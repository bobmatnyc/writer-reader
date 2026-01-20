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
        Tool(
            name="build_book",
            description="Render book to HTML with syntax highlighting, tables, mermaid diagrams.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Output directory for HTML files (default: book/html)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="generate_toc",
            description="Generate hierarchical table of contents from all headings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "include_sections": {
                        "type": "boolean",
                        "description": "Include intra-chapter headings (default: false)",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="generate_index",
            description="Generate alphabetical index from {{index: term}} markers.",
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
            name="validate_images",
            description="Check that all referenced images exist.",
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
            name="extract_images",
            description="List all image references in a chapter.",
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
            name="extract_mermaid",
            description="Extract mermaid diagram blocks from a chapter.",
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
            name="update_chapter",
            description="Replace full chapter content (preserves frontmatter). Creates backup by default.",
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
                    "content": {
                        "type": "string",
                        "description": "New content for the chapter body",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, return diff without making changes (default: false)",
                        "default": False,
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "Create .bak backup file before editing (default: true)",
                        "default": True,
                    },
                },
                "required": ["path", "chapter", "content"],
            },
        ),
        Tool(
            name="append_content",
            description="Append content to the end of a chapter. Creates backup by default.",
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
                    "content": {
                        "type": "string",
                        "description": "Content to append at the end of the chapter",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, return diff without making changes (default: false)",
                        "default": False,
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "Create .bak backup file before editing (default: true)",
                        "default": True,
                    },
                },
                "required": ["path", "chapter", "content"],
            },
        ),
        Tool(
            name="insert_section",
            description="Insert content before or after a section. Creates backup by default.",
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
                        "description": "Content to insert (typically a new section with ## heading)",
                    },
                    "position": {
                        "type": "string",
                        "enum": ["before", "after"],
                        "description": "Insert before or after the section (default: after)",
                        "default": "after",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, return diff without making changes (default: false)",
                        "default": False,
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "Create .bak backup file before editing (default: true)",
                        "default": True,
                    },
                },
                "required": ["path", "chapter", "section", "content"],
            },
        ),
        Tool(
            name="replace_section",
            description="Replace section content with new content (optionally preserves heading). Creates backup by default.",
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
                        "description": "New content for the section",
                    },
                    "preserve_heading": {
                        "type": "boolean",
                        "description": "Keep the original section heading (default: true)",
                        "default": True,
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, return diff without making changes (default: false)",
                        "default": False,
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "Create .bak backup file before editing (default: true)",
                        "default": True,
                    },
                },
                "required": ["path", "chapter", "section", "content"],
            },
        ),
        Tool(
            name="get_chapter_history",
            description="Get git commit history for a chapter file. Shows commits that modified the chapter.",
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
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of commits to return (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["path", "chapter"],
            },
        ),
        Tool(
            name="get_chapter_diff",
            description="Get diff between two versions of a chapter. Shows additions, deletions, and change hunks.",
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
                    "commit_from": {
                        "type": "string",
                        "description": "Starting commit (older version). Default: HEAD~1",
                        "default": "HEAD~1",
                    },
                    "commit_to": {
                        "type": "string",
                        "description": "Ending commit (newer version). Default: HEAD",
                        "default": "HEAD",
                    },
                },
                "required": ["path", "chapter"],
            },
        ),
        Tool(
            name="get_chapter_at_commit",
            description="Get the content of a chapter at a specific git commit.",
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
                    "commit": {
                        "type": "string",
                        "description": "Commit reference (hash, branch, tag, HEAD~N). Default: HEAD",
                        "default": "HEAD",
                    },
                },
                "required": ["path", "chapter"],
            },
        ),
        Tool(
            name="get_recent_changes",
            description="Get recent changes across the entire book. Shows commits that modified .md files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the book directory",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of changes to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["path"],
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
        elif name == "build_book":
            result = await handle_build_book(arguments)
        elif name == "generate_toc":
            result = await handle_generate_toc(arguments)
        elif name == "generate_index":
            result = await handle_generate_index(arguments)
        elif name == "validate_images":
            result = await handle_validate_images(arguments)
        elif name == "extract_images":
            result = await handle_extract_images(arguments)
        elif name == "extract_mermaid":
            result = await handle_extract_mermaid(arguments)
        elif name == "update_chapter":
            result = await handle_update_chapter(arguments)
        elif name == "append_content":
            result = await handle_append_content(arguments)
        elif name == "insert_section":
            result = await handle_insert_section(arguments)
        elif name == "replace_section":
            result = await handle_replace_section(arguments)
        elif name == "get_chapter_history":
            result = await handle_get_chapter_history(book_service, arguments)
        elif name == "get_chapter_diff":
            result = await handle_get_chapter_diff(book_service, arguments)
        elif name == "get_chapter_at_commit":
            result = await handle_get_chapter_at_commit(book_service, arguments)
        elif name == "get_recent_changes":
            result = await handle_get_recent_changes(arguments)
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


async def handle_build_book(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle build_book tool call.

    Args:
        arguments: Tool arguments containing 'path' and optional 'output_dir'.

    Returns:
        Dictionary with build status and generated files.
    """
    from ..services import RenderService

    path = Path(arguments["path"]).resolve()
    output_dir = arguments.get("output_dir")

    if output_dir:
        output_path = Path(output_dir).resolve()
    else:
        output_path = path / "html"

    container = configure_services()
    book_service = container.resolve(IBookService)
    render_service = container.resolve(RenderService)

    book = book_service.get_book_info(path)
    generated = render_service.render_book(book, output_path)

    return {
        "success": True,
        "output_dir": str(output_path),
        "files_generated": len(generated),
        "files": [str(f.name) for f in generated],
    }


async def handle_generate_toc(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle generate_toc tool call.

    Args:
        arguments: Tool arguments containing 'path' and optional 'include_sections'.

    Returns:
        Dictionary with TOC markdown.
    """
    from ..services import TocService

    path = Path(arguments["path"]).resolve()
    include_sections = arguments.get("include_sections", False)

    container = configure_services()
    book_service = container.resolve(IBookService)
    toc_service = container.resolve(TocService)

    book = book_service.get_book_info(path)
    toc_md = toc_service.generate_toc_markdown(
        book, include_chapter_tocs=include_sections
    )

    return {
        "success": True,
        "toc": toc_md,
    }


async def handle_generate_index(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle generate_index tool call.

    Args:
        arguments: Tool arguments containing 'path'.

    Returns:
        Dictionary with index markdown.
    """
    from ..services import IndexService

    path = Path(arguments["path"]).resolve()

    container = configure_services()
    book_service = container.resolve(IBookService)
    index_service = container.resolve(IndexService)

    book = book_service.get_book_info(path)
    index = index_service.build_index(book)

    return {
        "success": True,
        "term_count": len(index.entries),
        "index": index.to_markdown(),
    }


async def handle_validate_images(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle validate_images tool call.

    Args:
        arguments: Tool arguments containing 'path'.

    Returns:
        Dictionary with validation results.
    """
    from ..services import ContentService, IReaderService

    path = Path(arguments["path"]).resolve()

    container = configure_services()
    book_service = container.resolve(IBookService)
    content_service = container.resolve(ContentService)
    reader_service = container.resolve(IReaderService)

    book = book_service.get_book_info(path)
    missing_images = []

    for chapter in book.chapters:
        content = reader_service.get_chapter_content(chapter)
        missing = content_service.validate_images(content, chapter.file_path)
        for img in missing:
            missing_images.append(
                {
                    "chapter": chapter.number,
                    "chapter_title": chapter.title,
                    "line": img.line_number,
                    "path": img.path,
                }
            )

    return {
        "success": True,
        "valid": len(missing_images) == 0,
        "missing_count": len(missing_images),
        "missing_images": missing_images,
    }


async def handle_extract_images(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle extract_images tool call.

    Args:
        arguments: Tool arguments containing 'path' and 'chapter'.

    Returns:
        Dictionary with image list.
    """
    from ..services import ContentService, IReaderService

    path = Path(arguments["path"]).resolve()
    chapter_num = arguments["chapter"]

    container = configure_services()
    book_service = container.resolve(IBookService)
    content_service = container.resolve(ContentService)
    reader_service = container.resolve(IReaderService)

    book = book_service.get_book_info(path)
    chapter = book.get_chapter(chapter_num)

    if chapter is None:
        return {"error": f"Chapter {chapter_num} not found"}

    content = reader_service.get_chapter_content(chapter)
    images = content_service.extract_images(content, chapter.file_path)

    return {
        "chapter": chapter_num,
        "chapter_title": chapter.title,
        "image_count": len(images),
        "images": [
            {
                "alt_text": img.alt_text,
                "path": img.path,
                "line": img.line_number,
                "exists": img.exists,
            }
            for img in images
        ],
    }


async def handle_extract_mermaid(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle extract_mermaid tool call.

    Args:
        arguments: Tool arguments containing 'path' and 'chapter'.

    Returns:
        Dictionary with mermaid blocks.
    """
    from ..services import ContentService, IReaderService

    path = Path(arguments["path"]).resolve()
    chapter_num = arguments["chapter"]

    container = configure_services()
    book_service = container.resolve(IBookService)
    content_service = container.resolve(ContentService)
    reader_service = container.resolve(IReaderService)

    book = book_service.get_book_info(path)
    chapter = book.get_chapter(chapter_num)

    if chapter is None:
        return {"error": f"Chapter {chapter_num} not found"}

    content = reader_service.get_chapter_content(chapter)
    blocks = content_service.extract_mermaid_blocks(content)

    return {
        "chapter": chapter_num,
        "chapter_title": chapter.title,
        "has_mermaid": len(blocks) > 0,
        "block_count": len(blocks),
        "blocks": [
            {
                "content": block.content,
                "start_line": block.start_line,
                "end_line": block.end_line,
            }
            for block in blocks
        ],
    }


async def handle_update_chapter(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle update_chapter tool call.

    Args:
        arguments: Tool arguments containing 'path', 'chapter', 'content',
                  optional 'dry_run' and 'create_backup'.

    Returns:
        Dictionary with update status.
    """
    from ..services import IReaderService, IWriterService

    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]
    content = arguments["content"]
    dry_run = arguments.get("dry_run", False)
    create_backup = arguments.get("create_backup", True)

    container = configure_services()
    writer_service = container.resolve(IWriterService)
    reader_service = container.resolve(IReaderService)

    result = writer_service.update_chapter_content(
        path,
        chapter,
        content,
        reader_service,
        dry_run=dry_run,
        create_backup=create_backup,
    )

    return result.to_dict()


async def handle_append_content(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle append_content tool call.

    Args:
        arguments: Tool arguments containing 'path', 'chapter', 'content',
                  optional 'dry_run' and 'create_backup'.

    Returns:
        Dictionary with append status.
    """
    from ..services import IReaderService, IWriterService

    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]
    content = arguments["content"]
    dry_run = arguments.get("dry_run", False)
    create_backup = arguments.get("create_backup", True)

    container = configure_services()
    writer_service = container.resolve(IWriterService)
    reader_service = container.resolve(IReaderService)

    result = writer_service.append_to_chapter(
        path,
        chapter,
        content,
        reader_service,
        dry_run=dry_run,
        create_backup=create_backup,
    )

    return result.to_dict()


async def handle_insert_section(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle insert_section tool call.

    Args:
        arguments: Tool arguments containing 'path', 'chapter', 'section',
                  'content', optional 'position', 'dry_run', 'create_backup'.

    Returns:
        Dictionary with insert status.
    """
    from ..services import IReaderService, IWriterService

    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]
    section_id = arguments["section"]
    content = arguments["content"]
    position = arguments.get("position", "after")
    dry_run = arguments.get("dry_run", False)
    create_backup = arguments.get("create_backup", True)

    container = configure_services()
    writer_service = container.resolve(IWriterService)
    reader_service = container.resolve(IReaderService)

    result = writer_service.insert_at_section(
        path,
        chapter,
        section_id,
        content,
        reader_service,
        position=position,
        dry_run=dry_run,
        create_backup=create_backup,
    )

    return result.to_dict()


async def handle_replace_section(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle replace_section tool call.

    Args:
        arguments: Tool arguments containing 'path', 'chapter', 'section',
                  'content', optional 'preserve_heading', 'dry_run', 'create_backup'.

    Returns:
        Dictionary with replace status.
    """
    from ..services import IReaderService, IWriterService

    path = Path(arguments["path"]).resolve()
    chapter = arguments["chapter"]
    section_id = arguments["section"]
    content = arguments["content"]
    preserve_heading = arguments.get("preserve_heading", True)
    dry_run = arguments.get("dry_run", False)
    create_backup = arguments.get("create_backup", True)

    container = configure_services()
    writer_service = container.resolve(IWriterService)
    reader_service = container.resolve(IReaderService)

    result = writer_service.replace_section(
        path,
        chapter,
        section_id,
        content,
        reader_service,
        preserve_heading=preserve_heading,
        dry_run=dry_run,
        create_backup=create_backup,
    )

    return result.to_dict()


async def handle_get_chapter_history(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle get_chapter_history tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'chapter', optional 'limit'.

    Returns:
        Dictionary with commit history.
    """
    from ..services import GitService

    path = Path(arguments["path"]).resolve()
    chapter_num = arguments["chapter"]
    limit = arguments.get("limit", 50)

    container = configure_services()
    git_service = container.resolve(GitService)

    # Check if this is a git repo
    if not git_service.is_git_repo(path):
        return {"error": f"Not a git repository: {path}"}

    book = book_service.get_book_info(path)
    chapter = book.get_chapter(chapter_num)

    if chapter is None:
        return {"error": f"Chapter {chapter_num} not found"}

    history = git_service.get_chapter_history(chapter.file_path, limit)

    return {
        "chapter": chapter_num,
        "chapter_title": chapter.title,
        "file_path": str(chapter.file_path),
        "commit_count": history.commit_count,
        "commits": [
            {
                "hash": commit.hash,
                "short_hash": commit.short_hash,
                "author": commit.author,
                "author_email": commit.author_email,
                "date": commit.date.isoformat(),
                "subject": commit.subject,
                "message": commit.message,
            }
            for commit in history.commits
        ],
    }


async def handle_get_chapter_diff(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle get_chapter_diff tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'chapter',
                  optional 'commit_from' and 'commit_to'.

    Returns:
        Dictionary with diff information.
    """
    from ..services import GitService

    path = Path(arguments["path"]).resolve()
    chapter_num = arguments["chapter"]
    commit_from = arguments.get("commit_from", "HEAD~1")
    commit_to = arguments.get("commit_to", "HEAD")

    container = configure_services()
    git_service = container.resolve(GitService)

    # Check if this is a git repo
    if not git_service.is_git_repo(path):
        return {"error": f"Not a git repository: {path}"}

    book = book_service.get_book_info(path)
    chapter = book.get_chapter(chapter_num)

    if chapter is None:
        return {"error": f"Chapter {chapter_num} not found"}

    diff_data = git_service.get_chapter_diff(chapter.file_path, commit_from, commit_to)

    return {
        "chapter": chapter_num,
        "chapter_title": chapter.title,
        "file_path": str(chapter.file_path),
        "commit_from": diff_data.commit_from,
        "commit_to": diff_data.commit_to,
        "has_changes": diff_data.has_changes,
        "additions": diff_data.additions,
        "deletions": diff_data.deletions,
        "hunks": [
            {
                "old_start": hunk.old_start,
                "old_count": hunk.old_count,
                "new_start": hunk.new_start,
                "new_count": hunk.new_count,
                "content": hunk.content,
            }
            for hunk in diff_data.hunks
        ],
        "raw_diff": diff_data.raw_diff,
    }


async def handle_get_chapter_at_commit(
    book_service: IBookService,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle get_chapter_at_commit tool call.

    Args:
        book_service: The book service instance.
        arguments: Tool arguments containing 'path', 'chapter', optional 'commit'.

    Returns:
        Dictionary with chapter content at that commit.
    """
    from ..services import GitService

    path = Path(arguments["path"]).resolve()
    chapter_num = arguments["chapter"]
    commit = arguments.get("commit", "HEAD")

    container = configure_services()
    git_service = container.resolve(GitService)

    # Check if this is a git repo
    if not git_service.is_git_repo(path):
        return {"error": f"Not a git repository: {path}"}

    book = book_service.get_book_info(path)
    chapter = book.get_chapter(chapter_num)

    if chapter is None:
        return {"error": f"Chapter {chapter_num} not found"}

    content = git_service.get_chapter_at_commit(chapter.file_path, commit)

    return {
        "chapter": chapter_num,
        "chapter_title": chapter.title,
        "commit": commit,
        "content": content,
    }


async def handle_get_recent_changes(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle get_recent_changes tool call.

    Args:
        arguments: Tool arguments containing 'path' and optional 'limit'.

    Returns:
        Dictionary with recent changes.
    """
    from ..services import GitService

    path = Path(arguments["path"]).resolve()
    limit = arguments.get("limit", 20)

    container = configure_services()
    git_service = container.resolve(GitService)

    # Check if this is a git repo
    if not git_service.is_git_repo(path):
        return {"error": f"Not a git repository: {path}"}

    changes = git_service.get_recent_changes(path, limit)

    return {
        "path": str(path),
        "change_count": len(changes),
        "changes": [
            {
                "file_path": change.file_path,
                "change_type": change.change_type,
                "commit": {
                    "hash": change.commit.hash,
                    "short_hash": change.commit.short_hash,
                    "author": change.commit.author,
                    "date": change.commit.date.isoformat(),
                    "subject": change.commit.subject,
                },
            }
            for change in changes
        ],
    }


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
