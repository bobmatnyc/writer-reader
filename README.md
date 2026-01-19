# The Augmented Programmer Book Reader

A comprehensive Python markdown book reader that provides seamless navigation through "The Augmented Programmer" book chapters while filtering out non-book content.

## Features

- **Smart Chapter Detection**: Automatically identifies chapters 1-12 and prioritizes final content
- **Content Filtering**: Skips research drafts, project management files, and notes
- **Rich Terminal Display**: Beautiful markdown rendering with syntax highlighting
- **Interactive Navigation**: Forward/back navigation, chapter jumping, and table of contents
- **Cross-platform**: Works on macOS, Linux, and Windows
- **Configurable**: Customizable settings and book root directory

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Alternative Installation

```bash
pip install click markdown rich pymdown-extensions pygments
```

## Usage

### Basic Usage

Start the interactive reader:

```bash
python book_reader.py
```

### Command Line Options

```bash
# Jump to specific chapter
python book_reader.py --chapter 5

# Show table of contents
python book_reader.py --toc

# Specify custom book root directory
python book_reader.py --root /path/to/book/directory

# Show help
python book_reader.py --help
```

### Interactive Navigation

Once in the reader, use these commands:

- **`n`** or **`next`**: Navigate to next chapter
- **`p`** or **`previous`**: Navigate to previous chapter
- **`toc`** or **`table`**: Show table of contents
- **`j`** or **`jump`**: Jump to specific chapter
- **`q`** or **`quit`**: Exit the reader

### Environment Variables

Set the book root directory using an environment variable:

```bash
export BOOK_ROOT=/path/to/your/book/directory
python book_reader.py
```

## Book Structure

The reader expects the following directory structure:

```
book-root/
├── chapter-01/ through chapter-12/     # Target chapters
│   ├── content/                        # Final completed content (priority)
│   ├── research/                       # Skipped
│   └── drafts/                         # Skipped
├── master-documents/                   # Included as overview
├── project-management/                 # Skipped
├── background/                         # Skipped
├── notes/                             # Skipped
└── tasks/                             # Skipped
```

## Content Prioritization

The reader uses this priority order for selecting chapter content:

1. **Primary**: Files in `/chapter-XX/content/` directory
2. **Secondary**: Files in `/master-documents/` directory
3. **File Priority**: 
   - `*complete.md` (highest priority)
   - `*enhanced.md`
   - `*revised.md`
   - `*.md` (any other markdown file)

## Configuration

### Custom Configuration

Modify `config.py` to customize:

- Default book root directory
- Content prioritization rules
- Display settings
- Color scheme
- Markdown rendering options

### Example Configuration

```python
# Set custom book root
DEFAULT_BOOK_ROOT = Path("/custom/path/to/book")

# Customize colors
COLORS = {
    'header': 'bold cyan',
    'chapter_title': 'bold yellow',
    'error': 'red',
    'success': 'green'
}
```

## Troubleshooting

### Common Issues

1. **"Book root directory not found"**
   - Verify the path to your book directory
   - Use `--root` option to specify correct path
   - Check that the directory contains `chapter-XX` folders

2. **"No chapters found"**
   - Ensure chapter directories follow the pattern `chapter-01`, `chapter-02`, etc.
   - Check that chapters contain a `content/` subdirectory
   - Verify that content directories contain `.md` files

3. **"Error reading chapter"**
   - Check file permissions
   - Verify markdown files are not corrupted
   - Ensure files are in UTF-8 encoding

### Debug Mode

Run with Python's verbose mode for detailed error information:

```bash
python -v book_reader.py
```

## Development

### File Structure

- `book_reader.py` - Main application file
- `config.py` - Configuration settings
- `requirements.txt` - Python dependencies
- `README.md` - This documentation

### Extending the Reader

The `BookReader` class can be extended with additional features:

```python
class ExtendedBookReader(BookReader):
    def search_content(self, query: str):
        """Search for text across all chapters."""
        # Implementation here
        pass
    
    def export_chapter(self, chapter_num: int, format: str):
        """Export chapter to different formats."""
        # Implementation here
        pass
```

## Requirements

### Python Dependencies

- `click>=8.0.0` - Command line interface
- `markdown>=3.4.0` - Markdown processing
- `rich>=13.0.0` - Terminal formatting
- `pymdown-extensions>=9.0.0` - Enhanced markdown features
- `pygments>=2.14.0` - Syntax highlighting

### System Requirements

- Python 3.8+
- Terminal with UTF-8 support
- Minimum 80 character terminal width (120 recommended)

## License

This book reader is part of "The Augmented Programmer" project.

## Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review the configuration options
3. Ensure your book directory structure matches the expected format
4. Check that all dependencies are installed correctly

## Version History

- **v1.0.0** - Initial release with full chapter navigation and content filtering