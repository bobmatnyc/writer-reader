"""
Version information for md-book-reader/writer.

This module provides semantic versioning with build tracking.

Version format: MAJOR.MINOR.PATCH+build.BUILD_NUMBER
Example: 2.1.0+build.42

Usage:
    from version import __version__, get_version
    print(__version__)      # "2.1.0+build.42"
    print(get_version())    # "2.1.0+build.42"
"""

import subprocess
from pathlib import Path
from typing import Tuple

# Semantic version components
VERSION: Tuple[int, int, int] = (1, 0, 3)

# Build number - can be set manually or computed from git
_BUILD_NUMBER: int = 0


def _get_git_commit_count() -> int:
    """Get the number of commits in the git repository."""
    try:
        # Get the directory where this module lives
        module_dir = Path(__file__).parent.resolve()

        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=module_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (
        subprocess.TimeoutExpired,
        subprocess.SubprocessError,
        ValueError,
        FileNotFoundError,
    ):
        pass
    return 0


def _get_build_number() -> int:
    """Get the build number, preferring git commit count if available."""
    global _BUILD_NUMBER
    if _BUILD_NUMBER > 0:
        return _BUILD_NUMBER

    git_count = _get_git_commit_count()
    if git_count > 0:
        return git_count

    return _BUILD_NUMBER


def get_version() -> str:
    """
    Get the full version string including build number.

    Returns:
        Version string in format "MAJOR.MINOR.PATCH+build.BUILD_NUMBER"
        Example: "2.1.0+build.42"
    """
    major, minor, patch = VERSION
    build = _get_build_number()
    return f"{major}.{minor}.{patch}+build.{build}"


def get_short_version() -> str:
    """
    Get the short version string (without build number).

    Returns:
        Version string in format "MAJOR.MINOR.PATCH"
        Example: "2.1.0"
    """
    major, minor, patch = VERSION
    return f"{major}.{minor}.{patch}"


# Module-level version string for convenience
__version__ = get_version()


if __name__ == "__main__":
    print(f"Version: {__version__}")
    print(f"Short version: {get_short_version()}")
    print(f"VERSION tuple: {VERSION}")
    print(f"Build number: {_get_build_number()}")
