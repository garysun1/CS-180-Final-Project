"""Find the moments people cross a vertical line in a fixed-camera video.

Every frame's people are cut out against the clean plate (BgDiffMasker), split into blobs, and
tracked by greedy nearest-centroid matching, so each person keeps a track id. A crossing is a track
whose centroid x moves from one side of the line to the other between two frames.

    python scripts/find_moments.py data/sample/vtest.avi out/vtest_century/clean_bg.png --line-x 384
    python scripts/find_moments.py data/sample/vtest.avi out/vtest_century/clean_bg.png --line-x 384 \\
        --t0 58 --t1 64 --follow 271,510        # also print one walker's path, frame by frame
    python scripts/find_moments.py data/clips/crowd04.mp4 out/clips/crowd04/clean_bg.png --summary

Times are source seconds (frame / fps). The bbox is (x0, y0, x1, y1) in source pixels, x1/y1
exclusive; area is the blob's pixel count.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crossover.effects import blobs  # noqa: E402
from crossover.masks import BgDiffMasker  # noqa: E402
from crossover.video_io import iter_frames, probe  # noqa: E402


def people(video: str, clean: str, t0: float | None = None, t1: float | None = None):
    """Yield (frame index, fps, [person dicts]) for the frames in [t0, t1] (seconds)."""
    info = probe(video)
    bg = cv2.imread(clean)
    if bg is None:
        raise FileNotFoundError(clean)
    h, w = bg.shape[:2]
    fps = info.fps
    f0 = 0 if t0 is None else max(0, int(round(t0 * fps)))
    f1 = info.n_frames - 1 if t1 is None else min(info.n_frames - 1, int(round(t1 * fps)))
    warm = max(0, f0 - 1)                    # one earlier frame: the masker's temporal support
    frames = (f for k, f in enumerate(iter_frames(video, 1.0, f1 + 2)) if k >= warm)
    for j, _, a in BgDiffMasker(bg).iter_alphas(frames):
        i = warm + j
        if i < f0:
            continue
        if i > f1:
            break
        out = []
        for m, fx, fy, bh, cx, cy in blobs(a, 3e-4 * h * w):
            ys, xs = np.nonzero(m)
            out.append({"cx": float(cx), "cy": float(cy), "fx": float(fx), "fy": float(fy), "area": int(m.sum()),
                        "bbox": (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)})
        yield i, fps, out


class Tracker:
    """Greedy nearest-centroid matching with ids; a track survives `max_miss` frames unseen."""

    def __init__(self, gate: float, max_miss: int = 2):
        self.gate, self.max_miss = gate, max_miss
        self.tracks: dict[int, dict] = {}
        self.next_id = 0

    def update(self, items: list[dict]) -> list[tuple[int, dict | None]]:
        """Give every item a track id; returns (id, the track's previous state or None) per item."""
        pairs = sorted((float(np.hypot(b["cx"] - t["cx"], b["cy"] - t["cy"])), tid, k)
                       for tid, t in self.tracks.items() for k, b in enumerate(items))
        used_t, ids = set(), [None] * len(items)
        for d, tid, k in pairs:
            if d > self.gate:
                break
            if tid in used_t or ids[k] is not None:
                continue
            used_t.add(tid)
            ids[k] = tid
        out, new = [], {}
        for tid, t in self.tracks.items():               # unmatched tracks age, then drop
            if tid not in used_t and t["miss"] < self.max_miss:
                new[tid] = dict(t, miss=t["miss"] + 1)
        for k, b in enumerate(items):
            if ids[k] is None:
                ids[k] = self.next_id
                self.next_id += 1
            out.append((ids[k], self.tracks.get(ids[k])))
            new[ids[k]] = {"cx": b["cx"], "cy": b["cy"], "miss": 0}
        self.tracks = new
        return out


def crossings(video, clean, line_x, t0=None, t1=None, gate=None, follow=None):
    """(list of crossing dicts, list of per-frame dicts of the followed walker)."""
    found, path = [], []
    tracker, fid = None, None
    for i, fps, items in people(video, clean, t0, t1):
        if tracker is None:
            w = cv2.imread(clean).shape[1]
            tracker = Tracker(gate if gate is not None else 40.0 * w / 768.0)
        res = tracker.update(items)
        for (tid, prev), b in zip(res, items):
            if prev is not None and (prev["cx"] < line_x) != (b["cx"] < line_x):
                found.append({"t": round(i / fps, 2), "frame": i, "dir": "L->R" if prev["cx"] < line_x else "R->L",
                              "track": tid, "area": b["area"], "bbox": b["bbox"],
                              "centroid": (round(b["cx"], 1), round(b["cy"], 1))})
        if follow is not None and items:                 # one walker: the track nearest `follow` at the start
            ids = [tid for tid, _ in res]
            if fid is None:
                fid = ids[int(np.argmin([np.hypot(b["cx"] - follow[0], b["cy"] - follow[1]) for b in items]))]
            if fid in ids:
                b = items[ids.index(fid)]
                path.append({"t": round(i / fps, 2), "frame": i, "track": fid, "area": b["area"], "bbox": b["bbox"],
                             "centroid": (round(b["cx"], 1), round(b["cy"], 1)),
                             "foot": (round(b["fx"], 1), round(b["fy"], 1))})
    return found, path


def summary(video, bg_path, line_x):
    """The original survey: the biggest crossings and the longest-lived large tracks."""
    per = []
    for _, _, items in people(video, bg_path):
        per.append([(b["fx"], b["fy"], b["bbox"][3] - b["bbox"][1], b["cx"], b["cy"], b["area"]) for b in items])
    cross = []
    for i in range(1, len(per)):
        for (fx, fy, bh, cx, cy, ar) in per[i]:
            prev = [b for b in per[i - 1] if abs(b[3] - cx) < 30 and abs(b[4] - cy) < 30]
            if prev and (prev[0][3] - line_x) * (cx - line_x) < 0:
                cross.append((i, round(cx), round(cy), round(bh), ar))
    cross.sort(key=lambda c: -c[4])
    best = []
    for s in range(0, len(per) - 60, 10):
        for start in sorted(per[s], key=lambda b: -b[5])[:3]:
            cx, cy, alive, areas = start[3], start[4], 0, []
            for i in range(s, len(per)):
                cand = [b for b in per[i] if np.hypot(b[3] - cx, b[4] - cy) < 40]
                if not cand:
                    break
                b = min(cand, key=lambda b: np.hypot(b[3] - cx, b[4] - cy))
                cx, cy = b[3], b[4]
                areas.append(b[5])
                alive += 1
            if alive >= 60:
                best.append((s, alive, int(np.median(areas)), round(start[3]), round(start[4])))
    best.sort(key=lambda t: -(min(t[1], 140) * t[2]))
    return {"frames": len(per), "crossings_biggest": cross[:8], "tracks_best": best[:8]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="List the moments people cross a vertical line (fixed camera).")
    ap.add_argument("video")
    ap.add_argument("clean", help="clean plate (the empty scene) of the video")
    ap.add_argument("--line-x", type=float, default=None, help="line position in source px (default: the centre)")
    ap.add_argument("--t0", type=float, default=None, help="window start, seconds")
    ap.add_argument("--t1", type=float, default=None, help="window end, seconds")
    ap.add_argument("--gate", type=float, default=None, help="max centroid step for a track, px (default 40 @768w)")
    ap.add_argument("--follow", default=None, help="x,y: also print the path of the walker nearest this point "
                                                   "at the window start")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    ap.add_argument("--summary", action="store_true", help="the original survey (biggest crossings, long tracks)")
    a = ap.parse_args(argv)
    info = probe(a.video)
    line_x = a.line_x if a.line_x is not None else info.src_width / 2
    if a.summary:
        print(json.dumps(summary(a.video, a.clean, line_x)))
        return
    follow = tuple(float(v) for v in a.follow.split(",")) if a.follow else None
    found, path = crossings(a.video, a.clean, line_x, a.t0, a.t1, a.gate, follow)
    if a.json:
        print(json.dumps({"video": a.video, "fps": info.fps, "line_x": line_x, "crossings": found, "follow": path}))
        return
    lo = a.t0 if a.t0 is not None else 0.0
    hi = a.t1 if a.t1 is not None else info.n_frames / info.fps
    print(f"# {a.video}: {info.src_width}x{info.src_height} @ {info.fps:.2f} fps, {lo:.2f}-{hi:.2f} s, line x={line_x:g}")
    print(f"{'time':>7} {'frame':>6} {'dir':>5} {'track':>6} {'area':>6}  bbox (x0,y0,x1,y1)     centroid")
    for c in found:
        print(f"{c['t']:7.2f} {c['frame']:6d} {c['dir']:>5} {c['track']:6d} {c['area']:6d}  "
              f"{str(c['bbox']):22s} {c['centroid']}")
    if follow is not None:
        print(f"\n# walker nearest {follow} at {lo:.2f} s")
        print(f"{'time':>7} {'frame':>6} {'track':>6} {'area':>6}  bbox (x0,y0,x1,y1)     centroid        foot")
        for p in path:
            print(f"{p['t']:7.2f} {p['frame']:6d} {p['track']:6d} {p['area']:6d}  {str(p['bbox']):22s} "
                  f"{str(p['centroid']):15s} {p['foot']}")


if __name__ == "__main__":
    main()
