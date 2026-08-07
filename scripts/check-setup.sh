#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ok=0
fail=0

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "✓ $name"
    ok=$((ok + 1))
  else
    echo "✕ $name"
    fail=$((fail + 1))
  fi
}

echo "Airux APK Builder — setup check"
echo

check "python3" command -v python3
check "apk_builder.py compiles" python3 -m py_compile apk_builder.py
check "Start.sh present" test -f Start.sh
check "node" command -v node
check "npx" command -v npx

android_home="${ANDROID_HOME:-$HOME/Android/Sdk}"
if [[ -d "$android_home" ]]; then
  echo "✓ Android SDK ($android_home)"
  ok=$((ok + 1))
else
  echo "✕ Android SDK (set ANDROID_HOME or install to ~/Android/Sdk)"
  fail=$((fail + 1))
fi

if command -v npx >/dev/null 2>&1 && npx eas-cli whoami >/dev/null 2>&1; then
  echo "✓ Expo / EAS login"
  ok=$((ok + 1))
else
  echo "✕ Expo / EAS login (run: npx eas-cli login)"
  fail=$((fail + 1))
fi

echo
echo "Passed: $ok  Failed: $fail"
[[ "$fail" -eq 0 ]]
