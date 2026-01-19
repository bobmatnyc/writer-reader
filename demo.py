#!/usr/bin/env python3
"""
Demo script for The Augmented Programmer Book Reader
Shows key features and usage examples
"""

import sys
from pathlib import Path
from book_reader import BookReader
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

def demo_features():
    """Demonstrate key features of the book reader."""
    
    console.print(Panel(
        "[bold blue]The Augmented Programmer Book Reader - Demo[/bold blue]",
        subtitle="Demonstration of key features",
        border_style="blue"
    ))
    
    # Initialize reader
    book_root = Path("/Users/masa/Projects/books/augmented-programmer")
    reader = BookReader(book_root)
    
    console.print("\n[bold green]1. Book Discovery[/bold green]")
    console.print(f"   Book root: {book_root}")
    console.print(f"   Chapters found: {len(reader.chapters)}")
    
    console.print("\n[bold green]2. Chapter Listing[/bold green]")
    for chapter_num in sorted(reader.chapters.keys())[:5]:  # Show first 5
        chapter_info = reader.chapters[chapter_num]
        console.print(f"   Chapter {chapter_num}: {chapter_info['title']}")
    console.print("   ... (and more)")
    
    console.print("\n[bold green]3. Content Prioritization[/bold green]")
    console.print("   Priority order:")
    console.print("   - chapter-XX/content/*complete.md")
    console.print("   - chapter-XX/content/*enhanced.md")
    console.print("   - chapter-XX/content/*revised.md")
    console.print("   - chapter-XX/content/*.md")
    
    console.print("\n[bold green]4. Content Filtering[/bold green]")
    console.print("   Included directories:")
    console.print("   ✓ chapter-XX/content/")
    console.print("   ✓ master-documents/")
    console.print("   Excluded directories:")
    console.print("   ✗ research/")
    console.print("   ✗ drafts/")
    console.print("   ✗ notes/")
    console.print("   ✗ project-management/")
    console.print("   ✗ background/")
    
    console.print("\n[bold green]5. Sample Content[/bold green]")
    sample_content = reader.get_chapter_content(1)
    if sample_content:
        lines = sample_content.split('\n')[:10]
        sample_text = '\n'.join(lines)
        console.print(Panel(
            sample_text,
            title="Chapter 1 - First 10 lines",
            border_style="dim"
        ))
    
    console.print("\n[bold green]6. Navigation Features[/bold green]")
    console.print("   Interactive commands:")
    console.print("   • 'n' or 'next' - Next chapter")
    console.print("   • 'p' or 'previous' - Previous chapter")
    console.print("   • 'toc' or 'table' - Table of contents")
    console.print("   • 'j' or 'jump' - Jump to specific chapter")
    console.print("   • 'q' or 'quit' - Exit reader")
    
    console.print("\n[bold green]7. Command Line Usage[/bold green]")
    usage_examples = """
# Start interactive reader
python book_reader.py

# Jump to specific chapter
python book_reader.py --chapter 5

# Show table of contents
python book_reader.py --toc

# Use custom book directory
python book_reader.py --root /path/to/book
"""
    
    syntax = Syntax(usage_examples.strip(), "bash", theme="github-dark")
    console.print(syntax)
    
    console.print("\n[bold blue]Demo complete![/bold blue]")
    console.print("Run 'python book_reader.py' to start the interactive reader.")

if __name__ == "__main__":
    demo_features()