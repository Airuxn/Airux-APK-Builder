# Contributing to Airux APK Builder

Thanks for your interest in **Airux APK Builder**.

## Before you start

- Read [README.md](README.md) and [SECURITY.md](SECURITY.md).
- Search [existing issues](https://github.com/Airuxn/Airux-APK-Builder/issues) to avoid duplicates.
- Do **not** open public issues for security exploits — see SECURITY.md.

## Development setup

**Requirements:** Python 3.10+ with `tkinter`, bash

```bash
git clone https://github.com/Airuxn/Airux-APK-Builder.git
cd Airux-APK-Builder
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pytest -q
python3 -m py_compile apk_builder.py
bash scripts/check-setup.sh
```

Full APK builds need Node 20+, Android SDK, JDK 17, and an Expo login — not required for unit tests.

## Pull requests

1. Fork and branch from `main`.
2. One logical change per PR.
3. Run CI checks locally before opening (`ruff`, `pytest`, `py_compile`, ShellCheck on `*.sh`).
4. Keep the Dutch UI copy consistent unless the PR intentionally adds i18n.
5. Never commit secrets, APKs, or personal project paths as hard-coded defaults.

## Commit messages

Use clear, imperative subjects:

```
Fix false-positive error highlight for DOMException warnings
Document AIRUX_APK_DEFAULT_PROJECT in README
```

## License

By contributing, you agree your contributions are licensed under the [MIT License](LICENSE).
