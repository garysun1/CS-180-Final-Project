"""Depth-based split: near stays real, far is restyled (or the reverse).

Depth is estimated ONCE, on the clean plate (Depth Anything V2 Small, ONNX on CPU), so - like the
restyled plate - it cannot flicker. People get ONE style weight each, read from the plate's depth
where their feet touch the ground: a person is as far away as the ground they stand on. A person
walking away from the camera therefore takes on the style gradually.

Depth Anything outputs *relative disparity* (higher = nearer, unknown scale/offset), so we only use
it through quantiles: f = "farness" in [0, 1] after percentile normalisation.
"""
from __future__ import annotations

import os

import cv2
import numpy as np

DEFAULT_MODEL = os.path.join(os.path.dirname(__file__), "..", "models", "depth_anything_v2_vits.onnx")
_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)


# ------------------------------------------------------------------------------- estimation
def estimate_disparity(img: np.ndarray, model_path: str = DEFAULT_MODEL) -> np.ndarray:
    """Relative disparity (higher = nearer), HxW float32, same size as img (BGR uint8)."""
    import onnxruntime as ort  # optional dependency, only needed for depth mode

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"{model_path} - run scripts/fetch_depth_model.sh")
    h, w = img.shape[:2]
    x = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = cv2.resize(x, (518, 518), interpolation=cv2.INTER_CUBIC)       # as the reference does
    x = ((x - _MEAN) / _STD).transpose(2, 0, 1)[None].astype(np.float32)
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0]
    disp = np.squeeze(out).astype(np.float32)
    return cv2.resize(disp, (w, h), interpolation=cv2.INTER_CUBIC)


def refine(disp: np.ndarray, guide: np.ndarray, radius: int | None = None, eps: float = 1e-3) -> np.ndarray:
    """Edge-aware refinement: guided filter with the clean plate as guide, so depth edges snap to
    image edges (the network output is computed at 518 px and is soft at object boundaries)."""
    r = radius if radius is not None else max(4, int(round(8 * guide.shape[1] / 768)))
    lo, hi = np.percentile(disp, [1, 99])
    d = np.clip((disp - lo) / (hi - lo + 1e-6), 0, 1).astype(np.float32)
    g = guide.astype(np.float32) / 255.0
    out = cv2.ximgproc.guidedFilter(g, d, r, eps)
    return out * (hi - lo) + lo


def farness(disp: np.ndarray) -> np.ndarray:
    """Percentile-normalised far-ness in [0,1]: 0 = nearest (p98 disparity), 1 = farthest (p2)."""
    lo, hi = np.percentile(disp, [2, 98])
    return np.clip((hi - disp) / (hi - lo + 1e-6), 0, 1).astype(np.float32)


def load_depth(path: str, size: tuple[int, int], kind: str = "disparity") -> np.ndarray:
    """External depth (.npy or 8/16-bit .png). kind='disparity' (near = high) or 'depth' (near = low).
    Returned as disparity-like (near = high), resized to size=(w, h)."""
    if path.endswith(".npy"):
        d = np.load(path).astype(np.float32)
    else:
        d = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if d is None:
            raise FileNotFoundError(path)
        if d.ndim == 3:
            d = d[..., 0]
        d = d.astype(np.float32)
    d = cv2.resize(d, size, interpolation=cv2.INTER_LINEAR)
    return -d if kind == "depth" else d


