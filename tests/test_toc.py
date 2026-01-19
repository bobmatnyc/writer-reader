"""
Tests for Table of Contents (SUMMARY.md) Management

Tests:
- Parsing hierarchical SUMMARY.md
- Preserving structure when adding new files
- Flat generation when preserve_structure=False
- Handling of Part headers (## Part I, etc.)
"""

from writer_reader.toc import (
    TocEntry,
    _normalize_path,
    _path_to_title,
    discover_markdown_files,
    parse_summary_structure,
    update_summary,
)


class TestParseSimpleSummary:
    """Test parsing basic SUMMARY.md structures."""

    def test_parse_empty_summary(self):
        """Should handle empty SUMMARY.md."""
        content = "# Summary\n"
        structure = parse_summary_structure(content)

        assert structure.title == "Summary"
        assert structure.entries == []

    def test_parse_flat_entries(self):
        """Should parse flat list of entries."""
        content = """# Summary

- [Introduction](intro.md)
- [Getting Started](getting-started.md)
- [Conclusion](conclusion.md)
"""
        structure = parse_summary_structure(content)

        assert len(structure.entries) == 3
        assert structure.entries[0].title == "Introduction"
        assert structure.entries[0].path == "intro.md"
        assert structure.entries[1].title == "Getting Started"
        assert structure.entries[1].path == "getting-started.md"

    def test_parse_preserves_custom_title(self):
        """Should preserve custom Summary title."""
        content = "# Table of Contents\n\n- [Intro](intro.md)\n"
        structure = parse_summary_structure(content)

        assert structure.title == "Table of Contents"
        assert structure.raw_header == "# Table of Contents"


class TestParseHierarchicalSummary:
    """Test parsing nested SUMMARY.md structures."""

    def test_parse_nested_entries(self):
        """Should parse nested hierarchy correctly."""
        content = """# Summary

- [Basics](basics/index.md)
  - [Installation](basics/install.md)
  - [Configuration](basics/config.md)
- [Advanced](advanced/index.md)
  - [Plugins](advanced/plugins.md)
"""
        structure = parse_summary_structure(content)

        assert len(structure.entries) == 2

        # Check first top-level entry
        basics = structure.entries[0]
        assert basics.title == "Basics"
        assert basics.indent_level == 0
        assert len(basics.children) == 2
        assert basics.children[0].title == "Installation"
        assert basics.children[0].indent_level == 1

        # Check second top-level entry
        advanced = structure.entries[1]
        assert advanced.title == "Advanced"
        assert len(advanced.children) == 1

    def test_parse_deeply_nested(self):
        """Should handle multiple nesting levels."""
        content = """# Summary

- [Level 0](l0.md)
  - [Level 1](l1.md)
    - [Level 2](l2.md)
      - [Level 3](l3.md)
"""
        structure = parse_summary_structure(content)

        assert len(structure.entries) == 1
        level0 = structure.entries[0]
        assert level0.title == "Level 0"

        level1 = level0.children[0]
        assert level1.title == "Level 1"
        assert level1.indent_level == 1

        level2 = level1.children[0]
        assert level2.title == "Level 2"
        assert level2.indent_level == 2

        level3 = level2.children[0]
        assert level3.title == "Level 3"
        assert level3.indent_level == 3


class TestParsePartHeaders:
    """Test handling of Part headers (## Part I, etc.)."""

    def test_parse_part_headers(self):
        """Should recognize Part headers."""
        content = """# Summary

## Part I: Basics

- [Introduction](intro.md)
- [Setup](setup.md)

## Part II: Advanced

- [Deep Dive](deep-dive.md)
"""
        structure = parse_summary_structure(content)

        # Should have 4 top-level entries: 2 parts + 2 regular entries per part
        part_entries = [e for e in structure.entries if e.is_part_header]
        assert len(part_entries) == 2
        assert part_entries[0].title == "Part I: Basics"
        assert part_entries[1].title == "Part II: Advanced"

    def test_part_headers_reset_hierarchy(self):
        """Part headers should reset nesting context."""
        content = """# Summary

## Part I

- [Chapter 1](ch1.md)
  - [Section 1.1](s1-1.md)

## Part II

- [Chapter 2](ch2.md)
"""
        structure = parse_summary_structure(content)

        # Find non-part entries
        regular_entries = [e for e in structure.entries if not e.is_part_header]

        # Chapter 2 should be top-level, not nested under Part I's content
        ch2 = [e for e in regular_entries if e.title == "Chapter 2"]
        assert len(ch2) == 1
        assert ch2[0].indent_level == 0


