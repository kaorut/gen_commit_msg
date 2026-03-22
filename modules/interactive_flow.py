"""Interactive commit flow module."""

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from modules.git_operations import commit_with_message, run_git_command


def run_interactive_commit_flow(message: str, commit_options: list[str]) -> int:
    """
    Run interactive flow and commit depending on user choice.

    Args:
            message: Generated commit message
            commit_options: git commit options to pass through

    Returns:
            Exit code (0 for success/cancel, 1 for error)

    Raises:
            RuntimeError: If commit or edit process fails
    """
    display_generated_message(message)
    action = prompt_user_action()

    if action == "cancel":
        print("Commit canceled.")
        return 0

    if action == "ok":
        commit_with_message(message, commit_options)
        print("Commit completed.")
        return 0

    edited_message = edit_message_with_editor(message)
    if not edited_message:
        print("Commit message is empty. Commit canceled.")
        return 0

    commit_with_message(edited_message, commit_options)
    print("Commit completed.")
    return 0


def edit_message_with_editor(message: str) -> str:
    """
    Open editor with a temporary file and return edited content.

    This function blocks until editor process exits.

    Args:
            message: Initial commit message

    Returns:
            Edited commit message (possibly empty)

    Raises:
            RuntimeError: If editor fails to launch or exits with error
    """
    editor_command = resolve_editor_command()
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            errors="replace",
            suffix=".commitmsg",
            delete=False,
        ) as temp_file:
            temp_file.write(message)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)

        editor_parts = shlex.split(editor_command, posix=(os.name != "nt"))
        result = subprocess.run([*editor_parts, str(temp_path)], check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Editor exited with non-zero status: {result.returncode}"
            )

        return temp_path.read_text(encoding="utf-8", errors="replace").strip()
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def resolve_editor_command() -> str:
    """
    Resolve editor command for commit message editing.

    Priority:
    1. GIT_EDITOR env var
    2. git config core.editor
    3. VISUAL env var
    4. EDITOR env var

    Returns:
            Editor command string

    Raises:
            RuntimeError: If editor cannot be resolved
    """
    git_editor = os.environ.get("GIT_EDITOR", "").strip()
    if git_editor:
        return git_editor

    try:
        core_editor = run_git_command(["config", "--get", "core.editor"]).strip()
        if core_editor:
            return core_editor
    except RuntimeError:
        pass

    visual = os.environ.get("VISUAL", "").strip()
    if visual:
        return visual

    editor = os.environ.get("EDITOR", "").strip()
    if editor:
        return editor

    raise RuntimeError(
        "Cannot resolve editor for commit message editing. "
        "Set GIT_EDITOR, core.editor, VISUAL, or EDITOR."
    )


def prompt_user_action() -> str:
    """Prompt user action and return normalized choice."""
    while True:
        choice = input("Choose action [OK/Edit/Cancel] (default: OK): ").strip().lower()
        if not choice or choice in ("ok", "o"):
            return "ok"
        if choice in ("edit", "e"):
            return "edit"
        if choice in ("cancel", "c"):
            return "cancel"
        print("Invalid choice. Enter OK, Edit, or Cancel.")


def display_generated_message(message: str) -> None:
    """Display generated commit message to console."""
    print()
    print(message)
