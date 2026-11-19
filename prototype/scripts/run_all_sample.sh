#!/usr/bin/env bash
# Reproduce the check-in results on the stand-in clip (CPU only, ~3-5 min per run).
set -euo pipefail
cd "$(dirname "$0")/.."
V=data/sample/vtest.avi
python3 -m crossover.run --video $V --style century  --perturb --local-warp --out out/vtest_century  &
python3 -m crossover.run --video $V --style night    --perturb --local-warp --out out/vtest_night    &
wait
python3 -m crossover.run --video $V --style painting --perturb --local-warp --out out/vtest_painting &
python3 -m crossover.run --video $V --style ink      --perturb --local-warp --out out/vtest_ink      &
wait
python3 -m crossover.run --video $V --style century --sweep 0.3 --person-style matched --no-breakdown --out out/vtest_century_sweep
python3 scripts/contact_sheet.py out/vtest_century out/vtest_night out/vtest_painting out/vtest_ink -o out/contact_sheet.png
