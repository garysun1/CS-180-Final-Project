"""Step 5 - composite.

Notation (all float in [0,1]): F = original frame, B = clean plate, R = aligned restyled plate,
a = person alpha, S = shadow ratio, P = person as shown on the restyled side, w = restyled-side weight.

    restyled side = a*P + (1-a) * R*S
    output        = (1-w)*F + w*restyled side

On the real side (w = 0) the output is exactly the input frame - we never touch real pixels.

Edge decontamination (clean-plate keying): a soft mask edge contains some of the OLD background, which
shows up as a daylight halo around people on a night side. Because the camera is fixed we know that
background exactly (it is the clean plate), so under the matting model F = a*FG + (1-a)*B*S we can
swap it for the new one:
    restyled side = P + (1-a) * (R - Q) * S        (inside the mask's soft support)
where Q is the background as it appears in P (Q = B for filmed people, Q = style(B) for matched
people). At a = 1 this is P; at a -> 0 it is R*S. Outside the support we use R*S directly.

Shadow ratio: a person's shadow is missed by the mask (by design - we don't want grey ground pasted
into a painting), but it is still visible as the frame being darker than the clean plate. The ratio
S = Y(F)/Y(B) (luminance, clipped to <= 1) multiplies the restyled plate so the shadow carries
over in the new world's colours. It is only applied in a neighbourhood around people, and tiny
deviations are ignored, so sensor noise is not stamped onto the restyled image.
"""
from __future__ import annotations

import cv2
import numpy as np


def luma(img_f: np.ndarray) -> np.ndarray:
    return img_f[..., 0] * 0.114 + img_f[..., 1] * 0.587 + img_f[..., 2] * 0.299


class ShadowRatio:
    def __init__(self, clean_bg_f: np.ndarray, neigh_frac: float = 0.06, deadzone: float = 0.04,
                 blur_px: float | None = None):
        h, w = clean_bg_f.shape[:2]
        self.yb = cv2.GaussianBlur(luma(clean_bg_f), (0, 0), 1.0) + 1e-3
        r = max(1, int(neigh_frac * h))
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        self.neigh_sigma = r / 3
        self.deadzone = deadzone
        self.blur = blur_px if blur_px is not None else 1.5 * w / 768
        re = max(1, int(round(2 * w / 768)))
        self.person_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * re + 1, 2 * re + 1))

    def __call__(self, frame_f: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (S HxW, neighbourhood weight HxW)."""
        yf = cv2.GaussianBlur(luma(frame_f), (0, 0), 1.0)
        darkening = np.clip(1.0 - yf / self.yb, 0, 1)                    # 0 = no change
        darkening = np.clip(darkening - self.deadzone, 0, 1) / (1 - self.deadzone)
        # The person's own (usually darker) pixels are not shadow: zero them (slightly dilated) so
        # the feathered mask edge does not pick up a dark outline on the restyled side.
        person = cv2.dilate((alpha > 0.05).astype(np.uint8), self.person_kernel)
        darkening = darkening * (1 - person)
        darkening = cv2.GaussianBlur(darkening, (0, 0), self.blur)
        near = cv2.dilate((alpha > 0.3).astype(np.uint8), self.kernel).astype(np.float32)
        near = cv2.GaussianBlur(near, (0, 0), self.neigh_sigma)
        return (1.0 - near * darkening).astype(np.float32), near


def glow_overlay(d: np.ndarray, width_px: float, color=(1.0, 0.92, 0.75), strength: float = 0.55) -> np.ndarray:
    """Soft light curtain along the line (added in screen mode)."""
    g = np.exp(-(d / width_px) ** 2) + 0.35 * np.exp(-(d / (4 * width_px)) ** 2)
    return (strength * g)[..., None] * np.array(color, np.float32)[None, None]


def composite(F: np.ndarray, R: np.ndarray, alpha: np.ndarray, S: np.ndarray, w: np.ndarray,
              P: np.ndarray | None = None, glow: np.ndarray | None = None,
              Q: np.ndarray | None = None, support_eps: float = 0.004) -> np.ndarray:
    """All inputs float32. F,R,P,Q: HxWx3; alpha,S,w: HxW. Returns float32 HxWx3.
    Q = background as seen in P (enables edge decontamination); None = plain alpha blend."""
    a = alpha[..., None]
    P = F if P is None else P
    S3 = S[..., None]
    if Q is None:
        rs = a * P + (1 - a) * R * S3
    else:
        rs = np.where(a > support_eps, P + (1 - a) * (R - Q) * S3, R * S3)
    out = F + w[..., None] * (rs - F)
    if glow is not None:
        out = 1 - (1 - out) * (1 - glow)   # screen blend
    return np.clip(out, 0, 1)
