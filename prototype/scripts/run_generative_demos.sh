#!/usr/bin/env bash
# Generative restyles on CPU (SD 1.5 + ControlNet depth/canny + LCM-LoRA), then the full pipeline.
# Needs: pip install -r requirements-gen.txt (torch CPU), Hugging Face reachable, and the outputs of
# run_all_sample.sh + run_style_demos.sh (clean plate, depth map). ~35 min generation + ~15 min runs.
set -euo pipefail
cd "$(dirname "$0")/.."
V=data/sample/vtest.avi
CLEAN=out/vtest_century/clean_bg.png
DEPTH=out/vtest_depth_century/depth_disparity.npy
python3 -m crossover.generate --clean $CLEAN --depth $DEPTH \
    --styles winter --init filter --seeds 0 --strengths 0.6,0.75 --out out/gen --skip-existing
python3 -m crossover.generate --clean $CLEAN --depth $DEPTH \
    --styles night,1920s,underwater --init filter --seeds 0 --strengths 0.65,0.8 --out out/gen --skip-existing
python3 -m crossover.generate --clean $CLEAN --depth $DEPTH \
    --styles autumn,painting --init clean --seeds 0 --strengths 0.65,0.8 --out out/gen --skip-existing
python3 -m crossover.generate --clean $CLEAN --depth $DEPTH \
    --styles autumn --init filter --seeds 0 --strengths 0.65,0.8 --out out/gen --skip-existing
# rank every candidate by how well it re-aligns (lower seam jump after alignment = geometry kept)
python3 -m crossover.score --clean $CLEAN --restyled out/gen/*_s*_k*.png --json out/gen/scores.json
# the picks below were chosen from scores.json + a visual check (see README); edit to taste
while read -r style pick; do
  python3 -m crossover.run --video $V --restyled out/gen/$pick.png --style-name "$style (SD)" \
      --local-warp --person-style both --no-breakdown --out out/vtest_gen_$style
done < out/gen/picks.txt
