from __future__ import annotations

import os
import platform
import re
import socket
from datetime import datetime, timezone
from typing import Any


def _css_background_ok(value: str) -> bool:
    s = (value or "").strip()
    if re.fullmatch(r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})", s):
        return True
    if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9\-]{0,99}", s):
        return True
    if re.fullmatch(
        r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)",
        s,
    ):
        return True
    return False


def safe_css_background(value: str) -> str:
    """Restrict background color to a safe subset for inline CSS (injection-safe)."""
    s = (value or "").strip()
    if _css_background_ok(s):
        return s
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
