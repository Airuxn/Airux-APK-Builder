#!/usr/bin/env bash
# Install a Linux .desktop launcher that points at this clone.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${XDG_DATA_HOME:-$HOME/.local/share}/applications/Airux-APK-Builder.desktop"
DESKTOP_COPY="${1:-}"

mkdir -p "$(dirname "$TARGET")"
cat > "$TARGET" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Airux Tech · APK Builder
Comment=Professional local Android APK builds (Expo EAS)
Exec=python3 "${ROOT}/apk_builder.py"
Path=${ROOT}
Icon=android
Terminal=false
Categories=Development;Utility;
StartupNotify=true
EOF

chmod +x "$TARGET"
echo "Installed: $TARGET"

if [[ -n "$DESKTOP_COPY" ]]; then
  cp "$TARGET" "$DESKTOP_COPY"
  chmod +x "$DESKTOP_COPY"
  echo "Copied: $DESKTOP_COPY"
fi
