#!/usr/bin/env python3
"""
The Augmented Programmer Book Reader
====================================

A comprehensive Python markdown book reader that provides seamless navigation
through "The Augmented Programmer" book chapters while filtering out non-book content.

Author: Python Development Agent
Version: 1.0.0
"""

import os
import sys
import click
import markdown
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.columns import Columns
from rich.table import Table
import re

console = Console()

class BookReader:
    """Main book reader class that handles navigation and display."""
    
    def __init__(self, book_root: Path):
        """Initialize the book reader with the root directory."""
        self.book_root = Path(book_root)
        self.current_chapter = 1
        self.chapters = self._discover_chapters()
        self.total_chapters = len(self.chapters)
        
    def _discover_chapters(self) -> Dict[int, Dict[str, str]]:
        """Discover all available chapters and their content files."""
        chapters = {}
        
        # Priority order for content selection
        priority_dirs = ['content', 'master-documents']
        skip_dirs = {'research', 'drafts', 'notes', 'project-management', 'background', 'tasks'}
        
        # Find chapter directories (chapter-01 through chapter-12)
        for i in range(1, 13):
            chapter_num = i
            chapter_dir = self.book_root / f"chapter-{i:02d}"
            
            if chapter_dir.exists():
                chapter_info = self._find_chapter_content(chapter_dir, chapter_num)
                if chapter_info:
                    chapters[chapter_num] = chapter_info
        
        # Check master-documents for additional content
        master_docs = self.book_root / "master-documents"
        if master_docs.exists():
            for master_file in master_docs.glob("*.md"):
                if "complete" in master_file.stem.lower() or "master" in master_file.stem.lower():
                    # Add as a special chapter 0 (overview)
                    chapters[0] = {
                        'title': 'Complete Manuscript',
                        'file_path': str(master_file),
                        'description': 'Full book overview and master document'
                    }
        
        return chapters
    
    def _find_chapter_content(self, chapter_dir: Path, chapter_num: int) -> Optional[Dict[str, str]]:
        """Find the best content file for a chapter."""
        content_dir = chapter_dir / "content"
        
        if not content_dir.exists():
            return None
        
        # Look for content files in priority order
        content_files = list(content_dir.glob("*.md"))
        
        if not content_files:
            return None
        
        # Prioritize files with specific patterns
        priority_patterns = [
            r'chapter.*complete\.md$',
            r'chapter.*enhanced\.md$',
            r'chapter.*revised\.md$',
            r'chapter.*\.md$'
        ]
        
        best_file = None
        for pattern in priority_patterns:
            for file in content_files:
                if re.search(pattern, file.name, re.IGNORECASE):
                    best_file = file
                    break
            if best_file:
                break
        
        # If no priority match, use the first available file
        if not best_file:
            best_file = content_files[0]
        
        # Extract chapter title from the file
        title = self._extract_chapter_title(best_file)
        
        return {
            'title': title or f"Chapter {chapter_num}",
            'file_path': str(best_file),
            'description': f"Chapter {chapter_num} content"
        }
    
    def _extract_chapter_title(self, file_path: Path) -> Optional[str]:
        """Extract the chapter title from the markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for first markdown heading
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('# '):
                    return line.strip()[2:].strip()
                    
        except Exception:
            pass
        
        return None
    
    def get_chapter_content(self, chapter_num: int) -> Optional[str]:
        """Get the content of a specific chapter."""
        if chapter_num not in self.chapters:
            return None
        
        file_path = self.chapters[chapter_num]['file_path']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            console.print(f"[red]Error reading chapter {chapter_num}: {e}[/red]")
            return None
    
    def display_chapter(self, chapter_num: int):
        """Display a specific chapter with proper formatting."""
        if chapter_num not in self.chapters:
            console.print(f"[red]Chapter {chapter_num} not found[/red]")
            return
        
        content = self.get_chapter_content(chapter_num)
        if not content:
            console.print(f"[red]Could not read Chapter {chapter_num}[/red]")
            return
        
        # Clear screen
        console.clear()
        
        # Display header
        chapter_info = self.chapters[chapter_num]
        header = f"Chapter {chapter_num}" if chapter_num > 0 else "Complete Manuscript"
        
        console.print(Panel(
            f"[bold blue]{header}[/bold blue]\n[dim]{chapter_info['title']}[/dim]",
            title="The Augmented Programmer",
            subtitle=f"Page {chapter_num} of {self.total_chapters}",
            border_style="blue"
        ))
        
        console.print()
        
        # Display content with rich markdown rendering
        try:
            md = Markdown(content, hyperlinks=True, code_theme="github-dark")
            console.print(md)
        except Exception as e:
            # Fallback to plain text if markdown rendering fails
            console.print(content)
        
        console.print()
        
        # Display navigation help
        nav_help = "[dim]Navigation: [bold]n[/bold]=next, [bold]p[/bold]=previous, [bold]toc[/bold]=table of contents, [bold]j[/bold]=jump to chapter, [bold]q[/bold]=quit[/dim]"
        console.print(Panel(nav_help, border_style="dim"))
    
    def display_table_of_contents(self):
        """Display the table of contents."""
        console.clear()
        
        console.print(Panel(
            "[bold blue]Table of Contents[/bold blue]",
            title="The Augmented Programmer",
            border_style="blue"
        ))
        
        console.print()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Chapter", style="dim", width=8)
        table.add_column("Title", style="bold")
        table.add_column("Status", style="green")
        
        for chapter_num in sorted(self.chapters.keys()):
            chapter_info = self.chapters[chapter_num]
            status = "✓ Available" if Path(chapter_info['file_path']).exists() else "✗ Missing"
            
            display_num = str(chapter_num) if chapter_num > 0 else "Overview"
            table.add_row(display_num, chapter_info['title'], status)
        
        console.print(table)
        console.print()
        
        nav_help = "[dim]Enter chapter number to jump to, or press Enter to return to current chapter[/dim]"
        console.print(Panel(nav_help, border_style="dim"))
    
    def interactive_mode(self):
        """Start interactive reading mode."""
        console.print(Panel(
            "[bold blue]Welcome to The Augmented Programmer Book Reader[/bold blue]\n\n"
            "This reader provides seamless navigation through all 12 chapters\n"
            "while filtering out research drafts and project management files.\n\n"
            "[dim]Press any key to start reading...[/dim]",
            title="Book Reader",
            border_style="blue"
        ))
        
        input()  # Wait for user input
        
        while True:
            self.display_chapter(self.current_chapter)
            
            try:
                choice = Prompt.ask(
                    f"\n[bold]Chapter {self.current_chapter}[/bold] - What would you like to do?",
                    choices=["n", "p", "toc", "j", "q", "next", "previous", "quit", "jump", "table"],
                    default="n",
                    show_choices=False
                )
                
                if choice in ["n", "next"]:
                    self.next_chapter()
                elif choice in ["p", "previous"]:
                    self.previous_chapter()
                elif choice in ["toc", "table"]:
                    self.display_table_of_contents()
                    jump_choice = Prompt.ask("Enter chapter number (or press Enter to continue)")
                    if jump_choice.strip():
                        try:
                            target_chapter = int(jump_choice)
                            self.jump_to_chapter(target_chapter)
                        except ValueError:
                            console.print("[red]Invalid chapter number[/red]")
                elif choice in ["j", "jump"]:
                    target = Prompt.ask("Enter chapter number (1-12 or 0 for overview)")
                    try:
                        target_chapter = int(target)
                        self.jump_to_chapter(target_chapter)
                    except ValueError:
                        console.print("[red]Invalid chapter number[/red]")
                elif choice in ["q", "quit"]:
                    console.print("[blue]Thank you for reading The Augmented Programmer![/blue]")
                    break
                    
            except KeyboardInterrupt:
                console.print("\n[blue]Thank you for reading The Augmented Programmer![/blue]")
                break
            except EOFError:
                console.print("\n[blue]Thank you for reading The Augmented Programmer![/blue]")
                break
    
    def next_chapter(self):
        """Navigate to the next chapter."""
        available_chapters = sorted([c for c in self.chapters.keys() if c > 0])
        current_index = available_chapters.index(self.current_chapter) if self.current_chapter in available_chapters else 0
        
        if current_index < len(available_chapters) - 1:
            self.current_chapter = available_chapters[current_index + 1]
        else:
            console.print("[yellow]You're at the last chapter[/yellow]")
    
    def previous_chapter(self):
        """Navigate to the previous chapter."""
        available_chapters = sorted([c for c in self.chapters.keys() if c > 0])
        current_index = available_chapters.index(self.current_chapter) if self.current_chapter in available_chapters else 0
        
        if current_index > 0:
            self.current_chapter = available_chapters[current_index - 1]
        else:
            console.print("[yellow]You're at the first chapter[/yellow]")
    
    def jump_to_chapter(self, chapter_num: int):
        """Jump to a specific chapter."""
        if chapter_num in self.chapters:
            self.current_chapter = chapter_num
        else:
            console.print(f"[red]Chapter {chapter_num} not found[/red]")


@click.command()
@click.option('--chapter', '-c', type=int, help='Jump to specific chapter')
@click.option('--toc', is_flag=True, help='Show table of contents')
@click.option('--root', '-r', default=None,
              help='Root directory of the book (defaults to parent of script directory)')
def main(chapter: Optional[int], toc: bool, root: Optional[str]):
    """
    The Augmented Programmer Book Reader

    A comprehensive Python markdown book reader that provides seamless navigation
    through "The Augmented Programmer" book chapters.
    """

    # Use relative path from script location if no root specified
    if root is None:
        script_dir = Path(__file__).resolve().parent
        book_root = script_dir.parent  # book-reader is inside the book directory
    else:
        book_root = Path(root)
    
    if not book_root.exists():
        console.print(f"[red]Book root directory not found: {book_root}[/red]")
        console.print("Please specify the correct path using --root option")
        sys.exit(1)
    
    reader = BookReader(book_root)
    
    if not reader.chapters:
        console.print("[red]No chapters found in the specified directory[/red]")
        sys.exit(1)
    
    if toc:
        reader.display_table_of_contents()
        return
    
    if chapter:
        reader.jump_to_chapter(chapter)
        reader.interactive_mode()
    else:
        reader.interactive_mode()


if __name__ == "__main__":
    main()