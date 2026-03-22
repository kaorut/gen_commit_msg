"""Commit message processing and formatting module."""

import re
from typing import Pattern


CONVENTIONAL_SUBJECT_PATTERN: Pattern[str] = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+"
)

SUBJECT_WITH_OPTIONAL_SCOPE_PATTERN: Pattern[str] = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(([^)]+)\))?(!)?:\s+(.+)$"
)


def strip_surrounding_code_fence(text: str) -> str:
    """
    Remove markdown code fence wrappers (```) from text.

    Args:
            text: Original text possibly wrapped in code fence

    Returns:
            Text without surrounding code fences
    """
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


def normalize_conventional_commit_message(message: str) -> str:
    """
    Ensure commit message follows Conventional Commits format.

    Args:
            message: Raw commit message

    Returns:
            Normalized commit message with valid type prefix

    Raises:
            ValueError: If message is empty after processing
    """
    # Step 1: Remove all code fences first
    text = remove_all_code_fences(message).strip()
    if not text:
        return ""

    lines = text.splitlines()

    # Step 2: Try to find the best subject line
    subject = None

    # First, check the first line
    candidate = sanitize_subject_line(lines[0].strip())
    if (
        len(candidate) >= 5
        and any(c.isalpha() for c in candidate)
        and not candidate.startswith("chore: ")
    ):
        subject = candidate

    # If first line is not good, look for better candidates
    if not subject or len(subject) < 15 or candidate.startswith("chore: "):
        # Also check original message for markdown bold lines
        # Pattern handles both **text:** and **text):** formats
        for original_line in message.splitlines():
            # Extract content from markdown bold: **content:** or **content):**
            bold_match = re.search(r"\*\*([^:]+?):\s*(.+)", original_line)
            if bold_match:
                # Found a markdown bold subject, combine the groups
                part1 = bold_match.group(1).strip()
                part2 = bold_match.group(2).strip()
                # Remove any leading ** from part2
                part2 = part2.lstrip("*").strip()
                candidate = part1 + ": " + part2
                candidate = sanitize_subject_line(candidate)
                if len(candidate) >= 5:
                    subject = candidate
                    break

        # Still no good subject? Try other lines from decomposed message
        if not subject:
            for candidate_line in lines[1:]:
                candidate = candidate_line.strip()
                candidate = re.sub(r"\*+", "", candidate)
                candidate = sanitize_subject_line(candidate)
                if len(candidate) >= 5 and any(c.isalpha() for c in candidate):
                    subject = candidate
                    break

    # If still no subject, use a fallback
    if not subject:
        subject = "chore: update changes"

    # Step 3: Validate and fix Conventional Commits format
    if not CONVENTIONAL_SUBJECT_PATTERN.fullmatch(subject):
        subject = build_fallback_conventional_subject(subject)

    # Step 3.5: Convert type(scope): subject -> type: subject and move scope to body
    subject, extracted_scope = remove_scope_from_subject(subject)

    # Step 4: Clean body lines (everything after the first line we're using)
    body_lines = [line.rstrip() for line in lines[1:]]
    if body_lines:
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()

    if extracted_scope and not has_scope_line(body_lines):
        body_lines = (
            [f"Scope: {extracted_scope}", "", *body_lines]
            if body_lines
            else [f"Scope: {extracted_scope}"]
        )

    if not body_lines:
        return subject

    return "\n".join([subject, "", *body_lines]).strip()


def remove_scope_from_subject(subject: str) -> tuple[str, str | None]:
    """
    Convert subject from type(scope): text to type: text and return extracted scope.

    Args:
            subject: Normalized subject line

    Returns:
            Tuple of (subject_without_scope, extracted_scope_or_none)
    """
    match = SUBJECT_WITH_OPTIONAL_SCOPE_PATTERN.fullmatch(subject.strip())
    if not match:
        return subject, None

    commit_type = match.group(1)
    scope = match.group(3)
    breaking_mark = match.group(4) or ""
    summary = match.group(5).strip()

    if scope:
        return f"{commit_type}{breaking_mark}: {summary}", scope.strip()

    return subject, None


def has_scope_line(body_lines: list[str]) -> bool:
    """Return True if body already contains a Scope: line."""
    for line in body_lines:
        if line.strip().lower().startswith("scope:"):
            return True
    return False


def build_fallback_conventional_subject(subject: str) -> str:
    """
    Create a fallback subject line with 'chore:' type prefix.

    Args:
            subject: Original subject text

    Returns:
            Subject with 'chore:' prefix
    """
    # First sanitize the subject
    text = sanitize_subject_line(subject).strip()
    if not text:
        return "chore: update changes"

    if text[0].isupper():
        text = text[0].lower() + text[1:]

    return f"chore: {text}"


def sanitize_subject_line(subject: str) -> str:
    """
    Remove problematic characters and code fences from subject line.

    Args:
            subject: Original subject text

    Returns:
            Sanitized subject line
    """
    text = subject.strip()
    # Remove code fence markers (``` with optional language)
    text = re.sub(r"```\w*", "", text).strip()
    # Remove any remaining backticks
    text = re.sub(r"`+", "", text).strip()
    return text


def remove_all_code_fences(text: str) -> str:
    """
    Remove ALL markdown code fences (```) from text.

    Uses a simple regex approach to remove all code fence markers
    and their language specifiers.

    Args:
            text: Text possibly containing code fences

    Returns:
            Text with all code fences removed
    """
    # Remove code fence start markers with language specifier (e.g., ```python)
    result = re.sub(r"```\w*", "", text)
    # Remove any remaining backticks
    result = re.sub(r"`+", "", result)
    # Clean up excessive whitespace
    result = re.sub(r"\n\s*\n+", "\n\n", result)
    return result.strip()


def append_issue_reference_to_subject(message: str, issue_reference: str) -> str:
    """
    Append issue reference to the subject line (first line) of commit message.

    Args:
            message: Commit message
            issue_reference: Issue reference like '#42' or 'otherproject#4242'

    Returns:
            Message with issue reference appended to subject line
    """
    if not issue_reference:
        return message

    lines = message.splitlines()
    if not lines:
        return message

    lines[0] = f"{lines[0].rstrip()} {issue_reference}".strip()
    return "\n".join(lines)
