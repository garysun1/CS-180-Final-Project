"""Visualise per-person distance and composite people over a depth-banded background.

    python depth/people_demo.py SEQ_DIR --dir OUTDIR [--styled styled.png --center 6]

OUTDIR must hold plate.png, depth.npz and person_depth.npy (from seam.py and people.py).
Writes distance plots, an annotated video and, with --styled, a composite video in
which people take on the style gradually as their distance passes through the band.
"""
import argparse
import subprocess
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from blend import band, blend_multiband
from people import person_mask, smooth


def fit_color(src, dst):
    """Least-squares affine colour map (3x4) taking plate colours to styled colours."""
    a = src.reshape(-1, 3)[::53].astype(np.float32) / 255
    b = dst.reshape(-1, 3)[::53].astype(np.float32) / 255
    A = np.c_[a, np.ones(len(a))]
    return np.linalg.lstsq(A, b, rcond=None)[0]  # 4x3


def apply_color(img, M, strength):
    x = img.astype(np.float32) / 255
    y = x @ M[:3] + M[3]
    return np.clip((x + strength * (y - x)) * 255, 0, 255)


def writer(path, size, fps):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{size[0]}x{size[1]}",
           "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-crf", "20", str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--styled")
    ap.add_argument("--name", default="styled")
    ap.add_argument("--center", type=float, default=6)
    ap.add_argument("--person-band", type=float, default=3, help="metres over which a person changes style")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()
    seq, out = Path(args.seq), Path(args.dir)
    plate = cv2.imread(str(out / "plate.png"))
    r = np.load(out / "depth.npz")["r"]
    rows = np.load(out / "person_depth.npy")
    h, w = r.shape

    # smoothed per-track distance, keyed by (frame, id)
    dist, per_frame = {}, {}
    for i in np.unique(rows[:, 1]).astype(int):
        t = rows[rows[:, 1] == i]
        s = smooth(t[:, 2])
        for (f, *_), d in zip(t, s):
            dist[(int(f), i)] = d
    for f, i, *_ in rows:
        per_frame.setdefault(int(f), []).append(int(i))

    # --- plots ---
    ids = [i for i in np.unique(rows[:, 1]).astype(int) if (rows[:, 1] == i).sum() >= 200][:8]
    fig, axes = plt.subplots(2, 4, figsize=(18, 7), sharex=True, sharey=True)
    for ax, i in zip(axes.ravel(), ids):
        t = rows[rows[:, 1] == i]
        ax.plot(t[:, 0], t[:, 4], ".", ms=2, color="#d95f02", label="lowest mask pixel")
        ax.plot(t[:, 0], t[:, 2], "-", lw=1, color="#7570b3", label="box foot, raw")
        ax.plot(t[:, 0], smooth(t[:, 2]), "-", lw=2, color="#1b9e77", label="box foot, smoothed")
        ax.axhline(args.center, color="k", ls="--", lw=0.8)
        ax.set_title(f"person {i}")
        ax.set_ylim(0, 16)
    axes[0, 0].legend(fontsize=8)
    fig.supxlabel("frame")
    fig.supylabel("distance from camera (m, model scale)")
    fig.tight_layout()
    fig.savefig(out / "person_depth.png", dpi=110)

    # --- videos ---
    seam = cv2.findContours((r > args.center).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[0]
    ann = writer(out / "annotated.mp4", (w, h), args.fps)
    comp = None
    if args.styled:
        styled = cv2.resize(cv2.imread(args.styled), (w, h), interpolation=cv2.INTER_LANCZOS4)
        bg = blend_multiband(plate, styled, r, args.center).astype(np.float32)
        cv2.imwrite(str(out / f"background_{args.name}.jpg"), bg.astype(np.uint8))
        M = fit_color(plate, styled)
        comp = writer(out / f"composite_{args.name}.mp4", (w, h), args.fps)

    boxes = {(int(f), int(i)): None for f, i, *_ in rows}
    for line in np.loadtxt(seq / "gt" / "gt.txt", delimiter=","):
        k = (int(line[0]), int(line[1]))
        if k in boxes:
            boxes[k] = (line[2], line[3], line[2] + line[4], line[3] + line[5])

    cmap = plt.get_cmap("turbo")
    for f in sorted(per_frame):
        frame = cv2.imread(str(seq / "img1" / f"{f:06d}.jpg"))
        people = sorted(per_frame[f], key=lambda i: -np.nan_to_num(dist[(f, i)], nan=99))  # far first
        a_img = frame.copy()
        cv2.drawContours(a_img, seam, -1, (255, 255, 255), 2, cv2.LINE_AA)
        c_img = bg.copy() if comp else None
        for i in people:
            d, box = dist[(f, i)], boxes[(f, i)]
            if not np.isfinite(d):
                continue
            col = tuple(int(255 * v) for v in cmap(np.clip((d - 2) / 12, 0, 1))[2::-1])
            x0, y0, x1, y1 = [int(v) for v in box]
            cv2.rectangle(a_img, (x0, y0), (x1, y1), col, 3)
            cv2.putText(a_img, f"{d:.1f} m", (max(x0, 5), max(y0 - 8, 28)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5)
            cv2.putText(a_img, f"{d:.1f} m", (max(x0, 5), max(y0 - 8, 28)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
            if comp:
                m = person_mask(frame, plate, box)
                m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)[..., None]
                s = float(band(np.array(d), args.center, args.person_band).squeeze())
                c_img = c_img * (1 - m) + apply_color(frame, M, s) * m
        ann.stdin.write(a_img.tobytes())
        if comp:
            comp.stdin.write(c_img.astype(np.uint8).tobytes())
            if f in (120, 260, 400):
                cv2.imwrite(str(out / f"composite_{args.name}_{f:03d}.jpg"), c_img.astype(np.uint8))
        if f in (120, 260, 400):
            cv2.imwrite(str(out / f"annotated_{f:03d}.jpg"), a_img)
    for p in (ann, comp):
        if p:
            p.stdin.close()
            p.wait()


if __name__ == "__main__":
    main()
