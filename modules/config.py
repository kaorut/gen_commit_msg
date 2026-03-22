"""Configuration management module."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping


@dataclass(frozen=True)
class OpenAIConfig:
    """OpenAI-compatible API settings."""

    api_url: str
    model: str
    api_key: str


@dataclass(frozen=True)
class AppConfig:
    """Application runtime settings."""

    openai: OpenAIConfig
    github_resources: tuple["GitHubResource", ...]
    diff_unified_lines: int
    normalization_mode: Literal["strict", "loose"]


@dataclass(frozen=True)
class GitHubResource:
    """GitHub token bound to a repository selector."""

    name: str
    api_key: str

    def matches(self, owner: str, repo: str) -> bool:
        """Return True when this selector applies to the repository."""
        return self.priority(owner, repo) > 0

    def priority(self, owner: str, repo: str) -> int:
        """Return selector priority for the repository. Higher is more specific."""
        selector, owner_name, repo_name = _normalize_selector_inputs(
            self.name,
            owner,
            repo,
        )
        return _selector_priority(selector, owner_name, repo_name)


def _normalize_selector_inputs(
    selector: str,
    owner: str,
    repo: str,
) -> tuple[str, str, str]:
    """Normalize selector and repository names for matching."""
    return selector.strip().lower(), owner.strip().lower(), repo.strip().lower()


def _selector_priority(selector: str, owner_name: str, repo_name: str) -> int:
    """Return matching priority for one selector against owner/repo."""
    full_name = f"{owner_name}/{repo_name}"

    if selector == full_name:
        return 4
    if selector == f"{owner_name}/*":
        return 3
    if selector == owner_name or selector == repo_name:
        return 2
    if selector == "*":
        return 1
    return 0


def _normalize_github_entry(
    entry: Mapping[str, Any], *, config_path: Path
) -> GitHubResource:
    """Normalize one GitHub resource entry."""
    name = str(entry.get("name") or "").strip()
    api_key = str(entry.get("api_key") or "").strip()
    if not name:
        raise ValueError(f"Missing key in {config_path}: github[].name")
    if not api_key:
        raise ValueError(f"Missing key in {config_path}: github[].api_key")
    return GitHubResource(name=name, api_key=api_key)


def _require_non_empty_keys(
    values: Mapping[str, Any],
    *,
    required_keys: list[str],
    prefix: str,
    config_path: Path,
) -> None:
    """Validate required non-empty keys in one object."""
    missing_keys = [key for key in required_keys if key not in values or not values[key]]
    if missing_keys:
        missing = ", ".join(f"{prefix}.{key}" for key in missing_keys)
        raise ValueError(f"Missing keys in {config_path}: {missing}")


def _normalize_github_resources(
    github: Any, *, config_path: Path
) -> tuple[GitHubResource, ...]:
    """Normalize GitHub config into a list of resource/token mappings."""
    if github is None:
        return ()

    if isinstance(github, list):
        resources = [
            _normalize_github_entry(entry, config_path=config_path)
            for entry in github
            if isinstance(entry, dict)
        ]
        if len(resources) != len(github):
            raise ValueError(f"Invalid object in 'github' list in {config_path}")
        return tuple(resources)

    if isinstance(github, dict):
        api_key = str(github.get("api_key") or "").strip()
        return (GitHubResource(name="*", api_key=api_key),) if api_key else ()

    raise ValueError(f"Invalid object 'github' in {config_path}")


def load_api_config(base_dir: Path) -> AppConfig:
    """
    Load API configuration from .secret/api.json.

    Args:
            base_dir: Base directory where .secret folder is located

    Returns:
            Application configuration

    Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required keys are missing or empty
            json.JSONDecodeError: If config file is not valid JSON
    """
    config_path = base_dir / ".secret" / "api.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    normalized = _normalize_api_config(config, config_path=config_path)
    return normalized


def _read_diff_unified_lines(config: Mapping[str, Any], *, config_path: Path) -> int:
    """Read optional diff unified lines setting."""
    value = config.get("diff_unified_lines", 100)
    try:
        lines = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid value in {config_path}: diff_unified_lines must be a positive integer"
        ) from exc

    if lines <= 0:
        raise ValueError(
            f"Invalid value in {config_path}: diff_unified_lines must be a positive integer"
        )
    return lines


def _read_normalization_mode(
    config: Mapping[str, Any], *, config_path: Path
) -> Literal["strict", "loose"]:
    """Read optional commit message normalization mode."""
    mode = str(config.get("normalization_mode", "strict")).strip().lower()
    if mode in ("strict", "loose"):
        return mode

    raise ValueError(
        f"Invalid value in {config_path}: normalization_mode must be 'strict' or 'loose'"
    )


def _normalize_api_config(config: Mapping[str, Any], *, config_path: Path) -> AppConfig:
    """Normalize config into runtime keys used by the application."""
    if "openai" in config or "github" in config:
        return _normalize_nested_api_config(config, config_path=config_path)

    return _normalize_legacy_flat_config(config, config_path=config_path)


def _normalize_nested_api_config(
    config: Mapping[str, Any], *, config_path: Path
) -> AppConfig:
    """Normalize nested config format with openai/github objects."""
    openai = config.get("openai")
    if not isinstance(openai, dict):
        raise ValueError(f"Missing or invalid object 'openai' in {config_path}")

    _require_non_empty_keys(
        openai,
        required_keys=["api_url", "model", "api_key"],
        prefix="openai",
        config_path=config_path,
    )

    return AppConfig(
        openai=OpenAIConfig(
            api_url=str(openai["api_url"]),
            model=str(openai["model"]),
            api_key=str(openai["api_key"]),
        ),
        github_resources=_normalize_github_resources(
            config.get("github", {}),
            config_path=config_path,
        ),
        diff_unified_lines=_read_diff_unified_lines(config, config_path=config_path),
        normalization_mode=_read_normalization_mode(config, config_path=config_path),
    )


def _normalize_legacy_flat_config(
    config: Mapping[str, Any], *, config_path: Path
) -> AppConfig:
    """Normalize legacy flat config format for backward compatibility."""
    _require_non_empty_keys(
        config,
        required_keys=["api_url", "model", "api_key"],
        prefix="legacy",
        config_path=config_path,
    )

    return AppConfig(
        openai=OpenAIConfig(
            api_url=str(config["api_url"]),
            model=str(config["model"]),
            api_key=str(config["api_key"]),
        ),
        github_resources=(
            (GitHubResource(name="*", api_key=str(config.get("github_token") or "").strip()),)
            if str(config.get("github_token") or "").strip()
            else ()
        ),
        diff_unified_lines=_read_diff_unified_lines(config, config_path=config_path),
        normalization_mode=_read_normalization_mode(config, config_path=config_path),
    )
