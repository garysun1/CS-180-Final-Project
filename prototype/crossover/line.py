"""The dividing line. Defined by two points so it can be vertical or follow architecture."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Line:
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_spec(cls, spec: str, w: int, h: int) -> "Line":
        """spec = 'x0,y0,x1,y1' as fractions of width/height, e.g. '0.5,0,0.5,1' (vertical, centre)."""
        a = [float(v) for v in spec.split(",")]
        if len(a) != 4:
            raise ValueError("line spec must be 'x0,y0,x1,y1' (fractions of width/height)")
        return cls(a[0] * w, a[1] * h, a[2] * w, a[3] * h)

    @property
    def normal(self) -> np.ndarray:
        t = np.array([self.x1 - self.x0, self.y1 - self.y0], np.float64)
        t /= np.linalg.norm(t) + 1e-12
        return np.array([t[1], -t[0]])  # for a top->bottom line this points right (+x)

    def signed_distance(self, w: int, h: int) -> np.ndarray:
        """Positive on the restyled side (right of a top->bottom line)."""
        nx, ny = self.normal
        xs = np.arange(w, dtype=np.float32)[None, :]
        ys = np.arange(h, dtype=np.float32)[:, None]
        return ((xs - self.x0) * nx + (ys - self.y0) * ny).astype(np.float32)

    def shifted(self, dx: float, dy: float = 0.0) -> "Line":
        return Line(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    def sample_points(self, w: int, h: int, step: float, margin: float = 0.0) -> np.ndarray:
        """Points spaced `step` px along the (infinite) line, kept if inside the image minus margin."""
        p0 = np.array([self.x0, self.y0])
        t = np.array([self.x1 - self.x0, self.y1 - self.y0], np.float64)
        t /= np.linalg.norm(t) + 1e-12
        L = 2 * (w + h)
        s = np.arange(-L, L, step)
        pts = p0[None] + s[:, None] * t[None]
        keep = ((pts[:, 0] >= margin) & (pts[:, 0] < w - margin) &
                (pts[:, 1] >= margin) & (pts[:, 1] < h - margin))
        return pts[keep].astype(np.float32)


def side_weight(d: np.ndarray, mode: str = "feather", feather: float = 3.0) -> np.ndarray:
    """Weight of the restyled side given signed distance d. 'glow' blends like 'feather'."""
    if mode == "hard":
        return (d >= 0).astype(np.float32)
    return np.clip(0.5 + d / max(feather, 1e-3), 0, 1).astype(np.float32)


def band_weight(d: np.ndarray, band_px: float) -> np.ndarray:
    """1 on the line, smoothly falling to 0 at |d| = band_px (smoothstep)."""
    t = np.clip(1 - np.abs(d) / band_px, 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)
