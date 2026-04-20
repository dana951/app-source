from __future__ import annotations

import os
import platform
import socket
from datetime import datetime, timezone
from typing import Any

from matplotlib.colors import is_color_like


def _css_background_ok(value: str) -> bool:
    color_value = (value or "").strip()
    if not color_value:
        return False
    return is_color_like(color_value)


def safe_css_background(value: str) -> str:
    """Restrict background color to a safe subset for inline CSS (injection-safe)."""
    color_value = (value or "").strip()
    if _css_background_ok(color_value):
        return color_value
    fallback = os.getenv("THEME_COLOR", "blue")
    if _css_background_ok(fallback):
        return fallback
    return "blue"

class PodInfo:

    def get_version(self) -> dict[str, str]:
        return {
            "version": os.getenv("APP_VERSION", "unknown"),
            "git_sha": os.getenv("GIT_SHA", "unknown"),
        }

    def get_info(self) -> dict[str, str]:
        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "environment": os.getenv("APP_ENV", "unknown"),
            "theme_color": os.getenv("THEME_COLOR", "blue"),
        }

    def echo_message(self, message: str) -> dict[str, Any]:
        return {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def get_dashboard_html(self) -> dict[str, str]:
        return {
            "hostname": socket.gethostname(),
            "version": os.getenv("APP_VERSION", "unknown"),
            "git_sha": os.getenv("GIT_SHA", "unknown"),
            "environment": os.getenv("APP_ENV", "dev"),
            "theme_color": os.getenv("THEME_COLOR", "blue"),
        }
