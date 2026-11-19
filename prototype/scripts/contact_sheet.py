"""Grid of the showcase composite frame across styles: python scripts/contact_sheet.py out/vtest_* -o out/contact_sheet.png"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crossover.figures import label  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--which", default="matched", choices=["matched", "filmed"])
    ap.add_argument("--cols", type=int, default=2)
    a = ap.parse_args()
    tiles = []
    for r in a.runs:
        p = os.path.join(r, f"composite_frame_{a.which}.png")
        rep = os.path.join(r, "report.json")
        if not (os.path.exists(p) and os.path.exists(rep)):
            continue
        meta = json.load(open(rep))
        key = meta["seam_final_key"]
        sd = meta["seam_drift_px"][key]
        txt = f"{meta['style']}  |  seam jump {sd['median']:.2f}px" if sd.get("median") is not None else meta["style"]
        tr = (meta.get("true_residual_px") or {}).get(key)
        if tr and tr.get("median") is not None:
            txt += f" (true {tr['median']:.2f}px)"
        if meta.get("split") == "depth":
            txt += "  |  depth: " + ("near" if (meta.get("depth") or {}).get("near_restyled") else "far") + " restyled"
        tiles.append(label(cv2.imread(p), txt))
    if not tiles:
        sys.exit("no runs with composite frames found")
    h, w = tiles[0].shape[:2]
    tiles = [cv2.resize(t, (w, h)) for t in tiles]
    while len(tiles) % a.cols:
        tiles.append(np.full_like(tiles[0], 255))
    rows = [np.hstack(tiles[i:i + a.cols]) for i in range(0, len(tiles), a.cols)]
    cv2.imwrite(a.out, np.vstack(rows))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
