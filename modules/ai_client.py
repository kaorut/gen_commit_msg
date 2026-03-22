"""AI API client module for generating commit messages."""

from pathlib import Path
from typing import Any

from openai import OpenAI


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


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
    system_prompt = read_prompt_template("system_prompt.txt")
    user_prompt = build_user_prompt(diff_text)

    input_items = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
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


def build_user_prompt(diff_text: str) -> str:
    """Build user prompt by injecting git diff into template."""
    template = read_prompt_template("user_prompt.txt")
    return template.replace("{{DIFF_TEXT}}", diff_text)


def read_prompt_template(file_name: str) -> str:
    """Read prompt template text from repository-level prompts directory."""
    path = PROMPTS_DIR / file_name
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Prompt file not found: {path}") from exc


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
