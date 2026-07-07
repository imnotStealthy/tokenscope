#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON_BIN="${PYTHON:-python3}"

echo "[1/4] Creating build venv..."
if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate

echo "[2/4] Installing dependencies..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt pyinstaller

echo "[3/4] Preparing macOS icon..."
python - <<'PY'
from pathlib import Path
from icon import make_icon

iconset = Path("build/tokenscope.iconset")
iconset.mkdir(parents=True, exist_ok=True)
for size in (16, 32, 128, 256, 512):
    make_icon(size).save(iconset / f"icon_{size}x{size}.png")
    make_icon(size * 2).save(iconset / f"icon_{size}x{size}@2x.png")
PY
if command -v iconutil >/dev/null 2>&1; then
  iconutil -c icns build/tokenscope.iconset -o tokenscope.icns
fi

echo "[4/4] Building TokenScope.app..."
pyinstaller --noconfirm tokenscope-macos.spec

echo
echo "DONE -> dist/TokenScope.app"
