#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-/usr/local/bin}"
TARGET_NAME="${TARGET_NAME:-bps}"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.8 or newer is required. Install python3 first." >&2
    exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || {
    echo "Python 3.8 or newer is required." >&2
    exit 1
}
if [[ -z "$TARGET_NAME" || "$TARGET_NAME" == */* || "$TARGET_NAME" == "." || "$TARGET_NAME" == ".." ]]; then
    echo "TARGET_NAME must be a command name without a directory path." >&2
    exit 1
fi
# Absolute targets also work when PREFIX was given as a relative directory.
install -d "$PREFIX"
PREFIX="$(cd -- "$PREFIX" && pwd)"
install -m 0755 "$SOURCE_DIR/bps" "$PREFIX/bird-peer-summary"
if [[ "$TARGET_NAME" != "bird-peer-summary" ]]; then
    ln -sfn "$PREFIX/bird-peer-summary" "$PREFIX/$TARGET_NAME"
fi

echo "Installed: $PREFIX/bird-peer-summary"
echo "Alias:     $PREFIX/$TARGET_NAME"
echo
echo "Try:"
echo "  $TARGET_NAME --compact"
echo "  $TARGET_NAME --watch 1 --compact"
