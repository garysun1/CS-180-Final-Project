"""Colour filters of the empty scene.

Stable Diffusion starts from one of these instead of the raw plate (generate.INIT_FILTER): the filter
gives the colour layout the model would not invent from a green lawn (white snow, dark night, sepia),
and diffusion adds the content (snow texture, lit windows). They are also the first step of each
world's ladder for the Morph seam (morph.py).
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from .video_io import to_float, to_uint8

STYLES = ("night", "century", "painting", "winter", "underwater", "neon", "autumn", "overgrown", "comic")


@lru_cache(maxsize=8)
def _vignette(h: int, w: int, strength: float) -> np.ndarray:
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2
    return (1.0 - strength * np.clip(r2 / 2.0, 0, 1))[..., None]


def _luma(img_f: np.ndarray) -> np.ndarray:
    return img_f[..., 0] * 0.114 + img_f[..., 1] * 0.587 + img_f[..., 2] * 0.299


def night(img: np.ndarray, **_) -> np.ndarray:
    f = to_float(img)
    f = np.power(f, 1.7) * 0.55                       # darken, crush midtones
    y = _luma(f)[..., None]
    f = 0.55 * f + 0.45 * y                           # desaturate (scotopic vision)
    f = f * np.array([1.35, 0.95, 0.70], np.float32)  # BGR: moonlit blue cast
    f = f * _vignette(*img.shape[:2], strength=0.55)
    return to_uint8(f)


@lru_cache(maxsize=4)
def _grain(h: int, w: int, seed: int) -> np.ndarray:
    """Film grain fixed in screen space (fixed seed) - so it is identical on the still and on people."""
    rng = np.random.default_rng(seed)
    return cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 0.7)


def century(img: np.ndarray, seed: int = 0, **_) -> np.ndarray:
    h, w = img.shape[:2]
    f = to_float(img)
    y = _luma(f)
    y = cv2.GaussianBlur(y, (0, 0), 0.6 * max(1.0, w / 768))  # soft old lens
    y = np.clip((y - 0.5) * 1.15 + 0.5, 0, 1)                   # a bit more contrast
    y = np.clip(y + 0.035 * _grain(h, w, seed), 0, 1)
    sepia = np.array([0.62, 0.84, 1.0], np.float32)             # BGR tint
    f = y[..., None] * sepia
    f = 0.06 + 0.88 * f                                         # faded print: lifted blacks
    f = f * _vignette(h, w, strength=0.6)
    return to_uint8(f)


def _quantize(img: np.ndarray, k: int, seed: int = 0, fit_px: int = 60000) -> np.ndarray:
    """Posterize to k colours (k-means fitted on a pixel subsample, so it scales to 4K)."""
    Z = img.reshape(-1, 3).astype(np.float32)
    rng = np.random.default_rng(seed)
    sub = Z[rng.choice(len(Z), size=min(fit_px, len(Z)), replace=False)]
    cv2.setRNGSeed(seed)
    _, _, cen = cv2.kmeans(sub, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5),
                           2, cv2.KMEANS_PP_CENTERS)
    out = np.empty_like(Z)
    for i in range(0, len(Z), 1 << 18):
        z = Z[i:i + (1 << 18)]
        d = ((z[:, None, :] - cen[None]) ** 2).sum(-1)
        out[i:i + len(z)] = cen[d.argmin(1)]
    return out.reshape(img.shape).astype(np.uint8)


def _saturate(img: np.ndarray, factor: float) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * factor, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def _canvas(h: int, w: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 1)
    n = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 0.8)
    weave = 0.5 * (np.sin(np.arange(w)[None, :] * 1.9) + np.sin(np.arange(h)[:, None] * 1.9))
    return (1 + 0.035 * n + 0.02 * weave).astype(np.float32)[..., None]


def painting(img: np.ndarray, seed: int = 0, **_) -> np.ndarray:
    """Gouache-like: edge-preserving smoothing + posterized palette + canvas weave.
    Structure-preserving on purpose - like an edit guided by the image's edges (ControlNet)."""
    d = max(5, int(round(9 * img.shape[1] / 768)))
    out = cv2.bilateralFilter(cv2.bilateralFilter(img, d, 40, 7), d, 40, 7)
    out = _quantize(out, 20, seed)
    out = np.clip(out.astype(np.float32) * _canvas(*img.shape[:2], seed), 0, 255).astype(np.uint8)
    return _saturate(out, 1.3)




def _hsv(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)


