#!/usr/bin/env python3
"""
MD Book Tools Release Script

Automated semantic versioning and PyPI publishing.

Usage:
    python release.py patch      # 3.1.0 -> 3.1.1
    python release.py minor      # 3.1.0 -> 3.2.0
    python release.py major      # 3.1.0 -> 4.0.0
    python release.py --dry-run patch  # Show what would happen
    python release.py --publish patch  # Bump version and publish to PyPI

Examples:
    python release.py patch              # Just bump patch version
    python release.py --dry-run minor    # Preview minor version bump
    python release.py --publish patch    # Bump patch and publish to PyPI
"""
import argparse
import glob
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional


# Script directory (where version.py and pyproject.toml live)
SCRIPT_DIR = Path(__file__).parent.resolve()
VERSION_FILE = SCRIPT_DIR / "version.py"
PYPROJECT_FILE = SCRIPT_DIR / "pyproject.toml"
DIST_DIR = SCRIPT_DIR / "dist"


def run_command(
    cmd: list[str],
    check: bool = True,
    capture: bool = False,
    dry_run: bool = False,
    shell: bool = False
) -> Optional[subprocess.CompletedProcess]:
    """Run a command with optional dry-run support."""
    cmd_str = " ".join(cmd) if not shell else cmd[0]

    if dry_run:
        print(f"  [DRY-RUN] Would run: {cmd_str}")
        return None

    print(f"  Running: {cmd_str}")

    if shell:
        return subprocess.run(
            cmd_str,
            shell=True,
            check=check,
            capture_output=capture,
            text=True,
            cwd=SCRIPT_DIR
        )

    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        cwd=SCRIPT_DIR
    )


def get_current_version() -> Tuple[int, int, int]:
    """Read version from version.py.

    Parses the VERSION tuple from version.py file.

    Returns:
        Tuple of (major, minor, patch) version numbers.

    Raises:
        FileNotFoundError: If version.py doesn't exist.
        ValueError: If VERSION tuple cannot be parsed.
    """
    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"Version file not found: {VERSION_FILE}")

    content = VERSION_FILE.read_text()

    # Match: VERSION: Tuple[int, int, int] = (3, 1, 0)
    # or: VERSION = (3, 1, 0)
    pattern = r'VERSION[^=]*=\s*\((\d+),\s*(\d+),\s*(\d+)\)'
    match = re.search(pattern, content)

    if not match:
        raise ValueError(f"Could not parse VERSION from {VERSION_FILE}")

    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def bump_version(current: Tuple[int, int, int], bump_type: str) -> Tuple[int, int, int]:
    """Bump version based on type.

    Args:
        current: Current version as (major, minor, patch) tuple.
        bump_type: One of 'major', 'minor', or 'patch'.

    Returns:
        New version tuple with bumped component.
    """
    major, minor, patch = current

    if bump_type == "major":
        return (major + 1, 0, 0)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "patch":
        return (major, minor, patch + 1)

    return current


def version_to_string(version: Tuple[int, int, int]) -> str:
    """Convert version tuple to string."""
    return f"{version[0]}.{version[1]}.{version[2]}"


def update_version_files(new_version: Tuple[int, int, int], dry_run: bool = False) -> None:
    """Update version.py and pyproject.toml with new version.

    Args:
        new_version: New version as (major, minor, patch) tuple.
        dry_run: If True, only show what would be changed.
    """
    version_str = version_to_string(new_version)
    major, minor, patch = new_version

    # Update version.py
    print(f"\nUpdating {VERSION_FILE.name}...")
    content = VERSION_FILE.read_text()

    # Replace VERSION tuple
    new_content = re.sub(
        r'(VERSION[^=]*=\s*\()(\d+),\s*(\d+),\s*(\d+)(\))',
        f'\\g<1>{major}, {minor}, {patch}\\g<5>',
        content
    )

    if dry_run:
        print(f"  [DRY-RUN] Would update VERSION to ({major}, {minor}, {patch})")
    else:
        VERSION_FILE.write_text(new_content)
        print(f"  Updated VERSION to ({major}, {minor}, {patch})")

    # Update pyproject.toml
    print(f"\nUpdating {PYPROJECT_FILE.name}...")
    content = PYPROJECT_FILE.read_text()

    # Replace version = "x.y.z"
    new_content = re.sub(
        r'(version\s*=\s*")[\d.]+(")',
        f'\\g<1>{version_str}\\g<2>',
        content
    )

    if dry_run:
        print(f"  [DRY-RUN] Would update version to \"{version_str}\"")
    else:
        PYPROJECT_FILE.write_text(new_content)
        print(f"  Updated version to \"{version_str}\"")


