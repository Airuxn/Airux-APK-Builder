"""Unit tests for pure helpers in builder_core.py (no GUI required).

The tkinter GUI layer lives in ``apk_builder.py`` and is tested indirectly by
CI's ``python -m py_compile apk_builder.py`` plus manual desktop QA. The tests
below exercise the real helper functions that the coverage badge is based on:
log classification, app slug parsing, APK discovery, environment checks, and
shell helper scripts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import apk_builder as ab
import builder_core as bc

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- Log classification -----------------------------------------------------


def test_classify_log_line_error() -> None:
    assert bc.classify_log_line("Error: something broke") == "error"
    assert bc.classify_log_line("BUILD FAILED") == "error"
    assert bc.classify_log_line("Build mislukt — zie log.") == "error"
    assert bc.classify_log_line("Unhandled exception in worker") == "error"


def test_classify_log_line_ignores_domexception_noise() -> None:
    line = "npm warn deprecated node-domexception@1.0.0: Use your platform's native DOMException instead"
    assert bc.classify_log_line(line) is None


def test_classify_log_line_ignores_kotlin_configuration_noise() -> None:
    line = "Task :expo-modules-core:checkKotlinGradlePluginConfigurationErrors"
    assert bc.classify_log_line(line) is None
    assert bc._line_ignored_for_scan(line) is True


def test_classify_log_line_success() -> None:
    assert bc.classify_log_line("✔ APK klaar: /tmp/app.apk") == "success"
    assert bc.classify_log_line("Build successful") == "success"


def test_classify_log_line_warning() -> None:
    assert bc.classify_log_line("Warning: unused variable") == "warning"
    assert bc.classify_log_line("npm warn deprecated foo@1.0.0") == "warning"
    assert bc.classify_log_line("[RUN_GRADLEW] w: something") == "warning"


def test_classify_log_line_plain_info() -> None:
    assert bc.classify_log_line("Installing dependencies") is None
    assert bc.classify_log_line("Compiling 42 sources") is None


# --- App slug reading -------------------------------------------------------


def test_read_app_slug(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text(
        json.dumps({"expo": {"slug": "My Cool App"}}),
        encoding="utf-8",
    )
    assert bc.read_app_slug(tmp_path) == "my-cool-app"


def test_read_app_slug_top_level(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text(json.dumps({"slug": "My-App"}), encoding="utf-8")
    assert bc.read_app_slug(tmp_path) == "my-app"


def test_read_app_slug_missing(tmp_path: Path) -> None:
    assert bc.read_app_slug(tmp_path) is None


def test_read_app_slug_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text("{not-json", encoding="utf-8")
    assert bc.read_app_slug(tmp_path) is None


def test_read_app_slug_non_string_slug(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text(json.dumps({"expo": {"slug": 123}}), encoding="utf-8")
    assert bc.read_app_slug(tmp_path) is None


def test_read_app_slug_whitespace_only(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text(json.dumps({"expo": {"slug": "   "}}), encoding="utf-8")
    assert bc.read_app_slug(tmp_path) is None


def test_read_app_slug_not_dict(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text('"invalid"', encoding="utf-8")
    assert bc.read_app_slug(tmp_path) is None


# --- APK discovery ----------------------------------------------------------


def test_find_newest_apk(tmp_path: Path) -> None:
    old = tmp_path / "old.apk"
    new = tmp_path / "dist" / "new.apk"
    new.parent.mkdir()
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(new, (1_800_000_000, 1_800_000_000))
    assert bc.find_newest_apk(tmp_path) == new


def test_find_newest_apk_ignores_node_modules(tmp_path: Path) -> None:
    junk = tmp_path / "node_modules" / "x.apk"
    junk.parent.mkdir(parents=True)
    junk.write_bytes(b"x")
    good = tmp_path / "app.apk"
    good.write_bytes(b"y")
    assert bc.find_newest_apk(tmp_path) == good


def test_find_newest_apk_ignores_gradle_intermediates(tmp_path: Path) -> None:
    junk = tmp_path / ".gradle" / "intermediates" / "x.apk"
    junk.parent.mkdir(parents=True)
    junk.write_bytes(b"x")
    assert bc.find_newest_apk(tmp_path) is None


def test_find_newest_apk_nonexistent_path() -> None:
    assert bc.find_newest_apk(Path("/this/should/not/exist")) is None


# --- Environment checks -----------------------------------------------------


def test_check_node_success(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="v20.0.0", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert bc.check_node() == (True, "ok")
    assert [c[0] for c in calls] == ["node", "npx"]


def test_check_node_failure(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert bc.check_node() == (False, "fail")


def test_check_android_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANDROID_HOME", str(tmp_path))
    assert bc.check_android() == (True, str(tmp_path))


def test_check_android_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    fallback = tmp_path / "Android" / "Sdk"
    fallback.mkdir(parents=True)
    home = tmp_path

    def fake_home():
        return home

    monkeypatch.setattr(Path, "home", fake_home)
    assert bc.check_android() == (True, str(fallback))


def test_check_android_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANDROID_HOME", raising=False)

    def fake_home():
        return tmp_path

    monkeypatch.setattr(Path, "home", fake_home)
    expected = str(tmp_path / "Android" / "Sdk")
    assert bc.check_android() == (False, expected)


def test_check_eas_success(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        assert cmd[:3] == ["npx", "eas-cli", "whoami"]
        return subprocess.CompletedProcess(cmd, 0, stdout="alice", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert bc.check_eas() == (True, "alice")


def test_check_eas_failure(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert bc.check_eas() == (False, "fail")


def test_check_eas_nonzero_exit(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not logged in")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert bc.check_eas() == (False, "")


# --- Environment-derived defaults -------------------------------------------


def test_default_project_from_env(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["AIRUX_APK_DEFAULT_PROJECT"] = str(tmp_path)
    env.pop("AIRUX_BRAND_URL", None)
    code = "import builder_core as bc; print(bc._default_project())"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert Path(result.stdout.strip()).resolve() == tmp_path.resolve()


def test_default_project_empty_without_env() -> None:
    env = os.environ.copy()
    env.pop("AIRUX_APK_DEFAULT_PROJECT", None)
    env.pop("AIRUX_BRAND_URL", None)
    code = "import builder_core as bc; print(bc._default_project())"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "."


def test_brand_url_default() -> None:
    env = os.environ.copy()
    env.pop("AIRUX_BRAND_URL", None)
    env.pop("AIRUX_APK_DEFAULT_PROJECT", None)
    code = "import builder_core as bc; print(bc.BRAND_URL)"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == bc._DEFAULT_BRAND_URL


def test_brand_url_from_env() -> None:
    env = os.environ.copy()
    env["AIRUX_BRAND_URL"] = "https://example.com/"
    env.pop("AIRUX_APK_DEFAULT_PROJECT", None)
    code = "import builder_core as bc; print(bc.BRAND_URL)"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "https://example.com/"


# --- GUI module import / compile sanity --------------------------------------


def test_apk_builder_module_imports() -> None:
    """Importing the GUI module must not require a display (no instantiation)."""
    assert ab.ApkBuilderApp is not None
    assert ab.main is not None


# --- Shell helpers ----------------------------------------------------------


def test_install_desktop_script(tmp_path: Path) -> None:
    apps = tmp_path / "applications"
    apps.mkdir()
    desktop_copy = tmp_path / "Airux-APK-Builder.desktop"
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(tmp_path)
    subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "install-desktop.sh"), str(desktop_copy)],
        check=True,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    installed = apps / "Airux-APK-Builder.desktop"
    assert installed.is_file()
    assert desktop_copy.is_file()
    text = desktop_copy.read_text(encoding="utf-8")
    assert "Type=Application" in text
    assert "apk_builder.py" in text
    assert str(REPO_ROOT) in text
    assert "/path/to/" not in text


def test_start_sh_syntax() -> None:
    subprocess.run(["bash", "-n", str(REPO_ROOT / "Start.sh")], check=True)


def test_check_setup_sh_syntax() -> None:
    subprocess.run(["bash", "-n", str(REPO_ROOT / "scripts" / "check-setup.sh")], check=True)
