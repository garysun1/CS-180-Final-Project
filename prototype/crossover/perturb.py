"""Synthetic geometric drift with a known ground truth.

Our CPU stand-in styles keep geometry perfectly fixed, but diffusion editors nudge buildings by a few
pixels. To test alignment (and the seam metric itself) we deliberately warp the restyled image by a
random homography plus a smooth random displacement field, and keep the exact mapping.

Convention: the perturbed image P satisfies P(q) = I(m(q)), with m(q) = H^-1 q + d(q).
So m maps a pixel of the perturbed image back to where that content sits in the clean plate.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Perturbation:
    H: np.ndarray        # 3x3, clean-plate coords -> perturbed coords (global part)
    map_x: np.ndarray    # m(q) x-component, HxW float32
    map_y: np.ndarray    # m(q) y-component

    def apply(self, img: np.ndarray) -> np.ndarray:
        return cv2.remap(img, self.map_x, self.map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def m(self, qx: np.ndarray, qy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate m at arbitrary (sub-pixel) points of the perturbed image."""
        qx = np.asarray(qx, np.float32).reshape(-1, 1)
        qy = np.asarray(qy, np.float32).reshape(-1, 1)
        mx = cv2.remap(self.map_x, qx, qy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        my = cv2.remap(self.map_y, qx, qy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return mx.ravel(), my.ravel()


def random_homography(w: int, h: int, jitter_frac: float, rng: np.random.Generator) -> np.ndarray:
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + rng.uniform(-1, 1, src.shape).astype(np.float32) * jitter_frac * w
    return cv2.getPerspectiveTransform(src, dst)


def smooth_field(w: int, h: int, amp_px: float, grid: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    gh = max(2, int(round(grid * h / w)))
    dx = rng.normal(0, 1, (gh, grid)).astype(np.float32)
    dy = rng.normal(0, 1, (gh, grid)).astype(np.float32)
    dx = cv2.resize(dx, (w, h), interpolation=cv2.INTER_CUBIC)
    dy = cv2.resize(dy, (w, h), interpolation=cv2.INTER_CUBIC)
    mag = np.sqrt(dx ** 2 + dy ** 2).max() + 1e-6
    return dx * amp_px / mag, dy * amp_px / mag


def make_perturbation(w: int, h: int, seed: int = 0, jitter_frac: float = 0.01,
                      local_amp_px: float | None = None, grid: int = 6) -> Perturbation:
    rng = np.random.default_rng(seed)
    if local_amp_px is None:
        local_amp_px = 3.0 * w / 768
    H = random_homography(w, h, jitter_frac, rng)
    Hinv = np.linalg.inv(H)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    pts = np.stack([xs, ys, np.ones_like(xs)], -1) @ Hinv.T
    gx, gy = pts[..., 0] / pts[..., 2], pts[..., 1] / pts[..., 2]
    dx, dy = smooth_field(w, h, local_amp_px, grid, rng)
    return Perturbation(H, (gx + dx).astype(np.float32), (gy + dy).astype(np.float32))
