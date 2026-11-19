#!/usr/bin/env bash
# More demos: 5 new CPU styles (line split) + 3 depth-split demos, then contact sheets and a reel.
# Needs the depth model: bash scripts/fetch_depth_model.sh   (~10 min on 4 CPU cores)
set -euo pipefail
cd "$(dirname "$0")/.."
V=data/sample/vtest.avi
COMMON="--perturb --local-warp --person-style matched --no-breakdown"
for s in winter underwater thermal; do python3 -m crossover.run --video $V --style $s $COMMON --out out/vtest_$s & done; wait
for s in neon sketch; do python3 -m crossover.run --video $V --style $s $COMMON --out out/vtest_$s & done
python3 -m crossover.run --video $V --style century --split depth $COMMON --out out/vtest_depth_century &
wait
python3 -m crossover.run --video $V --style night --split depth --sweep 0.3 --depth-band 0.05 --seam glow \
    --person-style matched --no-breakdown --out out/vtest_depth_night_sweep &
python3 -m crossover.run --video $V --style thermal --split depth --depth-near --depth-split 0.45 \
    --person-style matched --out out/vtest_depth_thermal_near &
wait
python3 scripts/contact_sheet.py out/vtest_winter out/vtest_underwater out/vtest_thermal out/vtest_neon \
    out/vtest_sketch out/vtest_painting -o out/contact_sheet_styles.png
python3 scripts/contact_sheet.py out/vtest_depth_century out/vtest_depth_thermal_near -o out/contact_sheet_depth.png
python3 scripts/demo_reel.py out/vtest_winter out/vtest_underwater out/vtest_thermal out/vtest_neon out/vtest_sketch \
    out/vtest_century out/vtest_depth_century out/vtest_depth_night_sweep out/vtest_depth_thermal_near \
    -o out/demo_reel.mp4 --start 48 --dur 5
