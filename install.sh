#!/bin/sh
set -eu

ASSET_NAME="${ASSET_NAME:-pr-tui}"
REPO="${REPO:-${PR_TUI_UPDATE_REPO:-c-gerke/pr-tui}}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
TARGET="${TARGET:-$INSTALL_DIR/pr-tui}"

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "$INSTALL_DIR is not currently in PATH." >&2
    echo "Set INSTALL_DIR to a directory already in PATH, or update PATH first." >&2
    exit 2
    ;;
esac

tmp="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT INT TERM

downloaded="$tmp/$ASSET_NAME"
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh release download --repo "$REPO" --pattern "$ASSET_NAME" --output "$downloaded" --clobber
else
  curl -fsSL "https://github.com/$REPO/releases/latest/download/$ASSET_NAME" -o "$downloaded"
fi

chmod 0755 "$downloaded"
mkdir -p "$INSTALL_DIR"

if [ -w "$INSTALL_DIR" ]; then
  install -m 0755 "$downloaded" "$TARGET"
else
  sudo install -m 0755 "$downloaded" "$TARGET"
fi

echo "Installed pr-tui to $TARGET"
echo "For one-command updates later, run:"
echo "  PR_TUI_UPDATE_REPO=$REPO pr-tui --self-update"
