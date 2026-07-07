#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-run}"
APP_NAME="TokenScope"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/desktop"
APP_BUNDLE="$DESKTOP_DIR/dist/$APP_NAME.app"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/$APP_NAME"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS build/run is only supported on Darwin. Use desktop/build.bat on Windows." >&2
  exit 2
fi

pkill -x "$APP_NAME" >/dev/null 2>&1 || true

"$DESKTOP_DIR/build_macos.sh"

open_app() {
  /usr/bin/open -n "$APP_BUNDLE"
}

case "$MODE" in
  run)
    open_app
    ;;
  --debug|debug)
    lldb -- "$APP_BINARY"
    ;;
  --logs|logs)
    open_app
    /usr/bin/log stream --info --style compact --predicate "process == \"$APP_NAME\""
    ;;
  --telemetry|telemetry)
    open_app
    /usr/bin/log stream --info --style compact --predicate "subsystem == \"com.stealthy.tokenscope\""
    ;;
  --verify|verify)
    open_app
    sleep 2
    pgrep -x "$APP_NAME" >/dev/null
    ;;
  *)
    echo "usage: $0 [run|--debug|--logs|--telemetry|--verify]" >&2
    exit 2
    ;;
esac
