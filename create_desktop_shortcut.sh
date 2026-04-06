#!/usr/bin/env bash
# create_desktop_shortcut.sh
# Creates a VoxChart .desktop launcher on Linux/Ubuntu.
# Works for both:
#   - Compiled binary  (dist/VoxChart/VoxChart)
#   - Dev/Python mode  (python app.py inside venv)
#
# Usage:
#   chmod +x create_desktop_shortcut.sh
#   ./create_desktop_shortcut.sh

set -euo pipefail

APP_NAME="VoxChart"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/Desktop"
APPS_DIR="$HOME/.local/share/applications"
SHORTCUT_FILE="$DESKTOP_DIR/voxchart.desktop"
APPS_FILE="$APPS_DIR/voxchart.desktop"

# ── Find icon ────────────────────────────────────────────────────
ICON_PATH=""
for candidate in \
    "$REPO_DIR/assets/voxchart.png" \
    "$REPO_DIR/assets/icon.png" \
    "$REPO_DIR/icon_preview.png" \
    "$REPO_DIR/assets/voxchart.ico"
do
    if [[ -f "$candidate" ]]; then
        ICON_PATH="$candidate"
        break
    fi
done

[[ -z "$ICON_PATH" ]] && ICON_PATH="utilities-terminal"
echo "[VoxChart] Icon: $ICON_PATH"

# ── Find Python / venv ──────────────────────────────────────────
VENV_PYTHON=""
for candidate in \
    "$REPO_DIR/venv/bin/python" \
    "$REPO_DIR/.venv/bin/python" \
    "$REPO_DIR/env/bin/python"
do
    if [[ -f "$candidate" ]]; then
        VENV_PYTHON="$candidate"
        break
    fi
done

if [[ -z "$VENV_PYTHON" ]]; then
    VENV_PYTHON="$(command -v python3 || command -v python)"
    echo "[VoxChart] No venv found, using system Python: $VENV_PYTHON"
else
    echo "[VoxChart] Using venv Python: $VENV_PYTHON"
fi

# ── Check for compiled binary first ─────────────────────────────
BINARY="$REPO_DIR/dist/VoxChart/VoxChart"
if [[ -f "$BINARY" ]]; then
    EXEC_LINE="$BINARY"
    echo "[VoxChart] Using compiled binary: $BINARY"
else
    EXEC_LINE="bash -c 'cd $REPO_DIR && $VENV_PYTHON app.py'"
    echo "[VoxChart] Using Python launcher: $VENV_PYTHON app.py"
fi

# ── Write .desktop file ──────────────────────────────────────────
mkdir -p "$DESKTOP_DIR" "$APPS_DIR"

cat > "$SHORTCUT_FILE" <<EOF
[Desktop Entry]
Version=1.2
Type=Application
Name=$APP_NAME
Comment=Offline AI Medical Dictation — powered by Whisper
Exec=$EXEC_LINE
Icon=$ICON_PATH
Path=$REPO_DIR
Terminal=false
StartupNotify=true
Categories=AudioVideo;Audio;Medical;
Keywords=dictation;medical;voice;AI;chart;
EOF

# Make it executable (required by some desktop environments)
chmod +x "$SHORTCUT_FILE"

# Also install to ~/.local/share/applications so it appears in app menu
cp "$SHORTCUT_FILE" "$APPS_FILE"

# Trust the shortcut (GNOME)
if command -v gio &>/dev/null; then
    gio set "$SHORTCUT_FILE" metadata::trusted true 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo ""
echo "✅ Desktop shortcut created!"
echo "   Desktop  : $SHORTCUT_FILE"
echo "   App Menu : $APPS_FILE"
echo ""
echo "Double-click 'VoxChart' on your desktop to launch."