def git_tag_and_push(version_str: str, dry_run: bool = False) -> None:
    """Create git tag and push changes.

    Args:
        version_str: Version string (e.g., "3.1.1").
        dry_run: If True, only show what would be done.
    """
    tag_name = f"v{version_str}"

    print(f"\nGit operations for {tag_name}...")

    # Check if we're in a git repository
    result = run_command(["git", "rev-parse", "--git-dir"], check=False, capture=True, dry_run=False)
    if result and result.returncode != 0:
        print("  Warning: Not in a git repository, skipping git operations")
        return

    # Add changed files
    run_command(["git", "add", str(VERSION_FILE), str(PYPROJECT_FILE)], dry_run=dry_run)

    # Commit
    commit_msg = f"Release {version_str}"
    run_command(["git", "commit", "-m", commit_msg], dry_run=dry_run)

    # Create tag
    run_command(["git", "tag", "-a", tag_name, "-m", f"Version {version_str}"], dry_run=dry_run)

    # Push commit and tag
    run_command(["git", "push"], dry_run=dry_run)
    run_command(["git", "push", "origin", tag_name], dry_run=dry_run)


def clean_dist(dry_run: bool = False) -> None:
    """Clean the dist directory before building.

    Args:
        dry_run: If True, only show what would be done.
    """
    if DIST_DIR.exists():
        if dry_run:
            print(f"  [DRY-RUN] Would remove {DIST_DIR}")
        else:
            print(f"  Removing {DIST_DIR}")
            shutil.rmtree(DIST_DIR)


def build_and_publish(dry_run: bool = False) -> None:
    """Build with uv and publish with twine.

    Uses uv for building and twine for PyPI upload.
    Twine uses credentials from ~/.pypirc.

    Args:
        dry_run: If True, only show what would be done.
    """
    print("\nBuilding package...")

    # Clean dist directory first
    clean_dist(dry_run)

    # Build with uv
    run_command(["uv", "build"], dry_run=dry_run)

    if not dry_run:
        # Verify build artifacts exist
        dist_files = list(DIST_DIR.glob("*")) if DIST_DIR.exists() else []
        if not dist_files:
            raise RuntimeError("Build failed: no files in dist/")
        print(f"  Built: {[f.name for f in dist_files]}")

    print("\nChecking package with twine...")
    # Use glob pattern for twine commands
    run_command(["twine", "check", "dist/*"], shell=True, dry_run=dry_run)

    print("\nUploading to PyPI...")
    run_command(["twine", "upload", "dist/*"], shell=True, dry_run=dry_run)


def main():
    """Main entry point for the release script."""
    parser = argparse.ArgumentParser(
        description="MD Book Tools Release Script - Semantic versioning and PyPI publishing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python release.py patch              # Bump patch version (3.1.0 -> 3.1.1)
    python release.py minor              # Bump minor version (3.1.0 -> 3.2.0)
    python release.py major              # Bump major version (3.1.0 -> 4.0.0)
    python release.py --dry-run patch    # Preview patch bump without changes
    python release.py --publish patch    # Bump patch and publish to PyPI
        """
    )

    parser.add_argument(
        "bump_type",
        nargs="?",
        choices=["major", "minor", "patch"],
        help="Type of version bump to perform"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )

    parser.add_argument(
        "--publish",
        action="store_true",
        help="Build and publish to PyPI after version bump"
    )

    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git tag and push operations"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show current version and exit"
    )

    args = parser.parse_args()

    # Show current version if requested
    if args.version:
        try:
            current = get_current_version()
            print(f"Current version: {version_to_string(current)}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Require bump type for other operations
    if not args.bump_type:
        parser.print_help()
        sys.exit(1)

    try:
        # Get current version
        current = get_current_version()
        current_str = version_to_string(current)

        # Calculate new version
        new_version = bump_version(current, args.bump_type)
        new_str = version_to_string(new_version)

        print("=" * 60)
        print("MD Book Tools Release Script")
        print("=" * 60)
        print(f"Current version: {current_str}")
        print(f"New version:     {new_str} ({args.bump_type} bump)")
        print(f"Dry run:         {args.dry_run}")
        print(f"Publish:         {args.publish}")
        print(f"Git operations:  {not args.no_git}")
        print("=" * 60)

        if args.dry_run:
            print("\n*** DRY RUN MODE - No changes will be made ***\n")

        # Update version files
        update_version_files(new_version, dry_run=args.dry_run)

        # Git operations (unless skipped)
        if not args.no_git:
            git_tag_and_push(new_str, dry_run=args.dry_run)

        # Build and publish if requested
        if args.publish:
            build_and_publish(dry_run=args.dry_run)

        print("\n" + "=" * 60)
        if args.dry_run:
            print(f"DRY RUN complete. Would have released {new_str}")
        else:
            print(f"Successfully released version {new_str}!")
            if args.publish:
                print(f"Package published to PyPI: mdbook=={new_str}")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
