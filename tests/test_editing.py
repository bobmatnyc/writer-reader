"""Tests for chapter and section editing functionality.

Tests backup creation, diff generation, markdown validation,
and content editing operations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from mdbook.domain import (
    Book,
    BookMetadata,
    Chapter,
    ChapterMetadata,
)
from mdbook.services.writer_service import WriterService, EditResult
from mdbook.services.reader_service import ReaderService


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


class TestEditResult:
    """Tests for EditResult class."""

    def test_edit_result_to_dict_minimal(self):
        """Test EditResult to_dict with minimal fields."""
        result = EditResult(success=True, message="Updated successfully")
        d = result.to_dict()

        assert d["success"] is True
        assert d["message"] == "Updated successfully"
        assert "backup_path" not in d
        assert "diff" not in d

    def test_edit_result_to_dict_full(self):
        """Test EditResult to_dict with all fields."""
        result = EditResult(
            success=True,
            message="Updated",
            backup_path=Path("/tmp/test.bak"),
            diff="--- a/file\n+++ b/file\n@@ -1 +1 @@\n-old\n+new",
        )
        d = result.to_dict()

        assert d["success"] is True
        assert d["message"] == "Updated"
        assert d["backup_path"] == "/tmp/test.bak"
        assert "old" in d["diff"]
        assert "new" in d["diff"]


class TestMarkdownValidation:
    """Tests for markdown validation functionality."""

    def test_validate_markdown_valid(self, writer_service):
        """Test validation passes for valid markdown."""
        content = """# Title

Some content here.

```python
print("hello")
```

