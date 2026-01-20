"""Tests for section-level editing functionality.

Tests section parsing, identification, updating, and note management.
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch

from mdbook.domain import (
    Book,
    BookMetadata,
    Chapter,
    ChapterMetadata,
    Section,
    Note,
)
from mdbook.services.reader_service import ReaderService
from mdbook.services.writer_service import WriterService


@pytest.fixture
def mock_file_repo():
    """Create a mock file repository."""
    repo = Mock()
    repo.exists.return_value = True
    return repo


@pytest.fixture
def mock_config_repo():
    """Create a mock config repository."""
    return Mock()


@pytest.fixture
def mock_structure_service():
    """Create a mock structure service."""
    return Mock()


@pytest.fixture
def reader_service(mock_file_repo, mock_config_repo, mock_structure_service):
    """Create a ReaderService with mock dependencies."""
    return ReaderService(mock_file_repo, mock_config_repo, mock_structure_service)


@pytest.fixture
def writer_service(mock_file_repo, mock_config_repo, mock_structure_service):
    """Create a WriterService with mock dependencies."""
    return WriterService(mock_file_repo, mock_config_repo, mock_structure_service)


@pytest.fixture
def sample_book(tmp_path) -> Book:
    """Create a sample book for testing."""
    metadata = BookMetadata(
        title="Test Book",
        author="Test Author",
        description="",
        language="en",
        created=date.today(),
    )
    return Book(root_path=tmp_path, metadata=metadata, chapters=[])


@pytest.fixture
def sample_chapter(tmp_path) -> Chapter:
    """Create a sample chapter for testing."""
    return Chapter(
        file_path=tmp_path / "chapters" / "01-introduction.md",
        metadata=ChapterMetadata(
            title="Introduction",
            number=1,
            date=date.today(),
            draft=False,
        ),
        is_intro=False,
    )


class TestSectionParsing:
    """Tests for parse_sections functionality."""

    def test_parse_single_section_no_heading(self, reader_service):
        """Test parsing content without any ## headings."""
        content = """# Title

Some introduction text here.

More content."""

        sections = reader_service.parse_sections(content)

        assert len(sections) == 1
        assert sections[0].heading == ""
        assert sections[0].index == 0
        assert sections[0].start_line == 1
        assert "Some introduction text" in sections[0].content

    def test_parse_multiple_sections(self, reader_service):
        """Test parsing content with multiple ## headings."""
        content = """# Title

Intro paragraph.

## First Section

First section content.

## Second Section

Second section content.

## Third Section

Third section content."""

        sections = reader_service.parse_sections(content)

        assert len(sections) == 4
        # Section 0: Content before first ##
        assert sections[0].heading == ""
        assert sections[0].index == 0
        assert "Intro paragraph" in sections[0].content

        # Section 1: First Section
        assert sections[1].heading == "First Section"
        assert sections[1].index == 1
        assert "First section content" in sections[1].content

        # Section 2: Second Section
        assert sections[2].heading == "Second Section"
        assert sections[2].index == 2

        # Section 3: Third Section
        assert sections[3].heading == "Third Section"
        assert sections[3].index == 3

    def test_parse_ignores_level_3_headings(self, reader_service):
        """Test that ### headings are not treated as section boundaries."""
        content = """## Main Section

Some content.

### Subsection

More content under subsection.

## Another Section

Final content."""

        sections = reader_service.parse_sections(content)

        assert len(sections) == 3  # Empty intro + 2 sections
        assert sections[1].heading == "Main Section"
        assert "### Subsection" in sections[1].content
        assert sections[2].heading == "Another Section"

    def test_parse_sections_with_notes(self, reader_service):
        """Test that notes are extracted from section content."""
        content = """## Section with Notes

Some content here.

<!-- NOTE: 2024-01-19T15:30:00 - This is a test note -->

More content.

<!-- NOTE: 2024-01-20T10:00:00 - Another note -->\n"""

        sections = reader_service.parse_sections(content)

        assert len(sections) == 2  # Empty intro + 1 section
        section = sections[1]
        assert len(section.notes) == 2
        assert section.notes[0].text == "This is a test note"
        assert section.notes[0].timestamp.year == 2024
        assert section.notes[1].text == "Another note"

    def test_parse_empty_content(self, reader_service):
        """Test parsing empty content."""
        content = ""

        sections = reader_service.parse_sections(content)

        assert len(sections) == 1
        assert sections[0].heading == ""
        assert sections[0].content == ""

    def test_section_line_numbers(self, reader_service):
        """Test that line numbers are correctly tracked."""
        content = """Line 1
Line 2
## Section One
Line 4
Line 5
## Section Two
Line 7"""

        sections = reader_service.parse_sections(content)

        assert len(sections) == 3
        # First section (before ##) starts at line 1
        assert sections[0].start_line == 1
        assert sections[0].end_line == 3

        # Section One starts at line 3
        assert sections[1].start_line == 3
        assert sections[1].end_line == 6

        # Section Two starts at line 6
        assert sections[2].start_line == 6
        assert sections[2].end_line == 8


