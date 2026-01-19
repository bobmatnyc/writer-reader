#!/usr/bin/env python3
"""
Test script for The Augmented Programmer Book Reader
"""

import sys
from pathlib import Path
from book_reader import BookReader

def test_basic_functionality():
    """Test basic functionality of the book reader."""
    print("Testing The Augmented Programmer Book Reader...")
    
    # Test book discovery - use relative path from script location
    script_dir = Path(__file__).resolve().parent
    book_root = script_dir.parent  # book-reader is inside the book directory
    reader = BookReader(book_root)
    
    print(f"✓ Book root found: {book_root}")
    print(f"✓ Chapters discovered: {len(reader.chapters)}")
    
    # Test chapter listing
    print("\nAvailable chapters:")
    for chapter_num in sorted(reader.chapters.keys()):
        chapter_info = reader.chapters[chapter_num]
        print(f"  Chapter {chapter_num}: {chapter_info['title']}")
    
    # Test content reading
    test_chapter = 1
    content = reader.get_chapter_content(test_chapter)
    
    if content:
        print(f"\n✓ Chapter {test_chapter} content loaded successfully")
        print(f"  Content length: {len(content)} characters")
        print(f"  First line: {content.split('\\n')[0][:80]}...")
    else:
        print(f"✗ Failed to load Chapter {test_chapter}")
    
    # Test navigation
    print(f"\n✓ Current chapter: {reader.current_chapter}")
    reader.next_chapter()
    print(f"✓ After next_chapter(): {reader.current_chapter}")
    reader.previous_chapter()
    print(f"✓ After previous_chapter(): {reader.current_chapter}")
    
    print("\n✓ All basic functionality tests passed!")

if __name__ == "__main__":
    test_basic_functionality()