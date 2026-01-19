# MD Book Tools

A markdown book reader and writer with DI/SOA architecture and MCP server support for Claude Code integration.

## Features

- **Multi-Format Support**: mdBook, GitBook, Leanpub, Bookdown, and auto-detection
- **YAML Frontmatter**: Extract metadata (title, author, date, draft status)
- **Interactive Reader**: Terminal navigation with chapter jumping
- **Book Writing**: Initialize projects, add chapters, generate TOC
- **MCP Server**: Expose book operations as tools for AI assistants

## Architecture

```
mdbook/
├── domain/           # Core entities (Book, Chapter, ChapterMetadata)
├── services/         # Business logic with interface protocols
│   ├── interfaces.py # IBookService, IReaderService, IWriterService, IStructureService
│   ├── book_service.py
│   ├── reader_service.py
│   ├── writer_service.py
│   └── structure_service.py
├── repositories/     # Data access layer
│   ├── interfaces.py # IFileRepository, IConfigRepository
│   ├── file_repository.py
│   └── config_repository.py
├── infrastructure/   # DI container and composition root
│   └── container.py  # ServiceContainer with lazy singleton resolution
├── mcp/              # Model Context Protocol server
│   └── server.py     # Exposes book operations as MCP tools
└── cli.py            # Unified Click-based CLI
```

## Installation

### Using uv (recommended)

```bash
cd book-reader
uv pip install -e .
```

### Using pip

```bash
cd book-reader
pip install -e .
```

This installs the single `mdbook` command with all subcommands.

## Quick Start

```bash
# Read a book (pass book path as argument)
mdbook read /path/to/book

# Or use --book/-b global option
mdbook --book /path/to/book read

# Show book info
mdbook info /path/to/book

# Create a new book
mdbook init ./my-book -t "My Book Title" -a "Author Name"

# Add a chapter
mdbook new-chapter ./my-book -t "Introduction"

# Regenerate table of contents
mdbook toc ./my-book

# Start MCP server for a specific book
mdbook serve-mcp /path/to/book

# Auto-configure Claude Code MCP integration
mdbook setup /path/to/book
```

## Command Reference

```
mdbook [OPTIONS] COMMAND [ARGS]

Commands:
  read         Read a markdown book interactively
  info         Show book information
  init         Initialize a new book project
  new-chapter  Add a new chapter to a book
  toc          Regenerate table of contents
  serve-mcp    Start MCP server for Claude Code
  setup        Auto-configure Claude Code MCP integration

Global Options:
  -b, --book PATH  Book directory (used by all commands)
  --version        Show version and exit
  --help           Show help message and exit
```

### read

```bash
mdbook read [BOOK] [OPTIONS]

Arguments:
  BOOK         Book directory (or use global --book option)

Options:
  -c, --chapter NUM    Start at specific chapter
```

### init

```bash
mdbook init PATH [OPTIONS]

Arguments:
  PATH         Directory to create book in

Options:
  -t, --title TEXT     Book title (required)
  -a, --author TEXT    Author name (required)
```

### new-chapter

```bash
mdbook new-chapter [BOOK] [OPTIONS]

Arguments:
  BOOK         Book directory (or use global --book option)

Options:
  -t, --title TEXT     Chapter title (required)
  -d, --draft          Mark as draft
```

### setup

```bash
mdbook setup [BOOK]

Arguments:
  BOOK         Book directory (or use global --book option)

Auto-configures Claude Code MCP integration by updating .mcp.json
in the project directory. Creates the file if it doesn't exist or
adds/updates the mdbook server configuration.
```

## MCP Server Integration

The MCP server exposes book operations as tools for Claude Code and other AI assistants.

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `book_info` | Get book metadata and chapter list |
| `read_chapter` | Read chapter content by number |
| `list_chapters` | List all chapters with metadata |
| `create_book` | Create a new book project |
| `add_chapter` | Add a chapter to a book |
| `update_toc` | Regenerate SUMMARY.md |

### Claude Code Configuration

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "mdbook": {
      "command": "mdbook",
      "args": ["serve-mcp"]
    }
  }
}
```

Or with uv:

```json
{
  "mcpServers": {
    "mdbook": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/book-reader", "mdbook", "serve-mcp"]
    }
  }
}
```

## Supported Book Formats

| Format | Detection File |
|--------|----------------|
| mdBook/GitBook | `SUMMARY.md` |
| mdBook | `book.toml` |
| Leanpub | `Book.txt` |
| Bookdown | `_bookdown.yml` |
| Auto | Directory scan |

## Requirements

- Python 3.10+
- click, rich, markdown, pyyaml, mcp

## License

MIT License

## Version History

- **v3.1.0** - Multi-book support with BOOK argument and `--book/-b` global option, new `setup` command for Claude Code MCP auto-configuration
- **v3.0.0** - Complete rewrite with DI/SOA architecture, unified `mdbook` CLI, MCP server integration
- **v2.1.0** - Added md-book-writer tool
- **v2.0.0** - Generic multi-format support, YAML frontmatter parsing
- **v1.0.0** - Initial release