# ---- winter: snow on grass and ground, cold light -----------------------------------------
def winter_grade(img: np.ndarray, **_) -> np.ndarray:
    """Cold overcast light: desaturate, cool, slightly brighter and flatter."""
    f = to_float(img)
    y = _luma(f)[..., None]
    f = 0.45 * f + 0.55 * y
    f = np.power(f, 0.9) * np.array([1.10, 1.02, 0.93], np.float32)
    return to_uint8(0.05 + 0.92 * f)


def winter(img: np.ndarray, seed: int = 0, **_) -> np.ndarray:
    h, w = img.shape[:2]
    base = to_float(winter_grade(img))
    hsv = _hsv(img)
    grass = ((hsv[..., 0] > 28) & (hsv[..., 0] < 95) & (hsv[..., 1] > 45)).astype(np.float32)
    ground = ((hsv[..., 1] < 45) & (hsv[..., 2] > 70) & (hsv[..., 2] < 215)).astype(np.float32)
    k = max(1.0, 1.5 * w / 768)
    cover = cv2.GaussianBlur(np.clip(grass * 0.95 + ground * 0.22, 0, 1), (0, 0), k)   # roads: slush
    y = cv2.GaussianBlur(_luma(to_float(img)), (0, 0), 0.8)
    detail = y - cv2.GaussianBlur(y, (0, 0), 6 * k)                  # keep bumps / tyre tracks
    snow = 0.95 + 0.9 * detail
    snow = np.clip(snow, 0.6, 1.0)[..., None] * np.array([1.0, 0.985, 0.96], np.float32)  # cool white
    base = base * (1 - 0.25 * ground[..., None])                                  # wet, darker asphalt
    out = base * (1 - cover[..., None]) + snow * cover[..., None]
    return to_uint8(out * _vignette(h, w, 0.25))


# ---- autumn: green turns to orange and brown, golden light --------------------------------
def autumn_grade(img: np.ndarray, **_) -> np.ndarray:
    """Low golden sun: warm, a little more contrast."""
    f = to_float(img)
    f = np.clip((f - 0.5) * 1.08 + 0.5, 0, 1) * np.array([0.82, 0.96, 1.12], np.float32)
    return to_uint8(f)


