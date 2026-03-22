"""Command-line interface and argument parsing module."""

import argparse
import re
from dataclasses import dataclass
from typing import Sequence


ISSUE_REFERENCE_PATTERN = re.compile(r"(?:[A-Za-z0-9_.-]+)?#\d+")


@dataclass(frozen=True)
class ParsedOptions:
    """Parsed command-line options for commit generation flow."""

    issue_reference: str
    revision_spec: str
    commit_options: list[str]
    include_unstaged_for_diff: bool


def parse_arguments(args: Sequence[str]) -> ParsedOptions:
    """
    Parse command-line arguments.

    Args:
            args: Command-line arguments (typically sys.argv[1:])

    Returns:
            Parsed arguments namespace

    Raises:
            ValueError: If issue reference format is invalid
    """
    parser = _build_parser()

    # Keep argparse native help behavior.
    if any(token in ("-h", "--help") for token in args):
        parser.parse_args(args)

    issue_reference, revision_spec, commit_options = _parse_tokens(args)

    # If --amend is present and no revision_spec is provided,
    # treat it as if revision_spec was set to "HEAD^..HEAD"
    if not revision_spec and has_amend_option(commit_options):
        revision_spec = "HEAD^..HEAD"

    return ParsedOptions(
        issue_reference=issue_reference,
        revision_spec=revision_spec,
        commit_options=commit_options,
        include_unstaged_for_diff=has_all_option(commit_options),
    )


def _build_parser() -> argparse.ArgumentParser:
    """Create parser used only for help/usage output."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a commit message from git diff using AI and run git commit."
        ),
        epilog=(
            "Behavior:\n"
            "- Tokens starting with '-' or '--' are passed through to git commit.\n"
            "- Non-option arguments are not passed through to git commit.\n"
            "- If issue_reference is omitted, the latest commit subject is checked for issue references.\n"
            "- If -a or --all is present, unstaged changes are included in the diff for AI generation.\n"
            "- Without -a/--all, only staged changes are used for AI generation.\n"
            "- If --amend is present and no revision_spec is explicitly provided,\n"
            "  revision_spec is automatically set to 'HEAD^..HEAD' (the current commit)."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "issue_reference",
        nargs="?",
        default="",
        help=(
            "Optional issue reference like '#42' or 'otherproject#4242'. "
            "Appended to the generated commit subject; not passed to git commit as an argument. "
            "If omitted, issue references in the latest commit subject are reused when possible."
        ),
    )
    parser.add_argument(
        "revision_spec",
        nargs="?",
        default="",
        help=(
            "Optional git revision specification for diff range (follows git diff syntax):\n"
            "  REV1..REV2 - diff from REV1 to REV2 (2-dot form)\n"
            "  REV1...REV2- diff from merge-base to REV2 (3-dot form)\n"
            "  REV        - diff from REV to working tree (single commit)\n"
            "  (omitted)  - staged and unstaged changes (default)\n"
            "  When --amend is present without explicit revision_spec,\n"
            "  this is automatically set to 'HEAD^..HEAD' (current commit)"
        ),
    )
    return parser


def _parse_tokens(args: Sequence[str]) -> tuple[str, str, list[str]]:
    """Parse tokens into issue reference, revision spec, and git commit options."""
    issue_reference = ""
    revision_spec = ""
    commit_options: list[str] = []
    positional_count = 0

    for token in args:
        if token.startswith("-"):
            commit_options.append(token)
            continue

        # Non-option token: assign to issue_reference (1st) or revision_spec (2nd)
        if positional_count == 0:
            # First positional: check if it's a valid issue reference
            if ISSUE_REFERENCE_PATTERN.fullmatch(token):
                issue_reference = validate_issue_reference(token)
            else:
                # Not a valid issue ref, treat as revision_spec
                revision_spec = token
            positional_count += 1
            continue

        if positional_count == 1:
            # Second positional: assign to revision_spec (or issue_reference if first was revision)
            if revision_spec:
                # First arg was already treated as revision, second is not allowed
                raise ValueError(f"Non-option arguments are not supported: {token}")
            else:
                # First arg was issue_reference, second is revision_spec
                revision_spec = token
            positional_count += 1
            continue

        # Third or more positional arguments are never allowed
        raise ValueError(f"Non-option arguments are not supported: {token}")

    return issue_reference, revision_spec, commit_options


def has_all_option(commit_options: Sequence[str]) -> bool:
    """Return True if commit options include -a or --all."""
    for option in commit_options:
        if option == "--all":
            return True
        if option.startswith("-") and not option.startswith("--") and "a" in option[1:]:
            return True
    return False


def has_amend_option(commit_options: Sequence[str]) -> bool:
    """Return True if commit options include --amend."""
    return "--amend" in commit_options


def validate_issue_reference(issue_reference: str) -> str:
    """
    Validate issue reference format.

    Accepted formats:
    - '#42' (bare issue number)
    - 'project#123' (project-prefixed)

    Args:
            issue_reference: Issue reference string

    Returns:
            Validated issue reference (empty string if not provided)

    Raises:
            ValueError: If format is invalid
    """
    value = issue_reference.strip()
    if not value:
        return ""

    if not ISSUE_REFERENCE_PATTERN.fullmatch(value):
        raise ValueError("Issue reference must be like '#42' or 'otherproject#4242'")

    return value


def find_issue_references(text: str) -> str:
    """
    Extract all valid issue references from arbitrary text.

    Args:
            text: Source text to inspect

    Returns:
            Space-separated issue references, preserving first-seen order
    """
    matches = ISSUE_REFERENCE_PATTERN.findall(text)
    if not matches:
        return ""

    unique_references: list[str] = []
    for match in matches:
        issue_reference = validate_issue_reference(match)
        if issue_reference not in unique_references:
            unique_references.append(issue_reference)

    return " ".join(unique_references)
