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

    issue_reference, commit_options = _parse_tokens(args)
    return ParsedOptions(
        issue_reference=issue_reference,
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
            "- If -a or --all is present, unstaged changes are included in the diff for AI generation.\n"
            "- Without -a/--all, only staged changes are used for AI generation."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "issue_reference",
        nargs="?",
        default="",
        help=(
            "Optional issue reference like '#42' or 'otherproject#4242'. "
            "Appended to the generated commit subject; not passed to git commit as an argument."
        ),
    )
    return parser


def _parse_tokens(args: Sequence[str]) -> tuple[str, list[str]]:
    """Parse tokens into issue reference and git commit options."""
    issue_reference = ""
    commit_options: list[str] = []

    for token in args:
        if token.startswith("-"):
            commit_options.append(token)
            continue

        if not issue_reference and ISSUE_REFERENCE_PATTERN.fullmatch(token):
            issue_reference = validate_issue_reference(token)
            continue

        raise ValueError(f"Non-option arguments are not supported: {token}")

    return issue_reference, commit_options


def has_all_option(commit_options: Sequence[str]) -> bool:
    """Return True if commit options include -a or --all."""
    for option in commit_options:
        if option == "--all":
            return True
        if option.startswith("-") and not option.startswith("--") and "a" in option[1:]:
            return True
    return False


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
