#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/novarii/tts-extension.git}"
TARGET_DIR="${TARGET_DIR:-tts-extension}"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
fi

if [ ! -d "$TARGET_DIR/.git" ]; then
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
uv python install 3.12
uv python pin 3.12
uv sync

cat <<'EOF'
Setup complete.

Next steps:
1) Edit configs/config.yaml with your preferred settings.
2) Grant macOS permissions when prompted (Microphone, Accessibility, Input Monitoring).
3) Run:
   uv run tts-extension listen -c configs/config.yaml

Tip: list input devices with:
   uv run tts-extension devices
EOF