class TestTocStructure:
    """Test TocStructure methods."""

    def test_get_all_paths(self):
        """Should collect all file paths from structure."""
        content = """# Summary

- [Intro](intro.md)
  - [Sub](sub.md)
- [Main](main.md)
"""
        structure = parse_summary_structure(content)
        paths = structure.get_all_paths()

        assert paths == {"intro.md", "sub.md", "main.md"}

    def test_get_all_paths_with_parts(self):
        """Should include paths from all parts."""
        content = """# Summary

## Part I

- [Ch1](ch1.md)

## Part II

- [Ch2](ch2.md)
"""
        structure = parse_summary_structure(content)
        paths = structure.get_all_paths()

        assert "ch1.md" in paths
        assert "ch2.md" in paths

    def test_to_markdown_roundtrip(self):
        """Converting back to markdown should preserve content."""
        original = """# Summary

- [Introduction](intro.md)
- [Getting Started](getting-started.md)
"""
        structure = parse_summary_structure(original)
        regenerated = structure.to_markdown()

        # Re-parse and compare
        reparsed = parse_summary_structure(regenerated)
        assert len(reparsed.entries) == len(structure.entries)
        assert reparsed.entries[0].title == structure.entries[0].title
        assert reparsed.entries[0].path == structure.entries[0].path


class TestDiscoverMarkdownFiles:
    """Test markdown file discovery."""

    def test_discover_in_src_directory(self, tmp_path):
        """Should find .md files in src/ directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "intro.md").write_text("# Intro", encoding="utf-8")
        (src_dir / "chapter1.md").write_text("# Chapter 1", encoding="utf-8")
        (src_dir / "SUMMARY.md").write_text("# Summary", encoding="utf-8")

        files = discover_markdown_files(tmp_path)

        assert len(files) == 2
        assert "src/intro.md" in files or "src\\intro.md" in files
        # SUMMARY.md should be excluded
        assert all("SUMMARY.md" not in f for f in files)

    def test_discover_in_chapters_directory(self, tmp_path):
        """Should find .md files in chapters/ directory."""
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "ch01-intro.md").write_text("# Intro", encoding="utf-8")
        (chapters_dir / "ch02-main.md").write_text("# Main", encoding="utf-8")

        files = discover_markdown_files(tmp_path)

        assert len(files) == 2

    def test_discover_nested_files(self, tmp_path):
        """Should find .md files in subdirectories."""
        src_dir = tmp_path / "src"
        basics_dir = src_dir / "basics"
        basics_dir.mkdir(parents=True)
        (src_dir / "intro.md").write_text("# Intro", encoding="utf-8")
        (basics_dir / "install.md").write_text("# Install", encoding="utf-8")

        files = discover_markdown_files(tmp_path)

        assert len(files) == 2

    def test_discover_empty_directory(self, tmp_path):
        """Should handle missing directories gracefully."""
        files = discover_markdown_files(tmp_path)
        assert files == []


class TestUpdateSummaryPreserveStructure:
    """Test update_summary with preserve_structure=True."""

    def test_preserve_existing_hierarchy(self, tmp_path):
        """Should preserve existing structure when adding files."""
        # Setup existing SUMMARY.md
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        existing_summary = """# Summary

- [Introduction](src/intro.md)
  - [Getting Started](src/getting-started.md)
- [Main Content](src/main.md)
"""
        (src_dir / "SUMMARY.md").write_text(existing_summary, encoding="utf-8")

        # Create markdown files
        (src_dir / "intro.md").write_text("# Intro", encoding="utf-8")
        (src_dir / "getting-started.md").write_text("# Getting Started", encoding="utf-8")
        (src_dir / "main.md").write_text("# Main", encoding="utf-8")
        (src_dir / "new-chapter.md").write_text("# New Chapter", encoding="utf-8")

        result = update_summary(tmp_path, preserve_structure=True)

        assert len(result["added"]) == 1
        assert "new-chapter.md" in result["added"][0]
        assert len(result["existing"]) == 3

        # Verify hierarchy preserved in output
        output = (src_dir / "SUMMARY.md").read_text(encoding="utf-8")
        structure = parse_summary_structure(output)

        # Original nested structure should be preserved
        intro = [e for e in structure.entries if e.title == "Introduction"]
        assert len(intro) == 1
        assert len(intro[0].children) == 1

    def test_add_new_files_at_end(self, tmp_path):
        """New files should be added at end of structure."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        existing_summary = """# Summary

