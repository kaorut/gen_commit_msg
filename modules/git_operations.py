"""Git operations module for retrieving diffs."""

import subprocess
from typing import Sequence


GIT_NOT_FOUND_MESSAGE = "git command not found. Please install Git."
DIFF_UNIFIED_OPTION = "--unified=100"


def is_git_repository() -> bool:
    """Return True if current working directory is inside a Git repository."""
    result = _run_git(["rev-parse", "--is-inside-work-tree"], capture_output=True)
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def get_git_diff(
    revision_spec: str = "", include_unstaged: bool = False
) -> str:
    """
    Retrieve git diff text for commit message generation.

    Two modes:
    1. Revision-based mode (when revision_spec is provided):
       - diff from specified revision(s) + unstaged changes
    2. Staging mode (when revision_spec is empty):
       - staged only, or staged + unstaged based on include_unstaged

    Revision Spec Format (follows git diff syntax):
    - "REV1..REV2"  → diff from REV1 to REV2 (exclusive of REV2) + unstaged
    - "REV1...REV2" → diff from merge-base(REV1, REV2) to REV2 + unstaged
    - "REV"         → diff from REV to working tree + unstaged
    - ""            → staged and optionally unstaged changes

    Args:
            revision_spec: Git revision specification (follows git diff format)
            include_unstaged: Include unstaged changes when using staging mode

    Returns:
            Diff text for prompt generation

    Raises:
            RuntimeError: If git operations fail
    """
    parts = []

    if revision_spec:
        # Revision-based mode: always include unstaged along with revision diff
        revision_diff = _get_revision_diff(revision_spec)
        if revision_diff.strip():
            parts.append(revision_diff)
    else:
        # Staging mode
        staged_diff = run_git_command(_build_diff_command("--cached"))
        if staged_diff.strip():
            parts.append(staged_diff)

    # Append unstaged changes (in both revision and staging modes)
    unstaged_diff = run_git_command(_build_diff_command())
    if unstaged_diff.strip():
        parts.append(unstaged_diff)

    if not parts:
        return ""

    return "\n".join(parts).strip() + "\n"


def _get_revision_diff(revision_spec: str) -> str:
    """
    Generate diff for a git revision specification (follows git diff syntax).

    Formats:
    - "REV1..REV2"  → git diff REV1..REV2 (2-dot form)
    - "REV1...REV2" → git diff REV1...REV2 (3-dot form)
    - "REV"         → git diff REV (single commit)

    Args:
            revision_spec: Git revision specification

    Returns:
            Diff text

    Raises:
            ValueError: If revision_spec format is invalid
            RuntimeError: If git operations fail
    """
    spec = revision_spec.strip()
    if not spec:
        raise ValueError("Revision spec cannot be empty")

    # Check for 3-dot form (REV1...REV2)
    if "..." in spec:
        parts = spec.split("...")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid revision format '{revision_spec}'. "
                "Use 'REV1...REV2' format (only one ... separator allowed)."
            )
        rev1, rev2 = parts[0].strip(), parts[1].strip()
        if not rev1 or not rev2:
            raise ValueError(
                f"Invalid revision format '{revision_spec}'. "
                "Both REV1 and REV2 must be non-empty in 'REV1...REV2' format."
            )
        return run_git_command(_build_diff_command(f"{rev1}...{rev2}"))

    # Check for 2-dot form (REV1..REV2)
    if ".." in spec:
        parts = spec.split("..")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid revision format '{revision_spec}'. "
                "Use 'REV1..REV2' format (only one .. separator allowed)."
            )
        rev1, rev2 = parts[0].strip(), parts[1].strip()
        if not rev1 or not rev2:
            raise ValueError(
                f"Invalid revision format '{revision_spec}'. "
                "Both REV1 and REV2 must be non-empty in 'REV1..REV2' format."
            )
        return run_git_command(_build_diff_command(f"{rev1}..{rev2}"))

    # Single revision form (REV)
    return run_git_command(_build_diff_command(spec))


def _build_diff_command(*args: str) -> list[str]:
    """Build git diff command arguments with a fixed unified context."""
    return ["diff", DIFF_UNIFIED_OPTION, *args]


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


def get_last_commit_subject() -> str:
    """
    Return the subject line of the latest commit.

    Returns empty string when no commit exists yet.
    """
    result = _run_git(["log", "-1", "--pretty=%s"], capture_output=True)
    if result.returncode != 0:
        return ""

    return result.stdout.strip()


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
