"""Main module for commit message generation orchestration."""

import json
import sys
from pathlib import Path

from modules.ai_client import generate_commit_message
from modules.cli import find_issue_references, parse_arguments
from modules.config import load_api_config
from modules.git_operations import get_git_diff, get_last_commit_subject, is_git_repository
from modules.interactive_flow import run_interactive_commit_flow
from modules.message_processor import (
    append_issue_reference_to_subject,
    normalize_conventional_commit_message,
    remove_all_code_fences,
    strip_surrounding_code_fence,
)


def main() -> int:
    """
    Main entry point for commit message generation.

    Returns:
            Exit code (0 for success, 1 for failure)
    """
    base_dir = Path(__file__).resolve().parent

    try:
        options = parse_arguments(sys.argv[1:])
        if not is_git_repository():
            sys.stderr.write("Current directory is not a Git repository.\n")
            return 1

        config = load_api_config(base_dir)
        diff_text = get_git_diff(
            revision_spec=options.revision_spec,
            include_unstaged=options.include_unstaged_for_diff,
        )

        issue_reference = options.issue_reference or find_issue_references(
            get_last_commit_subject()
        )

        if not diff_text.strip():
            sys.stderr.write("No changes detected in git diff.\n")
            return 1

        message = build_commit_message(
            api_url=config["api_url"],
            model=config["model"],
            api_key=config["api_key"],
            diff_text=diff_text,
            issue_reference=issue_reference,
        )

        return run_interactive_commit_flow(message, options.commit_options)

    except FileNotFoundError:
        sys.stderr.write("Configuration file not found: .secret/api.json\n")
        return 1
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    return 0


def build_commit_message(
    *,
    api_url: str,
    model: str,
    api_key: str,
    diff_text: str,
    issue_reference: str,
) -> str:
    """Generate and normalize commit message from diff text."""
    message = generate_commit_message(
        api_url=api_url,
        model=model,
        api_key=api_key,
        diff_text=diff_text,
    )
    message = strip_surrounding_code_fence(message)
    message = remove_all_code_fences(message)
    message = normalize_conventional_commit_message(message)
    return append_issue_reference_to_subject(message, issue_reference)


if __name__ == "__main__":
    raise SystemExit(main())
