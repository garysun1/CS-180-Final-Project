"""Soft depth band between a real and a restyled background.

Two things make the transition seamless:
  1. align the restyled image to the real one (homography fitted on edge maps);
  2. blend each frequency band over its own depth range: coarse tone and colour
     change over many metres, fine texture switches over a short range, so the
     fade is gradual without doubled edges.
Masks come straight from depth, never from image-space blur, so silhouettes of
objects in front of the band stay sharp.

    python depth/blend.py REAL --depth depth.npz --styled DIR --out OUTDIR --center 10
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SIGMAS = [2, 4, 8, 16, 32]             # Laplacian stack scales (px), fine -> coarse
WIDTHS = [1.0, 1.5, 2.5, 4.0, 6.0, 8.0]  # band width in metres per level, last = residual


def edges(img, scale):
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 1.5)
    mag = cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    return mag / (mag.mean() + 1e-6)


def align(real, styled, scale=0.5):
    """Warp styled onto real. Returns (warped, edge correlation before, after)."""
    er, es = edges(real, scale), edges(styled, scale)
    before = float(np.corrcoef(er.ravel(), es.ravel())[0, 1])
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7)
    try:
        _, H = cv2.findTransformECC(er, es, np.eye(3, dtype=np.float32), cv2.MOTION_HOMOGRAPHY, crit, None, 5)
    except cv2.error:
        return styled, before, before, np.eye(3)
    S = np.diag([scale, scale, 1.0])
    H = np.linalg.inv(S) @ H @ S  # lift to full resolution
    h, w = real.shape[:2]
    warped = cv2.warpPerspective(styled, H, (w, h), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_REPLICATE)
    after = float(np.corrcoef(er.ravel(), edges(warped, scale).ravel())[0, 1])
    if after < before:
        return styled, before, before, np.eye(3)
    return warped, before, after, H


def band(d, center, width):
    a = np.clip((d - (center - width / 2)) / width, 0, 1)
    return (a * a * (3 - 2 * a)).astype(np.float32)[..., None]


def stack(img):
    """Laplacian stack: list of band-pass layers plus the low-pass residual."""
    cur, out = img.astype(np.float32), []
    for s in SIGMAS:
        low = cv2.GaussianBlur(cur, (0, 0), s)
        out.append(cur - low)
        cur = low
    return out + [cur]


def blend_hard(real, styled, d, center):
    a = (d > center).astype(np.float32)[..., None]
    return np.clip(real * (1 - a) + styled * a, 0, 255).astype(np.uint8)


def blend_crossfade(real, styled, d, center, width):
    a = band(d, center, width)
    return np.clip(real * (1 - a) + styled * a, 0, 255).astype(np.uint8)


def blend_multiband(real, styled, d, center, widths=WIDTHS):
    out = 0
    for lr, ls, w in zip(stack(real), stack(styled), widths):
        a = band(d, center, w)
        out = out + lr * (1 - a) + ls * a
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--depth", required=True)
    ap.add_argument("--styled", required=True, help="directory of restyled images")
    ap.add_argument("--out", required=True)
    ap.add_argument("--center", type=float, default=10)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    real = np.asarray(Image.open(args.image).convert("RGB"))
    d = np.load(args.depth)["r"]

    # Pass 1: fit a homography per style. Heavy styles defeat edge matching, so
    # styles whose fit is not trustworthy reuse the consensus of the ones that are
    # (the editor applies the same crop/resize to every output).
    paths = sorted(Path(args.styled).glob("*.jpg"))
    fits = {}
    for p in paths:
        styled = np.asarray(Image.open(p).convert("RGB"))
        _, c0, c1, H = align(real, styled)
        fits[p] = (c0, c1, H)
    trusted = [H for _, c1, H in fits.values() if c1 > 0.9]
    consensus = np.mean(trusted, 0) if trusted else np.eye(3)
    h, w = real.shape[:2]

    for p in paths:
        styled = np.asarray(Image.open(p).convert("RGB"))
        c0, c1, H = fits[p]
        src = "own fit"
        if c1 <= 0.9:
            H, src = consensus, "consensus"
        warped = cv2.warpPerspective(styled, H, (w, h), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                                     borderMode=cv2.BORDER_REPLICATE)
        c1 = float(np.corrcoef(edges(real, 0.5).ravel(), edges(warped, 0.5).ravel())[0, 1])
        print(f"{p.stem:14s} edge corr {c0:.3f} -> {c1:.3f} ({src})  "
              f"scale y{np.hypot(H[0,1],H[1,1]):.4f} shift {H[0,2]:+.1f},{H[1,2]:+.1f}px")
        Image.fromarray(warped).save(out / f"{p.stem}_aligned.jpg", quality=95)
        save = lambda name, im: Image.fromarray(im).save(out / f"{p.stem}_{name}.jpg", quality=92)
        save("hard", blend_hard(real, warped, d, args.center))
        save("crossfade", blend_crossfade(real, warped, d, args.center, WIDTHS[-1]))
        save("crossfade_unaligned", blend_crossfade(real, styled, d, args.center, WIDTHS[-1]))
        save("multiband", blend_multiband(real, warped, d, args.center))


if __name__ == "__main__":
    main()
