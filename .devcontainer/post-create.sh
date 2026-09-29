#!/usr/bin/env bash
# Codespaces / dev container setup for Core V1-MD.
set -euo pipefail

# Qt 6 runtime libraries: EGL/GL, fonts, D-Bus and the xcb platform plugin
# (needed to show the simulator window on the desktop-lite display).
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    libegl1 libgl1 libfontconfig1 libdbus-1-3 fonts-dejavu-core \
    libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1
sudo rm -rf /var/lib/apt/lists/*

cd "$(dirname "$0")/../core-v1-md"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt ruff

# Smoke test: render headless so a broken environment is obvious immediately.
python -m simulator --headless --frames 30 --screenshot /tmp/core-v1-md-smoke.png

cat <<'MSG'

Core V1-MD dev container ready.
  Tests:      cd core-v1-md && python -m pytest
  Simulator:  open the "Simulator desktop (noVNC)" port 6080 (password: vscode), then
              cd core-v1-md && python -m simulator
MSG
