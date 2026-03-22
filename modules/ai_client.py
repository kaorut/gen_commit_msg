"""AI API client module for generating commit messages."""

from typing import Any

from openai import OpenAI


def normalize_provider_base_url(api_url: str) -> str:
	"""
	Extract base URL by removing API endpoint-specific paths.

	Args:
		api_url: Full or partial API URL

	Returns:
		Base URL without endpoint-specific paths
	"""
	url = api_url.rstrip("/")
	for suffix in ("/chat/completions", "/responses"):
		if url.endswith(suffix):
			return url[: -len(suffix)]

	return url


def extract_text_from_response(response: Any) -> str:
	"""
	Extract text content from API response object.

	Handles both direct output_text attribute and nested output array.

	Args:
		response: API response object

	Returns:
		Extracted text content
	"""
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


def generate_commit_message(
	api_url: str, model: str, api_key: str, diff_text: str
) -> str:
	"""
	Generate a commit message from git diff using AI API.

	Args:
		api_url: Base API URL
		model: Model name to use
		api_key: API key for authentication
		diff_text: Git diff content

	Returns:
		Generated commit message

	Raises:
		RuntimeError: If API request fails or message is empty
	"""
	base_url = normalize_provider_base_url(api_url)
	client = OpenAI(api_key=api_key, base_url=base_url)

	input_items = [
		{
			"role": "system",
			"content": (
				"You are an assistant that writes Git commit messages using Conventional Commits. "
				"The commit message must be written in English. "
				"The first line must strictly follow Conventional Commits format: "
				"type: subject. "
				"Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert. "
				"Do NOT include scope in parentheses on the first line. "
				"If scope is important, put it in the body as: Scope: <area>. "
				"Return ONLY the commit message as plain text. "
				"NEVER use markdown code fences (```) or any markdown formatting. "
				"NEVER wrap output in code blocks or add explanations. "
				"Do not include any code snippets, diagrams, or code examples. "
				"Use a concise subject line and optional body lines when helpful. "
				"Output must be plain text only, suitable for 'git commit -m'."
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
		responses_url = f"{base_url}/responses"
		raise RuntimeError(f"API request failed ({responses_url}): {exc}") from exc

	message = (content or "").strip()
	if not message:
		raise RuntimeError("Generated commit message is empty")

	return message
