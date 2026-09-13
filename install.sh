#!/usr/bin/env bash
# hollyweeb installer for Linux / macOS.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== hollyweeb installer =="
python_bin="${PYTHON:-python3}"
command -v "$python_bin" >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
"$python_bin" -c 'import sys; assert sys.version_info >= (3, 9), "python 3.9+ required"'

if command -v pipx >/dev/null 2>&1; then
  echo "installing with pipx (isolated)…"
  pipx install --force "$here"
elif command -v uv >/dev/null 2>&1; then
  echo "installing with uv…"
  uv tool install --force "$here"
else
  echo "installing with pip --user…"
  "$python_bin" -m pip install --user --upgrade "$here"
fi

echo
echo "done. run:  hollyweeb"
echo "   or:     hollyweeb --list"
