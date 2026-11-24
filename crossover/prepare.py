"""Prepare a new clip for the pipeline: normalise it, check the camera is really fixed, and build the
clean plate and its depth map.

    python -m crossover.prepare data/clips/raw/crowd01.mp4 --name crowd01

Writes data/clips/<name>.mp4 (downscaled, trimmed, no audio) and out/clips/<name>/ with clean_bg.png,
motion_heatmap.png, depth_disparity.npy, depth.png and static.json. The whole method assumes a locked
camera; static.json says whether this clip qualifies.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess

import cv2
import numpy as np

from .background import heatmap_image, median_background
from .video_io import iter_frames, probe


def sift_homography(src: np.ndarray, dst: np.ndarray, ratio: float = 0.75, reproj_px: float = 2.0):
    """Homography mapping src pixels to dst pixels from SIFT matches: (H or None, matches, inliers)."""
    def gray(img):
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(g)
    sift = cv2.SIFT_create(nfeatures=10000)
    k1, d1 = sift.detectAndCompute(gray(src), None)
    k2, d2 = sift.detectAndCompute(gray(dst), None)
    if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
        return None, 0, 0
    knn = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    good = [p[0] for p in knn if len(p) == 2 and p[0].distance < ratio * p[1].distance]
    if len(good) < 8:
        return None, len(good), 0
    sp = np.float32([k1[m.queryIdx].pt for m in good])
    dp = np.float32([k2[m.trainIdx].pt for m in good])
    H, inl = cv2.findHomography(sp, dp, cv2.USAC_MAGSAC, reproj_px, maxIters=10000, confidence=0.9999)
    return (None, len(good), 0) if H is None else (H, len(good), int(inl.sum()))


def corner_shift(H: np.ndarray, w: int, h: int) -> float:
    """Largest displacement (px) of an image corner under H."""
    c = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    return float(np.linalg.norm(cv2.perspectiveTransform(c, H) - c, axis=-1).max())


def normalise(src: str, dst: str, max_width: int, max_seconds: float, start: float, fps: float | None = None) -> None:
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    vf = f"scale='min({max_width},iw)':-2" + (f",fps={fps}" if fps else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-i", src, "-t", str(max_seconds),
                    "-vf", vf, "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", dst], check=True)


def static_check(path: str, n: int, samples: int = 12) -> dict:
    """Is the camera fixed? (1) global drift: homography between the median of the first and last
    sixths of the clip (people removed by the median); (2) jitter: phase-correlation shift of sampled
    frames against the first-sixth median."""
    idx = np.linspace(0, n - 1, 60).astype(int)
    frames = {}
    want = set(idx.tolist())
    for i, f in enumerate(iter_frames(path)):
        if i in want:
            frames[i] = f
    keys = sorted(frames)
    k = max(3, len(keys) // 6)
    early = np.median(np.stack([frames[i] for i in keys[:k]]), axis=0).astype(np.uint8)
    late = np.median(np.stack([frames[i] for i in keys[-k:]]), axis=0).astype(np.uint8)
    H, nm, ni = sift_homography(late, early)
    h, w = early.shape[:2]
    drift = corner_shift(H, w, h) if H is not None else float("inf")
    g0 = cv2.cvtColor(early, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hann = cv2.createHanningWindow((w, h), cv2.CV_32F)
    jit = []
    for i in keys[:: max(1, len(keys) // samples)]:
        g = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY).astype(np.float32)
        (dx, dy), _ = cv2.phaseCorrelate(g0, g, hann)
        jit.append(float(np.hypot(dx, dy)))
    return {"drift_px": round(drift, 2), "jitter_max_px": round(max(jit), 2), "sift_inliers": ni,
            "static": bool(drift < 1.5 and max(jit) < 1.5)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Normalise a clip, check the camera is fixed, build plate + depth.")
    ap.add_argument("video")
    ap.add_argument("--name", required=True)
    ap.add_argument("--max-width", type=int, default=960)
    ap.add_argument("--max-seconds", type=float, default=45)
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--fps", type=float, default=None, help="cap the frame rate (e.g. 25 for a 50 fps clip)")
    ap.add_argument("--data-root", default="data/clips")
    ap.add_argument("--out-root", default="out/clips")
    ap.add_argument("--no-depth", action="store_true")
    a = ap.parse_args(argv)
    clip = os.path.join(a.data_root, a.name + ".mp4")
    out = os.path.join(a.out_root, a.name)
    os.makedirs(out, exist_ok=True)
    normalise(a.video, clip, a.max_width, a.max_seconds, a.start, a.fps)
    info = probe(clip)
    report = {"clip": clip, "width": info.width, "height": info.height, "frames": info.n_frames, "fps": info.fps}
    report.update(static_check(clip, info.n_frames))
    bg, heat, _ = median_background(clip)
    cv2.imwrite(os.path.join(out, "clean_bg.png"), bg)
    cv2.imwrite(os.path.join(out, "motion_heatmap.png"), heatmap_image(heat))
    report["motion_mean"] = round(float(heat.mean()), 4)
    if not a.no_depth:
        from .depth import depth_vis, estimate_disparity, farness
        disp = estimate_disparity(bg)
        np.save(os.path.join(out, "depth_disparity.npy"), disp)
        f = farness(disp)
        cv2.imwrite(os.path.join(out, "depth.png"), depth_vis(f, float(np.quantile(f, 0.5))))
    json.dump(report, open(os.path.join(out, "static.json"), "w"), indent=1)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
