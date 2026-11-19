#!/usr/bin/env bash
# Downloads OpenCV's public static-camera pedestrian clip (vtest.avi) as stand-in tripod footage.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/data/sample"
mkdir -p "$DIR"
URL="https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/vtest.avi"
if [ ! -s "$DIR/vtest.avi" ]; then
  curl -fL --retry 4 -o "$DIR/vtest.avi" "$URL"
fi
ls -lh "$DIR/vtest.avi"
