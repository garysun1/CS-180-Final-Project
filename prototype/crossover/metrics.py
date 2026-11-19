"""Evaluation.

Seam drift: if the restyled plate is misaligned, an edge crossing the line visibly jumps. We measure
the jump directly: in patches centred on the line we phase-correlate the clean plate against the
restyled plate (on gradient magnitude, which survives restyling) and report |displacement| in px.

True residual: when we injected a known perturbation we can compute the exact remaining error at
the same seam points - used to check that the seam metric itself can be trusted.

People round-trip: composite the people back onto the *unedited* clean plate; the result should
reproduce the original footage. Errors show where masks / shadow handling are off.
"""
from __future__ import annotations

import cv2
import numpy as np

from .align import AlignResult, grad_mag
from .line import Line
from .perturb import Perturbation


def _stats(v: np.ndarray) -> dict:
    if v.size == 0:
        return {"n": 0, "median": None, "p90": None, "mean": None, "max": None}
    return {"n": int(v.size), "median": round(float(np.median(v)), 3), "p90": round(float(np.percentile(v, 90)), 3),
            "mean": round(float(v.mean()), 3), "max": round(float(v.max()), 3)}


def seam_params(w: int) -> dict:
    """Patch size / stride / smoothing tuned at 768 px wide, scaled with resolution."""
    s = max(1.0, w / 768)
    patch = int(round(96 * s / 2)) * 2
    return {"patch": patch, "stride": int(round(32 * s)), "sigma": 2.0 * s}


def seam_points(line: Line, w: int, h: int, patch: int, stride: int) -> np.ndarray:
    return line.sample_points(w, h, stride, margin=patch / 2 + 1)


def seam_drift(clean: np.ndarray, restyled: np.ndarray, line: Line | None, min_energy: float = 0.12,
               min_response: float = 0.15, min_kept_frac: float = 0.6, points: np.ndarray | None = None) -> dict:
    """Edge jump at the line, in px. Patches whose phase-correlation peak is weak (response <
    min_response) are discarded: at zero true drift those are exactly the ones that report garbage
    (posterized / redrawn edges that do not exist in the original). If too few textured patches
    survive, the number is flagged unreliable."""
    h, w = clean.shape[:2]
    prm = seam_params(w)
    patch, stride = prm["patch"], prm["stride"]
    gc, gr = grad_mag(clean, prm["sigma"]), grad_mag(restyled, prm["sigma"])
    hann = cv2.createHanningWindow((patch, patch), cv2.CV_32F)
    pts = seam_points(line, w, h, patch, stride) if points is None else _inside(points, w, h, patch / 2 + 1)
    mags, kept, n_textured = [], [], 0
    r = patch // 2
    for x, y in pts:
        x0, y0 = int(round(x)) - r, int(round(y)) - r
        pc = gc[y0:y0 + patch, x0:x0 + patch]
        pr = gr[y0:y0 + patch, x0:x0 + patch]
        if pc.mean() < min_energy:
            continue  # flat patch (sky, lawn): no edges to jump
        n_textured += 1
        (dx, dy), resp = cv2.phaseCorrelate(pc, pr, hann)
        if resp < min_response:
            continue
        mags.append(float(np.hypot(dx, dy)))
        kept.append([round(float(x), 1), round(float(y), 1), round(float(dx), 3), round(float(dy), 3), round(float(resp), 3)])
    out = _stats(np.array(mags))
    out["n_textured"] = n_textured
    out["reliable"] = bool(n_textured > 0 and len(mags) >= min_kept_frac * n_textured)
    out["patches_xy_dx_dy_resp"] = kept
    return out


def _inside(points: np.ndarray, w: int, h: int, margin: float) -> np.ndarray:
    p = np.asarray(points, np.float32).reshape(-1, 2)
    return p[(p[:, 0] >= margin) & (p[:, 0] < w - margin) & (p[:, 1] >= margin) & (p[:, 1] < h - margin)]


def true_residual(pert: Perturbation, line: Line | None, w: int, h: int, align_res: AlignResult | None = None,
                  points: np.ndarray | None = None) -> dict:
    """Exact geometric error at the seam points: |m(M(p)) - p| (M = identity before alignment)."""
    prm = seam_params(w)
    pts = seam_points(line, w, h, prm["patch"], prm["stride"]) if points is None else \
        _inside(points, w, h, prm["patch"] / 2 + 1)
    px, py = pts[:, 0], pts[:, 1]
    if align_res is not None:
        qx = cv2.remap(align_res.map_x, px.reshape(-1, 1), py.reshape(-1, 1), cv2.INTER_LINEAR).ravel()
        qy = cv2.remap(align_res.map_y, px.reshape(-1, 1), py.reshape(-1, 1), cv2.INTER_LINEAR).ravel()
    else:
        qx, qy = px, py
    mx, my = pert.m(qx, qy)
    return _stats(np.hypot(mx - px, my - py))


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2)
    return float("inf") if mse == 0 else float(10 * np.log10(255.0 ** 2 / mse))


class RoundTrip:
    """Accumulates the people round-trip test over frames."""

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, frame: np.ndarray, recon_shadow: np.ndarray, recon_noshadow: np.ndarray,
            alpha: np.ndarray, ring: np.ndarray):
        diff_s = np.abs(recon_shadow.astype(np.float32) - frame).mean(-1)
        diff_n = np.abs(recon_noshadow.astype(np.float32) - frame).mean(-1)
        inside = alpha > 0.5
        ring = ring & ~inside
        row = {"psnr_shadow": psnr(frame, recon_shadow), "psnr_noshadow": psnr(frame, recon_noshadow)}
        for name, m in (("inside", inside), ("ring", ring), ("outside", ~inside)):
            row[f"mae_{name}_shadow"] = float(diff_s[m].mean()) if m.any() else np.nan
            row[f"mae_{name}_noshadow"] = float(diff_n[m].mean()) if m.any() else np.nan
        self.rows.append(row)

    def summary(self) -> dict:
        if not self.rows:
            return {}
        keys = self.rows[0].keys()
        out = {k: round(float(np.nanmean([r[k] for r in self.rows])), 3) for k in keys}
        out["n_frames"] = len(self.rows)
        return out
