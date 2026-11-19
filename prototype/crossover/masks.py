"""Step 4 - cut out the people.

Two sources of a per-frame soft alpha (float32 HxW in [0,1]):
  * BgDiffMasker (CPU stand-in): with a fixed camera, anything that differs from the clean plate is
    a person. We measure colour difference in LAB with luminance down-weighted (a shadow mostly
    darkens, it rarely changes hue - we want shadows OUT of the mask, they are carried separately by
    the shadow ratio), then clean the binary mask up with morphology, drop small blobs, vote over
    3 frames to kill flicker, and feather the edge.
  * PngMasks: masks written by SAM 3 in the Colab notebook (masks/00000.png, ...).
"""
from __future__ import annotations

import os
from typing import Iterator

import cv2
import numpy as np


def _ellipse(r: int) -> np.ndarray:
    r = max(1, int(r))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


class EdgeRefiner:
    """Trimap edge refinement against the clean plate (difference matting).

    The eroded mask (5 px in from the edge @768w) is certain person (alpha 1). In a band around the
    edge (5 px in, 2.5 px out), alpha comes from how different the pixel is from the clean plate:
    pixels that look like the background (ground between the legs, around the feet) get alpha ~0.
    This trims masks that are a bit too fat (which otherwise leave a rim of the OLD background around
    people) - possible only because a tripod gives us the exact background.
    """

    def __init__(self, clean_bg: np.ndarray, lo: float = 6.0, hi: float = 22.0, l_weight: float = 0.5,
                 inner_px: float | None = None, outer_px: float | None = None, feather_px: float | None = None):
        self.s = clean_bg.shape[1] / 768.0
        self.bg_lab = _lab(clean_bg)
        self.lo, self.hi, self.l_weight = lo, hi, l_weight
        self.k_core = _ellipse(inner_px if inner_px is not None else 5.0 * self.s)
        self.k_out = _ellipse(outer_px if outer_px is not None else 2.5 * self.s)
        self.feather = feather_px if feather_px is not None else 0.7 * self.s

    def dist(self, frame: np.ndarray) -> np.ndarray:
        return _lab_dist(_lab(frame), self.bg_lab, self.l_weight)

    def __call__(self, binary: np.ndarray, dist: np.ndarray) -> np.ndarray:
        core = cv2.erode(binary, self.k_core)
        band = cv2.dilate(binary, self.k_out) & (1 - core)
        soft = np.clip((dist - self.lo) / (self.hi - self.lo), 0, 1)
        a = core.astype(np.float32) + band.astype(np.float32) * soft
        return cv2.GaussianBlur(a, (0, 0), self.feather) if self.feather > 0 else a


def _lab(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(cv2.GaussianBlur(img, (0, 0), 1.0), cv2.COLOR_BGR2LAB).astype(np.float32)


def _lab_dist(lab: np.ndarray, bg_lab: np.ndarray, l_weight: float) -> np.ndarray:
    d = lab - bg_lab
    return np.sqrt((l_weight * d[..., 0]) ** 2 + d[..., 1] ** 2 + d[..., 2] ** 2)


class BgDiffMasker:
    def __init__(self, clean_bg: np.ndarray, thresh: float = 16.0, l_weight: float = 0.5,
                 min_area_frac: float = 3e-4, feather_px: float | None = None):
        h, w = clean_bg.shape[:2]
        self.s = w / 768.0
        self.bg_lab = _lab(clean_bg)
        self.thresh, self.l_weight = thresh, l_weight
        self.min_area = min_area_frac * h * w
        self.feather = feather_px if feather_px is not None else 1.2 * self.s
        self.k_open, self.k_close = _ellipse(1.5 * self.s), _ellipse(4 * self.s)
        self.refiner = EdgeRefiner(clean_bg, l_weight=l_weight)

    def binary(self, frame: np.ndarray, dist: np.ndarray | None = None) -> np.ndarray:
        if dist is None:
            dist = _lab_dist(_lab(frame), self.bg_lab, self.l_weight)
        m = (dist > self.thresh).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, self.k_open)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, self.k_close)
        n, lab_cc, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        keep = np.zeros(n, np.uint8)
        keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= self.min_area
        m = keep[lab_cc]
        # fill interior holes (clothes that happen to match the background colour)
        filled = m.copy()
        ff = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8)
        cv2.floodFill(filled, ff, (0, 0), 1)
        return (m | (1 - filled)).astype(np.uint8)

    def soft(self, binary: np.ndarray, dist: np.ndarray | None = None) -> np.ndarray:
        if dist is not None:
            return self.refiner(binary, dist)
        a = binary.astype(np.float32)
        return cv2.GaussianBlur(a, (0, 0), self.feather) if self.feather > 0 else a

    def iter_alphas(self, frames: Iterator[np.ndarray]) -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
        """Yield (index, frame, alpha). Temporal clean-up with 1-frame look-ahead: a pixel survives
        only if something was also detected near it (dilated) in the previous or next frame. This
        kills one-frame blips (noise, compression artefacts) without eroding moving people."""
        k = _ellipse(6 * self.s)
        prev = None
        cur = None
        for i, f in enumerate(frames):
            dist = _lab_dist(_lab(f), self.bg_lab, self.l_weight)
            b = self.binary(f, dist)
            if cur is not None:
                j, fj, bj, dj = cur
                support = cv2.dilate(b if prev is None else (prev | b), k)
                yield j, fj, self.soft(bj & support, dj)
                prev = bj
            cur = (i, f, b, dist)
        if cur is not None:
            j, fj, bj, dj = cur
            yield j, fj, self.soft(bj if prev is None else bj & cv2.dilate(prev, k), dj)


class PngMasks:
    """Load alphas written by SAM 3 (notebook): <dir>/00000.png ... (8-bit, 255 = person)."""

    def __init__(self, masks_dir: str, clean_bg: np.ndarray | None = None, feather_px: float = 1.0):
        """If clean_bg is given, mask edges are refined against it (EdgeRefiner)."""
        if not os.path.isdir(masks_dir):
            raise FileNotFoundError(masks_dir)
        self.dir, self.feather = masks_dir, feather_px
        self.refiner = EdgeRefiner(clean_bg) if clean_bg is not None else None

    def binary(self, idx: int, size: tuple[int, int]) -> np.ndarray:
        p = os.path.join(self.dir, f"{idx:05d}.png")
        if not os.path.exists(p):
            return np.zeros((size[1], size[0]), np.uint8)
        m = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if (m.shape[1], m.shape[0]) != size:
            m = cv2.resize(m, size, interpolation=cv2.INTER_LINEAR)
        return (m > 127).astype(np.uint8)

    def iter_alphas(self, frames: Iterator[np.ndarray]) -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
        for i, f in enumerate(frames):
            b = self.binary(i, (f.shape[1], f.shape[0]))
            if self.refiner is not None:
                a = self.refiner(b, self.refiner.dist(f))
            else:
                a = cv2.GaussianBlur(b.astype(np.float32), (0, 0), self.feather)
            yield i, f, a
