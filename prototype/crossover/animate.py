"""Procedural animation on the restyled side (optional, --no-anim turns it off).

The restyled world is still ONE still image; these layers are generated from the frame time with a
fixed seed, so they are smooth and deterministic (no flicker, no per-frame generation):
  * Snowfall  - particles drawn IN FRONT of everything on the restyled side (winter);
  * Caustics  - a moving light web that multiplies the plate BEHIND the people (underwater).
"""
from __future__ import annotations

import cv2
import numpy as np


class Snowfall:
    def __init__(self, w: int, h: int, fps: float, seed: int = 0, density: float = 1.4e-3):
        rng = np.random.default_rng(seed + 11)
        self.w, self.h, self.fps = w, h, fps
        s = w / 768.0
        n = int(density * w * h)
        depth = rng.uniform(0, 1, n) ** 2                   # most flakes far away (small, slow)
        self.x0 = rng.uniform(0, w, n)
        self.y0 = rng.uniform(-20 * s, h + 20 * s, n)
        self.r = (0.6 + 2.2 * depth) * s
        self.vy = (25 + 70 * depth) * s                     # px per second
        self.amp = (4 + 10 * depth) * s
        self.om = rng.uniform(0.6, 1.6, n)
        self.ph = rng.uniform(0, 2 * np.pi, n)
        self.opacity = 0.55 + 0.45 * depth
        self.span = h + 40 * s
        self.blur = 0.5 * s

    def layer(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        """(rgb HxWx3 float32, alpha HxW float32) for frame index i."""
        t = i / self.fps
        y = (self.y0 + self.vy * t) % self.span - 20 * self.w / 768.0
        x = (self.x0 + self.amp * np.sin(self.om * t + self.ph)) % self.w
        a = np.zeros((self.h, self.w), np.float32)
        for xi, yi, ri, oi in zip(x, y, self.r, self.opacity):
            # draw at 4x sub-pixel precision for smooth motion
            cv2.circle(a, (int(xi * 4), int(yi * 4)), max(1, int(ri * 4)), float(oi), -1, cv2.LINE_AA, shift=2)
        a = cv2.GaussianBlur(a, (0, 0), self.blur)
        rgb = np.ones((self.h, self.w, 3), np.float32)
        return rgb, np.clip(a, 0, 1)


class Caustics:
    def __init__(self, w: int, h: int, fps: float, seed: int = 0, strength: float = 0.45):
        self.w, self.h, self.fps, self.strength = w, h, fps, strength
        ds = 4                                               # compute at 1/4 res, upsample
        self.sw, self.sh = max(8, w // ds), max(8, h // ds)
        ys, xs = np.mgrid[0:self.sh, 0:self.sw].astype(np.float32)
        scale = 2 * np.pi / (self.sw / 9.0)                  # ~9 cells across the frame
        self.u, self.v = xs * scale, ys * scale * 1.6        # squashed vertically: ground in perspective
        self.near = np.linspace(0.35, 1.0, h, dtype=np.float32)[:, None]   # stronger near the camera

    def gain(self, i: int) -> np.ndarray:
        t = i / self.fps
        u, v = self.u, self.v
        a = np.sin(u + 0.9 * np.sin(v * 0.8 + 0.7 * t) + 0.5 * t)
        b = np.sin(v * 1.1 - 0.8 * np.sin(u * 0.9 - 0.6 * t) - 0.4 * t)
        web = np.clip(1 - np.abs(a + b) * 0.9, 0, 1) ** 4    # bright thin ridges where a + b ~ 0
        web = cv2.resize(web.astype(np.float32), (self.w, self.h), interpolation=cv2.INTER_CUBIC)
        return 1 + self.strength * np.clip(web, 0, 1) * self.near


class StyleAnimation:
    """What run.py talks to: plate gain (behind people) and front layer (over people)."""

    def __init__(self, plate=None, front=None):
        self.plate, self.front = plate, front

    def plate_gain(self, i: int) -> np.ndarray | None:
        return self.plate.gain(i) if self.plate else None

    def front_layer(self, i: int):
        return self.front.layer(i) if self.front else None


def make_animation(style: str, w: int, h: int, fps: float, seed: int = 0) -> StyleAnimation | None:
    style = style.split()[0].lower() if style else ""        # "winter (SD)" -> "winter"
    if style == "winter":
        return StyleAnimation(front=Snowfall(w, h, fps, seed))
    if style == "underwater":
        return StyleAnimation(plate=Caustics(w, h, fps, seed))
    return None
