"""Git operations module for retrieving diffs."""

import subprocess
from typing import Sequence


GIT_NOT_FOUND_MESSAGE = "git command not found. Please install Git."
DEFAULT_DIFF_UNIFIED_LINES = 100


def is_git_repository() -> bool:
    """Return True if current working directory is inside a Git repository."""
    result = _run_git(["rev-parse", "--is-inside-work-tree"], capture_output=True)
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def get_git_diff(
    revision_spec: str = "",
    include_unstaged: bool = False,
    unified_lines: int = DEFAULT_DIFF_UNIFIED_LINES,
) -> str:
    """
    Retrieve git diff text for commit message generation.

     Two modes:
     1. Revision-based mode (when revision_spec is provided):
         - diff from specified revision(s)
     2. Staging mode (when revision_spec is empty):
         - staged only, or staged + unstaged based on include_unstaged

     Revision Spec Format (follows git diff syntax):
     - "REV1..REV2"  → diff from REV1 to REV2 (exclusive of REV2)
     - "REV1...REV2" → diff from merge-base(REV1, REV2) to REV2
     - "REV"         → diff of commit REV (same as REV^..REV)
     - ""            → staged and optionally unstaged changes

    Args:
            revision_spec: Git revision specification (follows git diff format)
            include_unstaged: Include unstaged changes in AI input
            unified_lines: Number of unified context lines for git diff

    Returns:
            Diff text for prompt generation

    Raises:
            RuntimeError: If git operations fail
    """
    parts: list[str] = []

    if revision_spec:
        _append_non_empty_diff(parts, _get_revision_diff(revision_spec, unified_lines=unified_lines))
    else:
        _append_non_empty_diff(
            parts,
            run_git_command(_build_diff_command("--cached", unified_lines=unified_lines)),
        )

    if _should_include_unstaged_diff(include_unstaged=include_unstaged):
        _append_non_empty_diff(
            parts,
            run_git_command(_build_diff_command(unified_lines=unified_lines)),
        )

    if not parts:
        return ""

    return "\n".join(parts).strip() + "\n"


def _append_non_empty_diff(parts: list[str], diff_text: str) -> None:
    """Append diff text when it has non-whitespace content."""
    if diff_text.strip():
        parts.append(diff_text)


def _should_include_unstaged_diff(*, include_unstaged: bool) -> bool:
    """Return True when unstaged changes should be included in AI input."""
    return include_unstaged


def _get_revision_diff(revision_spec: str, *, unified_lines: int) -> str:
    """
    Generate diff for a git revision specification (follows git diff syntax).

    Formats:
    - "REV1..REV2"  → git diff REV1..REV2 (2-dot form)
    - "REV1...REV2" → git diff REV1...REV2 (3-dot form)
    - "REV"         → git diff REV^..REV (single commit)

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

    target = _resolve_revision_diff_target(
        spec,
        original_revision_spec=revision_spec,
    )
    return run_git_command(_build_diff_command(target, unified_lines=unified_lines))


def _resolve_revision_diff_target(
    revision_spec: str,
    *,
    original_revision_spec: str,
) -> str:
    """Resolve revision spec into one git diff target argument."""
    # Check for 3-dot form (REV1...REV2)
    if "..." in revision_spec:
        rev1, rev2 = _split_revision_pair(
            revision_spec,
            separator="...",
            original_revision_spec=original_revision_spec,
        )
        return f"{rev1}...{rev2}"

    # Check for 2-dot form (REV1..REV2)
    if ".." in revision_spec:
        rev1, rev2 = _split_revision_pair(
            revision_spec,
            separator="..",
            original_revision_spec=original_revision_spec,
        )
        return f"{rev1}..{rev2}"

    # Single revision form (REV) is interpreted as one-commit range.
    return f"{revision_spec}^..{revision_spec}"


def _build_diff_command(*args: str, unified_lines: int) -> list[str]:
    """Build git diff command arguments with a fixed unified context."""
    return ["diff", f"--unified={unified_lines}", *args]


def _split_revision_pair(
    revision_spec: str,
    *,
    separator: str,
    original_revision_spec: str,
) -> tuple[str, str]:
    """Split and validate one two-revision specification."""
    parts = revision_spec.split(separator)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid revision format '{original_revision_spec}'. "
            f"Use 'REV1{separator}REV2' format "
            f"(only one {separator} separator allowed)."
        )

    rev1, rev2 = parts[0].strip(), parts[1].strip()
    if not rev1 or not rev2:
        raise ValueError(
            f"Invalid revision format '{original_revision_spec}'. "
            f"Both REV1 and REV2 must be non-empty in 'REV1{separator}REV2' format."
        )

    return rev1, rev2


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


def get_origin_owner_repo() -> tuple[str, str]:
    """Return (owner, repo) parsed from git remote origin URL."""
    result = _run_git(["remote", "get-url", "origin"], capture_output=True)
    if result.returncode != 0:
        return "", ""

    return parse_owner_repo_from_remote_url(result.stdout.strip())


def parse_owner_repo_from_remote_url(url: str) -> tuple[str, str]:
    """Parse owner and repo name from HTTPS/SSH GitHub remote URL."""
    remote_path = _extract_remote_path(url)
    if not remote_path:
        return "", ""

    return _parse_owner_repo_from_path(remote_path)


def _parse_owner_repo_from_path(remote_path: str) -> tuple[str, str]:
    """Parse owner/repo from remote path-like text."""
    segments = [segment for segment in remote_path.split("/") if segment]
    if len(segments) < 2:
        return "", ""

    owner = segments[-2].strip()
    repo = segments[-1].strip()
    if not owner or not repo:
        return "", ""

    return owner, repo


def _extract_remote_path(url: str) -> str:
    """Extract owner/repo-like path from SSH/HTTPS remote URL."""
    value = url.strip()
    if not value:
        return ""

    ssh_path = _extract_ssh_remote_path(value)
    if ssh_path:
        value = ssh_path
    elif "://" in value:
        value = _extract_http_remote_path(value)
        if not value:
            return ""

    if value.endswith(".git"):
        value = value[:-4]
    return value


def _extract_ssh_remote_path(url: str) -> str:
    """Extract path from SSH remote URL (git@host:owner/repo.git)."""
    if not url.startswith("git@") or ":" not in url:
        return ""
    return url.split(":", 1)[1]


def _extract_http_remote_path(url: str) -> str:
    """Extract path from HTTP(S) remote URL."""
    parts = url.split("/", 3)
    if len(parts) < 5:
        return ""
    return "/".join(parts[3:])


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