def autumn(img: np.ndarray, **_) -> np.ndarray:
    w = img.shape[1]
    hsv = _hsv(img)
    green = ((hsv[..., 0] > 28) & (hsv[..., 0] < 95) & (hsv[..., 1] > 40)).astype(np.float32)
    green = cv2.GaussianBlur(green, (0, 0), max(1.0, 1.5 * w / 768))
    turned = hsv.copy()
    turned[..., 0] = 8 + (hsv[..., 0] - 28) * 0.2                    # green -> orange / rust
    turned[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 255)
    turned = cv2.cvtColor(np.clip(turned, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    mixed = img.astype(np.float32) * (1 - green[..., None]) + turned * green[..., None]
    return autumn_grade(np.clip(mixed, 0, 255).astype(np.uint8))


# ---- overgrown: moss and weeds creeping over everything that is not already green -----------
@lru_cache(maxsize=4)
def _moss_noise(h: int, w: int, seed: int) -> np.ndarray:
    """Blotchy multi-scale noise in [0, 1] (where moss grows)."""
    rng = np.random.default_rng(seed + 21)
    acc = np.zeros((h, w), np.float32)
    for scale, amp in ((48, 1.0), (16, 0.5), (6, 0.25)):
        g = rng.normal(0, 1, (max(2, h // scale), max(2, w // scale))).astype(np.float32)
        acc += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
    acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)
    return acc


def overgrown(img: np.ndarray, seed: int = 0, **_) -> np.ndarray:
    """A colour cue for 'nature took over': moss patches on paved ground and walls, duller light."""
    h, w = img.shape[:2]
    f = to_float(img)
    y = _luma(f)[..., None]
    f = 0.75 * f + 0.25 * y                                           # weathered, duller
    moss = np.clip((_moss_noise(h, w, seed) - 0.45) / 0.2, 0, 1)
    moss = moss * np.linspace(0.6, 1.0, h, dtype=np.float32)[:, None]  # more growth near the camera
    green = np.array([0.18, 0.42, 0.25], np.float32) * (0.6 + 0.8 * y)  # BGR moss, keeps shading
    f = f * (1 - 0.85 * moss[..., None]) + green * (0.85 * moss[..., None])
    return to_uint8(f * 0.92)


# ---- underwater: absorption + haze, like the proposal mock-up ------------------------------
@lru_cache(maxsize=4)
def _depth_ramp(h: int, w: int) -> np.ndarray:
    """0 at the bottom (near the camera) -> 1 at the top (far): stands in for water depth/distance."""
    return np.linspace(1, 0, h, dtype=np.float32)[:, None, None] * np.ones((1, w, 1), np.float32)


def underwater(img: np.ndarray, **_) -> np.ndarray:
    h, w = img.shape[:2]
    f = to_float(img)
    f = f * np.array([1.05, 0.88, 0.42], np.float32)            # water eats red first
    T = 0.78 - 0.45 * _depth_ramp(h, w)                          # transmission falls with distance
    water = np.array([0.42, 0.33, 0.05], np.float32)             # teal veil (BGR)
    f = f * T + water * (1 - T)
    return to_uint8(f * _vignette(h, w, 0.5))


# ---- thermal: the world is cold, people are hot ---------------------------------------------






# ---- neon: dark synthwave night + glowing outlines ---------------------------------------------
def neon_grade(img: np.ndarray, **_) -> np.ndarray:
    f = to_float(img)
    y = _luma(f)[..., None]
    dark = np.power(y, 1.5) * 0.55
    teal, magenta = np.array([0.95, 0.75, 0.15], np.float32), np.array([0.95, 0.25, 0.95], np.float32)
    return to_uint8(dark * (teal * (1 - y) + magenta * y) * 1.4 + 0.02)


def neon(img: np.ndarray, **_) -> np.ndarray:
    w = img.shape[1]
    s = max(1.0, w / 768)
    base = to_float(neon_grade(img))
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 1.2 * s)
    e = cv2.Canny(g, 40, 110).astype(np.float32) / 255
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    horiz = (np.abs(gy) > np.abs(gx)).astype(np.float32)          # edge runs horizontally
    cyan, pink = np.array([1.0, 0.95, 0.25], np.float32), np.array([0.85, 0.2, 1.0], np.float32)
    col = horiz[..., None] * cyan + (1 - horiz[..., None]) * pink
    core = cv2.GaussianBlur(e, (0, 0), 0.6 * s)[..., None]
    halo = cv2.GaussianBlur(e, (0, 0), 3.0 * s)[..., None]
    glow = np.clip(core * 1.6 + halo * 2.2, 0, 1) * col
    return to_uint8(1 - (1 - base) * (1 - glow))                   # screen blend


# ---- comic: posterised print with a halftone screen and ink lines ----------------------------
@lru_cache(maxsize=4)
def _halftone_screen(h: int, w: int, cell: float) -> np.ndarray:
    """Distance to the nearest dot centre on a 45-degree grid, 0 (centre) .. ~1 (between dots).
    Fixed in screen space, so it is identical on the plate and on people (no flicker)."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xs + ys) / np.sqrt(2), (xs - ys) / np.sqrt(2)
    du, dv = (u % cell) / cell - 0.5, (v % cell) / cell - 0.5
    return np.sqrt(du * du + dv * dv) / 0.7071


def comic_grade(img: np.ndarray, **_) -> np.ndarray:
    """Pixelwise comic print: punchier colour posterised to a few inks, halftone dots in the shadows."""
    h, w = img.shape[:2]
    hsv = _hsv(img)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.6, 0, 255)
    f = to_float(cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR))
    q = np.round(f * 3) / 3                                         # 4 ink levels per channel
    dark = 1 - _luma(f)
    dots = (_halftone_screen(h, w, 5.0 * max(1.0, w / 768)) < np.clip(dark * 1.15 - 0.15, 0, 1)).astype(np.float32)
    out = q * (1 - 0.6 * dots[..., None]) + 0.04
    return to_uint8(out)


def comic(img: np.ndarray, **_) -> np.ndarray:
    s = max(1.0, img.shape[1] / 768)
    out = comic_grade(img)
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 1.4 * s)
    ink = cv2.dilate(cv2.Canny(g, 50, 130), np.ones((2, 2), np.uint8)) > 0
    out[ink] = (20, 18, 22)
    return out






_FUNCS = {"night": night, "century": century, "painting": painting, "winter": winter, "underwater": underwater,
          "neon": neon, "autumn": autumn, "overgrown": overgrown, "comic": comic}


def apply_style(img: np.ndarray, name: str, seed: int = 0) -> np.ndarray:
    if name not in _FUNCS:
        raise ValueError(f"unknown style {name!r}; choose from {STYLES}")
    return _FUNCS[name](img, seed=seed)
