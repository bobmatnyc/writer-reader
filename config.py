"""
Configuration settings for The Augmented Programmer Book Reader
"""

import os
from pathlib import Path

class BookReaderConfig:
    """Configuration class for book reader settings."""
    
    # Default book root directory
    DEFAULT_BOOK_ROOT = Path.home() / "Projects" / "books" / "augmented-programmer"
    
    # Content prioritization
    PRIORITY_DIRECTORIES = ['content', 'master-documents']
    SKIP_DIRECTORIES = {'research', 'drafts', 'notes', 'project-management', 'background', 'tasks'}
    
    # File selection patterns (in priority order)
    FILE_PRIORITY_PATTERNS = [
        r'chapter.*complete\.md$',
        r'chapter.*enhanced\.md$',
        r'chapter.*revised\.md$',
        r'chapter.*\.md$'
    ]
    
    # Display settings
    CONSOLE_WIDTH = 120
    WRAP_TEXT = True
    
    # Chapter range
    MIN_CHAPTER = 1
    MAX_CHAPTER = 12
    
    # Navigation settings
    NAVIGATION_HELP = {
        'n': 'Next chapter',
        'p': 'Previous chapter',
        'toc': 'Table of contents',
        'j': 'Jump to chapter',
        'q': 'Quit'
    }
    
    # Color scheme
    COLORS = {
        'header': 'bold blue',
        'chapter_title': 'bold green',
        'navigation': 'dim',
        'error': 'red',
        'success': 'green',
        'warning': 'yellow',
        'info': 'blue'
    }
    
    # Markdown rendering settings
    MARKDOWN_EXTENSIONS = [
        'codehilite',
        'fenced_code',
        'tables',
        'toc',
        'footnotes',
        'attr_list',
        'def_list'
    ]
    
    # Code highlighting theme
    CODE_THEME = 'github-dark'
    
    @classmethod
    def get_book_root(cls) -> Path:
        """Get the book root directory, checking environment variables."""
        env_root = os.environ.get('BOOK_ROOT')
        if env_root:
            return Path(env_root)
        return cls.DEFAULT_BOOK_ROOT
    
    @classmethod
    def validate_book_root(cls, book_root: Path) -> bool:
        """Validate that the book root directory exists and contains expected structure."""
        if not book_root.exists():
            return False
        
        # Check for at least one chapter directory
        chapter_dirs = list(book_root.glob('chapter-*'))
        if not chapter_dirs:
            return False
        
        return True