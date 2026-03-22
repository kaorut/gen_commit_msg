"""Git operations module for retrieving diffs."""

import subprocess
from typing import Sequence


GIT_NOT_FOUND_MESSAGE = "git command not found. Please install Git."


def is_git_repository() -> bool:
    """Return True if current working directory is inside a Git repository."""
    result = _run_git(["rev-parse", "--is-inside-work-tree"], capture_output=True)
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def get_git_diff(include_unstaged: bool = False) -> str:
    """
    Retrieve git diff text for commit message generation.

    When include_unstaged is False, only staged changes are included.
    When include_unstaged is True, both staged and unstaged changes are included.

    Args:
            include_unstaged: Include unstaged changes when True

    Returns:
            Diff text for prompt generation

    Raises:
            RuntimeError: If git operations fail
    """
    staged_diff = run_git_command(["diff", "--cached"])

    parts = [part for part in (staged_diff,) if part.strip()]
    if include_unstaged:
        unstaged_diff = run_git_command(["diff"])
        if unstaged_diff.strip():
            parts.append(unstaged_diff)

    if not parts:
        return ""

    return "\n".join(parts).strip() + "\n"


def run_git_command(args: list[str]) -> str:
    """
    Execute a git command and return the output.

    Args:
            args: Command arguments (without 'git' prefix)

    Returns:
            Command output as string

    Raises:
            RuntimeError: If the git command fails
    """
    result = _run_git(args, capture_output=True)

    if result.returncode != 0:
        command_text = "git " + " ".join(args)
        raise RuntimeError(result.stderr.strip() or f"Failed to run {command_text}")

    return result.stdout


def commit_with_message(message: str, commit_options: Sequence[str]) -> None:
    """
    Run git commit with the provided message and pass-through options.

    Args:
            message: Commit message text
            commit_options: git commit options (must start with '-' or '--')

    Raises:
            RuntimeError: If commit message is empty or commit command fails
    """
    text = message.strip()
    if not text:
        raise RuntimeError("Commit message is empty")

    command = ["git", "commit", *commit_options, "-F", "-"]
    result = _run_git(command[1:], capture_output=False, input_text=text + "\n")

    if result.returncode != 0:
        raise RuntimeError(f"git commit failed (exit code: {result.returncode})")


def _run_git(
    args: list[str],
    *,
    capture_output: bool,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git command and normalize FileNotFoundError into RuntimeError."""
    try:
        return subprocess.run(
            ["git", *args],
            input=input_text,
            capture_output=capture_output,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError(GIT_NOT_FOUND_MESSAGE) from exc
