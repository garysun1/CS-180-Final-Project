"""Figures for the check-in / write-up, and the 'how it was made' breakdown frames."""
from __future__ import annotations

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .line import Line  # noqa: E402


def label(img: np.ndarray, text: str, scale: float | None = None) -> np.ndarray:
    """Burn a readable label (white on a dark box) into the top-left corner."""
    out = img.copy()
    s = scale if scale is not None else max(0.45, img.shape[1] / 900)
    th = max(1, int(round(s * 2)))
    (tw, tht), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, s, th)
    if tw > 0.96 * img.shape[1]:                     # shrink to fit the width
        s *= 0.96 * img.shape[1] / tw
        th = max(1, int(round(s * 2)))
        (tw, tht), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, s, th)
    pad = int(6 * s)
    cv2.rectangle(out, (0, 0), (tw + 2 * pad, tht + base + 2 * pad), (20, 20, 20), -1)
    cv2.putText(out, text, (pad, tht + pad), cv2.FONT_HERSHEY_SIMPLEX, s, (255, 255, 255), th, cv2.LINE_AA)
    return out


def mask_overlay(frame: np.ndarray, alpha: np.ndarray, color=(60, 60, 255)) -> np.ndarray:
    a = (alpha * 0.55)[..., None]
    return (frame * (1 - a) + np.array(color, np.float32) * a).astype(np.uint8)


def breakdown_tile(frame, clean, alpha, final) -> np.ndarray:
    """2x2 'how it was made' grid at the original resolution."""
    h, w = frame.shape[:2]
    hw, hh = w // 2, h // 2
    sm = lambda im: cv2.resize(im, (hw, hh), interpolation=cv2.INTER_AREA)
    tl = label(sm(frame), "1. filmed (tripod)")
    tr = label(sm(clean), "2. median = empty scene")
    bl = label(sm(mask_overlay(frame, alpha)), "3. people mask")
    br = label(sm(final), "4. restyle once + composite")
    return np.vstack([np.hstack([tl, tr]), np.hstack([bl, br])])


