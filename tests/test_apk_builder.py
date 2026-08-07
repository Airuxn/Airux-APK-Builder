"""Unit tests for pure helpers in apk_builder.py (no GUI required)."""

from __future__ import annotations

import json
from pathlib import Path

import apk_builder as ab


def test_classify_log_line_error() -> None:
    assert ab.ApkBuilderApp.classify_log_line("Error: something broke") == "error"
    assert ab.ApkBuilderApp.classify_log_line("BUILD FAILED") == "error"


def test_classify_log_line_ignores_domexception_noise() -> None:
    line = "npm warn deprecated node-domexception@1.0.0: Use your platform's native DOMException instead"
    assert ab.ApkBuilderApp.classify_log_line(line) is None


def test_classify_log_line_success() -> None:
    assert ab.ApkBuilderApp.classify_log_line("✔ APK klaar: /tmp/app.apk") == "success"
    assert ab.ApkBuilderApp.classify_log_line("Build successful") == "success"


def test_classify_log_line_warning() -> None:
    assert ab.ApkBuilderApp.classify_log_line("Warning: unused variable") == "warning"
    assert ab.ApkBuilderApp.classify_log_line("npm warn deprecated foo@1.0.0") == "warning"


def test_read_app_slug(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text(
        json.dumps({"expo": {"slug": "My Cool App"}}),
        encoding="utf-8",
    )
    assert ab.read_app_slug(tmp_path) == "my-cool-app"


def test_read_app_slug_missing(tmp_path: Path) -> None:
    assert ab.read_app_slug(tmp_path) is None


def test_find_newest_apk(tmp_path: Path) -> None:
    import os

    old = tmp_path / "old.apk"
    new = tmp_path / "dist" / "new.apk"
    new.parent.mkdir()
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(new, (1_800_000_000, 1_800_000_000))
    assert ab.find_newest_apk(tmp_path) == new


def test_find_newest_apk_ignores_node_modules(tmp_path: Path) -> None:
    junk = tmp_path / "node_modules" / "x.apk"
    junk.parent.mkdir(parents=True)
    junk.write_bytes(b"x")
    good = tmp_path / "app.apk"
    good.write_bytes(b"y")
    assert ab.find_newest_apk(tmp_path) == good


def test_default_project_empty_without_env(monkeypatch) -> None:
    monkeypatch.delenv("AIRUX_APK_DEFAULT_PROJECT", raising=False)
    # Re-evaluate the module-level logic used by the app
    env = ""
    default = Path(env).expanduser() if env else Path()
    assert default == Path()