class TestSectionIdentification:
    """Tests for get_section functionality."""

    def test_get_section_by_index(self, reader_service):
        """Test getting a section by 0-based index."""
        content = """## First

Content.

## Second

More content."""

        sections = reader_service.parse_sections(content)

        # Get by index
        section = reader_service.get_section(sections, 1)
        assert section is not None
        assert section.heading == "First"

        section = reader_service.get_section(sections, 2)
        assert section is not None
        assert section.heading == "Second"

    def test_get_section_by_heading_exact(self, reader_service):
        """Test getting a section by exact heading match."""
        content = """## Introduction

Content.

## Getting Started

More content."""

        sections = reader_service.parse_sections(content)

        section = reader_service.get_section(sections, "Introduction")
        assert section is not None
        assert section.heading == "Introduction"

    def test_get_section_by_heading_partial(self, reader_service):
        """Test getting a section by partial heading match."""
        content = """## Introduction to Programming

Content.

## Getting Started

More content."""

        sections = reader_service.parse_sections(content)

        # Partial match
        section = reader_service.get_section(sections, "Programming")
        assert section is not None
        assert section.heading == "Introduction to Programming"

    def test_get_section_by_heading_case_insensitive(self, reader_service):
        """Test that heading matching is case-insensitive."""
        content = """## Introduction

Content."""

        sections = reader_service.parse_sections(content)

        section = reader_service.get_section(sections, "INTRODUCTION")
        assert section is not None
        assert section.heading == "Introduction"

        section = reader_service.get_section(sections, "introduction")
        assert section is not None
        assert section.heading == "Introduction"

    def test_get_section_not_found_index(self, reader_service):
        """Test getting a section with invalid index returns None."""
        content = """## Only Section

Content."""

        sections = reader_service.parse_sections(content)

        section = reader_service.get_section(sections, 99)
        assert section is None

        section = reader_service.get_section(sections, -1)
        assert section is None

    def test_get_section_not_found_heading(self, reader_service):
        """Test getting a section with non-matching heading returns None."""
        content = """## Introduction

Content."""

        sections = reader_service.parse_sections(content)

        section = reader_service.get_section(sections, "Nonexistent")
        assert section is None


class TestSectionSlug:
    """Tests for Section.slug property."""

    def test_slug_simple(self):
        """Test slug generation for simple heading."""
        section = Section(
            heading="Introduction",
            content="",
            start_line=1,
            end_line=5,
            index=0,
        )

        assert section.slug == "introduction"

    def test_slug_with_spaces(self):
        """Test slug generation with spaces."""
        section = Section(
            heading="Getting Started Guide",
            content="",
            start_line=1,
            end_line=5,
            index=0,
        )

        assert section.slug == "getting-started-guide"

    def test_slug_with_special_characters(self):
        """Test slug generation removes special characters."""
        section = Section(
            heading="What's New? (2024)",
            content="",
            start_line=1,
            end_line=5,
            index=0,
        )

        assert section.slug == "whats-new-2024"

    def test_slug_empty_heading(self):
        """Test slug generation for empty heading."""
        section = Section(
            heading="",
            content="",
            start_line=1,
            end_line=5,
            index=0,
        )

        assert section.slug == ""


class TestSectionBody:
    """Tests for Section.body property."""

    def test_body_strips_heading(self):
        """Test that body excludes the heading line."""
        section = Section(
            heading="Test Heading",
            content="## Test Heading\n\nThis is the body content.\n\nMore content.",
            start_line=1,
            end_line=5,
            index=0,
        )

        assert section.body == "This is the body content.\n\nMore content."
        assert "## Test Heading" not in section.body

    def test_body_no_heading(self):
        """Test body when there's no heading line."""
        section = Section(
            heading="",
            content="Just plain content.\n\nMore content.",
            start_line=1,
            end_line=5,
            index=0,
        )

        assert section.body == "Just plain content.\n\nMore content."


class TestNoteModel:
    """Tests for Note dataclass."""

    def test_note_creation(self):
        """Test creating a Note object."""
        timestamp = datetime(2024, 1, 19, 15, 30, 0)
        note = Note(timestamp=timestamp, text="Test note text")

        assert note.timestamp == timestamp
        assert note.text == "Test note text"