def depth_vis(f: np.ndarray, contour_level: float | None = None) -> np.ndarray:
    """Colour-mapped farness (bright = near), optional white contour at the split level."""
    vis = cv2.applyColorMap(((1 - f) * 255).astype(np.uint8), cv2.COLORMAP_MAGMA)
    if contour_level is not None:
        m = (f >= contour_level).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(vis, cs, -1, (255, 255, 255), max(1, f.shape[1] // 400), cv2.LINE_AA)
    return vis


# ------------------------------------------------------------------------------- the split
def smoothstep(x: np.ndarray) -> np.ndarray:
    t = np.clip(x, 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


class _Track:
    __slots__ = ("cx", "cy", "f", "last", "raw_prev", "ema_prev")

    def __init__(self, cx, cy, f, t):
        self.cx, self.cy, self.f, self.last = cx, cy, f, t
        self.raw_prev, self.ema_prev = f, f


class DepthSplit:
    """Per-pixel restyle weight from depth.

    background:  w_bg = smoothstep((f - tau)/band + 1/2)     (f = farness of the clean plate)
    person k:    w_k  = same mapping at f(feet of k), smoothed over time by a tiny tracker
    final:       w    = a * W_person + (1 - a) * w_bg
    """

    def __init__(self, f: np.ndarray, split: float = 0.5, band: float = 0.08, near: bool = False,
                 ema: float = 0.35, min_area_frac: float = 3e-4):
        self.f = f
        self.h, self.w = f.shape
        self.s = self.w / 768.0
        # 'split' = fraction of the image restyled: the farthest `split` (or the nearest, if near)
        self.base_tau = float(np.quantile(f, split if near else 1 - split))
        self.tau = self.base_tau
        self.band, self.near, self.ema = band, near, ema
        self.min_area = min_area_frac * self.h * self.w
        self.tracks: list[_Track] = []
        self.dilate_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(3 * self.s) + 1,) * 2)
        self.match_r = 40 * self.s
        self.stats = {"flicker_raw": [], "flicker_ema": [], "height_px": [], "disp_feet": []}

    def set_shift(self, shift: float) -> None:
        """Move the threshold (for --sweep), in farness units."""
        self.tau = float(np.clip(self.base_tau + shift, 0.0, 1.0))

    def weight_of(self, f) -> np.ndarray:
        x = (np.asarray(f, np.float32) - self.tau) / self.band + 0.5
        w = smoothstep(x)
        return 1 - w if self.near else w

    def background_weight(self) -> np.ndarray:
        return self.weight_of(self.f)

    def contour_distance(self) -> np.ndarray:
        """First-order signed pixel distance to the tau-contour, (f - tau)/|grad f| (for glow)."""
        gx = cv2.Sobel(self.f, cv2.CV_32F, 1, 0, ksize=3) / 8
        gy = cv2.Sobel(self.f, cv2.CV_32F, 0, 1, ksize=3) / 8
        g = np.sqrt(gx * gx + gy * gy) + 1e-4
        d = (self.f - self.tau) / g
        return np.clip(-d if self.near else d, -50, 50).astype(np.float32)

    def foot_farness(self, comp_mask: np.ndarray, x0: int, y0: int, bw: int, bh: int) -> tuple[float, float, float]:
        """(farness at the feet, foot x, foot y). Feet = median x of the bottom 8% rows of the blob;
        farness = median of the plate's f in a small window just below the lowest point."""
        rows = max(2, int(0.08 * bh))
        sub = comp_mask[y0 + bh - rows:y0 + bh, x0:x0 + bw]
        ys, xs = np.nonzero(sub)
        fx = x0 + float(np.median(xs)) if len(xs) else x0 + bw / 2
        fy = float(y0 + bh - 1)
        r = max(2, int(3 * self.s))
        ya, yb = int(min(self.h - 1, fy)), int(min(self.h, fy + 2 * r + 1))
        xa, xb = int(max(0, fx - r)), int(min(self.w, fx + r + 1))
        patch = self.f[ya:yb, xa:xb]
        return float(np.median(patch)) if patch.size else float(self.f[int(fy), int(fx)]), fx, fy

    def person_weights(self, alpha: np.ndarray, t: int, disp: np.ndarray | None = None) -> np.ndarray:
        """W_person map (HxW, value only meaningful where alpha > 0)."""
        binm = (alpha > 0.5).astype(np.uint8)
        n, lab, st, cen = cv2.connectedComponentsWithStats(binm, connectivity=8)
        W = np.zeros((self.h, self.w), np.float32)
        new_tracks: list[_Track] = []
        used = set()
        for k in range(1, n):
            x0, y0, bw, bh, area = st[k]
            if area < self.min_area:
                continue
            comp = (lab == k).astype(np.uint8)
            f_raw, fx, fy = self.foot_farness(comp, x0, y0, bw, bh)
            # match to an existing track (nearest centroid within radius, each track used once)
            cx, cy = cen[k]
            best, bd = None, self.match_r
            for i, tr in enumerate(self.tracks):
                d = np.hypot(tr.cx - cx, tr.cy - cy)
                if i not in used and d < bd:
                    best, bd = i, d
            if best is not None:
                used.add(best)
                tr = self.tracks[best]
                f_s = (1 - self.ema) * tr.f + self.ema * f_raw
                self.stats["flicker_raw"].append(abs(float(self.weight_of(f_raw)) - float(self.weight_of(tr.raw_prev))))
                self.stats["flicker_ema"].append(abs(float(self.weight_of(f_s)) - float(self.weight_of(tr.ema_prev))))
                tr.cx, tr.cy, tr.f, tr.last, tr.raw_prev, tr.ema_prev = cx, cy, f_s, t, f_raw, f_s
            else:
                tr = _Track(cx, cy, f_raw, t)
            new_tracks.append(tr)
            region = cv2.dilate(comp, self.dilate_k).astype(bool)
            W[region] = float(self.weight_of(tr.f))
            if disp is not None and y0 > 2 and y0 + bh < self.h - 2:   # skip people cut by the border
                self.stats["height_px"].append(float(bh))
                self.stats["disp_feet"].append(float(disp[int(fy), int(np.clip(fx, 0, self.w - 1))]))
        self.tracks = new_tracks
        return W

    def weight(self, alpha: np.ndarray, t: int, disp: np.ndarray | None = None) -> np.ndarray:
        wb = self.background_weight()
        wp = self.person_weights(alpha, t, disp)
        return (alpha * wp + (1 - alpha) * wb).astype(np.float32)

    def summary(self) -> dict:
        s = self.stats
        out = {"tau": round(self.base_tau, 4), "band": self.band, "near_restyled": self.near, "ema": self.ema}
        if s["flicker_raw"]:
            out["person_weight_flicker_raw"] = round(float(np.mean(s["flicker_raw"])), 4)
            out["person_weight_flicker_ema"] = round(float(np.mean(s["flicker_ema"])), 4)
        if len(s["height_px"]) > 10:
            h, d = np.array(s["height_px"]), np.array(s["disp_feet"])
            out["height_vs_disparity_pearson_r"] = round(float(np.corrcoef(h, d)[0, 1]), 3)
            out["height_vs_disparity_n"] = int(len(h))
        return out


def contour_points(f: np.ndarray, tau: float, stride: float, margin: float) -> np.ndarray:
    """Points every `stride` px along the tau iso-contour of f (for the seam metric)."""
    h, w = f.shape
    m = (f >= tau).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    pts = []
    for c in cs:
        c = c[:, 0, :].astype(np.float32)
        if len(c) < 3:
            continue
        seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
        for s in np.arange(0, seg[-1], stride):
            i = np.searchsorted(seg, s)
            pts.append(c[min(i, len(c) - 1)])
    pts = np.array(pts, np.float32).reshape(-1, 2)
    keep = ((pts[:, 0] >= margin) & (pts[:, 0] < w - margin) & (pts[:, 1] >= margin) & (pts[:, 1] < h - margin))
    return pts[keep]
