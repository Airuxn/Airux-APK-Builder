"""Pure helpers for Airux APK Builder (no GUI required)."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

_DEFAULT_BRAND_URL = "https://the-airux-ecosystem.vercel.app/"


def _default_project() -> Path:
    """Return the optional prefilled project path from the environment."""
    env = os.environ.get("AIRUX_APK_DEFAULT_PROJECT", "").strip()
    return Path(env).expanduser() if env else Path()


DEFAULT_PROJECT = _default_project()
BRAND_URL = os.environ.get("AIRUX_BRAND_URL", _DEFAULT_BRAND_URL).strip()

BUILD_START_MARKER = "▸ Build gestart "
BUILD_LOG_ERROR_PATTERN = re.compile(
    r"\berror:|build failed|failure:|build mislukt|\bexception\b",
    re.I,
)
WARNING_PATTERN = re.compile(
    r"\bwarning:|\[run_gradlew\] w:|npm warn\b|deprecated",
    re.I,
)
LOG_IGNORE_PATTERNS = (
    re.compile(r"checkkotlingradlepluginconfigurationerrors", re.I),
    re.compile(r"node-domexception", re.I),
)


def _line_ignored_for_scan(line: str) -> bool:
    """Return True for noisy Gradle/EAS lines that should not affect counts."""
    lowered = line.lower()
    return any(pattern.search(lowered) for pattern in LOG_IGNORE_PATTERNS)


def classify_log_line(line: str) -> str | None:
    """Classify a single EAS/local-build log line.

    Returns one of ``error``, ``warning``, ``success`` or ``None`` for plain
    informational output. Intentionally ignores common false positives such as
    the Kotlin Gradle plugin configuration check and ``node-domexception``.
    """
    lowered = line.lower()
    if _line_ignored_for_scan(line):
        return None
    if BUILD_LOG_ERROR_PATTERN.search(lowered):
        return "error"
    if WARNING_PATTERN.search(lowered):
        return "warning"
    if "build successful" in lowered or "✔ apk klaar" in lowered:
        return "success"
    return None


def read_app_slug(project: Path) -> str | None:
    """Read the Expo slug from ``app.json`` and sanitize it for filenames."""
    app_json = project / "app.json"
    if not app_json.is_file():
        return None
    try:
        data = json.loads(app_json.read_text(encoding="utf-8"))
        slug = data.get("expo", data).get("slug") if isinstance(data, dict) else None
        return slug.strip().lower().replace(" ", "-") if isinstance(slug, str) and slug.strip() else None
    except (OSError, ValueError, AttributeError):
        return None


def find_newest_apk(project: Path) -> Path | None:
    """Return the most recently modified APK under ``project``.

    Ignores common build-cache directories (``node_modules``, ``.gradle``,
    ``intermediates``) so the copied APK is the one the build just produced.
    """
    if not project.is_dir():
        return None
    ignore = {"node_modules", ".gradle", "intermediates"}
    files = [p for p in project.glob("**/*.apk") if p.is_file() and not any(x in ignore for x in p.parts)]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def check_node() -> tuple[bool, str]:
    """Verify that ``node`` and ``npx`` are available on PATH."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True, timeout=5)
        subprocess.run(["npx", "--version"], capture_output=True, check=True, timeout=8)
        return True, "ok"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False, "fail"


def check_android() -> tuple[bool, str]:
    """Verify that an Android SDK is present at ``ANDROID_HOME`` or ``~/Android/Sdk``."""
    home = os.environ.get("ANDROID_HOME") or str(Path.home() / "Android" / "Sdk")
    return Path(home).is_dir(), home


def check_eas() -> tuple[bool, str]:
    """Verify that the user is logged in to Expo EAS."""
    try:
        r = subprocess.run(["npx", "eas-cli", "whoami"], capture_output=True, text=True, timeout=25)
        return r.returncode == 0, r.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "fail"
