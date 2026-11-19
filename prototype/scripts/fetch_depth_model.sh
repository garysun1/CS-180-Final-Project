#!/usr/bin/env bash
# Depth Anything V2 Small (ViT-S), ONNX export by fabio-sim (Apache-2.0). ~99 MB. Input (1,3,518,518).
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/models"
mkdir -p "$DIR"
URL="https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v2.0.0/depth_anything_v2_vits.onnx"
OUT="$DIR/depth_anything_v2_vits.onnx"
if [ ! -s "$OUT" ]; then
  curl -fL --retry 4 -o "$OUT.part" "$URL" && mv "$OUT.part" "$OUT"
fi
ls -lh "$OUT"
