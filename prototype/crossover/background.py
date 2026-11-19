"""Step 1 - clean background plate via the temporal median.

With a locked-off camera, every pixel shows the static scene most of the time; people only pass
through. The per-pixel median over many frames therefore recovers the empty scene. It fails where a
person stands still for more than ~half the sampled frames - the motion heatmap shows those spots.
"""
from __future__ import annotations

import os
import tempfile

import cv2
import numpy as np

from .video_io import iter_frames, probe


def sample_indices(n_frames: int, k: int) -> np.ndarray:
    k = max(1, min(n_frames, k))
    return np.unique(np.linspace(0, n_frames - 1, k).round().astype(int))


def _load_mask(masks_dir: str, idx: int, size: tuple[int, int]) -> np.ndarray | None:
    p = os.path.join(masks_dir, f"{idx:05d}.png")
    if not os.path.exists(p):
        return None
    m = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if (m.shape[1], m.shape[0]) != size:
        m = cv2.resize(m, size, interpolation=cv2.INTER_NEAREST)
    return m > 127


def median_background(
    path: str,
    scale: float = 1.0,
    max_samples: int = 150,
    masks_dir: str | None = None,
    strip_rows: int = 64,
    diff_thresh: int = 25,
    max_frames: int | None = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (clean_bg uint8 HxWx3, motion_heatmap float32 HxW in [0,1], info).

    Frames are decoded sequentially; sampled ones go into a stack that lives on disk (memmap) when
    it would be large, so 4K clips fit in RAM. The median is computed strip by strip.
    If masks_dir is given (e.g. SAM 3 masks), person pixels are ignored (masked median).
    """
    info = probe(path, scale)
    n = info.n_frames if max_frames is None else min(info.n_frames, max_frames)
    idx = sample_indices(n, max_samples)
    H, W = info.height, info.width
    k = len(idx)
    nbytes = k * H * W * 3
    tmp = None
    if nbytes > 1.5e9:
        tmp = tempfile.NamedTemporaryFile(suffix=".u8", delete=False)
        stack = np.memmap(tmp.name, dtype=np.uint8, mode="w+", shape=(k, H, W, 3))
    else:
        stack = np.empty((k, H, W, 3), np.uint8)
    valid = np.ones((k, H, W), bool) if masks_dir else None

    want = set(idx.tolist())
    j = 0
    for i, frame in enumerate(iter_frames(path, scale, max_frames=n)):
        if i in want:
            stack[j] = frame
            if masks_dir:
                m = _load_mask(masks_dir, i, (W, H))
                if m is not None:
                    valid[j] = ~m
            j += 1
    stack = stack[:j]
    if valid is not None:
        valid = valid[:j]

    bg = np.empty((H, W, 3), np.uint8)
    heat = np.empty((H, W), np.float32)
    for r0 in range(0, H, strip_rows):
        r1 = min(H, r0 + strip_rows)
        s = stack[:, r0:r1]
        if valid is None:
            med = np.median(s, axis=0)
        else:
            sf = s.astype(np.float32)
            sf[~valid[:, r0:r1]] = np.nan
            with np.errstate(all="ignore"):
                med = np.nanmedian(sf, axis=0)
            fallback = np.median(s, axis=0)
            med = np.where(np.isnan(med), fallback, med)
        bg[r0:r1] = np.clip(np.round(med), 0, 255).astype(np.uint8)
        dev = np.abs(s.astype(np.int16) - bg[r0:r1][None].astype(np.int16)).max(axis=-1)
        heat[r0:r1] = (dev > diff_thresh).mean(axis=0)

    if tmp is not None:
        del stack
        os.unlink(tmp.name)

    meta = {"n_frames": n, "n_samples": int(j), "masked_median": bool(masks_dir),
            "size": [W, H], "fps": info.fps}
    return bg, heat, meta


def heatmap_image(heat: np.ndarray) -> np.ndarray:
    """Colour-map the motion heatmap (fraction of sampled frames a pixel was occupied)."""
    v = np.clip(heat / max(0.5, float(heat.max())), 0, 1)
    return cv2.applyColorMap((v * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
