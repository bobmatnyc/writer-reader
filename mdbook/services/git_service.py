"""Git integration service for version history and diffs.

Provides git-based version control features for markdown books,
including commit history, diffs between versions, and content
at specific commits.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path

from ..domain import (
    CommitInfo,
    DiffHunk,
    FileDiff,
    ChapterHistory,
    RecentChange,
)


class GitService:
    """Service for git operations on book repositories.

    Implements git history, diff, and content retrieval operations
    using subprocess calls to git CLI.
    """

    # Git log format for parsing commits
    # Fields: hash, short_hash, author, email, timestamp, subject, body
    LOG_FORMAT = "%H%n%h%n%an%n%ae%n%at%n%s%n%b%n---COMMIT_END---"

    def __init__(self) -> None:
        """Initialize the git service."""
        pass

    def is_git_repo(self, path: Path) -> bool:
        """Check if a path is inside a git repository.

        Args:
            path: Path to check.

        Returns:
            True if the path is inside a git repo.
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path if path.is_dir() else path.parent,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_repo_root(self, path: Path) -> Path | None:
        """Get the root directory of the git repository.

        Args:
            path: A path inside the repository.

        Returns:
            The repository root path, or None if not a git repo.
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=path if path.is_dir() else path.parent,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def get_chapter_history(
        self,
        chapter_path: Path,
        limit: int = 50,
    ) -> ChapterHistory:
        """Get the commit history for a chapter file.

        Args:
            chapter_path: Path to the chapter markdown file.
            limit: Maximum number of commits to return.

        Returns:
            ChapterHistory with list of commits affecting the file.

        Raises:
            FileNotFoundError: If the chapter file doesn't exist.
            ValueError: If the path is not in a git repository.
        """
        if not chapter_path.exists():
            raise FileNotFoundError(f"Chapter not found: {chapter_path}")

        if not self.is_git_repo(chapter_path):
            raise ValueError(f"Not a git repository: {chapter_path}")

        repo_root = self.get_repo_root(chapter_path)
        if repo_root is None:
            raise ValueError(f"Cannot find git repository root for: {chapter_path}")

        # Get relative path from repo root
        try:
            rel_path = chapter_path.resolve().relative_to(repo_root)
        except ValueError:
            rel_path = chapter_path

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-n{limit}",
                    f"--format={self.LOG_FORMAT}",
                    "--follow",  # Follow file renames
                    "--",
                    str(rel_path),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return ChapterHistory(chapter_path=str(chapter_path), commits=[])

        if result.returncode != 0:
            return ChapterHistory(chapter_path=str(chapter_path), commits=[])

        commits = self._parse_log_output(result.stdout)
        return ChapterHistory(chapter_path=str(chapter_path), commits=commits)

    def get_chapter_diff(
        self,
        chapter_path: Path,
        commit_from: str = "HEAD~1",
        commit_to: str = "HEAD",
    ) -> FileDiff:
        """Get the diff between two versions of a chapter.

        Args:
            chapter_path: Path to the chapter markdown file.
            commit_from: Starting commit (older version).
            commit_to: Ending commit (newer version).

        Returns:
            FileDiff with changes between versions.

        Raises:
            FileNotFoundError: If the chapter file doesn't exist.
            ValueError: If the path is not in a git repository.
        """
        if not chapter_path.exists():
            raise FileNotFoundError(f"Chapter not found: {chapter_path}")

        if not self.is_git_repo(chapter_path):
            raise ValueError(f"Not a git repository: {chapter_path}")

        repo_root = self.get_repo_root(chapter_path)
        if repo_root is None:
            raise ValueError(f"Cannot find git repository root for: {chapter_path}")

        try:
            rel_path = chapter_path.resolve().relative_to(repo_root)
        except ValueError:
            rel_path = chapter_path

        try:
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    commit_from,
                    commit_to,
                    "--",
                    str(rel_path),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return FileDiff(
                file_path=str(chapter_path),
                commit_from=commit_from,
                commit_to=commit_to,
                additions=0,
                deletions=0,
            )

        if result.returncode != 0:
            return FileDiff(
                file_path=str(chapter_path),
                commit_from=commit_from,
                commit_to=commit_to,
                additions=0,
                deletions=0,
            )

        return self._parse_diff_output(
            result.stdout,
            str(chapter_path),
            commit_from,
            commit_to,
        )

    def get_chapter_at_commit(
        self,
        chapter_path: Path,
        commit: str = "HEAD",
    ) -> str:
        """Get the content of a chapter at a specific commit.

        Args:
            chapter_path: Path to the chapter markdown file.
            commit: The commit reference (hash, branch, tag, HEAD~N, etc.).

        Returns:
            The chapter content at that commit.

        Raises:
            FileNotFoundError: If the chapter file doesn't exist at that commit.
            ValueError: If the path is not in a git repository.
        """
        if not self.is_git_repo(chapter_path):
            raise ValueError(f"Not a git repository: {chapter_path}")

        repo_root = self.get_repo_root(chapter_path)
        if repo_root is None:
            raise ValueError(f"Cannot find git repository root for: {chapter_path}")

        try:
            rel_path = chapter_path.resolve().relative_to(repo_root)
        except ValueError:
            rel_path = chapter_path

        try:
            result = subprocess.run(
                ["git", "show", f"{commit}:{rel_path}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as e:
            raise FileNotFoundError(
                f"Timeout getting {chapter_path} at {commit}"
            ) from e

        if result.returncode != 0:
            raise FileNotFoundError(
                f"Chapter not found at commit {commit}: {chapter_path}"
            )

        return result.stdout

    def get_recent_changes(
        self,
        book_path: Path,
        limit: int = 20,
    ) -> list[RecentChange]:
        """Get recent changes across the entire book.

        Args:
            book_path: Root path of the book directory.
            limit: Maximum number of changes to return.

        Returns:
            List of RecentChange objects for .md files.

        Raises:
            ValueError: If the path is not in a git repository.
        """
        if not book_path.is_dir():
            raise ValueError(f"Not a directory: {book_path}")

        if not self.is_git_repo(book_path):
            raise ValueError(f"Not a git repository: {book_path}")

        repo_root = self.get_repo_root(book_path)
        if repo_root is None:
            raise ValueError(f"Cannot find git repository root for: {book_path}")

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-n{limit * 3}",  # Fetch more, filter later
                    "--name-status",
                    f"--format={self.LOG_FORMAT}",
                    "--",
                    "*.md",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return []

        if result.returncode != 0:
            return []

        return self._parse_recent_changes(result.stdout, limit)

    def _parse_log_output(self, output: str) -> list[CommitInfo]:
        """Parse git log output into CommitInfo objects.

        Args:
            output: Raw git log output.

        Returns:
            List of CommitInfo objects.
        """
        commits = []
        raw_commits = output.split("---COMMIT_END---")

        for raw in raw_commits:
            raw = raw.strip()
            if not raw:
                continue

            lines = raw.split("\n")
            if len(lines) < 6:
                continue

            try:
                full_hash = lines[0].strip()
                short_hash = lines[1].strip()
                author = lines[2].strip()
                email = lines[3].strip()
                timestamp = int(lines[4].strip())
                subject = lines[5].strip()
                body = "\n".join(lines[6:]).strip() if len(lines) > 6 else ""

                commit = CommitInfo(
                    hash=full_hash,
                    short_hash=short_hash,
                    author=author,
                    author_email=email,
                    date=datetime.fromtimestamp(timestamp),
                    message=f"{subject}\n\n{body}".strip() if body else subject,
                    subject=subject,
                )
                commits.append(commit)
            except (ValueError, IndexError):
                continue

        return commits

    def _parse_diff_output(
        self,
        output: str,
        file_path: str,
        commit_from: str,
        commit_to: str,
    ) -> FileDiff:
        """Parse git diff output into FileDiff object.

        Args:
            output: Raw git diff output.
            file_path: Path to the file.
            commit_from: Starting commit.
            commit_to: Ending commit.

        Returns:
            FileDiff with parsed hunks and statistics.
        """
        additions = 0
        deletions = 0
        hunks: list[DiffHunk] = []

        # Parse hunks using @@ pattern
        hunk_pattern = re.compile(
            r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$",
            re.MULTILINE,
        )

        for match in hunk_pattern.finditer(output):
            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1

            # Find the content until next hunk or end
            hunk_start = match.end()
            next_match = hunk_pattern.search(output, hunk_start)
            hunk_end = next_match.start() if next_match else len(output)
            content = output[hunk_start:hunk_end].strip()

            # Count additions and deletions in this hunk
            for line in content.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

            hunks.append(
                DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    content=content,
                )
            )

        return FileDiff(
            file_path=file_path,
            commit_from=commit_from,
            commit_to=commit_to,
            additions=additions,
            deletions=deletions,
            hunks=hunks,
            raw_diff=output,
        )

    def _parse_recent_changes(
        self,
        output: str,
        limit: int,
    ) -> list[RecentChange]:
        """Parse git log with name-status into RecentChange objects.

        Args:
            output: Raw git log output with name-status.
            limit: Maximum number of changes to return.

        Returns:
            List of RecentChange objects.
        """
        changes: list[RecentChange] = []
        raw_commits = output.split("---COMMIT_END---")

        for raw in raw_commits:
            raw = raw.strip()
            if not raw:
                continue

            # Split into commit info and file status
            parts = raw.split("\n")
            if len(parts) < 7:
                continue

            try:
                full_hash = parts[0].strip()
                short_hash = parts[1].strip()
                author = parts[2].strip()
                email = parts[3].strip()
                timestamp = int(parts[4].strip())
                subject = parts[5].strip()

                # Find where body ends and file status begins
                body_lines = []
                file_status_start = 6
                for i in range(6, len(parts)):
                    line = parts[i]
                    # File status lines start with A, M, D, R followed by tab
                    if re.match(r"^[AMDRC]\t", line):
                        file_status_start = i
                        break
                    body_lines.append(line)

                body = "\n".join(body_lines).strip()

                commit = CommitInfo(
                    hash=full_hash,
                    short_hash=short_hash,
                    author=author,
                    author_email=email,
                    date=datetime.fromtimestamp(timestamp),
                    message=f"{subject}\n\n{body}".strip() if body else subject,
                    subject=subject,
                )

                # Parse file status lines
                for i in range(file_status_start, len(parts)):
                    line = parts[i].strip()
                    if not line:
                        continue

                    match = re.match(r"^([AMDRC])\t(.+)$", line)
                    if match:
                        status_code = match.group(1)
                        file_path = match.group(2)

                        # Only include .md files
                        if not file_path.endswith(".md"):
                            continue

                        change_type = {
                            "A": "added",
                            "M": "modified",
                            "D": "deleted",
                            "R": "renamed",
                            "C": "copied",
                        }.get(status_code, "modified")

                        changes.append(
                            RecentChange(
                                file_path=file_path,
                                commit=commit,
                                change_type=change_type,
                            )
                        )

                        if len(changes) >= limit:
                            return changes

            except (ValueError, IndexError):
                continue

        return changes[:limit]
