"""Per-person distance from the camera on a fixed-camera clip.

A person standing on the ground is as far away as the ground under their feet,
so no per-frame depth estimation is needed. Three estimates are compared:

  box    foot = bottom-centre of the tracker box, distance from the fitted ground plane
         (works even when the feet are below the frame, if the box extends there)
  map    same foot point, distance read from the background depth map (in-frame only)
  mask   foot = lowest pixel of the visible person mask, read from the depth map
         (what a segmenter like SAM gives; fails when feet are hidden or cut off)

Tracks here come from MOT ground truth and masks from background subtraction,
both stand-ins for SAM 3.

    python depth/people.py SEQ_DIR --plate plate.png --depth depth.npz --out OUTDIR
"""
import argparse
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


def fit_ground(z, focal, rows=0.2):
    """Plane n.X = c through the bottom rows of the depth map (camera coordinates)."""
    h, w = z.shape
    y0 = int(h * (1 - rows))
    xx, yy = np.meshgrid((np.arange(w) - (w - 1) / 2) / focal, (np.arange(y0, h) - (h - 1) / 2) / focal)
    zz = z[y0:]
    pts = np.stack([xx * zz, yy * zz, zz], -1).reshape(-1, 3)[::37]
    c = pts.mean(0)
    n = np.linalg.svd(pts - c, full_matrices=False)[2][-1]
    return n, float(n @ c)


def plane_distance(x, y, shape, focal, n, c):
    """Distance from the camera to where the ray through pixel (x, y) hits the ground."""
    h, w = shape
    ray = np.array([(x - (w - 1) / 2) / focal, (y - (h - 1) / 2) / focal, 1.0])
    t = c / (n @ ray)
    return float(t * np.linalg.norm(ray)) if t > 0 else np.nan


def person_mask(frame, plate, box, thr=28):
    """Background-subtraction mask inside a box (stand-in for a real segmenter)."""
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
    m = np.zeros((h, w), np.uint8)
    if x1 <= x0 or y1 <= y0:
        return m
    diff = cv2.absdiff(frame[y0:y1, x0:x1], plate[y0:y1, x0:x1]).max(-1)
    roi = (cv2.GaussianBlur(diff, (0, 0), 1.5) > thr).astype(np.uint8)
    roi = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    roi = cv2.morphologyEx(roi, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m[y0:y1, x0:x1] = roi
    return m


def load_tracks(seq):
    """MOT ground truth -> {frame: [(id, x0, y0, x1, y1)]}, pedestrians only."""
    tracks = defaultdict(list)
    for row in np.loadtxt(seq / "gt" / "gt.txt", delimiter=","):
        f, i, x, y, w, h, conf, cls = row[:8]
        if conf == 1 and cls == 1:
            tracks[int(f)].append((int(i), x, y, x + w, y + h))
    return tracks


def smooth(v, k=9):
    """Median then mean filter over time, ignoring NaNs."""
    v = np.asarray(v, float)
    out = np.empty_like(v)
    for i in range(len(v)):
        win = v[max(0, i - k // 2): i + k // 2 + 1]
        out[i] = np.nanmedian(win) if np.isfinite(win).any() else np.nan
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq")
    ap.add_argument("--plate", required=True)
    ap.add_argument("--depth", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    seq, out = Path(args.seq), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    plate = cv2.imread(args.plate)
    dd = np.load(args.depth)
    z, r, focal = dd["z"], dd["r"], float(dd["focal"])
    h, w = z.shape
    n, c = fit_ground(z, focal)
    tracks = load_tracks(seq)

    rows = []  # frame, id, d_box, d_map, d_mask, feet_cut_off, x_foot, y_foot
    for f in sorted(tracks):
        frame = cv2.imread(str(seq / "img1" / f"{f:06d}.jpg"))
        for i, x0, y0, x1, y1 in tracks[f]:
            fx = (x0 + x1) / 2
            cut = y1 >= h - 1 or fx < 0 or fx >= w
            d_box = plane_distance(fx, y1, (h, w), focal, n, c)
            d_map = np.nan if cut else float(r[int(y1), int(fx)])
            m = person_mask(frame, plate, (x0, y0, x1, y1))
            ys, xs = np.nonzero(m)
            if len(ys) > 200:
                yb = np.percentile(ys, 99)
                xb = np.median(xs[ys >= yb - 3])
                d_mask = float(r[int(yb), int(xb)])
            else:
                d_mask = np.nan
            rows.append((f, i, d_box, d_map, d_mask, cut, fx, y1))
    rows = np.array(rows, float)
    np.save(out / "person_depth.npy", rows)

    print("id   frames  cut%   dist(m) first->last   jitter(cm/frame): box  map  mask")
    for i in np.unique(rows[:, 1]).astype(int):
        t = rows[rows[:, 1] == i]
        if len(t) < 60:
            continue
        jit = lambda v: 100 * np.nanmedian(np.abs(np.diff(v, 2))) if np.isfinite(v).sum() > 10 else np.nan
        print(f"{i:3d}  {len(t):5d}  {100 * t[:, 5].mean():4.0f}   {t[0, 2]:5.1f} -> {t[-1, 2]:5.1f}"
              f"            {jit(t[:, 2]):6.1f} {jit(t[:, 3]):6.1f} {jit(t[:, 4]):6.1f}")


if __name__ == "__main__":
    main()
