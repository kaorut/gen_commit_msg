"""Main module for commit message generation orchestration."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

from modules.ai_client import generate_commit_message
from modules.cli import ParsedOptions, find_issue_references, parse_arguments
from modules.config import GitHubResource, OpenAIConfig, load_api_config
from modules.git_operations import (
    get_git_diff,
    get_last_commit_subject,
    get_origin_owner_repo,
    is_git_repository,
)
from modules.github_issue_client import build_issue_context
from modules.interactive_flow import run_interactive_commit_flow
from modules.message_processor import (
    append_issue_reference_to_subject,
    normalize_conventional_commit_message,
    remove_all_code_fences,
    strip_surrounding_code_fence,
)


ERROR_NOT_GIT_REPOSITORY = "Current directory is not a Git repository."
ERROR_NO_DIFF = "No changes detected in git diff."
WARNING_ISSUE_CONTEXT_UNAVAILABLE = (
    "Warning: GitHub issue context could not be loaded for the given issue references. "
    "Continuing without issue RAG context."
)


@dataclass(frozen=True)
class PreparedCommitMessage:
    """Prepared inputs required to generate one commit message."""

    openai_config: OpenAIConfig
    diff_text: str
    issue_reference: str
    issue_context: str
    normalization_mode: Literal["strict", "loose"]


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
            write_error(ERROR_NOT_GIT_REPOSITORY)
            return 1

        return run_commit_flow(base_dir, options)

    except FileNotFoundError:
        write_error("Configuration file not found: .secret/api.json")
        return 1
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        write_error(str(exc))
        return 1

    return 0


def write_error(message: str) -> None:
    """Write one error line to stderr."""
    sys.stderr.write(message.rstrip() + "\n")


def write_warning(message: str) -> None:
    """Write one warning line to stderr."""
    sys.stderr.write(message.rstrip() + "\n")


def run_commit_flow(base_dir: Path, options: ParsedOptions) -> int:
    """Build commit message and run interactive commit flow."""
    prepared = prepare_commit_message(base_dir, options)
    message = build_commit_message(
        openai_config=prepared.openai_config,
        diff_text=prepared.diff_text,
        issue_context=prepared.issue_context,
        issue_reference=prepared.issue_reference,
        normalization_mode=prepared.normalization_mode,
    )
    return run_interactive_commit_flow(message, options.commit_options)


def prepare_commit_message(
    base_dir: Path,
    options: ParsedOptions,
) -> PreparedCommitMessage:
    """Load all inputs needed for commit message generation."""
    config = load_api_config(base_dir)
    diff_text = get_git_diff(
        revision_spec=options.revision_spec,
        include_unstaged=options.include_unstaged_for_diff,
        unified_lines=config.diff_unified_lines,
    )
    if not diff_text.strip():
        raise RuntimeError(ERROR_NO_DIFF)

    resolved_issue_reference = resolve_issue_references(options.issue_reference)
    issue_context = build_issue_context_for_commit(
        resolved_issue_reference,
        github_resources=config.github_resources,
    )
    if resolved_issue_reference and not issue_context:
        write_warning(WARNING_ISSUE_CONTEXT_UNAVAILABLE)

    return PreparedCommitMessage(
        openai_config=config.openai,
        diff_text=diff_text,
        issue_reference=resolved_issue_reference,
        issue_context=issue_context,
        normalization_mode=config.normalization_mode,
    )


def resolve_issue_references(issue_reference: str) -> str:
    """Resolve explicit or inherited issue references for this commit flow."""
    if issue_reference:
        return issue_reference

    return find_issue_references(get_last_commit_subject())


def build_issue_context_for_commit(
    issue_reference: str,
    *,
    github_resources: Sequence[GitHubResource],
) -> str:
    """Build GitHub issue context for commit message generation."""
    if not issue_reference:
        return ""

    owner, repo = get_origin_owner_repo()
    return build_issue_context(
        issue_reference,
        default_owner=owner,
        default_repo=repo,
        github_resources=github_resources,
    )


def build_commit_message(
    *,
    openai_config: OpenAIConfig,
    diff_text: str,
    issue_context: str,
    issue_reference: str,
    normalization_mode: Literal["strict", "loose"],
) -> str:
    """Generate and normalize commit message from diff text."""
    message = generate_commit_message(
        openai_config=openai_config,
        diff_text=diff_text,
        issue_context=issue_context,
    )
    return normalize_generated_message(
        message,
        issue_reference=issue_reference,
        normalization_mode=normalization_mode,
    )


def normalize_generated_message(
    message: str,
    *,
    issue_reference: str,
    normalization_mode: Literal["strict", "loose"],
) -> str:
    """Normalize raw model output into the final commit message text."""
    normalized = strip_surrounding_code_fence(message)
    normalized = remove_all_code_fences(normalized)
    if normalization_mode == "strict":
        normalized = normalize_conventional_commit_message(normalized)
    return append_issue_reference_to_subject(normalized, issue_reference)


if __name__ == "__main__":
    raise SystemExit(main())
