"""Concatenate the same few seconds from several runs into one labelled reel.

    python scripts/demo_reel.py out/vtest_winter out/vtest_thermal ... -o out/demo_reel.mp4 --start 49 --dur 5
"""
import argparse
import json
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crossover.figures import label  # noqa: E402
from crossover.video_io import VideoWriter  # noqa: E402


def run_label(run: str) -> str:
    try:
        m = json.load(open(os.path.join(run, "report.json")))
    except FileNotFoundError:
        return os.path.basename(run)
    if m.get("split") == "depth":
        near = (m.get("depth") or {}).get("near_restyled")
        return f"{m['style']}  |  depth split: {'near' if near else 'far'} restyled"
    return f"{m['style']}  |  line split"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--video", default="final_matched.mp4", help="which video inside each run dir")
    ap.add_argument("--start", type=float, default=49.0, help="seconds")
    ap.add_argument("--dur", type=float, default=5.0, help="seconds per run")
    a = ap.parse_args()
    writer = None
    for r in a.runs:
        p = os.path.join(r, a.video)
        if not os.path.exists(p):
            print("skip (missing)", p)
            continue
        cap = cv2.VideoCapture(p)
        fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(a.start * fps))
        txt = run_label(r)
        n = 0
        while n < int(a.dur * fps):
            ok, f = cap.read()
            if not ok:
                break
            if writer is None:
                writer = VideoWriter(a.out, f.shape[1], f.shape[0], fps)
            writer.write(label(f, txt))
            n += 1
        cap.release()
        print(f"{p}: {n} frames")
    if writer is None:
        sys.exit("nothing written")
    writer.close()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
