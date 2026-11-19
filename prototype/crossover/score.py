"""Rank candidate restyled plates (different editors / prompts / seeds) by how well they keep geometry.

    python -m crossover.score --clean out/x/clean_bg.png --restyled restyled/*.png [--line 0.5,0,0.5,1]

For each candidate: align it to the clean plate, then report the seam edge jump before/after
alignment, SIFT inliers and ECC correlation. Lower 'after' = buildings preserved better. This is
how we pick "whichever editor best preserves the buildings" with a number instead of by eye.
"""
from __future__ import annotations

import argparse
import json

import cv2

from .align import align, corner_shift
from .line import Line
from .metrics import seam_drift


def score(clean_path: str, paths: list[str], line_spec: str = "0.5,0,0.5,1", local_warp: bool = False) -> list[dict]:
    clean = cv2.imread(clean_path)
    if clean is None:
        raise FileNotFoundError(clean_path)
    h, w = clean.shape[:2]
    line = Line.from_spec(line_spec, w, h)
    rows = []
    for p in paths:
        R = cv2.imread(p)
        if R is None:
            print(f"skip unreadable {p}")
            continue
        if R.shape[:2] != (h, w):
            R = cv2.resize(R, (w, h), interpolation=cv2.INTER_AREA)
        before = seam_drift(clean, R, line)
        res = align(R, clean, "auto", local_warp=local_warp, line=line)
        after = seam_drift(clean, res.apply(R), line)
        rows.append({"file": p, "method": res.method, "sift_inliers": res.n_inliers,
                     "ecc_cc": None if res.ecc_cc is None else round(res.ecc_cc, 3),
                     "global_shift_px": round(corner_shift(res.H, w, h), 2),
                     "seam_before_med": before["median"], "seam_after_med": after["median"],
                     "seam_after_p90": after["p90"], "reliable": after["reliable"]})
    rows.sort(key=lambda r: (not r["reliable"], r["seam_after_med"] if r["seam_after_med"] is not None else 1e9))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--clean", required=True)
    ap.add_argument("--restyled", nargs="+", required=True)
    ap.add_argument("--line", default="0.5,0,0.5,1")
    ap.add_argument("--local-warp", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rows = score(a.clean, a.restyled, a.line, a.local_warp)
    cols = ["file", "method", "sift_inliers", "ecc_cc", "global_shift_px", "seam_before_med", "seam_after_med",
            "seam_after_p90", "reliable"]
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(rows, fh, indent=2)
    return rows


if __name__ == "__main__":
    main()
