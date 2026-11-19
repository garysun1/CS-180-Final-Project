"""Depth-based seam on a single clean background image.

Runs Depth Pro once (metric depth + focal length), converts forward depth to
true distance from the camera, and draws the seam for both definitions.

    python depth/seam.py IMAGE --out OUTDIR [--dist 8 12 18]
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import DepthProForDepthEstimation, DepthProImageProcessor

MODEL = "apple/DepthPro-hf"


def estimate(image_path):
    """Return (rgb uint8 HxWx3, forward depth in metres HxW, focal length in px)."""
    img = Image.open(image_path).convert("RGB")
    proc = DepthProImageProcessor.from_pretrained(MODEL)
    model = DepthProForDepthEstimation.from_pretrained(MODEL).eval()
    with torch.no_grad():
        out = model(**proc(images=img, return_tensors="pt"))
    res = proc.post_process_depth_estimation(out, target_sizes=[(img.height, img.width)])[0]
    return np.asarray(img), res["predicted_depth"].numpy(), float(res["focal_length"])


def radial_distance(z, focal):
    """Forward depth -> Euclidean distance from the camera centre."""
    h, w = z.shape
    x = (np.arange(w) - (w - 1) / 2) / focal
    y = (np.arange(h) - (h - 1) / 2) / focal
    xx, yy = np.meshgrid(x, y)
    return z * np.sqrt(1 + xx**2 + yy**2)


def camera_height(z, focal, rows=0.2):
    """Fit a plane to the bottom rows (assumed ground); return camera height above it."""
    h, w = z.shape
    y0 = int(h * (1 - rows))
    xx, yy = np.meshgrid((np.arange(w) - (w - 1) / 2) / focal, (np.arange(y0, h) - (h - 1) / 2) / focal)
    zz = z[y0:]
    pts = np.stack([xx * zz, yy * zz, zz], -1).reshape(-1, 3)[::37]
    c = pts.mean(0)
    n = np.linalg.svd(pts - c, full_matrices=False)[2][-1]
    return abs(n @ c)


def colorize(d, lo, hi):
    """Log-scaled depth visualisation, near = bright."""
    t = (np.log(np.clip(d, lo, hi)) - np.log(lo)) / (np.log(hi) - np.log(lo))
    return cv2.applyColorMap((255 * (1 - t)).astype(np.uint8), cv2.COLORMAP_INFERNO)


def draw_seam(bgr, d, thresholds, colors, thickness=3):
    out = bgr.copy()
    for t, c in zip(thresholds, colors):
        cs, _ = cv2.findContours((d > t).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(out, cs, -1, c, thickness, cv2.LINE_AA)
    return out


def split_preview(bgr, d, t, band=0.0):
    """Stand-in for the restyle: far side becomes a cool-tinted monochrome."""
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    far = np.stack([grey * 1.0, grey * 0.75, grey * 0.45], -1)  # blue-ish in BGR
    if band > 0:
        a = np.clip((d - (t - band / 2)) / band, 0, 1)
        a = a * a * (3 - 2 * a)
    else:
        a = (d > t).astype(np.float32)
    return (bgr * (1 - a[..., None]) + far * a[..., None]).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dist", type=float, nargs="+", default=[8, 12, 18])
    ap.add_argument("--cam-height", type=float, help="measured camera height in metres; rescales depth")
    ap.add_argument("--reuse", action="store_true", help="reuse OUT/raw.npz instead of running the model")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.reuse:
        raw = np.load(out / "raw.npz")
        rgb, z, focal = np.asarray(Image.open(args.image).convert("RGB")), raw["z"], float(raw["focal"])
    else:
        rgb, z, focal = estimate(args.image)
        np.savez_compressed(out / "raw.npz", z=z.astype(np.float32), focal=focal)
    est_h = camera_height(z, focal)
    print(f"model's camera height above ground: {est_h:.2f} m")
    if args.cam_height:
        z = z * (args.cam_height / est_h)
        print(f"rescaled depth by {args.cam_height / est_h:.2f}x to match {args.cam_height} m")
    r = radial_distance(z, focal)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    h, w = z.shape
    fov = 2 * np.degrees(np.arctan(w / 2 / focal))
    print(f"focal {focal:.0f}px, horizontal FOV {fov:.1f} deg, "
          f"depth range {z.min():.1f}-{z.max():.1f} m")
    np.savez_compressed(out / "depth.npz", z=z.astype(np.float32), r=r.astype(np.float32), focal=focal)

    lo, hi = np.percentile(r, 1), min(np.percentile(r, 99), 100)
    cv2.imwrite(str(out / "depth_radial.jpg"), colorize(r, lo, hi))

    colors = [(0, 255, 255), (0, 128, 255), (255, 0, 255)]
    cv2.imwrite(str(out / "seam_radial.jpg"), draw_seam(bgr, r, args.dist, colors))
    cv2.imwrite(str(out / "seam_forward.jpg"), draw_seam(bgr, z, args.dist, colors))
    # both definitions on one image at the middle threshold
    mid = args.dist[len(args.dist) // 2]
    both = draw_seam(bgr, z, [mid], [(255, 255, 0)])
    both = draw_seam(both, r, [mid], [(0, 0, 255)])
    cv2.imwrite(str(out / "seam_compare.jpg"), both)
    for t in args.dist:
        cv2.imwrite(str(out / f"split_{t:g}m_hard.jpg"), split_preview(bgr, r, t))
    cv2.imwrite(str(out / f"split_{mid:g}m_soft.jpg"), split_preview(bgr, r, mid, band=mid * 0.4))


if __name__ == "__main__":
    main()
