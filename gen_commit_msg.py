import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from openai import OpenAI


def main() -> int:
	base_dir = Path(__file__).resolve().parent

	try:
		options = parse_arguments(sys.argv[1:])
		config = load_api_config(base_dir)
		diff_text = get_git_diff()
		if not diff_text.strip():
			sys.stderr.write("No changes detected in git diff.\n")
			return 1

		message = generate_commit_message(
			api_url=config["api_url"],
			model=config["model"],
			api_key=config["api_key"],
			diff_text=diff_text,
		)
		message = append_issue_reference_to_subject(message, options.issue_reference)
	except FileNotFoundError:
		sys.stderr.write("Configuration file not found: .secret/api.json\n")
		return 1
	except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
		sys.stderr.write(f"{exc}\n")
		return 1

	sys.stdout.write(f"{message}\n")
	return 0


def load_api_config(base_dir: Path) -> dict:
	config_path = base_dir / ".secret" / "api.json"
	with config_path.open("r", encoding="utf-8") as file:
		config = json.load(file)

	required_keys = ["api_url", "model", "api_key"]
	missing_keys = [key for key in required_keys if key not in config or not config[key]]
	if missing_keys:
		missing = ", ".join(missing_keys)
		raise ValueError(f"Missing keys in {config_path}: {missing}")

	return config


def parse_arguments(args: list[str]) -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		prog="gen_commit_msg.py",
		description="Generate a commit message from git diff using AI.",
	)
	parser.add_argument(
		"issue_reference",
		nargs="?",
		default="",
		help="Optional issue reference like '#42' or 'otherproject#4242'.",
	)

	parsed_args = parser.parse_args(args)
	parsed_args.issue_reference = validate_issue_reference(parsed_args.issue_reference)
	return parsed_args


def validate_issue_reference(issue_reference: str) -> str:
	value = issue_reference.strip()
	if not value:
		return ""

	if not re.fullmatch(r"(?:[A-Za-z0-9_.-]+)?#\d+", value):
		raise ValueError("Issue reference must be like '#42' or 'otherproject#4242'")

	return value


def append_issue_reference_to_subject(message: str, issue_reference: str) -> str:
	if not issue_reference:
		return message

	lines = message.splitlines()
	if not lines:
		return message

	lines[0] = f"{lines[0].rstrip()} {issue_reference}".strip()
	return "\n".join(lines)


def get_git_diff() -> str:
	result = subprocess.run(
		["git", "diff"],
		capture_output=True,
		text=True,
		encoding="utf-8",
		errors="replace",
	)

	if result.returncode != 0:
		raise RuntimeError(result.stderr.strip() or "Failed to run git diff")

	return result.stdout


def generate_commit_message(api_url: str, model: str, api_key: str, diff_text: str) -> str:
	base_url = normalize_provider_base_url(api_url)
	responses_url = f"{base_url}/responses"
	client = OpenAI(api_key=api_key, base_url=base_url)

	input_items = [
		{
			"role": "system",
			"content": (
				"You are an assistant that writes Git commit messages using Conventional Commits. "
				"The commit message must be written in English. "
				"Return only the generated commit message as plain Markdown text. "
				"Do not add explanations, labels, or surrounding text. "
				"Do not wrap the full output in a code block. "
				"Use a concise subject line and optional body lines when helpful."
			),
		},
		{
			"role": "user",
			"content": (
				"Generate a Git commit message from this git diff. "
				"Follow Conventional Commits and keep it clear and concise.\n\n"
				f"{diff_text}"
			),
		},
	]

	try:
		response = client.responses.create(
			model=model,
			input=input_items,
			temperature=0.2,
			store=False,
		)
		content = extract_text_from_response(response)
	except Exception as exc:
		raise RuntimeError(f"API request failed ({responses_url}): {exc}") from exc

	message = (content or "").strip()
	message = strip_surrounding_code_fence(message)
	if not message:
		raise RuntimeError("Generated commit message is empty")

	return message


def normalize_provider_base_url(api_url: str) -> str:
	url = api_url.rstrip("/")
	for suffix in ("/chat/completions", "/responses"):
		if url.endswith(suffix):
			return url[: -len(suffix)]

	return url


def extract_text_from_response(response: object) -> str:
	output_text = getattr(response, "output_text", None)
	if isinstance(output_text, str) and output_text.strip():
		return output_text

	output_items = getattr(response, "output", None)
	if not isinstance(output_items, list):
		return ""

	parts = []
	for item in output_items:
		if getattr(item, "type", None) != "message":
			continue
		for content in getattr(item, "content", []):
			if getattr(content, "type", None) == "output_text":
				text = getattr(content, "text", "")
				if text:
					parts.append(text)

	return "\n".join(parts)


def strip_surrounding_code_fence(text: str) -> str:
	stripped = text.strip()
	if not stripped.startswith("```"):
		return stripped

	lines = stripped.splitlines()
	if len(lines) < 3:
		return stripped

	if not lines[0].startswith("```"):
		return stripped

	if lines[-1].strip() != "```":
		return stripped

	inner_text = "\n".join(lines[1:-1]).strip()
	return inner_text


if __name__ == "__main__":
	raise SystemExit(main())