[Link](https://example.com)
"""
        warnings = writer_service._validate_markdown(content)
        assert len(warnings) == 0

    def test_validate_markdown_unclosed_code_block(self, writer_service):
        """Test validation catches unclosed code block."""
        content = """# Title

```python
print("hello")

More content without closing code block.
"""
        warnings = writer_service._validate_markdown(content)
        assert len(warnings) == 1
        assert "code block" in warnings[0].lower()

    def test_validate_markdown_mismatched_brackets(self, writer_service):
        """Test validation catches mismatched brackets."""
        content = """# Title

[Link without closing bracket(https://example.com)
"""
        warnings = writer_service._validate_markdown(content)
        assert len(warnings) == 1
        assert "bracket" in warnings[0].lower()


class TestDiffGeneration:
    """Tests for diff generation functionality."""

    def test_generate_diff_simple_change(self, writer_service):
        """Test diff generation for simple content change."""
        original = "Line 1\nLine 2\nLine 3\n"
        modified = "Line 1\nModified Line 2\nLine 3\n"

        diff = writer_service._generate_diff(original, modified, "test.md")

        assert "--- a/test.md" in diff
        assert "+++ b/test.md" in diff
        assert "-Line 2" in diff
        assert "+Modified Line 2" in diff

    def test_generate_diff_no_changes(self, writer_service):
        """Test diff generation when content is identical."""
        original = "Line 1\nLine 2\n"
        modified = "Line 1\nLine 2\n"

        diff = writer_service._generate_diff(original, modified, "test.md")

        assert diff == ""


class TestUpdateChapterContent:
    """Tests for update_chapter_content functionality."""

    def test_update_chapter_content_preserves_frontmatter(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test that frontmatter is preserved when updating content."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = """---
title: Introduction
date: 2024-01-01
---

# Old Title

Old content here.
"""

        mock_file_repo.read_file.return_value = original_content

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
            result = writer_service.update_chapter_content(
                tmp_path,
                1,
                "# New Title\n\nNew content here.",
                reader_service,
                dry_run=False,
                create_backup=False,
            )

        assert result.success is True
        written_content = mock_file_repo.write_file.call_args[0][1]

        # Should preserve frontmatter
        assert "---" in written_content
        assert "title: Introduction" in written_content

        # Should have new content
        assert "New Title" in written_content
        assert "New content" in written_content

    def test_update_chapter_dry_run(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test dry run returns diff without writing."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = "# Title\n\nOriginal content.\n"

        mock_file_repo.read_file.return_value = original_content

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
            result = writer_service.update_chapter_content(
                tmp_path,
                1,
                "# Title\n\nModified content.",
                reader_service,
                dry_run=True,
                create_backup=False,
            )

        assert result.success is True
        assert "Dry run" in result.message
        assert result.diff is not None
        assert "-Original content" in result.diff
        assert "+Modified content" in result.diff

        # Should not write
        mock_file_repo.write_file.assert_not_called()


class TestAppendToChapter:
    """Tests for append_to_chapter functionality."""

    def test_append_to_chapter(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test appending content to a chapter."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = "# Title\n\nExisting content.\n"

        mock_file_repo.read_file.return_value = original_content

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
            result = writer_service.append_to_chapter(
                tmp_path,
                1,
                "## New Section\n\nAppended content.",
                reader_service,
                dry_run=False,
                create_backup=False,
            )

        assert result.success is True
        written_content = mock_file_repo.write_file.call_args[0][1]

        # Should have original content
        assert "Existing content" in written_content

        # Should have appended content
        assert "New Section" in written_content
        assert "Appended content" in written_content


class TestInsertAtSection:
    """Tests for insert_at_section functionality."""

    def test_insert_after_section(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test inserting content after a section."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = """# Title

## Introduction

Intro content.

## Conclusion

Final content.
"""

        mock_file_repo.read_file.return_value = original_content

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
            result = writer_service.insert_at_section(
                tmp_path,
                1,
                "Introduction",
                "## Middle Section\n\nInserted content.",
                reader_service,
                position="after",
                dry_run=False,
                create_backup=False,
            )

        assert result.success is True
        written_content = mock_file_repo.write_file.call_args[0][1]

        # Check order: Introduction, Middle, Conclusion
        intro_pos = written_content.find("## Introduction")
        middle_pos = written_content.find("## Middle Section")
        conclusion_pos = written_content.find("## Conclusion")

        assert intro_pos < middle_pos < conclusion_pos

    def test_insert_before_section(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test inserting content before a section."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = """# Title

## Introduction

Intro content.

## Conclusion

Final content.
"""

        mock_file_repo.read_file.return_value = original_content

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
            result = writer_service.insert_at_section(
                tmp_path,
                1,
                "Conclusion",
                "## Summary\n\nSummary content.",
                reader_service,
                position="before",
                dry_run=False,
                create_backup=False,
            )

        assert result.success is True
        written_content = mock_file_repo.write_file.call_args[0][1]

        # Check order: Introduction, Summary, Conclusion
        intro_pos = written_content.find("## Introduction")
        summary_pos = written_content.find("## Summary")
        conclusion_pos = written_content.find("## Conclusion")

        assert intro_pos < summary_pos < conclusion_pos


class TestReplaceSection:
    """Tests for replace_section functionality."""

    def test_replace_section_preserves_heading(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test replacing section content while preserving heading."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = """# Title

## Introduction

Old intro content.

## Conclusion

Final content.
"""

        mock_file_repo.read_file.return_value = original_content

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
            result = writer_service.replace_section(
                tmp_path,
                1,
                "Introduction",
                "New intro content here.",
                reader_service,
                preserve_heading=True,
                dry_run=False,
                create_backup=False,
            )

        assert result.success is True
        written_content = mock_file_repo.write_file.call_args[0][1]

        # Should preserve heading
        assert "## Introduction" in written_content

        # Should have new content
        assert "New intro content" in written_content

        # Should not have old content
        assert "Old intro content" not in written_content

        # Should preserve other sections
        assert "## Conclusion" in written_content


class TestBackupCreation:
    """Tests for backup file creation."""

    def test_create_backup(self, writer_service, tmp_path):
        """Test backup file creation."""
        # Create a real file for backup test
        test_file = tmp_path / "test.md"
        test_file.write_text("Original content")

        backup_path = writer_service._create_backup(test_file)

        assert backup_path.exists()
        assert backup_path.suffix == ".bak"
        assert backup_path.read_text() == "Original content"

        # Clean up
        backup_path.unlink()


class TestChapterNotFound:
    """Tests for error handling when chapter not found."""

    def test_update_chapter_not_found(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test error when chapter doesn't exist."""
        book = Book(
            root_path=tmp_path,
            metadata=BookMetadata(title="Test", author="Test"),
            chapters=[],
        )

        with patch.object(reader_service, "load_book", return_value=book):
            with pytest.raises(KeyError) as exc_info:
                writer_service.update_chapter_content(
                    tmp_path, 99, "Content", reader_service
                )

            assert "99" in str(exc_info.value)


class TestSectionNotFound:
    """Tests for error handling when section not found."""

    def test_insert_section_not_found(
        self, writer_service, reader_service, mock_file_repo, tmp_path
    ):
        """Test error when section doesn't exist."""
        chapter_path = tmp_path / "chapters" / "01-intro.md"
        original_content = """# Title

## Only Section

Content here.
"""

        mock_file_repo.read_file.return_value = original_content

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
            with pytest.raises(KeyError) as exc_info:
                writer_service.insert_at_section(
                    tmp_path,
                    1,
                    "Nonexistent Section",
                    "Content",
                    reader_service,
                )

            assert "Nonexistent" in str(exc_info.value)
