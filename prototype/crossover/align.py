"""Step 3 - re-align the restyled plate to the clean plate.

Image editors nudge geometry, so a building edge would "jump" at the line. We register the restyled
image back onto the clean plate:
  1. global homography from SIFT matches (CLAHE-normalised grey so tone changes matter less),
     robustly fitted with MAGSAC;
  2. fallback / refinement: ECC (enhanced correlation coefficient) on gradient-magnitude images,
     coarse to fine - edges survive restyling better than raw colours do;
  3. optional local warp: dense DIS optical flow on gradient-magnitude images, heavily smoothed
     (confidence-weighted), and only applied in a band around the line where it matters.

Everything is folded into ONE backward map M (output pixel -> restyled pixel), so the restyled
image is resampled exactly once.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .line import Line, band_weight


def clahe_gray(img: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(g)


def grad_mag(img: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Gradient magnitude of the CLAHE grey image, normalised so its 99th percentile is 1."""
    g = clahe_gray(img).astype(np.float32) / 255.0
    if sigma > 0:
        g = cv2.GaussianBlur(g, (0, 0), sigma)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    m = np.sqrt(gx * gx + gy * gy)
    return np.clip(m / (np.percentile(m, 99) + 1e-6), 0, 1.5).astype(np.float32)


@dataclass
class AlignResult:
    map_x: np.ndarray
    map_y: np.ndarray
    H: np.ndarray                      # restyled -> clean homography (global part)
    method: str
    n_matches: int = 0
    n_inliers: int = 0
    ecc_cc: float | None = None
    local_flow_max_px: float = 0.0
    notes: list[str] = field(default_factory=list)

    def apply(self, img: np.ndarray) -> np.ndarray:
        return cv2.remap(img, self.map_x, self.map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def summary(self) -> dict:
        return {"method": self.method, "n_matches": self.n_matches, "n_inliers": self.n_inliers,
                "ecc_cc": self.ecc_cc, "local_flow_max_px": round(self.local_flow_max_px, 3),
                "H": np.round(self.H, 6).tolist(), "notes": self.notes}


def sift_homography(src: np.ndarray, dst: np.ndarray, ratio: float = 0.75, reproj_px: float = 2.0):
    """Homography mapping src pixels -> dst pixels. Returns (H or None, n_matches, n_inliers)."""
    sift = cv2.SIFT_create(nfeatures=10000)
    k1, d1 = sift.detectAndCompute(clahe_gray(src), None)
    k2, d2 = sift.detectAndCompute(clahe_gray(dst), None)
    if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
        return None, 0, 0
    knn = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    good = [p[0] for p in knn if len(p) == 2 and p[0].distance < ratio * p[1].distance]
    if len(good) < 8:
        return None, len(good), 0
    sp = np.float32([k1[m.queryIdx].pt for m in good])
    dp = np.float32([k2[m.trainIdx].pt for m in good])
    H, inl = cv2.findHomography(sp, dp, cv2.USAC_MAGSAC, reproj_px, maxIters=10000, confidence=0.9999)
    if H is None:
        return None, len(good), 0
    return H, len(good), int(inl.sum())


def ecc_homography(src: np.ndarray, dst: np.ndarray, H_init: np.ndarray | None = None,
                   levels: int = 3, iters: int = 200, eps: float = 1e-6):
    """Refine a src->dst homography with coarse-to-fine ECC on gradient magnitude.

    cv2.findTransformECC finds W with src(W x) ~ dst(x), i.e. W maps dst coords -> src coords,
    which is the inverse of what we return. Returns (H src->dst, correlation) or (H_init, None).
    """
    T = grad_mag(dst, sigma=1.5)
    I = grad_mag(src, sigma=1.5)
    pT, pI = [T], [I]
    for _ in range(levels - 1):
        pT.append(cv2.pyrDown(pT[-1]))
        pI.append(cv2.pyrDown(pI[-1]))
    W = np.linalg.inv(H_init) if H_init is not None else np.eye(3)
    W = W / W[2, 2]
    s = 2.0 ** (levels - 1)
    S = np.diag([1 / s, 1 / s, 1.0])
    W = S @ W @ np.linalg.inv(S)
    up = np.diag([2.0, 2.0, 1.0])
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, iters, eps)
    cc = None
    try:
        for lvl in range(levels - 1, -1, -1):
            cc, Wf = cv2.findTransformECC(pT[lvl], pI[lvl], W.astype(np.float32),
                                          cv2.MOTION_HOMOGRAPHY, crit, None, 5)
            W = Wf.astype(np.float64)
            if lvl > 0:
                W = up @ W @ np.linalg.inv(up)
    except cv2.error:
        return H_init, None
    H = np.linalg.inv(W)
    return H / H[2, 2], float(cc)


