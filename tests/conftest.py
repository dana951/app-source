"""Shared pytest helpers."""

from __future__ import annotations


def mock_getenv(
    env: dict[str, str] | None = None, env_is_empty: bool = False
):
    def _getenv(
        key: str, default: str | None = None
    ) -> str | None:
        if env_is_empty:
            return default
        if env and key in env:
            return env[key]
        return default

    return _getenv
