#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-/usr/local/bin}"
TARGET_NAME="${TARGET_NAME:-bps}"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

install -d "$PREFIX"
install -m 0755 "$SOURCE_DIR/bps" "$PREFIX/bird-peer-summary"
ln -sfn "$PREFIX/bird-peer-summary" "$PREFIX/$TARGET_NAME"

echo "Installed: $PREFIX/bird-peer-summary"
echo "Alias:     $PREFIX/$TARGET_NAME"
echo
echo "Try:"
echo "  $TARGET_NAME --compact"
echo "  $TARGET_NAME --watch 1 --compact"
