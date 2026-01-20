"""Tests for content features: images, mermaid, TOC, index.

Tests the new ContentService, TocService, IndexService, and RenderService.
"""

import pytest
from unittest.mock import Mock

from mdbook.domain import (
    Chapter,
    ChapterMetadata,
    TocEntry,
    ImageRef,
    MermaidBlock,
    IndexTerm,
    IndexEntry,
    BookIndex,
)
from mdbook.services.content_service import ContentService
from mdbook.services.toc_service import TocService
from mdbook.services.index_service import IndexService


@pytest.fixture
def mock_file_repo():
    """Create a mock file repository."""
    repo = Mock()
    repo.exists.return_value = True
    return repo


@pytest.fixture
def mock_reader_service():
    """Create a mock reader service."""
    service = Mock()
    return service


@pytest.fixture
def content_service(mock_file_repo):
    """Create a ContentService with mock dependencies."""
    return ContentService(mock_file_repo)


@pytest.fixture
def toc_service(mock_reader_service):
    """Create a TocService with mock dependencies."""
    return TocService(mock_reader_service)


@pytest.fixture
def index_service(mock_reader_service):
    """Create an IndexService with mock dependencies."""
    return IndexService(mock_reader_service)


@pytest.fixture
def sample_chapter(tmp_path) -> Chapter:
    """Create a sample chapter for testing."""
    return Chapter(
        file_path=tmp_path / "chapters" / "01-introduction.md",
        metadata=ChapterMetadata(
            title="Introduction",
            number=1,
            draft=False,
        ),
        is_intro=False,
    )


class TestImageExtraction:
    """Tests for image extraction functionality."""

    def test_extract_simple_images(self, content_service, tmp_path):
        """Test extracting simple image references."""
        content = """# Chapter

![Logo](images/logo.png)

Some text.

![Diagram](./diagrams/flow.svg)
"""
        chapter_path = tmp_path / "chapter.md"
        images = content_service.extract_images(content, chapter_path, validate=False)

        assert len(images) == 2
        assert images[0].alt_text == "Logo"
        assert images[0].path == "images/logo.png"
        assert images[0].line_number == 3
        assert images[1].alt_text == "Diagram"
        assert images[1].path == "./diagrams/flow.svg"
        assert images[1].line_number == 7

    def test_extract_external_urls(self, content_service, tmp_path):
        """Test that external URLs are recognized."""
        content = """![External](https://example.com/image.png)
![Another](http://cdn.example.com/photo.jpg)
"""
        chapter_path = tmp_path / "chapter.md"
        images = content_service.extract_images(content, chapter_path, validate=False)

        assert len(images) == 2
        assert images[0].exists is True  # External URLs assumed to exist
        assert images[1].exists is True

    def test_validate_missing_images(self, content_service, mock_file_repo, tmp_path):
        """Test validation of missing images."""
        content = """![Exists](existing.png)
![Missing](missing.png)
"""
        chapter_path = tmp_path / "chapter.md"

        def exists_side_effect(path):
            return "existing" in str(path)

        mock_file_repo.exists.side_effect = exists_side_effect

        missing = content_service.validate_images(content, chapter_path)

        assert len(missing) == 1
        assert missing[0].path == "missing.png"
        assert missing[0].exists is False


class TestMermaidExtraction:
    """Tests for mermaid block extraction."""

    def test_extract_mermaid_blocks(self, content_service):
        """Test extracting mermaid code blocks."""
        content = """# Chapter

Some text.

```mermaid
graph TD
    A --> B
    B --> C
```

More text.

```mermaid
sequenceDiagram
    Alice->>Bob: Hello
```
"""
        blocks = content_service.extract_mermaid_blocks(content)

        assert len(blocks) == 2
        assert "graph TD" in blocks[0].content
        assert "sequenceDiagram" in blocks[1].content

    def test_has_mermaid_true(self, content_service):
        """Test has_mermaid returns True when mermaid exists."""
        content = """```mermaid
graph TD
    A --> B
```"""
        assert content_service.has_mermaid(content) is True

    def test_has_mermaid_false(self, content_service):
        """Test has_mermaid returns False when no mermaid."""
        content = """```python
print('hello')
```"""
        assert content_service.has_mermaid(content) is False