def pick_seam_points(clean: np.ndarray, line: Line | None, k: int = 3, half: int = 40,
                     avoid: np.ndarray | None = None, points: np.ndarray | None = None) -> np.ndarray:
    """k points on the seam where edges CROSS it (those show a misalignment as a visible jump),
    spread apart. `avoid` (e.g. the motion heatmap) down-weights places people walk through.
    Seam = a Line, or explicit candidate `points` (e.g. a depth contour)."""
    h, w = clean.shape[:2]
    g = cv2.GaussianBlur(cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    if points is not None:
        crossing = np.sqrt(gx * gx + gy * gy)            # no single direction for a curved seam
        m = half + 2
        pts = points[(points[:, 0] >= m) & (points[:, 0] < w - m) & (points[:, 1] >= m) & (points[:, 1] < h - m)]
        if avoid is not None:
            crossing = crossing * (1 - np.clip(avoid * 4, 0, 1))
    else:
        t = np.array([line.x1 - line.x0, line.y1 - line.y0], np.float32)
        t /= np.linalg.norm(t) + 1e-9
        crossing = np.abs(gx * t[0] + gy * t[1])        # gradient along the line = edge across it
        if avoid is not None:
            crossing = crossing * (1 - np.clip(avoid * 4, 0, 1))
        d = np.abs(line.signed_distance(w, h))
        crossing = crossing * (d < half / 3)
        pts = line.sample_points(w, h, 4, margin=half + 2)
    if len(pts) == 0:
        return np.zeros((0, 2), np.float32)
    score = np.array([crossing[int(y) - half:int(y) + half, int(x) - half:int(x) + half].mean() for x, y in pts])
    chosen: list[np.ndarray] = []
    for i in np.argsort(-score):
        p = pts[i]
        if all(np.linalg.norm(p - q) > 2.2 * half for q in chosen):
            chosen.append(p)
        if len(chosen) == k:
            break
    return np.array(chosen)


def seam_still(clean: np.ndarray, restyled: np.ndarray, line: Line | None = None,
               mask: np.ndarray | None = None) -> np.ndarray:
    """Hard cut at the seam: real on one side, restyled on the other (no people).
    Seam = a Line, or a boolean `mask` of the restyled region."""
    if mask is None:
        mask = line.signed_distance(clean.shape[1], clean.shape[0]) >= 0
    return np.where(mask[..., None], restyled, clean)


def seam_crops(clean: np.ndarray, before: np.ndarray, after: np.ndarray, line: Line | None,
               k: int = 3, half: int | None = None, zoom: int = 4, avoid: np.ndarray | None = None,
               mask: np.ndarray | None = None, points: np.ndarray | None = None) -> np.ndarray:
    """Two rows (before / after alignment) of k zoomed crops centred on the seam: real clean plate
    on one side, restyled plate on the other; a misalignment shows as a jump. Red ticks mark a
    straight line; for a depth seam pass `mask` + candidate `points` instead."""
    h, w = clean.shape[:2]
    half = half if half is not None else int(round(36 * max(1.0, w / 768)))
    sb, sa = seam_still(clean, before, line, mask), seam_still(clean, after, line, mask)
    pts = pick_seam_points(clean, line, k, half, avoid, points)
    if len(pts) == 0:
        return np.full((60, 400, 3), 255, np.uint8)
    gap = 12
    rows = []
    for im in (sb, sa):
        tiles = []
        for x, y in pts:
            x0, y0 = int(round(x)) - half, int(round(y)) - half
            c = cv2.resize(im[y0:y0 + 2 * half, x0:x0 + 2 * half], None, fx=zoom, fy=zoom,
                           interpolation=cv2.INTER_NEAREST)
            bars = []
            for yy in (y0, y0 + 2 * half):          # red tick where the line enters / leaves the crop
                bar = np.full((12, c.shape[1], 3), 255, np.uint8)
                if line is not None and abs(line.y1 - line.y0) > 1e-6:   # ticks: straight lines only
                    xx = line.x0 + (yy - line.y0) * (line.x1 - line.x0) / (line.y1 - line.y0)
                    tx = int(round((xx - x0) * zoom))
                    cv2.line(bar, (tx, 0), (tx, 11), (0, 0, 255), 3)
                bars.append(bar)
            tiles.append(np.vstack([bars[0], c, bars[1]]))
        row = tiles[0]
        for t_ in tiles[1:]:
            row = np.hstack([row, np.full((row.shape[0], gap, 3), 255, np.uint8), t_])
        rows.append(row)
    out = []
    for name, row in zip(("before alignment", "after alignment"), rows):
        hdr = np.full((44, row.shape[1], 3), 255, np.uint8)
        cv2.putText(hdr, name, (6, 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv2.LINE_AA)
        out += [hdr, row, np.full((gap, row.shape[1], 3), 255, np.uint8)]
    return np.vstack(out[:-1])


def checkin_figure(path: str, frame, clean, restyled_aligned, crops, composite_img, title: str,
                   caption: str, panel_c: tuple[np.ndarray, str] | None = None,
                   composite_title: str = "(e) composite: real | restyled") -> None:
    rgb = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    fig = plt.figure(figsize=(15, 10))
    outer = fig.add_gridspec(2, 1, height_ratios=[1, 1.25])
    top = outer[0].subgridspec(1, 3)
    bot = outer[1].subgridspec(1, 2, width_ratios=[1.0, 1.25])
    panels = [(top[0, 0], frame, "(a) one filmed frame"),
              (top[0, 1], clean, "(b) clean plate (per-pixel median)"),
              (top[0, 2], *(panel_c if panel_c is not None else (restyled_aligned, "(c) restyled once, re-aligned"))),
              (bot[0, 0], crops, "(d) seam zoom: edges crossing the seam"),
              (bot[0, 1], composite_img, composite_title)]
    for spec, im, t in panels:
        ax = fig.add_subplot(spec)
        ax.imshow(rgb(im))
        ax.set_title(t, fontsize=12, loc="left")
        ax.axis("off")
    fig.suptitle(title, fontsize=15, x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.005, caption, fontsize=10, ha="left", va="bottom", family="monospace")
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(path, dpi=130)
    plt.close(fig)
