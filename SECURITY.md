# Security Policy

## Reporting a Vulnerability

If you discover a security issue, please **do not** open a public GitHub issue.

Contact the maintainer privately via GitHub Security Advisories or direct message.

## Security Model

Airux APK Builder is a **local desktop tool**:

- No server, no hosted API, and no telemetry in this repository.
- Builds run as your user via `npx eas-cli` against a project path you choose.
- Expo / EAS authentication uses whatever is already configured on the machine (`eas whoami`).
- Android SDK and JDK paths are read from the environment or common local defaults.

## Guidance

1. Never commit Expo tokens, keystores, `google-services.json`, or `.env` files from app projects.
2. Only point the builder at projects you trust — a malicious `eas.json` / Gradle script can execute arbitrary build steps under your account.
3. Keep Node.js, the Android SDK, and JDK updated.
4. Treat generated APKs and build logs as potentially sensitive (they may contain app IDs, paths, or signing metadata).

## Scope

Issues in upstream Expo, EAS CLI, Gradle, or the Android SDK should be reported to those projects. This policy covers the Airux APK Builder UI and helper scripts in this repository.
