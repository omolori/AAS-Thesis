"""Centralized configuration loader.

Reads `config/settings.toml` once and exposes it as a typed-ish object.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.toml"


class Config:
    """Lightweight wrapper around the parsed TOML dict."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @property
    def raw(self) -> dict[str, Any]:
        return self._data


def load_config(path: Path | None = None) -> Config:
    target = path or CONFIG_PATH
    if not target.exists():
        raise FileNotFoundError(
            f"Config file not found at {target}. "
            "Copy and edit config/settings.toml."
        )
    with target.open("rb") as fh:
        return Config(tomllib.load(fh))


# Module-level singleton; import this from anywhere.
config = load_config()
