"""Learned colour mapping for people: what did the editor do to the light and colour *here*?

After alignment, the clean plate B and the restyled plate R are pixel-aligned, so we can regress R on
B. We fit a smooth field of 3x4 affine colour transforms, R(x) ~ A(x) . [B(x), 1]:
  * per tile of a coarse grid, a ridge regression pulled toward one global affine;
  * robust (Cauchy) re-weighting: where the editor changed CONTENT (snow replacing grass, a lit
    window replacing a dark one) the affine fit is poor, those pixels get low weight, and the tile
    falls back toward the global mapping - so 'green grass -> white snow' is not taught to people;
  * the tile grid is smoothed and upsampled to one transform per pixel.
Applying it to a filmed person is pixelwise for a fixed position, so it cannot flicker, and it
carries spatially varying light (a warm lamp pool at night, a dark far side) onto people.

explained_frac / fit_psnr say how much of an edit is 'just colour and light': a regrade scores
high, an edit that adds new content (snow over grass) scores low.
"""
from __future__ import annotations

import cv2
import numpy as np

from .metrics import psnr
from .video_io import to_float, to_uint8


def _solve(X: np.ndarray, Y: np.ndarray, w: np.ndarray, prior: np.ndarray, lam: float) -> np.ndarray:
    """argmin_A sum_i w_i |Y_i - A X_i|^2 + lam |A - prior|^2, with X: (n,4), Y: (n,3); returns A (3,4)."""
    Xw = X * w[:, None]
    lhs = X.T @ Xw + lam * np.eye(4)
    rhs = Xw.T @ Y + lam * prior.T
    return np.linalg.solve(lhs, rhs).T


class LocalAffineColor:
    # lam / cauchy_global trade local-lighting fidelity against robustness to content swaps; tuned on
    # the two synthetic tests (strongly varying light: ~32 dB; snow-like swap: 0.025 mean abs error).
    def __init__(self, grid: tuple[int, int] = (12, 9), lam: float = 0.02, cauchy: float = 0.08,
                 cauchy_global: float = 0.15, iters: int = 4, smooth: float = 1.0, samples: int = 3000,
                 strength: float = 1.0, seed: int = 0):
        self.gx, self.gy = grid
        self.lam, self.c, self.cg, self.iters, self.smooth = lam, cauchy, cauchy_global, iters, smooth
        self.samples, self.strength, self.seed = samples, strength, seed
        self.field: np.ndarray | None = None      # (H, W, 3, 4)
        self.grid: np.ndarray | None = None       # (gy, gx, 12), the smoothed tiles the field is resized from
        self.A_global: np.ndarray | None = None
        self._fit_psnr: float | None = None
        self._explained: float | None = None

    def _irls(self, X, Y, prior, lam, w0=None):
        """Robust fit. w0 = prior weights (how plausible each pixel is under the GLOBAL mapping):
        a tile made entirely of new content is self-consistent, so only a global reference can
        flag it."""
        w0 = np.ones(len(X)) if w0 is None else w0
        w = w0.copy()
        A = prior
        for _ in range(self.iters):
            A = _solve(X, Y, w, prior, lam)
            r = np.linalg.norm(Y - X @ A.T, axis=1)
            w = w0 / (1.0 + (r / self.c) ** 2)
        return A

    def fit(self, B: np.ndarray, R: np.ndarray) -> "LocalAffineColor":
        rng = np.random.default_rng(self.seed)
        Bf, Rf = to_float(B), to_float(R)
        H, W = Bf.shape[:2]
        X = np.concatenate([Bf, np.ones((H, W, 1), np.float32)], axis=2)
        # global mapping (robust), the prior every tile is pulled toward
        idx = rng.choice(H * W, size=min(20000, H * W), replace=False)
        Xs, Ys = X.reshape(-1, 4)[idx], Rf.reshape(-1, 3)[idx]
        ident = np.hstack([np.eye(3), np.zeros((3, 1))]).astype(np.float64)
        self.A_global = self._irls(Xs.astype(np.float64), Ys.astype(np.float64), ident, self.lam * len(Xs))
        # per tile
        ys = np.linspace(0, H, self.gy + 1).astype(int)
        xs = np.linspace(0, W, self.gx + 1).astype(int)
        grid = np.zeros((self.gy, self.gx, 12), np.float32)
        for j in range(self.gy):
            for i in range(self.gx):
                Xt = X[ys[j]:ys[j + 1], xs[i]:xs[i + 1]].reshape(-1, 4)
                Yt = Rf[ys[j]:ys[j + 1], xs[i]:xs[i + 1]].reshape(-1, 3)
                if len(Xt) > self.samples:
                    k = rng.choice(len(Xt), self.samples, replace=False)
                    Xt, Yt = Xt[k], Yt[k]
                # absolute ridge weight: if every pixel in the tile is an outlier (content swap),
                # the robust weights all shrink and the global prior takes over
                Xt, Yt = Xt.astype(np.float64), Yt.astype(np.float64)
                rg = np.linalg.norm(Yt - Xt @ self.A_global.T, axis=1)
                w0 = 1.0 / (1.0 + (rg / self.cg) ** 2)        # content swaps -> far from global -> low
                A = self._irls(Xt, Yt, self.A_global, self.lam * len(Xt), w0)
                grid[j, i] = A.reshape(-1)
        if self.smooth > 0:
            for c in range(12):
                grid[..., c] = cv2.GaussianBlur(grid[..., c], (0, 0), self.smooth, borderType=cv2.BORDER_REPLICATE)
        self.grid = grid.copy()
        self.field = cv2.resize(grid, (W, H), interpolation=cv2.INTER_LINEAR).reshape(H, W, 3, 4)
        pred = self.apply_float(Bf, strength=1.0)
        self._fit_psnr = psnr(R, to_uint8(pred))
        self._explained = float((np.linalg.norm(pred - Rf, axis=2) < 0.1).mean())
        return self

    def export_rgb(self, strength: float | None = None) -> np.ndarray:
        """The tile grid for a renderer working in RGB, with the strength blend baked in:
        (gy, gx, 3, 4), rows = output R, G, B, columns = coefficients of R, G, B and the offset.
        Interpolated with half-pixel centres (as cv2.resize does), it reproduces apply()."""
        s = self.strength if strength is None else strength
        g = self.grid.reshape(self.gy, self.gx, 3, 4)[:, :, ::-1, :][..., [2, 1, 0, 3]]   # BGR -> RGB
        ident = np.hstack([np.eye(3), np.zeros((3, 1))]).astype(np.float32)
        return (s * g + (1 - s) * ident).astype(np.float32)

    def apply_float(self, Ff: np.ndarray, strength: float | None = None) -> np.ndarray:
        s = self.strength if strength is None else strength
        A = self.field
        out = (A[..., :3] * Ff[..., None, :]).sum(-1) + A[..., 3]
        return np.clip(s * out + (1 - s) * Ff, 0, 1).astype(np.float32)

    def apply(self, F: np.ndarray, strength: float | None = None) -> np.ndarray:
        return to_uint8(self.apply_float(to_float(F), strength))

    @property
    def fit_psnr(self) -> float | None:
        return None if self._fit_psnr is None else round(float(self._fit_psnr), 2)

    @property
    def explained_frac(self) -> float | None:
        """Share of pixels the colour mapping reproduces within 0.1 (RGB distance, 0-1 scale): the
        part of the edit that is 'just colour and light'. The rest is new content."""
        return None if self._explained is None else round(self._explained, 3)
