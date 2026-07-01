"""GitHub Pages publisher."""

from __future__ import annotations

import subprocess  # nosec B404 - argv is a fixed list, never passed through a shell
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PublishResult:
    """Result of a GitHub Pages publish operation."""

    success: bool
    branch: str
    message: str = ""


class PublisherInterface(ABC):
    """Abstract interface for GitHub Pages publishers."""

    @abstractmethod
    def publish(self, source_dir: Path, branch: str = "gh-pages") -> PublishResult:
        """Publish source_dir contents to the target branch."""

    @abstractmethod
    def validate(self, source_dir: Path) -> bool:
        """Return True if source_dir is a valid publishable directory."""


class GitHubPagesPublisher(PublisherInterface):
    """Publishes a directory to GitHub Pages via git subtree push."""

    def __init__(self, remote: str = "origin") -> None:
        self.remote = remote

    def validate(self, source_dir: Path) -> bool:
        """Return True if source_dir is a valid publishable directory."""
        return source_dir.exists() and source_dir.is_dir()

    def publish(self, source_dir: Path, branch: str = "gh-pages") -> PublishResult:
        """Publish source_dir contents to the target branch via git subtree push."""
        if not self.validate(source_dir):
            return PublishResult(
                success=False,
                branch=branch,
                message=f"Source directory not found: {source_dir}",
            )
        try:
            result = subprocess.run(  # nosec B603 B607 - fixed argv, no shell; git resolved via PATH intentionally
                ["git", "subtree", "push", "--prefix", str(source_dir), self.remote, branch],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return PublishResult(success=True, branch=branch)
            return PublishResult(
                success=False,
                branch=branch,
                message=result.stderr.strip() or result.stdout.strip(),
            )
        except FileNotFoundError:
            return PublishResult(
                success=False,
                branch=branch,
                message="git executable not found",
            )
