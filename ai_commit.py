"""Main module for commit message generation orchestration."""

import json
import sys
from pathlib import Path

from modules.ai_client import generate_commit_message
from modules.cli import parse_arguments
from modules.config import load_api_config
from modules.git_operations import get_git_diff
from modules.interactive_flow import run_interactive_commit_flow
from modules.message_processor import (
	append_issue_reference_to_subject,
	strip_surrounding_code_fence,
	remove_all_code_fences,
	normalize_conventional_commit_message,
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
		config = load_api_config(base_dir)
		diff_text = get_git_diff(include_unstaged=options.include_unstaged_for_diff)
		
		if not diff_text.strip():
			sys.stderr.write("No changes detected in git diff.\n")
			return 1

		message = generate_commit_message(
			api_url=config["api_url"],
			model=config["model"],
			api_key=config["api_key"],
			diff_text=diff_text,
		)
		
		# Post-process the message (multiple passes for robustness)
		message = strip_surrounding_code_fence(message)  # Remove outer fences
		message = remove_all_code_fences(message)  # Remove all embedded fences
		message = normalize_conventional_commit_message(message)  # Final normalization
		message = append_issue_reference_to_subject(message, options.issue_reference)
		return run_interactive_commit_flow(message, options.commit_options)
		
	except FileNotFoundError:
		sys.stderr.write("Configuration file not found: .secret/api.json\n")
		return 1
	except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
		sys.stderr.write(f"{exc}\n")
		return 1

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