class TestNoteParsing:
    """Tests for _parse_notes functionality."""

    def test_parse_single_note(self, reader_service):
        """Test parsing a single note from content."""
        content = """Some content.

<!-- NOTE: 2024-01-19T15:30:00 - This is a note -->

More content."""

        notes = reader_service._parse_notes(content)

        assert len(notes) == 1
        assert notes[0].text == "This is a note"
        assert notes[0].timestamp.year == 2024
        assert notes[0].timestamp.month == 1
        assert notes[0].timestamp.day == 19
        assert notes[0].timestamp.hour == 15
        assert notes[0].timestamp.minute == 30

    def test_parse_multiple_notes(self, reader_service):
        """Test parsing multiple notes from content."""
        content = """<!-- NOTE: 2024-01-19T10:00:00 - First note -->

Some content.

<!-- NOTE: 2024-01-20T11:30:00 - Second note -->"""

        notes = reader_service._parse_notes(content)

        assert len(notes) == 2
        assert notes[0].text == "First note"
        assert notes[1].text == "Second note"

    def test_parse_no_notes(self, reader_service):
        """Test parsing content with no notes."""
        content = """Just regular content.

No notes here."""

        notes = reader_service._parse_notes(content)

        assert len(notes) == 0

    def test_parse_note_with_multiline_text(self, reader_service):
        """Test parsing note with complex text."""
        content = """<!-- NOTE: 2024-01-19T15:30:00 - This is a longer note
with some details -->"""

        notes = reader_service._parse_notes(content)

        assert len(notes) == 1
        assert "longer note" in notes[0].text

    def test_parse_ignores_invalid_timestamps(self, reader_service):
        """Test that invalid timestamps are skipped."""
        content = """<!-- NOTE: invalid-timestamp - Should be skipped -->
<!-- NOTE: 2024-01-19T15:30:00 - Valid note -->"""

        notes = reader_service._parse_notes(content)

        assert len(notes) == 1
        assert notes[0].text == "Valid note"


class TestUpdateSection:
    """Tests for update_section functionality."""

    def test_update_section_content(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test updating section content preserves heading."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = """---
title: Intro
---

# Title

## Introduction

Old content here.

## Second Section

Other content."""

        mock_file_repo.read_file.return_value = original_content

        # Create mock book and chapter
        book = Book(
            root_path=tmp_path,
            metadata=BookMetadata(title="Test", author="Test"),
            chapters=[
                Chapter(
                    file_path=chapter_path,
                    metadata=ChapterMetadata(title="Intro", number=1),
                    is_intro=False,
                )
            ],
        )

        # Mock load_book to return our book
        with patch.object(reader_service, "load_book", return_value=book):
            result = writer_service.update_section(
                tmp_path, 1, "Introduction", "New content here.", reader_service
            )

        assert result["success"] is True
        assert result["heading"] == "Introduction"

        # Verify write was called
        mock_file_repo.write_file.assert_called_once()
        written_content = mock_file_repo.write_file.call_args[0][1]

        # Should preserve heading
        assert "## Introduction" in written_content
        # Should have new content
        assert "New content here." in written_content
        # Should preserve other sections
        assert "## Second Section" in written_content


class TestAddNote:
    """Tests for add_note functionality."""

    def test_add_note_to_section(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test adding a note to a section."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = """---
title: Intro
---

# Title

## Introduction

Some content here."""

        mock_file_repo.read_file.return_value = original_content

        # Create mock book and chapter
        book = Book(
            root_path=tmp_path,
            metadata=BookMetadata(title="Test", author="Test"),
            chapters=[
                Chapter(
                    file_path=chapter_path,
                    metadata=ChapterMetadata(title="Intro", number=1),
                    is_intro=False,
                )
            ],
        )

        # Mock load_book and datetime
        with patch.object(reader_service, "load_book", return_value=book):
            with patch("mdbook.services.writer_service.datetime") as mock_datetime:
                mock_datetime.now.return_value = datetime(2024, 1, 19, 15, 30, 0)
                mock_datetime.strftime = datetime.strftime
                result = writer_service.add_note(
                    tmp_path, 1, "Introduction", "Test note", reader_service
                )

        assert result["success"] is True
        assert result["text"] == "Test note"
        assert "2024-01-19" in result["timestamp"]

        # Verify write was called with note comment
        written_content = mock_file_repo.write_file.call_args[0][1]
        assert "<!-- NOTE:" in written_content
        assert "Test note" in written_content


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_section_not_found_raises_keyerror(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test that updating nonexistent section raises KeyError."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        content = """## Only Section

Content."""

        mock_file_repo.read_file.return_value = content

        book = Book(
            root_path=tmp_path,
            metadata=BookMetadata(title="Test", author="Test"),
            chapters=[
                Chapter(
                    file_path=chapter_path,
                    metadata=ChapterMetadata(title="Intro", number=1),
                    is_intro=False,
                )
            ],
        )

        with patch.object(reader_service, "load_book", return_value=book):
            with pytest.raises(KeyError):
                writer_service.update_section(
                    tmp_path, 1, "Nonexistent", "Content", reader_service
                )

    def test_chapter_not_found_raises_keyerror(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test that accessing nonexistent chapter raises KeyError."""
        book = Book(
            root_path=tmp_path,
            metadata=BookMetadata(title="Test", author="Test"),
            chapters=[],  # No chapters
        )

        with patch.object(reader_service, "load_book", return_value=book):
            with pytest.raises(KeyError):
                writer_service.update_section(
                    tmp_path, 99, "Any", "Content", reader_service
                )

    def test_empty_section_handling(self, reader_service):
        """Test handling of empty sections."""
        content = """## Empty Section

## Another Section

Content here."""

        sections = reader_service.parse_sections(content)

        # Empty section should still be parsed
        assert len(sections) == 3
        assert sections[1].heading == "Empty Section"
        assert sections[1].content.strip() == "## Empty Section"
