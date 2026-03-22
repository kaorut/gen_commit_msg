"""Command-line interface and argument parsing module."""

import argparse
import re
from typing import Sequence


ISSUE_REFERENCE_PATTERN = re.compile(r"(?:[A-Za-z0-9_.-]+)?#\d+")


def parse_arguments(args: Sequence[str]) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
            args: Command-line arguments (typically sys.argv[1:])

    Returns:
            Parsed arguments namespace

    Raises:
            ValueError: If issue reference format is invalid
    """
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
    # argparse should keep handling built-in help behavior.
    if any(token in ("-h", "--help") for token in args):
        parser.parse_args(args)

    parsed_args = argparse.Namespace()
    parsed_args.issue_reference = ""
    parsed_args.commit_options = []

    for token in args:
        if token.startswith("-"):
            parsed_args.commit_options.append(token)
            continue

        if not parsed_args.issue_reference and ISSUE_REFERENCE_PATTERN.fullmatch(token):
            parsed_args.issue_reference = validate_issue_reference(token)
            continue

        raise ValueError(f"Non-option arguments are not supported: {token}")

    parsed_args.include_unstaged_for_diff = has_all_option(parsed_args.commit_options)
    return parsed_args


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