- [First](src/first.md)
"""
        (src_dir / "SUMMARY.md").write_text(existing_summary, encoding="utf-8")
        (src_dir / "first.md").write_text("# First", encoding="utf-8")
        (src_dir / "second.md").write_text("# Second", encoding="utf-8")
        (src_dir / "third.md").write_text("# Third", encoding="utf-8")

        update_summary(tmp_path, preserve_structure=True)

        output = (src_dir / "SUMMARY.md").read_text(encoding="utf-8")
        structure = parse_summary_structure(output)

        # First entry should still be "First"
        non_part_entries = [e for e in structure.entries if not e.is_part_header]
        assert non_part_entries[0].title == "First"

        # New entries added after
        assert len(non_part_entries) == 3


class TestUpdateSummaryFlatStructure:
    """Test update_summary with preserve_structure=False."""

    def test_generate_flat_structure(self, tmp_path):
        """Should generate flat list ignoring existing hierarchy."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Existing hierarchical SUMMARY
        existing_summary = """# Summary

- [Introduction](src/intro.md)
  - [Getting Started](src/getting-started.md)
"""
        (src_dir / "SUMMARY.md").write_text(existing_summary, encoding="utf-8")
        (src_dir / "intro.md").write_text("# Intro", encoding="utf-8")
        (src_dir / "getting-started.md").write_text("# Getting Started", encoding="utf-8")

        result = update_summary(tmp_path, preserve_structure=False)

        # All files should be in "added" since we're regenerating
        assert len(result["added"]) == 2
        assert len(result["existing"]) == 0

        # Output should be flat
        output = (src_dir / "SUMMARY.md").read_text(encoding="utf-8")
        structure = parse_summary_structure(output)

        for entry in structure.entries:
            assert entry.indent_level == 0
            assert len(entry.children) == 0

    def test_create_summary_if_not_exists(self, tmp_path):
        """Should create SUMMARY.md if it doesn't exist."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "chapter.md").write_text("# Chapter", encoding="utf-8")

        result = update_summary(tmp_path, preserve_structure=False)

        assert (src_dir / "SUMMARY.md").exists()
        assert len(result["added"]) == 1


class TestPathToTitle:
    """Test path to title conversion."""

    def test_simple_filename(self):
        """Should convert simple filename to title."""
        assert _path_to_title("introduction.md") == "Introduction"

    def test_kebab_case_filename(self):
        """Should convert kebab-case to title."""
        assert _path_to_title("getting-started.md") == "Getting Started"

    def test_snake_case_filename(self):
        """Should convert snake_case to title."""
        assert _path_to_title("user_guide.md") == "User Guide"

    def test_chapter_prefix_removed(self):
        """Should remove chapter prefixes."""
        assert _path_to_title("ch01-introduction.md") == "Introduction"
        assert _path_to_title("chapter-02-basics.md") == "Basics"

    def test_path_with_directory(self):
        """Should handle paths with directories."""
        assert _path_to_title("chapters/ch01-intro.md") == "Intro"


class TestNormalizePath:
    """Test path normalization."""

    def test_normalize_removes_dot_slash(self):
        """Should remove leading ./"""
        assert _normalize_path("./intro.md") == "intro.md"

    def test_normalize_backslashes(self):
        """Should convert backslashes to forward slashes."""
        assert _normalize_path("chapters\\intro.md") == "chapters/intro.md"

    def test_normalize_lowercase(self):
        """Should lowercase for comparison."""
        assert _normalize_path("Chapter/INTRO.md") == "chapter/intro.md"


class TestTocEntry:
    """Test TocEntry methods."""

    def test_to_markdown_with_link(self):
        """Should generate correct markdown for linked entry."""
        entry = TocEntry(title="Introduction", path="intro.md", indent_level=0)
        assert entry.to_markdown() == "- [Introduction](intro.md)"

    def test_to_markdown_nested(self):
        """Should generate correct indentation."""
        entry = TocEntry(title="Sub Section", path="sub.md", indent_level=2)
        assert entry.to_markdown() == "    - [Sub Section](sub.md)"

    def test_to_markdown_part_header(self):
        """Should preserve part header format."""
        entry = TocEntry(
            title="Part I: Basics",
            path=None,
            is_part_header=True,
            raw_line="## Part I: Basics",
        )
        assert "## Part I: Basics" in entry.to_markdown()


class TestCLIIntegration:
    """Test CLI command integration."""

    def test_cli_command_exists(self):
        """Should have update-toc command registered."""
        from click.testing import CliRunner

        from writer_reader.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert "update-toc" in result.output

    def test_cli_update_toc_help(self):
        """Should show help for update-toc command."""
        from click.testing import CliRunner

        from writer_reader.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["update-toc", "--help"])

        assert result.exit_code == 0
        assert "preserve-structure" in result.output
        assert "SUMMARY.md" in result.output

    def test_cli_update_toc_runs(self, tmp_path):
        """Should run update-toc command successfully."""
        from click.testing import CliRunner

        from writer_reader.cli import main

        # Setup
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "chapter.md").write_text("# Chapter", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["update-toc", str(tmp_path)])

        assert result.exit_code == 0
        assert "Updating SUMMARY.md" in result.output
        assert (src_dir / "SUMMARY.md").exists()