class TestTocExtraction:
    """Tests for TOC extraction functionality."""

    def test_extract_chapter_toc(
        self, toc_service, mock_reader_service, sample_chapter
    ):
        """Test extracting TOC from a chapter."""
        content = """# Title

## Introduction

Some text.

### Getting Started

More text.

## Features

### Feature One

Details.

### Feature Two

More details.
"""
        mock_reader_service.get_chapter_content.return_value = content

        toc = toc_service.extract_chapter_toc(sample_chapter)

        assert toc.chapter_number == 1
        assert toc.chapter_title == "Introduction"
        assert len(toc.entries) == 2  # Two ## headings

    def test_toc_entry_anchors(self, toc_service, mock_reader_service, sample_chapter):
        """Test that TOC entries have proper slugified anchors."""
        content = """## Getting Started Guide

## What's New in 2024?
"""
        mock_reader_service.get_chapter_content.return_value = content

        toc = toc_service.extract_chapter_toc(sample_chapter)

        assert toc.entries[0].anchor == "getting-started-guide"
        assert toc.entries[1].anchor == "whats-new-in-2024"

    def test_expand_toc_marker(self, toc_service):
        """Test expanding [TOC] marker in content."""
        content = """# Chapter

[TOC]

## Section One

Text.

## Section Two

More text.
"""
        expanded = toc_service.expand_toc_marker(content)

        assert "[TOC]" not in expanded
        assert "Section One" in expanded
        assert "Section Two" in expanded


class TestIndexExtraction:
    """Tests for index term extraction."""

    def test_extract_explicit_terms(
        self, index_service, mock_reader_service, sample_chapter
    ):
        """Test extracting {{index: term}} markers."""
        content = """# Chapter

This is about {{index: Python}} programming.

## Data Structures

Learn about {{index: lists}} and {{index: dictionaries}}.
"""
        mock_reader_service.get_chapter_content.return_value = content

        terms = index_service.extract_terms(sample_chapter)

        assert len(terms) == 3
        assert terms[0].term == "Python"
        assert terms[1].term == "lists"
        assert terms[2].term == "dictionaries"

    def test_term_section_context(
        self, index_service, mock_reader_service, sample_chapter
    ):
        """Test that terms capture section context."""
        content = """# Title

## Introduction

Learn about {{index: basics}}.

## Advanced

More about {{index: advanced topics}}.
"""
        mock_reader_service.get_chapter_content.return_value = content

        terms = index_service.extract_terms(sample_chapter)

        assert terms[0].section_heading == "Introduction"
        assert terms[1].section_heading == "Advanced"

    def test_strip_index_markers(self, index_service):
        """Test removing index markers from content."""
        content = "This is about {{index: Python}} programming."
        stripped = index_service.strip_index_markers(content)

        assert "{{index:" not in stripped
        assert "Python" not in stripped
        assert "This is about  programming." == stripped


class TestBookIndex:
    """Tests for BookIndex model."""

    def test_to_markdown(self):
        """Test generating markdown from BookIndex."""
        index = BookIndex(
            entries=[
                IndexEntry(
                    term="Python",
                    locations=[
                        IndexTerm(
                            term="Python",
                            chapter_number=1,
                            chapter_title="Introduction",
                            section_heading="Overview",
                            anchor="overview",
                        ),
                    ],
                ),
                IndexEntry(
                    term="algorithms",
                    locations=[
                        IndexTerm(
                            term="algorithms",
                            chapter_number=2,
                            chapter_title="Basics",
                            section_heading="",
                            anchor="",
                        ),
                    ],
                ),
            ]
        )

        md = index.to_markdown()

        assert "# Index" in md
        assert "## A" in md
        assert "## P" in md
        assert "**Python**" in md
        assert "**algorithms**" in md


class TestTocEntry:
    """Tests for TocEntry model."""

    def test_indent_property(self):
        """Test indent calculation for different levels."""
        entry1 = TocEntry(title="Level 1", level=1, anchor="level-1")
        entry2 = TocEntry(title="Level 2", level=2, anchor="level-2")
        entry3 = TocEntry(title="Level 3", level=3, anchor="level-3")

        assert entry1.indent == ""
        assert entry2.indent == "  "
        assert entry3.indent == "    "


class TestImageRef:
    """Tests for ImageRef model."""

    def test_creation(self):
        """Test creating ImageRef."""
        img = ImageRef(
            alt_text="Logo",
            path="images/logo.png",
            line_number=5,
            exists=True,
        )

        assert img.alt_text == "Logo"
        assert img.path == "images/logo.png"
        assert img.line_number == 5
        assert img.exists is True


class TestMermaidBlock:
    """Tests for MermaidBlock model."""

    def test_creation(self):
        """Test creating MermaidBlock."""
        block = MermaidBlock(
            content="graph TD\n    A --> B",
            start_line=10,
            end_line=14,
        )

        assert "graph TD" in block.content
        assert block.start_line == 10
        assert block.end_line == 14
