# Airux APK Builder

Desktop GUI to build **Android APKs locally** with **Expo EAS** (`eas build --local`). Wood-panel Airux Tech UI, live coloured build log, preflight checks for Node / Android SDK / Expo, and auto-named APK + log export.

**Status:** stable · **Stack:** Python 3.10+ · tkinter · EAS CLI · [MIT](LICENSE)

**Project age:** first public release on 2026-08-07 — this repo is a few days old and intentionally scoped to one job: turn an Expo app folder into a local Android APK with minimal friction.

[![CI](https://github.com/Airuxn/Airux-APK-Builder/actions/workflows/ci.yml/badge.svg)](https://github.com/Airuxn/Airux-APK-Builder/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Airuxn/Airux-APK-Builder/branch/main/graph/badge.svg)](https://codecov.io/gh/Airuxn/Airux-APK-Builder)
[![License](https://img.shields.io/github/license/Airuxn/Airux-APK-Builder)](LICENSE)

**Quality:** CI (Ruff, pip-audit, pytest, py_compile, ShellCheck) · CodeQL · Dependabot

---

## Quick start

```bash
git clone https://github.com/Airuxn/Airux-APK-Builder.git
cd Airux-APK-Builder
./Start.sh
# or: python3 apk_builder.py
```

Linux desktop shortcut (optional):

```bash
bash scripts/install-desktop.sh
# or also copy to ~/Desktop:
bash scripts/install-desktop.sh "$HOME/Desktop/Airux-APK-Builder.desktop"
```

---

## What you get

- **Local EAS preview builds** — no Expo cloud build minutes for day-to-day APKs
- **Preflight tiles** — Node.js, Android SDK, Expo/EAS login (click to re-check)
- **Live build log** — colour tags for errors, warnings, and success
- **Auto artefacts** after each run:
  - APK: `airux-tech-{slug}-{stamp}.apk`
  - Log: `airux-tech-{slug}-{stamp}.success.log` or `.failed.log`
- **Manual log export** and open-output-folder actions

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Linux desktop with a display (tkinter / X11 or Wayland) |
| Python | 3.10+ with `tkinter` |
| Node.js | 20+ (`node`, `npx`) |
| Android | SDK (`ANDROID_HOME` or `~/Android/Sdk`) |
| JDK | 17 (optional auto-detect: `~/.local/jdk-17`) |
| Expo | `npx eas-cli login` for your Expo account |
| Project | Expo app folder with `eas.json` (typically `apps/mobile`) |

Optional env:

| Variable | Description |
|----------|-------------|
| `AIRUX_APK_DEFAULT_PROJECT` | Prefill project path (must contain `eas.json`) |
| `AIRUX_BRAND_URL` | Override Ecosysteem button URL |
| `ANDROID_HOME` / `JAVA_HOME` | Standard Android / JDK paths |

---

## Usage

1. Start the app (`./Start.sh`).
2. Confirm the system tiles are green (or fix Node / SDK / `eas whoami`).
3. Choose your Expo **project folder** (directory that contains `eas.json`) and an **output folder**.
4. Click **Build APK** — the UI runs:

   ```bash
   npx eas-cli build -p android --profile preview --local
   ```

5. On success, the newest `.apk` under the project is copied into the output folder with an Airux Tech filename.

> Tip: share APKs via Drive (or similar), not WhatsApp — messaging apps often corrupt or block APKs.

---

## Repository layout

| Path | Description |
|------|-------------|
| [`apk_builder.py`](apk_builder.py) | Main tkinter application (GUI) |
| [`builder_core.py`](builder_core.py) | Pure, testable helper functions used by the GUI |
| [`Start.sh`](Start.sh) | Launcher |
| [`Airux-APK-Builder.desktop`](Airux-APK-Builder.desktop) | Linux desktop entry |
| [`tests/`](tests/) | Unit tests for pure helpers in `builder_core.py` and shell scripts |
| [`scripts/check-setup.sh`](scripts/check-setup.sh) | Local toolchain smoke check |
| [`scripts/install-desktop.sh`](scripts/install-desktop.sh) | Install Linux `.desktop` launcher |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI |

---

## Testing strategy

Coverage is measured by `pytest --cov=builder_core` and reported to Codecov.
The badge reflects the **pure, display-free helpers** in [`builder_core.py`](builder_core.py):

- `classify_log_line` / `_line_ignored_for_scan` — EAS/local-build log-line classification
- `read_app_slug` — Expo slug parsing and sanitization for auto-generated filenames
- `find_newest_apk` — APK discovery with cache-directory filtering
- `check_node`, `check_android`, `check_eas` — local toolchain smoke checks
- `scripts/install-desktop.sh` — Linux desktop-entry install

The GUI layer in `apk_builder.py` (`ApkBuilderApp`, `ShimmerHeader`, `PreflightTile`,
`AccentPanel`, `BuildButton`, `StatusChip`, and event handlers) is **not** included
in the coverage badge because it requires a display server (X11/Wayland). CI still
validates it with `python -m py_compile apk_builder.py`, and manual desktop QA is
run on a Linux workstation. Real GUI coverage would need Xvfb-based headless tkinter
fixtures, which we have not added yet.

---

## What makes this different

Most Expo APK tooling is cloud-first. Airux APK Builder keeps the build **local** so
you retain full control of your Android keystore, signing credentials, and network
path. It is intentionally a single-file desktop app rather than a SaaS wrapper or
full CI pipeline.

### Lessons learned

- **Separate the testable bits.** A polished tkinter UI is fast to build but hard to
  unit-test without a display. Putting pure helpers into `builder_core.py` makes the
  coverage badge honest and the GUI easy to ignore in Codecov.
- **Real coverage > high coverage.** The helper suite is small, but every tested
  function does a real job the app depends on.
- **CI is part of the product.** Ruff, `pip-audit`, compile checks, and pytest all
  run before a commit is pushed, so a reviewer can trust the green checkmark.

---

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pip-audit -r requirements-dev.txt
pytest -q
python3 -m py_compile apk_builder.py
bash scripts/check-setup.sh
```

---

## Security

This tool runs **local** builds with your machine’s Node, Android SDK, and Expo credentials. It does not ship secrets and does not open a network service. Treat Expo tokens and keystores like production credentials.

See [SECURITY.md](SECURITY.md) for the security model and reporting.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for local checks and PR expectations.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Expo](https://expo.dev/) / [EAS CLI](https://docs.expo.dev/eas/) — local Android builds
- [React Native](https://reactnative.dev/) — mobile runtime behind Expo apps

---

## 📞 Support

For support and questions:

- Create an issue on [GitHub](https://github.com/Airuxn/Airux-APK-Builder/issues)
- Security: see [SECURITY.md](SECURITY.md)

---

**⭐ If this project helped you, please give it a star!**
