#!/usr/bin/env bash
# Public fixed-camera crowd clips (MIT licence): huggingface.co/datasets/parsafaramarzi/Small-Crowd-and-Traffic-Video-Footages
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/data/clips/raw"
mkdir -p "$DIR"
BASE="https://huggingface.co/datasets/parsafaramarzi/Small-Crowd-and-Traffic-Video-Footages/resolve/main"
for f in crowd01 crowd02 crowd03 crowd04 crowd05 crowd06 cartraffic01 cartraffic02 cartraffic03 cartraffic04; do
  [ -s "$DIR/$f.mp4" ] || curl -fL --retry 4 -o "$DIR/$f.mp4" "$BASE/$f.mp4"
done
ls -lh "$DIR"
