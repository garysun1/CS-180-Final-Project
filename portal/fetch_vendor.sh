#!/usr/bin/env bash
# Downloads the in-browser segmenter (MediaPipe Tasks Vision, Apache-2.0) and its models so the
# portal runs fully offline. ~31 MB, gitignored.
set -euo pipefail
cd "$(dirname "$0")"
VER=1.2.3
mkdir -p vendor models
if [ ! -s vendor/vision_bundle.mjs ]; then
  tmp=$(mktemp -d)
  curl -fsSL --retry 4 -o "$tmp/pkg.tgz" "https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-$VER.tgz"
  tar -xzf "$tmp/pkg.tgz" -C "$tmp"
  cp "$tmp/package/vision_bundle.mjs" vendor/
  cp -r "$tmp/package/wasm" vendor/
  cp "$tmp/package/LICENSE" vendor/LICENSE.mediapipe 2>/dev/null || true
  rm -rf "$tmp"
fi
B=https://storage.googleapis.com/mediapipe-models/image_segmenter
for m in selfie_segmenter selfie_segmenter_landscape; do
  [ -s models/$m.tflite ] || curl -fsSL --retry 4 -o models/$m.tflite "$B/$m/float16/latest/$m.tflite"
done
ls -lh vendor vendor/wasm models