def local_flow(clean: np.ndarray, aligned: np.ndarray, weight: np.ndarray,
               sigma_frac: float = 0.03, max_px: float = 8.0) -> np.ndarray:
    """Smooth residual flow f with clean(p) ~ aligned(p + f(p)), multiplied by `weight`."""
    a = clean_gm = grad_mag(clean, sigma=1.0)
    b = grad_mag(aligned, sigma=1.0)
    to8 = lambda x: np.clip(x * 170, 0, 255).astype(np.uint8)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    flow = dis.calc(to8(a), to8(b), None)
    conf = cv2.GaussianBlur(clean_gm, (0, 0), 2.0) + 1e-3
    sigma = sigma_frac * clean.shape[1]
    num = cv2.GaussianBlur(flow * conf[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(conf, (0, 0), sigma)[..., None]
    f = num / den
    mag = np.linalg.norm(f, axis=-1, keepdims=True)
    f = f * np.minimum(1.0, max_px / (mag + 1e-6))
    return (f * weight[..., None]).astype(np.float32)


def _maps_from(H_inv: np.ndarray, w: int, h: int, flow: np.ndarray | None):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    if flow is not None:
        xs = xs + flow[..., 0]
        ys = ys + flow[..., 1]
    P = np.stack([xs, ys, np.ones_like(xs)], -1) @ H_inv.T
    return (P[..., 0] / P[..., 2]).astype(np.float32), (P[..., 1] / P[..., 2]).astype(np.float32)


def corner_shift(H: np.ndarray, w: int, h: int) -> float:
    """Largest displacement (px) of an image corner under H - a sanity check on the estimate."""
    c = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    return float(np.linalg.norm(cv2.perspectiveTransform(c, H) - c, axis=-1).max())


def align(restyled: np.ndarray, clean: np.ndarray, method: str = "auto", local_warp: bool = False,
          line: Line | None = None, band_frac: float = 0.15, min_inliers: int = 60,
          max_corner_frac: float = 0.08, min_ncc_for_local: float = 0.6,
          band: np.ndarray | None = None) -> AlignResult:
    """method:
      'auto'     - SIFT homography; if it has too few inliers (big style gap) fall back to ECC,
                   started from identity (editors only drift a few px) and from the SIFT guess,
                   keeping the start with the best ECC correlation;
      'sift', 'ecc', 'sift+ecc' (ECC refining SIFT), 'none'.
    Any estimate that moves a corner by more than max_corner_frac * width is rejected as implausible.
    The local warp acts near the seam: a band around `line`, or an explicit `band` weight map.
    """
    h, w = clean.shape[:2]
    notes: list[str] = []
    H, nm, ni, cc = np.eye(3), 0, 0, None
    used = "none"
    plausible = lambda M: M is not None and corner_shift(M, w, h) <= max_corner_frac * w
    Hs = None
    if method in ("auto", "sift", "sift+ecc"):
        Hs, nm, ni = sift_homography(restyled, clean)
        if Hs is None:
            notes.append("SIFT found no homography")
        elif not plausible(Hs):
            notes.append(f"SIFT homography implausible (corner shift {corner_shift(Hs, w, h):.1f}px); discarded")
            Hs = None
    if method == "sift" and Hs is not None:
        H, used = Hs, "sift"
    elif method == "sift+ecc":
        He, cc = ecc_homography(restyled, clean, Hs)
        if cc is not None and plausible(He):
            H, used = He, ("sift+ecc" if Hs is not None else "ecc")
        elif Hs is not None:
            H, used = Hs, "sift"
    elif method == "ecc" or (method == "auto" and (Hs is None or ni < min_inliers)):
        if method == "auto":
            notes.append(f"SIFT inliers {ni} < {min_inliers}: falling back to ECC")
        best = None
        for init in ([None] + ([Hs] if Hs is not None else [])):
            He, c = ecc_homography(restyled, clean, init)
            if c is not None and plausible(He) and (best is None or c > best[1]):
                best = (He, c, "identity" if init is None else "sift")
        if best is not None:
            H, cc, used = best[0], best[1], f"ecc(init={best[2]})"
        else:
            notes.append("ECC failed from every start; using identity")
    elif method == "auto":
        H, used = Hs, "sift"

    # Self-check: never do worse than not warping at all. With few matches (a generated restyle that
    # changed lots of content) ECC can lock onto the wrong structure while ControlNet has already kept
    # the geometry; keep the estimate only if image edges agree better with the clean plate.
    if used != "none" and not np.allclose(H, np.eye(3)):
        gc = grad_mag(clean, 1.5)
        ones = np.ones(gc.shape, np.float32)
        n_id = _wncc(gc, grad_mag(restyled, 1.5), ones)
        n_h = _wncc(gc, grad_mag(cv2.warpPerspective(restyled, H, (w, h), flags=cv2.INTER_LINEAR,
                                                     borderMode=cv2.BORDER_REPLICATE), 1.5), ones)
        # real corrections of ~4 px drift gain +0.05 (neon) to +0.49 (century); a noise fit gains ~0.003
        if n_h < n_id + 0.02:
            notes.append(f"global estimate rejected: edge NCC {n_id:.3f} unwarped vs {n_h:.3f} warped")
            H, used = np.eye(3), "none (kept unwarped)"
        else:
            notes.append(f"global estimate kept: edge NCC {n_id:.3f} -> {n_h:.3f}")
    H_inv = np.linalg.inv(H)
    mx, my = _maps_from(H_inv, w, h, None)
    res = AlignResult(mx, my, H, used, nm, ni, cc, 0.0, notes)
    if local_warp:
        if band is not None:
            weight = band                     # e.g. a band around a depth contour
        elif line is not None:
            weight = band_weight(line.signed_distance(w, h), band_frac * w)
        else:
            raise ValueError("local warp needs the seam: a line or a band weight map")
        glob = res.apply(restyled)
        flow = local_flow(clean, glob, weight)
        mx2, my2 = _maps_from(H_inv, w, h, flow)
        loc = cv2.remap(restyled, mx2, my2, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        # Self-check: optical flow assumes both images look alike. Across a big style gap (band edge
        # correlation below min_ncc_for_local) it fits noise - on our 'ink' test it made the true
        # error worse even though correlation rose. So: require a similar-looking pair AND an
        # improvement. (Threshold set from our 5 synthetic cases: 0.78-0.89 helped, 0.42 hurt.)
        gc = grad_mag(clean, 1.5)
        before, after = _wncc(gc, grad_mag(glob, 1.5), weight), _wncc(gc, grad_mag(loc, 1.5), weight)
        if before >= min_ncc_for_local and after > before + 1e-3:
            res.map_x, res.map_y = mx2, my2
            res.local_flow_max_px = float(np.linalg.norm(flow, axis=-1).max())
            res.method = used + "+local"
            notes.append(f"local warp kept (band edge NCC {before:.3f} -> {after:.3f})")
        else:
            notes.append(f"local warp rejected (band edge NCC {before:.3f} -> {after:.3f})")
    return res


def _wncc(a: np.ndarray, b: np.ndarray, wgt: np.ndarray) -> float:
    """Weighted normalised cross-correlation."""
    s = wgt.sum() + 1e-9
    ma, mb = (a * wgt).sum() / s, (b * wgt).sum() / s
    da, db = a - ma, b - mb
    return float((wgt * da * db).sum() / np.sqrt((wgt * da * da).sum() * (wgt * db * db).sum() + 1e-12))
