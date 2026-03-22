"""Configuration management module."""

import json
from pathlib import Path
from typing import Dict, Any


def load_api_config(base_dir: Path) -> Dict[str, Any]:
    """
    Load API configuration from .secret/api.json.

    Args:
            base_dir: Base directory where .secret folder is located

    Returns:
            Configuration dictionary with api_url, model, api_key

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

    required_keys = ["api_url", "model", "api_key"]
    missing_keys = [
        key for key in required_keys if key not in config or not config[key]
    ]

    if missing_keys:
        missing = ", ".join(missing_keys)
        raise ValueError(f"Missing keys in {config_path}: {missing}")

    return config
