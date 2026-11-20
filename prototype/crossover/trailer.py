"""A ~55 s movie-trailer cut and a 15 s loop: rapid beat-synced cuts, one story, a freeze-scan-flood
signature shot, and a style-glitch climax where a walker flashes through art styles frame by frame.

    python -m crossover.trailer --out out/trailer.mp4
    python -m crossover.trailer --out out/trailer_draft.mp4 --sections drop,title   # quick draft
    python -m crossover.trailer --out out/trailer.mp4 --names "Ada L. · Alan T."    # the end card's names
    python -m crossover.trailer --out out/trailer.mp4 --music track.mp3 --bpm 120   # your own music
    python -m crossover.trailer --edit teaser --size 960x540 --crf 23 --out out/teaser_wide.mp4
    python -m crossover.trailer --edit teaser --size 720x720 --crf 23 --out out/teaser_square.mp4

Every shot length is a whole number of beats (120 BPM = 15 frames at 30 fps), and the synthesized
soundtrack is built on the same grid, so cuts, flashes and hits line up exactly.
Inputs are the outputs of the other scripts (generated worlds, effect renders, clean plates).

The signature shot (section "drop"): she walks to the line, which lights up as she nears it (approach);
time stops for everyone but her (freeze); the frozen frame holds while the line slides back across her
and only she changes (scan); then time restarts, everyone else resuming from where they stopped, and the
world floods out from her feet over the whole plaza (flood).
The teaser is a seamless loop: its last frame is exactly its first.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

import cv2
import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
from scipy import signal
from scipy.io import wavfile

from .composite import ShadowRatio, composite, glow_overlay
from .depth import farness, smoothstep
from .effects import NAMES, FeetTracker, World, blobs, portal_q, portal_weight, screen
from .line import side_weight
from .masks import BgDiffMasker
from .styles import century, comic, ink, neon, sketch, thermal_person
from .video_io import VideoWriter, iter_frames, to_float, to_uint8

W, H, FPS = 960, 540, 30                 # W, H are set from --size before any setup; read at call time
SR = 44100
INK, SEPIA, SEAM = (239, 235, 232), (122, 176, 212), (255, 233, 191)          # BGR
SCAN_LIGHT = (1.0, 0.92, 0.75)                                                # BGR float, the line's cold white
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")


def _font(name: str, family: str, weight: str = "normal") -> str:
    """A bundled font (crossover/assets/fonts, OFL), or DejaVu when the file is missing (with a warning:
    the cards would silently change their look otherwise)."""
    p = os.path.join(FONT_DIR, name)
    if os.path.exists(p):
        return p
    alt = font_manager.findfont(font_manager.FontProperties(family=family, weight=weight))
    print(f"[trailer] warning: {name} is missing from {FONT_DIR}; using {os.path.basename(alt)}", file=sys.stderr)
    return alt


FONT_B = _font("Inter-Black.otf", "DejaVu Sans", "bold")           # titles
FONT_L = _font("Inter-Light.otf", "DejaVu Sans")                   # subtitles, names
FONT_M = _font("JetBrainsMono-Medium.ttf", "DejaVu Sans Mono")     # the URL, labels
FONT_R = FONT_L
OUT = "out"
VTEST = "data/sample/vtest.avi"
CLEAN = f"{OUT}/vtest_century/clean_bg.png"
URL = "https://claude.ai/artifact/BZs9iGmSYMXA7z81XCxDnf"
NAMES_PLACEHOLDER = "[ TEAM NAMES ]"
# her track in vtest (scripts/find_moments.py): start frame, frames, her centroid at the start (58.8 s).
# She walks to the line at x=384, straddles it at 61.2 s (frame 612) and turns back at 62.0 s.
HER = (588, 40, (271.0, 510.0))
LONDON = ("data/clips/crowd04.mp4", f"{OUT}/clips/crowd04/clean_bg.png",
          f"{OUT}/clips/crowd04/run_line_vangogh/restyled_aligned.png")


# ============================================================================ frame helpers
def fit_window(w: int, h: int, crop_x: float = 0.5, crop_y: float = 0.5) -> tuple[int, int, int, int]:
    """The part of a w x h source that fit() keeps, (x0, y0, cw, ch) in source pixels: a band of rows
    (at crop_y) when the source is taller than W:H, a band of columns (at crop_x) when it is wider."""
    if w / h < W / H - 0.01:
        ch = int(round(w * H / W))
        return 0, int((h - ch) * crop_y), w, ch
    if w / h > W / H + 0.01:
        cw = int(round(h * W / H))
        return int((w - cw) * crop_x), 0, cw, h
    return 0, 0, w, h


def fit(img: np.ndarray, crop_y: float = 0.5, crop_x: float = 0.5) -> np.ndarray:
    """Crop to W:H (keeping the band at crop_y or crop_x) and resize to W x H."""
    x0, y0, cw, ch = fit_window(img.shape[1], img.shape[0], crop_x, crop_y)
    img = img[y0:y0 + ch, x0:x0 + cw]
    interp = cv2.INTER_CUBIC if img.shape[1] < W else cv2.INTER_AREA
    return cv2.resize(img, (W, H), interpolation=interp)


def src_to_out(x: float, y: float, src_w: int, src_h: int, crop_x: float = 0.5, crop_y: float = 0.5):
    """Where the source pixel (x, y) lands in fit()'s output, in output pixels (mirrors fit())."""
    x0, y0, cw, ch = fit_window(src_w, src_h, crop_x, crop_y)
    return (x - x0 + 0.5) * W / cw - 0.5, (y - y0 + 0.5) * H / ch - 0.5


def zoom(img: np.ndarray, z: float, cx: float = 0.5, cy: float = 0.5) -> np.ndarray:
    if abs(z - 1) < 1e-3:
        return img
    px, py = cx * W, cy * H
    M = np.float32([[z, 0, px * (1 - z)], [0, z, py * (1 - z)]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def crop_zoom(img: np.ndarray, z: float, cx: float, cy: float) -> np.ndarray:
    """Zoom in by z on the point (cx, cy) (fractions), keeping the window inside the frame."""
    z = max(1.0, z)
    ww, hh = W / z, H / z
    x0 = float(np.clip(cx * W - ww / 2, 0, W - ww))
    y0 = float(np.clip(cy * H - hh / 2, 0, H - hh))
    M = np.float32([[z, 0, -x0 * z], [0, z, -y0 * z]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def rgb_split(img: np.ndarray, px: float) -> np.ndarray:
    if px < 0.5:
        return img
    out = img.copy()
    M1 = np.float32([[1, 0, px], [0, 1, 0]])
    M2 = np.float32([[1, 0, -px], [0, 1, 0]])
    out[..., 2] = cv2.warpAffine(img[..., 2], M1, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
    out[..., 0] = cv2.warpAffine(img[..., 0], M2, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
    return out


def tear(img: np.ndarray, rng: np.random.Generator, n: int, alts=(), shift: int = 40) -> np.ndarray:
    """Horizontal slice glitch: bands shifted sideways, some showing another world."""
    out = img.copy()
    for _ in range(n):
        y0 = int(rng.integers(0, H - 8))
        hh = int(rng.integers(6, 56))
        dx = int(rng.integers(-shift, shift + 1))
        src = alts[int(rng.integers(len(alts)))] if alts and rng.random() < 0.6 else img
        out[y0:y0 + hh] = np.roll(src[y0:y0 + hh], dx, axis=1)
    return out


def flash(img: np.ndarray, amount: float, color=(255, 255, 255)) -> np.ndarray:
    if amount <= 0:
        return img
    return (img * (1 - amount) + np.array(color, np.float32) * amount).astype(np.uint8)


_VIG: dict = {}


def finish(img: np.ndarray, rng: np.random.Generator, bars: bool = True) -> np.ndarray:
    """Letterbox, vignette, film grain."""
    vig = _VIG.get((H, W))
    if vig is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2
        vig = _VIG[(H, W)] = (1 - 0.28 * np.clip(r2 / 2, 0, 1))[..., None]
    f = img.astype(np.float32) * vig + rng.normal(0, 3.2, (H, W, 1)).astype(np.float32)
    out = np.clip(f, 0, 255).astype(np.uint8)
    if bars:
        b = int(round(30 * H / 540))
        out[:b] = 0
        out[-b:] = 0
    return out


def desaturate(img: np.ndarray, k: float) -> np.ndarray:
    g = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(img, 1 - k, g, k, 0)


def drain(img_f: np.ndarray, k) -> np.ndarray:
    """Float desaturation by k (a scalar or a per-pixel HxW map), towards the luma."""
    if np.isscalar(k) and k <= 0:
        return img_f
    g = (img_f[..., 0] * 0.114 + img_f[..., 1] * 0.587 + img_f[..., 2] * 0.299)[..., None]
    k = k[..., None] if not np.isscalar(k) else k
    return img_f + k * (g - img_f)


def line_glow(img_f: np.ndarray, x: float, strength: float = 0.55) -> np.ndarray:
    """Screen the glowing vertical line at column x (source px) over a float image."""
    w = img_f.shape[1]
    d = (np.arange(w, dtype=np.float32) - np.float32(x))[None, :]
    return screen(img_f, glow_overlay(d, 2.0 * w / 768, strength=strength))


def ease(x) -> float:
    return float(smoothstep(np.float32(x)))


def lerp(a: float, b: float, t: float) -> float:
    """a -> b, exact at both ends (so a shot can end exactly where the next one starts)."""
    return a * (1 - t) + b * t


class Reader:
    """Random access into a video by frame index (sequential decode, reopened when seeking back)."""

    _cache: dict = {}

    def __init__(self, path: str):
        self.path = path
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise FileNotFoundError(path)
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
        cap.release()
        self.cap, self.pos, self.last = None, -1, None

    @classmethod
    def get(cls, path):
        if path not in cls._cache:
            cls._cache[path] = Reader(path)
        return cls._cache[path]

    def frame(self, idx: int) -> np.ndarray:
        idx = max(0, idx)
        if self.cap is None or idx < self.pos:
            self.cap = cv2.VideoCapture(self.path)
            self.pos, self.last = -1, None
        while self.pos < idx:
            ok, f = self.cap.read()
            if not ok:
                break
            self.pos, self.last = self.pos + 1, f
        return self.last


# ============================================================================ tracking one walker
def track_walker(video: str, clean, start_frame: int, n: int, target, gate: float = 70.0, pad: int = 12):
    """Follow one walker for n frames: the person blob nearest `target` (a centroid, source px) at
    start_frame, then on each frame the blob nearest the last centroid, if it is within `gate` px
    (otherwise the last mask is kept). Returns a list where src[i] is source frame start_frame + i:
    (frame, alpha of every person, this walker's soft mask, padded bbox (x0, y0, x1, y1)), all in
    source pixels. The frame before start_frame only feeds the masker's temporal clean-up."""
    bg = cv2.imread(clean) if isinstance(clean, str) else clean
    if bg is None:
        raise FileNotFoundError(clean)
    h, w = bg.shape[:2]
    warm = max(0, start_frame - 1)
    frames = (f for k, f in enumerate(iter_frames(video, 1.0, start_frame + n + 1)) if k >= warm)
    cx, cy = target
    prev, src = None, []
    for j, f, a in BgDiffMasker(bg).iter_alphas(frames):
        if warm + j < start_frame:
            continue
        bl = blobs(a, 3e-4 * h * w)
        pick = min(bl, key=lambda b: np.hypot(b[4] - cx, b[5] - cy), default=None)
        if pick is not None and np.hypot(pick[4] - cx, pick[5] - cy) < gate:
            m, cx, cy = pick[0], pick[4], pick[5]
            prev = m
        else:
            m = prev if prev is not None else np.zeros((h, w), np.uint8)
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))
        soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
        ys, xs = np.nonzero(m)
        bbox = (int(max(0, xs.min() - pad)), int(max(0, ys.min() - pad)), int(min(w, xs.max() + pad + 1)),
                int(min(h, ys.max() + pad + 1))) if len(xs) else (0, 0, 1, 1)
        src.append((f, a, soft, bbox))
        if len(src) >= n:
            break
    return src


_TRACKS: dict = {}


def walker(video: str, clean: str, start_frame: int, n: int, target, gate: float = 70.0):
    """track_walker(), cached: the shots of one sequence share one track."""
    key = (video, clean, int(start_frame), int(n), tuple(float(v) for v in target), float(gate))
    if key not in _TRACKS:
        _TRACKS[key] = track_walker(video, clean, start_frame, n, target, gate)
    return _TRACKS[key]


def cam_path(src, crop_x: float, crop_y: float, k: int = 5) -> np.ndarray:
    """A follow-cam: the tracked bbox centres in output fractions (after fit()), box-smoothed over k
    (odd) frames."""
    h, w = src[0][0].shape[:2]
    cen = np.array([src_to_out((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, w, h, crop_x, crop_y) for *_, b in src])
    cen = cen / np.array([W, H], np.float64)
    if k > 1 and len(cen) > 1:
        ker = np.ones(k) / k
        cen = np.stack([np.convolve(np.pad(cen[:, i], k // 2, mode="edge"), ker, "valid") for i in range(2)], 1)
    return cen


def foot_of(soft: np.ndarray) -> tuple[float, float]:
    """(x, y) of a walker's feet: the median x of the bottom rows of their mask, and its bottom row."""
    ys, xs = np.nonzero(soft > 0.5)
    if not len(ys):
        return soft.shape[1] / 2, soft.shape[0] - 1.0
    y1 = ys.max()
    rows = max(2, int(0.08 * (y1 - ys.min() + 1)))
    return float(np.median(xs[ys > y1 - rows])), float(y1)


# ============================================================================ worlds and masks
_WORLDS: dict = {}
_FEEDS: dict = {}


def plate_path(name: str) -> str:
    """The generated plaza plate of a world (out/gen/picks.txt)."""
    picks = dict(line.split() for line in open(f"{OUT}/gen/picks.txt") if line.strip())
    return f"{OUT}/gen/{picks[name]}.png"


def world_obj(name: str, clean: str, plate: str, fps: float = 10.0) -> World:
    key = (name, clean, plate, fps)
    if key not in _WORLDS:
        bg, R = cv2.imread(clean), cv2.imread(plate)
        if bg is None or R is None:
            raise FileNotFoundError(clean if bg is None else plate)
        _WORLDS[key] = World(name, bg, R, fps)
    return _WORLDS[key]


class Feed:
    """Frames [f0, f1] of a video with every person's alpha, cut out against the clean plate."""

    def __init__(self, video: str, clean: str, f0: int, f1: int):
        self.bg = cv2.imread(clean)
        if self.bg is None:
            raise FileNotFoundError(clean)
        warm = max(0, f0 - 1)
        frames = (f for k, f in enumerate(iter_frames(video, 1.0, f1 + 2)) if k >= warm)
        self.items = {}
        for j, f, a in BgDiffMasker(self.bg).iter_alphas(frames):
            if warm + j > f1:
                break
            if warm + j >= f0:
                self.items[warm + j] = (f, a.astype(np.float16))
        self.lo, self.hi = min(self.items), max(self.items)
        self.shadow = ShadowRatio(to_float(self.bg))
        self.ones = np.ones(self.bg.shape[:2], np.float32)

    def get(self, i: int):
        """(frame, F float, alpha, shadow ratio S) of frame i (clamped to the range)."""
        f, a = self.items[int(np.clip(i, self.lo, self.hi))]
        F, a = to_float(f), a.astype(np.float32)
        return f, F, a, self.shadow(F, a)[0]


def feed(video: str, clean: str, t0: float, t1: float) -> Feed:
    fps = Reader.get(video).fps
    key = (video, clean, int(t0 * fps + 1e-6), int(np.ceil(t1 * fps)))
    if key not in _FEEDS:
        _FEEDS[key] = Feed(video, clean, *key[2:])
    return _FEEDS[key]


# ============================================================================ shots
@dataclass
class Shot:
    beats: float
    section: str = ""
    flash_in: bool = False
    rgb_in: bool = False
    bars: bool = True
    name: str = ""
    nf: int = 0                # frames in the cut (set by main(); 0 = beats at 120 BPM)
    t_start: float = 0.0       # where the shot starts in the cut, seconds (set by main())

    def frames(self) -> int:
        return self.nf or int(round(self.beats * 15))

    def setup(self):
        pass

    def render(self, j: int, n: int) -> np.ndarray:
        raise NotImplementedError

    def source(self, n: int):
        """(source path, t0, t1) in source seconds for the edit decision list; None for cards."""
        return None

    def others(self, n: int):
        """(t0, t1) of everyone else when the shot runs them on their own clock (Scan, Flood), else None."""
        return None


@dataclass
class Clip(Shot):
    path: str = ""
    start: float = 0.0
    speed: float = 1.0
    crop_y: float = 0.5
    crop_x: float = 0.5
    z: tuple = (1.0, 1.0)
    center: tuple = (0.5, 0.5)
    line: bool = False
    line_ramp: tuple | None = None     # (t_on, t_full), source s: the line fades in (dark while others cross)
    desat: float = 0.0
    fade_to: str | None = None         # crossfade the footage into this still (people vanish)
    fade_from_black: int = 0

    def line_strength(self, t: float) -> float:
        """The line's glow at source time t (continuous, so it fades in smoothly over held frames)."""
        if self.line_ramp is None:
            return 0.55
        t_on, t_full = self.line_ramp
        return 0.55 * ease((t - t_on) / (t_full - t_on))

    def render(self, j, n):
        r = Reader.get(self.path)
        t = self.start + j / FPS * self.speed
        img = r.frame(int(t * r.fps)).copy()
        if self.fade_to is not None:
            p = float(smoothstep(np.float32((j - 0.25 * n) / (0.6 * n))))
            img = cv2.addWeighted(img, 1 - p, cv2.imread(self.fade_to), p, 0)
        if self.line and self.line_strength(t) > 0:
            img = to_uint8(line_glow(to_float(img), img.shape[1] / 2, self.line_strength(t)))
        img = fit(img, self.crop_y, self.crop_x)
        u = j / max(1, n - 1)
        img = zoom(img, lerp(self.z[0], self.z[1], u), *self.center)
        if self.desat:
            img = desaturate(img, self.desat)
        if self.fade_from_black and j < self.fade_from_black:
            img = (img * (j / self.fade_from_black)).astype(np.uint8)
        return img

    def source(self, n):
        return self.path, self.start, self.start + n / FPS * self.speed


def _text_size(draw, text, font, spacing):
    w = sum(font.getlength(c) for c in text) + spacing * (len(text) - 1)
    bb = draw.textbbox((0, 0), "HG", font=font)
    return w, bb[3] - bb[1], bb[1]


def draw_spaced(img: Image.Image, text: str, size: int, y: int, fill, spacing: float, bold=True,
                font: str | None = None, x: float | None = None):
    """Letter-spaced text with its cap top at y, centred unless x is given. Returns the cap height."""
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font or (FONT_B if bold else FONT_R), size)
    w, h, top = _text_size(d, text, f, spacing)
    x = (img.width - w) / 2 if x is None else x
    for c in text:
        d.text((x, y - top), c, font=f, fill=fill)
        x += f.getlength(c) + spacing
    return h


def fitted_size(text: str, size: int, font: str, spacing_em: float, max_w: float) -> tuple[int, int]:
    """Shrink a font size until the letter-spaced text fits max_w px; (size, cap height)."""
    d = ImageDraw.Draw(Image.new("L", (8, 8)))
    size = max(8, int(round(size)))
    while True:
        tw, th, _ = _text_size(d, text, ImageFont.truetype(font, size), spacing_em * size)
        if tw <= max_w or size <= 9:
            return size, th
        size = int(size * 0.94)


def text_mask(lines, size: float, font: str | None = None, spacing_em: float = 0.03, max_w: float = 0.86,
              gap_em: float = 0.28, cy: float = 0.5) -> np.ndarray:
    """Centred lines of text as a float mask (H x W, 1 = ink), one size for all lines, shrunk so the
    widest line fits max_w * W; the block is centred on the row cy * H."""
    font = font or FONT_B
    size = min(fitted_size(t, size, font, spacing_em, max_w * W)[0] for t in lines)
    _, th = fitted_size(lines[0], size, font, spacing_em, 1e9)
    gap = int(round(gap_em * size))
    total = len(lines) * th + (len(lines) - 1) * gap
    im = Image.new("L", (W, H), 0)
    y = cy * H - total / 2
    for t in lines:
        draw_spaced(im, t, size, int(round(y)), 255, spacing_em * size, font=font)
        y += th + gap
    return np.array(im, np.float32) / 255


@dataclass
class Card(Shot):
    text: str = ""
    size: int = 58
    sub: str | None = None
    title: bool = False
    bars: bool = False

    def setup(self):
        im = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(im)
        while True:                                       # shrink long lines to fit
            font = ImageFont.truetype(FONT_B, self.size)
            spacing = self.size * 0.18
            tw, th, _ = _text_size(d, self.text, font, spacing)
            if tw <= 0.8 * W or self.size <= 20:
                break
            self.size = int(self.size * 0.92)
        sub_h = 0 if not self.sub else 26 + 22
        y = int((H - th - sub_h) / 2)
        if self.title:
            mask = Image.new("L", (W, H), 0)
            draw_spaced(mask, self.text, self.size, y, 255, spacing)
            m = np.array(mask, np.float32)[..., None] / 255
            col = np.where(np.arange(W)[None, :, None] < W // 2, np.array(INK, np.float32), np.array(SEPIA, np.float32))
            arr = (col * m).astype(np.float32)
            xs = np.arange(W, dtype=np.float32) - W / 2
            band = (np.abs(np.arange(H) - (y + th / 2)) < th * 1.05)[:, None].astype(np.float32)
            glow = (np.exp(-(xs / 1.6) ** 2) + 0.35 * np.exp(-(xs / 9) ** 2))[None, :] * band
            arr = arr + glow[..., None] * (np.array(SEAM, np.float32) - arr) * 0.95
            self.base = np.clip(arr, 0, 255).astype(np.uint8)
        else:
            draw_spaced(im, self.text, self.size, y, (232, 235, 239), spacing)
            self.base = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        if self.sub:
            sim = Image.new("RGB", (W, H), (0, 0, 0))
            draw_spaced(sim, self.sub, 22, y + th + 26, (160, 168, 178), 22 * 0.3, bold=False)
            self.base = np.maximum(self.base, cv2.cvtColor(np.array(sim), cv2.COLOR_RGB2BGR))

    def render(self, j, n):
        u = j / max(1, n - 1)
        return zoom(self.base, 1.06 - 0.06 * float(smoothstep(np.float32(u * 1.4))))


def make_qr(text: str, px: int = 6, quiet: int = 2) -> np.ndarray:
    """QR code of `text` as a grayscale image: dark modules on white, `px` pixels per module, and a
    quiet zone of the usual 2 modules plus `quiet` more around the symbol."""
    enc = cv2.QRCodeEncoder.create()
    q = enc.encode(text)
    if q is None or not q.size:
        raise ValueError(f"cannot encode {text!r} as a QR code")
    dark = q < 128
    ys, xs = np.nonzero(dark)
    sym = np.pad(dark[ys.min():ys.max() + 1, xs.min():xs.max() + 1], 2 + quiet, constant_values=False)
    img = np.where(sym, 0, 255).astype(np.uint8)
    return np.repeat(np.repeat(img, px, axis=0), px, axis=1)


@dataclass
class EndCard(Shot):
    """The course line, the team's names, the public URL and a QR code of it."""
    head: str = "CS180/280A · UC BERKELEY · FALL 2026"
    names: str = NAMES_PLACEHOLDER
    url: str = URL
    bars: bool = False

    def setup(self):
        s = min(W / 960, H / 540)
        px = max(5, int(6 * s))                                  # >= 5 px per QR module
        qr = cv2.cvtColor(make_qr(self.url, px), cv2.COLOR_GRAY2BGR)
        qs = qr.shape[0]
        rows = [(self.head, FONT_B, 22 * s, 0.22, (214, 218, 224)),
                (self.names, FONT_L, 34 * s, 0.06, (246, 247, 249)),
                (self.url, FONT_M, 17 * s, 0.0, (178, 186, 196))]
        sized = [(t, f, *fitted_size(t, sz, f, sp, 0.9 * W), sp, c) for t, f, sz, sp, c in rows]
        g1, g2, g3 = round(16 * s), round(30 * s), round(22 * s)
        total = sized[0][3] + g1 + sized[1][3] + g2 + qs + g3 + sized[2][3]
        y = (H - total) // 2
        im = Image.new("RGB", (W, H), (0, 0, 0))
        (t, f, sz, th, sp, c) = sized[0]
        draw_spaced(im, t, sz, y, c, sp * sz, font=f)
        y += th + g1
        (t, f, sz, th, sp, c) = sized[1]
        draw_spaced(im, t, sz, y, c, sp * sz, font=f)
        y += th + g2
        yq = y
        y += qs + g3
        (t, f, sz, th, sp, c) = sized[2]
        draw_spaced(im, t, sz, y, c, sp * sz, font=f)
        base = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        xq = (W - qs) // 2
        base[yq:yq + qs, xq:xq + qs] = qr
        self.base, self.qr_box = base, (xq, yq, qs)

    def render(self, j, n):
        k = min(1.0, (j + 1) / 6)                                 # a short fade in, then still
        return self.base.copy() if k >= 1 else (self.base * k).astype(np.uint8)


@dataclass
class Black(Shot):
    bars: bool = False

    def render(self, j, n):
        return np.zeros((H, W, 3), np.uint8)


@dataclass
class Wave(Shot):
    """The empty scene turning into a generated world as a depth wave from the horizon."""
    clean: str = ""
    plate: str = ""
    disparity: str = ""
    crop_y: float = 0.5

    def setup(self):
        self.B, self.R = cv2.imread(self.clean), cv2.imread(self.plate)
        self.f = farness(np.load(self.disparity))

    def render(self, j, n):
        p = float(smoothstep(np.float32(j / max(1, n - 1) * 1.15)))
        tau = 1.08 - 1.2 * p
        w = smoothstep((self.f - tau) / 0.05 + 0.5)
        img = to_float(self.B) + w[..., None] * (to_float(self.R) - to_float(self.B))
        rim = np.exp(-((self.f - tau) / 0.012) ** 2) * (0.9 * np.sin(np.pi * min(1, p * 1.05)))
        img = screen(img, rim[..., None] * np.array([1.0, 0.95, 0.85], np.float32))
        return zoom(fit(to_uint8(img), self.crop_y), 1.0 + 0.05 * p)

    def source(self, n):
        return self.plate, None, None


# ---------------------------------------------------------------------------- freeze, scan, flood
@dataclass
class _Her(Shot):
    """Shared by the shots that follow her through the plaza (one cached track).

    `others_t` decouples everyone else's clock from hers: the plaza is then composed with her at her
    own time and everyone else at others_t (+ the time elapsed in the shot), her old position filled
    from the clean plate. The trailer sets it to the Freeze's t0, so the world the Freeze stopped stays
    stopped through the Scan, and the Flood restarts it from there."""
    video: str = VTEST
    clean: str = CLEAN
    track: tuple = HER                 # (start frame, frames, her centroid at the start)
    crop_x: float = 0.5
    crop_y: float = 1.0
    others_t: float | None = None      # everyone else's clock, source s (None: hers)
    hole_px: int = 14                  # her zone: her mask dilated this much, then feathered (her faint shadow)

    def _track(self):
        self.fps = Reader.get(self.video).fps
        self.tr = walker(self.video, self.clean, *self.track)
        self.cam = cam_path(self.tr, self.crop_x, self.crop_y)
        self.Bf = to_float(cv2.imread(self.clean))
        self._mattes, self._gone, self._plazas = {}, {}, {}

    def _k(self, t: float) -> int:
        """Index into the track of the source frame shown at source time t (held on threes)."""
        return int(np.clip(int(t * self.fps + 1e-6) - self.track[0], 0, len(self.tr) - 1))

    def _zone(self, soft: np.ndarray) -> np.ndarray:
        """Her mask grown by hole_px and feathered (1 on her and close around her, 0 well away): what is
        moved with her, or filled from the clean plate where she is removed. Nobody else comes within
        40 px of her over the track (scripts/find_moments.py), so nobody else is cut."""
        r = self.hole_px
        m = cv2.dilate((soft > 0.01).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2))
        return cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(0.5, r / 3))

    def _without_her(self, k: int):
        """Track frame k with her removed: (frame float with her zone filled from the clean plate,
        everyone else's alpha)."""
        if k not in self._gone:
            f, alpha, soft, _ = self.tr[k]
            z = self._zone(soft)
            F = to_float(f)
            self._gone[k] = (F + z[..., None] * (self.Bf - F), alpha * (1 - z))
        return self._gone[k]

    def _plaza(self, k: int, ko: int | None = None):
        """The plaza with her at track index k and everyone else at ko (None or k: the filmed frame k):
        (frame uint8, alpha of every person, her soft mask, her padded bbox), as a track entry."""
        if ko is None or ko == k:
            return self._her(k)
        if (k, ko) not in self._plazas:
            f, alpha, soft, bbox = self._her(k)
            Fo, ao = self._without_her(ko)
            z = self._zone(soft)
            F = Fo + z[..., None] * (to_float(f) - Fo)
            self._plazas[(k, ko)] = (to_uint8(F), (ao + z * (alpha - ao)).astype(np.float32), soft, bbox)
        return self._plazas[(k, ko)]

    def _ko(self, t_rel: float, k: int) -> int:
        """Everyone else's track index t_rel source seconds into the shot (k: hers)."""
        return k if self.others_t is None else self._k(self.others_t + t_rel)

    def _her(self, k: int):
        """Track entry k with the alpha cleaned inside her mask: pixels there whose colour matches the
        clean plate (the ground between her legs, which the masker's hole filling closes where she
        touches the frame edge, often in her own shadow, and the grass in her hair's fringe) are
        background again, so they take the world's ground instead of a recoloured patch of grass.
        The test is on chroma (luminance weighted 0.15), so her shadow on the grass still counts as
        ground; her coat, jeans and hair are far from the grass in colour and stay solid."""
        if k not in self._mattes:
            if not hasattr(self, "_plate_lab"):
                self._plate_lab = _lab(cv2.imread(self.clean))
            f, alpha, soft, bbox = self.tr[k]
            d = _lab(f) - self._plate_lab
            dist = np.sqrt((0.15 * d[..., 0]) ** 2 + d[..., 1] ** 2 + d[..., 2] ** 2)
            g = np.clip((dist - 10.0) / 16.0, 0, 1).astype(np.float32)
            self._mattes[k] = (f, alpha * (1 - soft * (1 - g)), soft, bbox)
        return self._mattes[k]


def _lab(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(cv2.GaussianBlur(img, (0, 0), 1.0), cv2.COLOR_BGR2LAB).astype(np.float32)


@dataclass
class Freeze(_Her):
    """Time stops for everyone but her: the plaza holds on t0, drained of 30% of its colour, and she
    keeps walking. out = a_t * F_t + (1 - a_t) * base, a_t = her tracked soft mask only."""
    t0: float = 59.7
    t1: float = 61.2
    desat: float = 0.3
    line: bool = True
    z: tuple = (1.0, 1.03)

    def setup(self):
        self._track()
        k0 = self._k(self.t0)
        base, _ = self._without_her(k0)                                 # her, removed (zone from the plate)
        self.base = to_float(desaturate(to_uint8(base), self.desat))
        self.line_x = self.tr[k0][0].shape[1] / 2
        self.center = tuple(self.cam[max(0, self._k(self.t1) - 1)])  # push in on where she ends up

    def composed(self, j, n) -> np.ndarray:
        """The frame before the zoom: her (live) over the frozen plaza, the line glowing."""
        k = min(self._k(self.t0 + j / FPS), max(self._k(self.t0), self._k(self.t1) - 1))
        f, _, soft, _ = self.tr[k]
        a = soft[..., None]
        img = to_float(f) * a + self.base * (1 - a)
        if self.line:
            img = line_glow(img, self.line_x)
        return fit(to_uint8(img), self.crop_y, self.crop_x)

    def render(self, j, n):
        u = j / max(1, n - 1)
        return zoom(self.composed(j, n), lerp(self.z[0], self.z[1], u), *self.center)

    def source(self, n):
        return self.video, self.t0, self.t1


def person_over(wo: World, F, frame, alpha, S, back, ones) -> np.ndarray:
    """People recoloured into the world wo (its person styler), keyed over the background `back`
    instead of the world's plate: only the people change, with clean edges (composite() with R=back)."""
    return composite(F, back, alpha, S, ones, to_float(wo.styler(frame)), None, Q=wo.Q)


@dataclass
class Scan(_Her):
    """The frame holds at t1; the line slides back across her and only she turns into the world:
    w = side_weight(x - line_x) * her soft mask. Her front part has already crossed. While the line
    moves, a scan light runs over her where it crosses her (it is off when the line rests).
    With others_t (the trailer), everyone else is still where the Freeze stopped them."""
    t1: float = 61.2
    world: str = "winter"
    plate: str = ""                    # the world's plate (default: out/gen/picks.txt)
    line_from: float | None = None     # source px (default: the centre column, where the line stands)
    line_to: float | None = None       # default: her back (left) edge
    move: tuple = (0.1, 0.8)           # the part of the shot the line takes to cross her
    desat: float = 0.3                 # the frozen world stays drained (0 in the teaser)
    light: float = 0.6                 # the scan light's peak strength (screen), on her only
    z: tuple = (1.5, 1.55)

    def setup(self):
        self._track()
        self.k = self._k(self.t1)
        self.ko = self._ko(0.0, self.k)
        f, alpha, soft, bbox = self._plaza(self.k, self.ko)
        self.wo = world_obj(self.world, self.clean, self.plate or plate_path(self.world))
        F = to_float(f)
        ones = np.ones(alpha.shape, np.float32)
        S, _ = ShadowRatio(self.Bf)(F, alpha)
        self.L = drain(F, self.desat * (1 - soft))                    # her in colour, the rest drained
        self.Hw = person_over(self.wo, F, f, alpha, S, drain(self.Bf, self.desat), ones)
        self.soft = soft
        self.xs = np.arange(f.shape[1], dtype=np.float32)
        self.px = f.shape[1] / 768.0
        self.lx0 = f.shape[1] / 2 if self.line_from is None else self.line_from
        self.lx1 = float(bbox[0]) if self.line_to is None else self.line_to
        self.cx, self.cy = self.cam[self.k]

    def progress(self, j, n) -> float:
        """How far the line has moved, 0 (at line_from) to 1 (at line_to), before easing."""
        u = j / max(1, n - 1)
        return (u - self.move[0]) / (self.move[1] - self.move[0])

    def line_at(self, j, n) -> float:
        return self.lx0 + (self.lx1 - self.lx0) * ease(self.progress(j, n))

    def light_at(self, j, n) -> float:
        """The scan light's strength: sin(pi p) while the line moves, exactly 0 while it rests (so the
        last frame is the Flood's first)."""
        p = self.progress(j, n)
        return float(self.light * np.sin(np.pi * p)) if 0 < p < 1 else 0.0

    def weight(self, j, n) -> np.ndarray:
        """Her share of the world per pixel (source px): her pixels on the world side of the line."""
        return side_weight(self.xs - self.line_at(j, n))[None, :] * self.soft

    def composed(self, j, n) -> np.ndarray:
        """The frame before the zoom (fit to W x H)."""
        lx = self.line_at(j, n)
        out = self.L + self.weight(j, n)[..., None] * (self.Hw - self.L)
        s = self.light_at(j, n)
        if s > 0:        # the line lights her up where it crosses her, with an afterglow on her converted side
            d = (self.xs - lx)[None, :]
            g = 0.9 * np.exp(-(d / (5 * self.px)) ** 2) + 0.7 * np.exp(-np.clip(d, 0, None) / (22 * self.px)) * (d >= 0)
            out = screen(out, (s * g * self.soft)[..., None] * np.array(SCAN_LIGHT, np.float32))
        out = line_glow(out, lx)
        return fit(to_uint8(out), self.crop_y, self.crop_x)

    def render(self, j, n):
        u = j / max(1, n - 1)
        return crop_zoom(self.composed(j, n), lerp(self.z[0], self.z[1], u), self.cx, self.cy)

    def source(self, n):
        return self.video, self.t1, self.t1

    def others(self, n):
        """Everyone else's source window (t0, t1), or None when they keep her time."""
        return None if self.others_t is None else (self.others_t, self.others_t)


@dataclass
class Flood(_Her):
    """Time restarts and the world floods out from her feet over the whole plaza: the background
    weight is portal_weight(portal_q(...)) of a ring growing from her feet until it covers the visible
    window, and the squash eases from 0.38 (a ring on the ground) to 1. Everyone else changes when
    the ring reaches their feet (as in effects.run_portal); she is in the world from the first frame.
    With others_t (the trailer), everyone else resumes from where the Freeze stopped them."""
    t2: float = 61.2
    world: str = "winter"
    plate: str = ""
    speed: float = 0.5
    squash: tuple = (0.38, 1.0)
    z: tuple = (1.55, 1.0)
    desat: float = 0.3                 # the frozen world's drain, fading out as time restarts
    line_x: float | None = None        # where the scan left the line (it fades out); default: her back
    cover: float = 0.85                # the ring reaches the farthest visible corner here (fraction)
    ring_color: tuple = (0.75, 0.92, 1.0)

    def setup(self):
        self._track()
        h, w = self.Bf.shape[:2]
        self.wo = world_obj(self.world, self.clean, self.plate or plate_path(self.world))
        self.shadow = ShadowRatio(self.Bf)
        self.ones = np.ones((h, w), np.float32)
        self.k0 = self._k(self.t2)
        n_src = int(np.ceil(self.frames() * self.speed / FPS * self.fps)) + 1
        feet = [foot_of(self.tr[k][2]) for k in range(self.k0, min(len(self.tr), self.k0 + n_src))]
        self.fx = float(np.median([p[0] for p in feet]))              # her feet, about (401, 575)
        self.fy = feet[0][1]
        x0, y0, cw, ch = fit_window(w, h, self.crop_x, self.crop_y)    # the visible window, source px
        # a plain float: a numpy float64 scalar here would promote every frame's maths to float64
        self.r_max = float(max(np.hypot(x - self.fx, (y - self.fy) / self.squash[1])
                               for x in (x0, x0 + cw) for y in (y0, y0 + ch))) / 0.95
        self.lx = float(self.tr[self.k0][3][0]) if self.line_x is None else self.line_x
        self.cx, self.cy = self.cam[self.k0]
        self.tracker = FeetTracker(40.0 * w / 768.0)
        self.dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        self.px = w / 768.0
        self.ring = np.array(self.ring_color, np.float32)

    def ring_at(self, u: float) -> tuple[float, float]:
        """(radius, squash) of the ring at u in [0, 1]: a burst that slows as it reaches the corners."""
        uc = min(1.0, u / self.cover)
        return self.r_max * (1 - (1 - uc) ** 2.2), self.squash[0] + (self.squash[1] - self.squash[0]) * ease(uc)

    def kk(self, j) -> tuple[int, int]:
        """(her track index, everyone else's) at output frame j: both clocks run at the same speed."""
        t = j / FPS * self.speed
        k = self._k(self.t2 + t)
        return k, self._ko(t, k)

    def render(self, j, n):
        u = j / max(1, n - 1)
        f, alpha, soft, _ = self._plaza(*self.kk(j))
        h, w = alpha.shape
        F = to_float(f)
        S, _ = self.shadow(F, alpha)
        r, sq = self.ring_at(u)
        q = portal_q(h, w, self.fx, self.fy, r, sq)
        wb = portal_weight(q) if r >= 1 else np.zeros((h, w), np.float32)
        last = ease((u - 0.9) / 0.1)                         # safety net: everything covered at the end
        if last > 0:
            wb = np.maximum(wb, last)
        # everyone else takes the weight at their feet, smoothed per person (effects.run_portal)
        her = soft > 0.5
        wp = np.zeros((h, w), np.float32)
        items, masks = [], []
        for m, bfx, bfy, _, bcx, bcy in blobs(alpha, 3e-4 * h * w):
            if (her & (m > 0)).sum() > 0.3 * m.sum():
                continue                                      # that is her
            qv = float(q[int(min(bfy, h - 1)), int(np.clip(bfx, 0, w - 1))])
            items.append((bcx, bcy, float(portal_weight(np.float32(qv))) if r >= 1 else 0.0))
            masks.append(m)
        for m, v in zip(masks, self.tracker.update(items)):
            wp[cv2.dilate(m, self.dil).astype(bool)] = max(v, last)
        # her own layer (below) carries her; her matte's fringe follows the ground right behind it
        zone = cv2.dilate((soft > 0.01).astype(np.uint8), self.dil) > 0
        wp[zone] = wb[zone]
        wf = alpha * wp + (1 - alpha) * wb
        kd = self.desat * (1 - ease(u / 0.4))                 # colour returns as time restarts
        L = drain(F, kd * (1 - soft))
        i = (self.t_start + j / FPS) * 10.0                    # the world's animation clock (snow, 10 fps)
        G = self.wo.render(i, F, f, alpha, S, self.ones)
        G = G * (1 - 0.3 * np.exp(-((q - 1) * r / (18 * self.px)) ** 2) * (q < 1))[..., None]
        base = L + wf[..., None] * (G - L)
        # her: already in the world, her edges keyed against the local background (real or world)
        Bk = drain(self.Bf, kd)
        Hw = person_over(self.wo, F, f, alpha, S, Bk + wb[..., None] * (self.wo.Rf - Bk), self.ones)
        front = self.wo.anim.front_layer(i) if self.wo.anim is not None else None
        if front is not None:                                 # snow over her once the flood is there
            rgb, af = front
            Hw = Hw + (af * wb)[..., None] * (rgb - Hw)
        out = base + soft[..., None] * (Hw - base)
        if r >= 1:                                            # the ring's rim glows, behind people
            rim = np.exp(-((q - 1) * r / (4.5 * self.px)) ** 2) * (1 - alpha)
            out = screen(out, np.clip(rim * 0.9, 0, 1)[..., None] * self.ring)
        fade = 1 - ease(j / max(1.0, n / self.beats))          # the scan's line fades over a beat
        if fade > 0:
            out = line_glow(out, self.lx, 0.55 * fade)
        img = fit(to_uint8(out), self.crop_y, self.crop_x)
        return crop_zoom(img, lerp(self.z[0], self.z[1], ease(u / 0.85)), self.cx, self.cy)

    def source(self, n):
        return self.video, self.t2, self.t2 + n / FPS * self.speed

    def others(self, n):
        """Everyone else's source window (t0, t1), or None when they keep her time."""
        return None if self.others_t is None else (self.others_t, self.others_t + n / FPS * self.speed)


@dataclass
class Walk(_Her):
    """The teaser's opening: she walks to the glowing line while the camera eases in on her
    (a follow-crop on her tracked centre, mapped with src_to_out), ending on the scan's framing."""
    t0: float = 59.7
    speed: float = 1.0
    line: bool = True
    z: tuple = (1.0, 1.5)
    bars: bool = False

    def setup(self):
        self._track()

    def centre_at(self, t: float) -> np.ndarray:
        x = float(np.clip(t * self.fps - self.track[0], 0, len(self.cam) - 1))
        k = min(int(x), len(self.cam) - 2)
        return self.cam[k] + (x - k) * (self.cam[k + 1] - self.cam[k])

    def render(self, j, n):
        t = self.t0 + j / FPS * self.speed
        f = self.tr[self._k(t)][0]
        img = to_float(f)
        if self.line:
            img = line_glow(img, f.shape[1] / 2)
        img = fit(to_uint8(img), self.crop_y, self.crop_x)
        u = j / max(1, n - 1)
        cx, cy = self.centre_at(t + self.speed / FPS)        # one frame ahead: the last one meets the scan's
        return crop_zoom(img, lerp(self.z[0], self.z[1], ease(u)), cx, cy)

    def source(self, n):
        return self.video, self.t0, self.t0 + n / FPS * self.speed


# ---------------------------------------------------------------------------- the teaser's other shots
def mono_label(img: np.ndarray, text: str) -> np.ndarray:
    """A small JetBrains Mono label in the bottom-left corner, on a dark chip."""
    s = min(W / 960, H / 540)
    size = max(11, int(round(16 * s)))
    f = ImageFont.truetype(FONT_M, size)
    sp = 0.14 * size
    tw = sum(f.getlength(c) for c in text) + sp * (len(text) - 1)
    pad, m = int(8 * s), int(26 * s)
    x0, y1 = m, H - m
    y0 = y1 - size - 2 * pad
    out = img.copy()
    chip = out[y0:y1, x0:int(x0 + tw + 2 * pad)]
    chip[:] = (chip * 0.45).astype(np.uint8)
    pil = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    cap = _text_size(ImageDraw.Draw(pil), text, f, sp)[1]
    draw_spaced(pil, text, size, y0 + (y1 - y0 - cap) // 2, (240, 242, 245), sp, font=FONT_M, x=x0 + pad)
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


@dataclass
class Verse(Shot):
    """One beat of the full-frame plaza in one world (World.render), with a small mono label."""
    world: str = "night"
    video: str = VTEST
    clean: str = CLEAN
    start: float = 62.0
    span: tuple = (62.0, 66.0)         # the source window the verse shots share (one masking pass)
    label: str = ""
    crop_x: float = 0.5
    crop_y: float = 1.0
    bars: bool = False

    def setup(self):
        self.feed = feed(self.video, self.clean, *self.span)
        self.fps = Reader.get(self.video).fps
        self.wo = world_obj(self.world, self.clean, plate_path(self.world))
        self._cache = {}

    def render(self, j, n):
        i = int((self.start + j / FPS) * self.fps + 1e-6)
        if i not in self._cache:
            f, F, a, S = self.feed.get(i)
            G = self.wo.render((self.t_start + j / FPS) * 10.0, F, f, a, S, self.feed.ones)
            self._cache[i] = mono_label(fit(to_uint8(G), self.crop_y, self.crop_x),
                                        self.label or NAMES.get(self.world, self.world).upper())
        return self._cache[i]

    def source(self, n):
        return self.video, self.start, self.start + n / FPS


@dataclass
class Sweep(Shot):
    """A glowing line slides across the frame (right to left) and uncovers the world on its far side."""
    video: str = LONDON[0]
    clean: str = LONDON[1]
    plate: str = LONDON[2]
    world: str = "vangogh"
    world_fps: float = 29.97
    start: float = 4.6
    span: tuple = (4.6, 9.7)           # shared with the Super that follows
    move: tuple = (0.06, 0.9)
    crop_x: float = 0.5
    crop_y: float = 0.5
    trim: float = 0.022                # the London plate's bottom ~2% is a smeared border: cut before fit()
    bars: bool = False

    def setup(self):
        self.feed = feed(self.video, self.clean, *self.span)
        self.fps = Reader.get(self.video).fps
        self.wo = world_obj(self.world, self.clean, self.plate, self.world_fps)
        h, w = self.feed.bg.shape[:2]
        self.h_keep = h - int(round(self.trim * h))
        self.win = fit_window(w, self.h_keep, self.crop_x, self.crop_y)
        self.xs = np.arange(w, dtype=np.float32)

    def fit_src(self, img: np.ndarray) -> np.ndarray:
        """fit() of a source-size frame, without the trimmed bottom rows."""
        return fit(img[:self.h_keep], self.crop_y, self.crop_x)

    def frame_at(self, j):
        f, F, a, S = self.feed.get(int((self.start + j / FPS) * self.fps + 1e-6))
        return F, self.wo.render(j, F, f, a, S, self.feed.ones)

    def render(self, j, n):
        F, G = self.frame_at(j)
        x0, _, cw, _ = self.win
        p = ease((j / max(1, n - 1) - self.move[0]) / (self.move[1] - self.move[0]))
        lx = x0 + cw * (1.04 - 1.08 * p)                      # from past the right edge to past the left
        w = side_weight(self.xs - lx, feather=3.0 * F.shape[1] / 768)[None, :, None]
        out = line_glow(F + w * (G - F), lx)
        return self.fit_src(to_uint8(out))

    def source(self, n):
        return self.video, self.start, self.start + n / FPS


@dataclass
class Super(Sweep):
    """Knockout title: the letters are windows into the world frame, the filmed frame around them is
    dimmed and drained, and a 35% dark outline separates the two. The second line lands halfway.
    The block sits a little high (the street level of the frame is dark) and the letters' deepest
    shadows are lifted to `floor`, so no letter breaks up."""
    lines: tuple = ("ONE IMAGE.", "EVERY FRAME.")
    size: int = 118
    outline: float = 0.35
    dim: float = 0.26
    drain_out: float = 0.8
    floor: float = 0.22
    cy: float = 0.36
    start: float = 7.6

    def setup(self):
        super().setup()
        full = text_mask(self.lines, self.size, cy=self.cy)
        rows = np.nonzero(full.max(1) > 0)[0]                 # the first line alone, in its final place
        gaps = np.nonzero(np.diff(rows) > 1)[0] if len(rows) else []
        first = full.copy()
        if len(gaps):
            first[rows[gaps[0]] + 1:] = 0
        self.masks = [first, full]

    def render(self, j, n):
        F, G = self.frame_at(j)
        Fo = to_float(self.fit_src(to_uint8(F)))
        Go = to_float(self.fit_src(to_uint8(G)))
        m = self.masks[0 if j < n // 2 else 1]
        u = j / max(1, n - 1)
        m = zoom(m, 1.0 + 0.04 * u, 0.5, self.cy)            # a slow push on the type
        s = min(W / 960, H / 540)
        r = max(2, int(round(7 * s)))
        ring = cv2.GaussianBlur(cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2)),
                                (0, 0), 3.5 * s)
        ring = np.clip(ring - m, 0, 1)
        out = drain(Fo, self.drain_out) * self.dim
        out = out * (1 - self.outline * ring)[..., None]
        out = out + m[..., None] * (self.floor + (1 - self.floor) * Go - out)
        return to_uint8(out)


@dataclass
class LoopTitle(Card):
    """The title card; over its last `fade` beats it dissolves into the first frame of `loop_to`, and
    its last frame is exactly loop_to.render(0, n): the loop point is invisible."""
    loop_to: Shot | None = None
    fade: float = 1.0

    def setup(self):
        super().setup()
        if self.loop_to is not None:
            self.loop_to.setup()
            self.first = self.loop_to.render(0, self.loop_to.frames())

    def render(self, j, n):
        img = super().render(j, n)
        if self.loop_to is None:
            return img
        k = max(1, int(round(self.fade * n / self.beats)))
        if j >= n - 1:
            return self.first.copy()
        if j < n - 1 - k:
            return img
        p = ease((j - (n - 1 - k)) / k)
        return cv2.addWeighted(img, 1 - p, self.first, p, 0)


# ---------------------------------------------------------------------------- the glitch climax
def _pixelate(img):
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(1, w // 6), max(1, h // 6)), interpolation=cv2.INTER_AREA)
    small = (small // 64) * 64 + 32
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def _negative(img):
    hsv = cv2.cvtColor(255 - img, cv2.COLOR_BGR2HSV)
    hsv[..., 0] = (hsv[..., 0].astype(int) + 60) % 180
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def _oil(img):
    return cv2.xphoto.oilPainting(img, 5, 1)


CROP_STYLES = {"comic": comic, "thermal": thermal_person, "neon": neon, "ink": ink, "sketch": sketch,
               "sepia": century, "pixel": _pixelate, "negative": _negative, "oil": _oil}


@dataclass
class Glitch(Shot):
    """One tracked walker flashes through styles, faster and faster; the world tears around them in
    the last two beats. The schedule scales with the shot: a switch every 4 frames for the first
    half, every 2 until two beats from the end, then every frame (with chaos)."""
    video: str = VTEST
    clean: str = ""
    start_frame: int = 640
    target: tuple = (360.0, 453.0)
    worlds: tuple = ("vangogh", "cyberpunk", "1920s", "night", "winter")
    person_styles: tuple = ("comic", "world:vangogh", "thermal", "ink", "world:cyberpunk", "sketch", "pixel",
                            "world:1920s", "neon", "negative", "oil", "sepia", "world:night", "world:winter")
    crop_y: float = 1.0
    crop_x: float = 0.5
    seed: int = 7
    switch_frames: list = field(default_factory=list)
    accents: list = field(default_factory=list)

    def setup(self):
        self.bg = cv2.imread(self.clean)
        h, w = self.bg.shape[:2]
        n = self.frames()
        n_src = int(np.ceil(n / 3)) + 2
        names = set(self.worlds) | {s.split(":")[1] for s in self.person_styles if s.startswith("world:")}
        self.wobj = {k: world_obj(k, self.clean, plate_path(k)) for k in names}
        self.src = walker(self.video, self.clean, self.start_frame, n_src, self.target, gate=70.0)
        self.cam = cam_path(self.src, self.crop_x, self.crop_y, k=7)  # a follow-cam on the walker
        self.shadow = ShadowRatio(to_float(self.bg))
        self.ones = np.ones((h, w), np.float32)
        self._wcache = {}
        two = int(round(2 * n / self.beats))                 # the last two beats
        self.chaos_from = n - two
        sched, k = [], 0
        while k < n:
            sched.append(k)
            k += 4 if k < n // 2 else 2 if k < n - two else 1
        self.switch_frames = sched
        self.accents = list(range(n - two, n))
        rng = np.random.default_rng(self.seed)
        styles, last = [], None
        for _ in sched:
            s = rng.choice([s for s in self.person_styles if s != last])
            styles.append(s)
            last = s
        self.styles = styles
        self.bgworld = {a: self.worlds[int(rng.integers(len(self.worlds)))] for a in self.accents}
        self.rng = rng

    def world_frame(self, si: int, name: str) -> np.ndarray:
        key = (si, name)
        if key not in self._wcache:
            f, a, _, _ = self.src[si]
            F = to_float(f)
            S, _ = self.shadow(F, a)
            self._wcache[key] = to_uint8(self.wobj[name].render(si, F, f, a, S, self.ones))
        return self._wcache[key]

    def person(self, si: int, style: str) -> np.ndarray:
        f, _, _, (x0, y0, x1, y1) = self.src[si]
        if style.startswith("world:"):
            return self.world_frame(si, style.split(":")[1])
        out = f.copy()
        crop = np.ascontiguousarray(f[y0:y1, x0:x1])
        if crop.size:
            out[y0:y1, x0:x1] = CROP_STYLES[style](crop)
        return out

    def render(self, j, n):
        si = min(len(self.src) - 1, j // 3)                 # 10 fps source, held "on threes"
        k = max(0, np.searchsorted(self.switch_frames, j, side="right") - 1)
        style = self.styles[k]
        just = j - self.switch_frames[k]
        f, _, soft, _ = self.src[si]
        base = self.world_frame(si, self.bgworld[j]) if j in self.bgworld else f
        P = self.person(si, style)
        a = soft[..., None]
        img = (base * (1 - a) + P * a).astype(np.uint8)
        # comic ink outline + misregistered colour outlines around the walker
        m = (soft > 0.5).astype(np.uint8)
        edge = cv2.dilate(m, np.ones((5, 5), np.uint8)) - m
        img[edge > 0] = (18, 16, 20)
        if just < 2:
            for dx, col in ((4, (255, 255, 0)), (-4, (255, 0, 255))):
                e2 = np.roll(edge, dx, axis=1) > 0
                img[e2 & (m == 0)] = col
        img = fit(img, self.crop_y, self.crop_x)
        cx, cy = self.cam[si]
        img = crop_zoom(img, 1.9 + 0.5 * j / max(1, n - 1), cx, cy)
        chaos = j >= self.chaos_from
        if chaos:
            alts = [crop_zoom(fit(self.world_frame(si, w), self.crop_y, self.crop_x), 2.2, cx, cy)
                    for w in self.worlds[:3]]
            img = tear(img, self.rng, 7, alts, shift=50)
        img = rgb_split(img, (10 if just == 0 else 5 if just == 1 else 1.5) * (1.5 if chaos else 1))
        if j >= n - 3:
            img = flash(img, (j - (n - 4)) / 3)
        return img

    def source(self, n):
        fps = Reader.get(self.video).fps
        return self.video, self.start_frame / fps, (self.start_frame + int(np.ceil(n / 3))) / fps


# ============================================================================ the edits
def edit(names: str = NAMES_PLACEHOLDER) -> list[Shot]:
    gen = lambda s: f"{OUT}/vtest_gen_{s}/final_matched.mp4"
    lv = f"{OUT}/clips/crowd04/run_line_vangogh/final_matched.mp4"
    bgv = CLEAN
    freeze = Freeze(3, "drop", t0=59.7, t1=61.2, name="freeze")
    # everyone else stays where the freeze stopped them through the scan, and resumes from there
    scan = Scan(3, "drop", t1=61.2, world="winter", others_t=freeze.t0, name="scan")
    shots: list[Shot] = [
        # cold open: the real world
        Clip(6, "cold", path=VTEST, start=20, z=(1.0, 1.08), center=(0.5, 0.55), desat=0.25, fade_from_black=12, name="real plaza"),
        Card(2, "cold", text="EVERY PLACE", name="card"),
        Clip(4, "cold", path=VTEST, start=33, z=(1.06, 1.0), desat=0.25, name="real plaza 2"),
        Card(2, "cold", text="HAS ANOTHER VERSION", name="card"),
        # the trick
        Card(2, "trick", text="THE CAMERA NEVER MOVES", size=50, name="card"),
        Clip(4, "trick", path=VTEST, start=40, fade_to=bgv, desat=0.15, name="people vanish"),
        Card(2, "trick", text="SO WE CHANGE THE WORLD ONCE", size=46, name="card"),
        Wave(4, "trick", clean=bgv, plate=f"{OUT}/gen/winterf_s0_k75.png",
             disparity=f"{OUT}/vtest_depth_century/depth_disparity.npy", name="world arrives"),
        # the drop: she walks to the line, time stops for everyone but her, the line scans back across
        # her and only she changes, then the world floods out from her feet (scripts/find_moments.py).
        # The line lights up only once the red-jacket man is past it (his back edge leaves x=384 at
        # 59.4-59.5 s), at full strength on the approach's last frame, as in the freeze.
        Clip(2, "drop", path=VTEST, start=58.7, line=True, line_ramp=(59.4, 59.65), crop_y=1.0, name="approach"),
        freeze,
        scan,
        Flood(5, "drop", t2=61.2, world="winter", speed=0.5, z=(scan.z[1], 1.0), others_t=freeze.t0, name="flood"),
        # montage
        Card(1, "montage", text="ANY CITY", size=64, name="card"),
        Clip(3, "montage", path=lv, start=3.0, rgb_in=True, name="London Van Gogh"),
        Clip(2, "montage", path=f"{OUT}/fx_crowd04_shards/shards.mp4", start=8.0, name="London shards"),
        Clip(3, "montage", path=f"{OUT}/fx_car_seasons/seasons.mp4", start=17.5, speed=2, z=(1.2, 1.25), name="highway cyberpunk"),
        Card(1, "montage", text="ANY ERA", size=64, name="card"),
        Clip(2, "montage", path=gen("1920s_depth"), start=47, name="1920 far away"),
        Clip(3, "montage", path=f"{OUT}/fx_seasons/seasons.mp4", start=44.5, speed=3, name="seasons wave"),
        Clip(2, "montage", path=gen("1920s"), start=30, z=(1.0, 1.06), name="1920s seam"),
        Card(1, "montage", text="ANY WORLD", size=64, name="card"),
        Clip(2, "montage", path=f"{OUT}/fx_vtest_windows/windows.mp4", start=4.5, name="windows"),
        Clip(2, "montage", path=f"{OUT}/fx_vtest_portal/portal.mp4", start=24, speed=1.5, name="portal"),
        Clip(2, "montage", path=f"{OUT}/fx_trails/trails.mp4", start=36, speed=2, name="trails"),
        Clip(2, "montage", path=f"{OUT}/fx_car_seasons/seasons.mp4", start=2.0, speed=2, z=(1.2, 1.2), name="highway winter"),
        Clip(2, "montage", path=f"{OUT}/fx_vtest_shards/shards.mp4", start=20, speed=1.5, name="plaza shards"),
    ]
    # rapid run: the same moment, a different world every half beat
    rapid = ["night", "vangogh", "cyberpunk", "1920s", "autumn", "underwater", "winter", "vangogh",
             "night", "cyberpunk", "1920s", "vangogh"]
    for k, w in enumerate(rapid):
        shots.append(Clip(0.5, "montage", path=gen(w), start=41.0 + 0.25 * k, rgb_in=True, name=f"flicker {w}"))
    shots += [
        Glitch(12, "glitch", clean=bgv, name="glitch"),
        Clip(6, "resolve", path=lv, start=12.6, speed=0.5, flash_in=True, name="slow crossing"),
        Card(1, "resolve", text="ONE IMAGE.", size=60, name="card"),
        Card(1, "resolve", text="EVERY FRAME.", size=60, name="card"),
        Card(8, "title", text="CROSS THE LINE", size=84, title=True, name="title"),
        EndCard(6, "title", names=names, name="end"),
        Black(2, "title", name="black"),
    ]
    return shots


def edit_teaser() -> list[Shot]:
    """A 15 s loop (30 beats at 120 BPM): her walk, scan and flood; the plaza in eight worlds; a line
    sweeping London into Van Gogh; a knockout super; the title, which dissolves back into the start."""
    real = Walk(3, "teaser", t0=59.7, z=(1.0, 1.5), name="real")
    scan = Scan(2, "teaser", t1=61.2, desat=0.0, z=(1.5, 1.55), move=(0.06, 0.78), bars=False, name="scan")
    shots: list[Shot] = [
        real,
        scan,
        Flood(3, "teaser", t2=61.2, desat=0.0, z=(scan.z[1], 1.0), speed=0.5, bars=False, name="flood"),
    ]
    verse = ["night", "1920s", "cyberpunk", "autumn", "underwater", "winter", "night", "vangogh"]
    for k, w in enumerate(verse):
        shots.append(Verse(1, "teaser", world=w, start=62.0 + 0.5 * k, name=f"verse {w}"))
    shots += [
        Sweep(6, "teaser", start=4.6, name="london sweep"),
        Super(4, "teaser", start=7.6, name="super"),
        LoopTitle(4, "teaser", text="CROSS THE LINE", size=84, title=True, loop_to=real, name="title"),
    ]
    return shots


# ============================================================================ sound
def _env(n, attack=0.002, tau=0.2):
    t = np.arange(n) / SR
    a = np.minimum(1, t / max(attack, 1e-4))
    return a * np.exp(-t / tau)


def _noise(n, rng):
    return rng.normal(0, 1, n).astype(np.float32)


def _bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def _lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x).astype(np.float32)


def _hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x).astype(np.float32)


def kick(rng, dur=0.45, f0=110, f1=42):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.001, 0.22)
    click = _hp(_noise(n, rng), 2000) * _env(n, 0.0005, 0.004) * 0.3
    return (x + click).astype(np.float32)


def snare(rng, dur=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 185 * t) * _env(n, 0.001, 0.05) * 0.6
    sn = _bp(_noise(n, rng), 900, 7000) * _env(n, 0.001, 0.09)
    return (body + sn * 0.9).astype(np.float32)


def hat(rng, dur=0.08):
    n = int(dur * SR)
    return (_hp(_noise(n, rng), 7000) * _env(n, 0.0005, 0.018) * 0.35).astype(np.float32)


def braam(rng, dur=2.8, root=55.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for mult, amp in ((1, 1.0), (1.5, 0.6), (2, 0.5), (1.004, 0.8), (2.995, 0.25)):
        ph = 2 * np.pi * root * mult * t
        x += amp * (2 * ((ph / (2 * np.pi)) % 1) - 1)           # sawtooth
    x = np.tanh(_lp(x, 900) * 1.6) * _env(n, 0.015, 1.1)
    sub = np.sin(2 * np.pi * root / 2 * t) * _env(n, 0.005, 0.9)
    hit = _lp(_noise(n, rng), 3000) * _env(n, 0.001, 0.08) * 0.8
    return (0.55 * x + 0.7 * sub + hit).astype(np.float32)


def whoosh(rng, dur=0.35, rev=False):
    n = int(dur * SR)
    x = _bp(_noise(n, rng), 400, 5000) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.6
    return (x[::-1] if rev else x).astype(np.float32)


def riser(rng, dur, hold=0.0):
    """Noise band-passed around a centre sweeping 300 Hz -> 6 kHz plus a tone 180 Hz -> 1.44 kHz, the
    level rising as t^2, over dur seconds; then `hold` more seconds at the top (what a tape-stop dives from)."""
    nd = max(2, int(dur * SR))
    n = nd + int(hold * SR)
    t = np.minimum(np.arange(n) / (nd - 1), 1.0)
    out = np.zeros(n, np.float32)
    blk = 2048
    x = _noise(n, rng)
    for s in range(0, n, blk):                                 # band-pass sweeping up
        c = 300 * (20 ** t[s])
        out[s:s + blk] = _bp(x[max(0, s - 512):s + blk], c * 0.7, min(c * 1.5, 18000))[-len(out[s:s + blk]):]
    tone = np.sin(2 * np.pi * np.cumsum(180 * 8 ** t) / SR) * 0.25
    return ((out * 0.7 + tone) * t ** 2).astype(np.float32)


def blip(rng, dur=0.05):
    n = int(dur * SR)
    f = rng.choice([220, 330, 440, 660, 880, 1320, 1760])
    x = np.sign(np.sin(2 * np.pi * f * np.arange(n) / SR)) * _env(n, 0.001, 0.03)
    return (np.round(x * 6) / 6 * 0.35).astype(np.float32)               # crushed square


def drone(dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((55, 0.5), (82.4, 0.3), (110, 0.2), (164.8, 0.08)))
    x = x * (0.75 + 0.25 * np.sin(2 * np.pi * 0.15 * t))
    air = _lp(_noise(n, rng), 600) * 0.15
    return ((x + air) * np.minimum(1, t / 2.5)).astype(np.float32)


def pad(dur, freqs, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t) for f in freqs)
    return (x / len(freqs) * 0.5 * np.minimum(1, t / 0.6) * np.exp(-t / (dur * 0.9))).astype(np.float32)


def tape_stop(x, dur):
    """Play x while the tape slows to a halt over dur seconds: pitch and level dive together."""
    n = int(dur * SR)
    u = np.arange(n) / n
    pos = np.cumsum((1 - u) ** 1.5)                             # read position, samples
    y = np.interp(pos, np.arange(len(x)), x, right=0.0)
    return (y * (1 - u) ** 0.6).astype(np.float32)


def ring(dur, f0=1318.5):
    """One sustained glassy ring (a bowed wine glass): a few partials, a slow beat, soft ends."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f0 * t) + 0.6 * np.sin(2 * np.pi * f0 * 1.0035 * t)
         + 0.22 * np.sin(2 * np.pi * f0 * 2.32 * t) + 0.1 * np.sin(2 * np.pi * f0 * 4.25 * t))
    env = np.minimum(1, t / 0.08) * np.clip((dur - t) / 0.1, 0, 1) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.8 * t))
    return (x * env * 0.2).astype(np.float32)


def crash(rng, dur=1.2):
    n = int(dur * SR)
    return (_hp(_noise(n, rng), 3500) * _env(n, 0.001, 0.35) * 0.5).astype(np.float32)


def reverb(x, rng, secs=1.6, mix=0.3):
    ir = _noise(int(secs * SR), rng) * np.exp(-np.arange(int(secs * SR)) / (0.35 * SR))
    ir = _lp(ir, 5000) / np.sqrt((ir ** 2).sum())
    return x + mix * signal.fftconvolve(x, ir)[: len(x)].astype(np.float32)


def _hush(mix, t, beat_s):
    """Half a beat of near-silence right before t (the hit lands on nothing)."""
    a, b = int((t - beat_s * 0.5) * SR), int(t * SR)
    if 0 <= a < b <= len(mix):
        k = min(b - a, int(0.03 * SR))
        mix[a:a + k] *= np.linspace(1, 0.03, k)
        mix[a + k:b] *= 0.03


def soundtrack(shots, starts, n_frames, beat_s, seed=0):
    if any(sh.section == "teaser" for sh in shots):
        return teaser_soundtrack(shots, starts, n_frames, beat_s, seed)
    rng = np.random.default_rng(seed)
    N = int(n_frames / FPS * SR) + SR
    music, fx, bed = (np.zeros(N, np.float32) for _ in range(3))

    def add(track, x, t, g=1.0):
        s = int(t * SR)
        if 0 <= s < N:
            e = min(N, s + len(x))
            track[s:e] += g * x[: e - s]

    sec = {}
    for sh, s0 in zip(shots, starts):
        a, b = sec.get(sh.section, (1e9, 0))
        sec[sh.section] = (min(a, s0 / FPS), max(b, s0 / FPS + sh.beats * beat_s))
    # bed: drone under the opening, riser into the drop
    if "cold" in sec:
        a = sec["cold"][0]
        b = sec.get("trick", sec["cold"])[1]
        add(bed, drone(b - a + 1.0, rng), a, 0.5)
    if "trick" in sec:
        a, b = sec["trick"]
        add(bed, riser(rng, (b - a) * 0.6), a + (b - a) * 0.4, 0.55)
        for k in range(int((b - a) / beat_s * 2)):
            add(music, hat(rng), a + k * beat_s / 2, 0.35 + 0.4 * k / ((b - a) / beat_s * 2))
    # the drop, keyed on the shot names: a riser that builds over the whole approach and peaks on the
    # freeze's first frame, where a tape-stop dives from its top; a heartbeat in the frozen world, one
    # sustained ring under the scan, then (after half a beat of near-silence, below) the braam and a
    # whoosh on the step into the flood
    rise_tail = None
    for sh, s0 in zip(shots, starts):
        t, d = s0 / FPS, sh.beats * beat_s
        if sh.name == "approach":
            x = riser(rng, d, hold=0.5)                            # the full sweep, then its top held
            cut = int(d * SR)
            add(bed, x[:cut], t, 0.7)
            rise_tail = x[cut:]
        elif sh.name == "freeze":
            tail = rise_tail if rise_tail is not None else riser(rng, 0.5, hold=0.5)[int(0.5 * SR):]
            add(bed, tape_stop(tail, 0.75), t, 0.7)
            add(fx, kick(rng, 0.7, 70, 30), t, 0.8)
            for k in range(1, int(sh.beats), 2):                   # lub-dub
                add(fx, kick(rng, 0.35, 75, 38), t + k * beat_s, 0.45)
                add(fx, kick(rng, 0.3, 70, 36), t + k * beat_s + 0.17, 0.3)
        elif sh.name == "scan":
            add(fx, ring(d - beat_s * 0.5 + 0.15), t, 0.5)
        elif sh.name == "flood":
            add(fx, whoosh(rng, min(d, 1.4)), t, 0.6)
    # montage beat
    mont = sec.get("montage")
    if mont:
        a, b = mont
        roots = [55, 43.65, 65.4, 49]
        nb = int(round((b - a) / beat_s))
        for k in range(nb):
            t = a + k * beat_s
            add(music, kick(rng), t, 0.95)
            if k % 2 == 1:
                add(music, snare(rng), t, 0.7)
            add(music, hat(rng), t + beat_s / 2, 0.5)
            r = roots[(k // 4) % 4]
            for e in (0, 0.5):
                n = int(beat_s / 2 * SR)
                tt = np.arange(n) / SR
                add(music, (np.sin(2 * np.pi * r * tt) * _env(n, 0.003, 0.12)).astype(np.float32), t + e * beat_s, 0.55)
            if k >= nb - 6:                                     # snare roll into the glitch
                for q in range(1, 4):
                    add(music, snare(rng, 0.12), t + q * beat_s / 4, 0.25 + 0.08 * (k - nb + 6))
        add(bed, riser(rng, 6 * beat_s), b - 6 * beat_s, 0.45)
    # glitch: stuttered beat, a blip on every style switch; the hats speed up with the switches
    for sh, s0 in zip(shots, starts):
        if isinstance(sh, Glitch):
            a = s0 / FPS
            nb = int(sh.beats)
            for k in range(nb):
                t = a + k * beat_s
                add(music, kick(rng, 0.3), t, 0.9)
                if k % 2 == 1:
                    add(music, snare(rng), t, 0.6)
                reps = 2 if k < nb / 2 else 4 if k < nb - 2 else 8
                for q in range(reps):
                    add(music, hat(rng, 0.04), t + q * beat_s / reps, 0.45)
            for f in sh.switch_frames:
                add(fx, blip(rng), a + f / FPS, 0.7)
            for f in sh.accents:
                add(fx, whoosh(rng, 0.12), a + f / FPS, 0.25)
            add(bed, whoosh(rng, 2 * beat_s, rev=True), a + (nb - 2) * beat_s, 0.9)
    # resolve: everything drops out, a soft chord
    if "resolve" in sec:
        a, b = sec["resolve"]
        add(bed, pad(b - a + 1.5, [220, 261.6, 329.6, 493.9], rng), a, 0.55)
        add(bed, whoosh(rng, 1.0, rev=True), b - 1.0, 0.5)
    # hits on cuts: impacts on cards and the steps, small thuds on clip cuts
    for sh, s0 in zip(shots, starts):
        t = s0 / FPS
        if sh.section in ("cold", "trick") and isinstance(sh, Card):
            add(fx, kick(rng, 0.6, 80, 35), t, 0.7)
            add(fx, whoosh(rng, 0.3, rev=True), t - 0.3, 0.35)
        elif sh.name in ("flood", "slow crossing"):
            add(fx, braam(rng, 3.0), t, 1.0)
        elif sh.name == "title":
            add(fx, braam(rng, 4.0, 41.2), t, 1.1)
        elif sh.name == "end":
            add(fx, kick(rng, 0.8, 70, 30), t, 0.8)
        elif sh.section == "montage" and isinstance(sh, Card):
            add(fx, braam(rng, 0.9), t, 0.55)
        elif sh.section == "montage" and sh.beats >= 1:
            add(fx, whoosh(rng, 0.18), t - 0.09, 0.3)
    mix = 0.8 * reverb(music, rng, 0.8, 0.12) + reverb(fx, rng, 1.6, 0.35) + 0.9 * bed
    # silence the half beat right before the step into the flood, for the impact to land
    for sh, s0 in zip(shots, starts):
        if sh.name == "flood":
            _hush(mix, s0 / FPS, beat_s)
    mix = mix[: int(n_frames / FPS * SR)]
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-6) * 1.4) * 0.89
    return np.stack([mix, mix], 1)


def teaser_soundtrack(shots, starts, n_frames, beat_s, seed=0):
    """The loop's mix: a pulse under her walk, a ring under the scan, a stinger on the step into the
    flood, a driving beat under the worlds and London, hits on the super, a braam on the title, and a
    ~20 ms fade at the tail so the loop point does not click."""
    rng = np.random.default_rng(seed)
    n_out = int(n_frames / FPS * SR)
    N = n_out + SR
    music, fx, bed = (np.zeros(N, np.float32) for _ in range(3))

    def add(track, x, t, g=1.0):
        s = int(round(t * SR))
        if 0 <= s < N:
            e = min(N, s + len(x))
            track[s:e] += g * x[: e - s]

    at = {}
    for sh, s0 in zip(shots, starts):
        key = sh.name.split()[0]
        a, b = at.get(key, (1e9, 0))
        at[key] = (min(a, s0 / FPS), max(b, s0 / FPS + sh.beats * beat_s))
    end = n_frames / FPS
    t_scan = at.get("scan", (None,))[0]
    t_flood = at.get("flood", (None,))[0]
    groove = [at[k] for k in ("verse", "london") if k in at]
    roots = [55, 43.65, 65.4, 49]
    nb = int(round(end / beat_s))
    for k in range(nb):
        t = k * beat_s
        if "real" in at and at["real"][0] <= t < at["real"][1]:          # a heartbeat pulse
            add(music, kick(rng, 0.35, 90, 45), t, 0.55)
            add(music, hat(rng), t + beat_s / 2, 0.2 + 0.1 * k)
        if "flood" in at and at["flood"][0] + 2 * beat_s <= t < at["flood"][1]:
            add(music, kick(rng, 0.4, 100, 42), t, 0.7)
        if any(a <= t < b - 1e-6 for a, b in groove):                    # the groove
            kb = int(round((t - groove[0][0]) / beat_s))
            add(music, kick(rng), t, 0.95)
            if kb % 2 == 1:
                add(music, snare(rng), t, 0.7)
            for q in (0.5,) if kb < 8 else (0.25, 0.5, 0.75):
                add(music, hat(rng), t + q * beat_s, 0.45)
            r = roots[(kb // 2) % 4]
            n = int(beat_s / 2 * SR)
            tt = np.arange(n) / SR
            for e in (0, 0.5):
                add(music, (np.sin(2 * np.pi * r * tt) * _env(n, 0.003, 0.12)).astype(np.float32), t + e * beat_s, 0.55)
    if t_scan is not None:
        add(bed, riser(rng, t_scan), 0.0, 0.35)
        add(fx, ring((t_flood or t_scan + 1.0) - t_scan - beat_s * 0.5 + 0.12), t_scan, 0.5)
    for sh, s0 in zip(shots, starts):
        t = s0 / FPS
        if sh.name == "flood":                                            # the stinger on the step
            add(fx, braam(rng, 2.6), t, 1.0)
            add(fx, kick(rng, 0.7, 120, 30), t, 1.0)
            add(fx, crash(rng, 1.4), t, 0.6)
            add(fx, whoosh(rng, 1.2), t, 0.5)
        elif sh.name.startswith("verse"):
            add(fx, whoosh(rng, 0.16), t - 0.08, 0.3)
            add(fx, blip(rng), t, 0.35)
        elif sh.name == "london sweep":
            add(fx, whoosh(rng, 2.4), t + 0.2, 0.45)
            add(bed, riser(rng, 2 * beat_s), t + sh.beats * beat_s - 2 * beat_s, 0.45)
        elif sh.name == "super":
            for k in (0, sh.beats / 2):
                add(fx, braam(rng, 0.9), t + k * beat_s, 0.6)
                add(fx, kick(rng, 0.6, 80, 35), t + k * beat_s, 0.8)
        elif sh.name == "title":
            add(fx, braam(rng, 2.2, 41.2), t, 1.0)
            add(fx, whoosh(rng, 1.0, rev=True), t + sh.beats * beat_s - 1.0, 0.35)
    mix = 0.8 * reverb(music, rng, 0.8, 0.12) + reverb(fx, rng, 1.6, 0.35) + 0.9 * bed
    if t_flood is not None:
        _hush(mix, t_flood, beat_s)
    mix = mix[:n_out]
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-6) * 1.4) * 0.89
    k = int(0.02 * SR)                                                    # the loop point: no click
    mix[-k:] *= np.linspace(1, 0, k)
    mix[:int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))
    return np.stack([mix, mix], 1)


def load_music(path, n_frames):
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "m.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ar", str(SR), "-ac", "2", wav], check=True)
        sr, x = wavfile.read(wav)
    x = x.astype(np.float32) / (np.abs(x).max() + 1e-6) * 0.9
    n = int(n_frames / FPS * SR)
    x = np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]
    fade = int(1.5 * SR)
    x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return x


# ============================================================================ main
def parse_size(s: str) -> tuple[int, int]:
    w, h = (int(v) for v in s.lower().split("x"))
    if w < 64 or h < 64 or w % 2 or h % 2:
        raise ValueError(f"--size {s}: width and height must be even and >= 64")
    return w, h


def main(argv=None):
    global W, H
    ap = argparse.ArgumentParser(description="Movie-trailer cut with beat-synced cuts and a style-glitch climax.")
    ap.add_argument("--out", default=f"{OUT}/trailer.mp4")
    ap.add_argument("--edit", choices=["trailer", "teaser"], default="trailer",
                    help="the ~55 s trailer, or the 15 s seamless loop")
    ap.add_argument("--size", default="960x540", help="output WxH, e.g. 960x540 or 720x720")
    ap.add_argument("--crf", type=int, default=18, help="x264 quality (lower is better and bigger)")
    ap.add_argument("--names", default=NAMES_PLACEHOLDER, help="the end card's names line")
    ap.add_argument("--bpm", type=float, default=120.0)
    ap.add_argument("--music", help="use this track instead of the synthesized one (set --bpm to its tempo)")
    ap.add_argument("--sections", help="comma list of sections (or shot names) to render (a quick draft)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    W, H = parse_size(a.size)                                  # before any shot is built or set up
    beat_s = 60.0 / a.bpm
    fpb = FPS * beat_s
    shots = edit_teaser() if a.edit == "teaser" else edit(a.names)
    if a.sections:
        keep = set(a.sections.split(","))
        shots = [s for s in shots if s.section in keep or s.name in keep]
    starts, t = [], 0.0
    for s in shots:
        starts.append(int(round(t * fpb)))
        t += s.beats
    n_total = int(round(t * fpb))
    for k, (sh, s0) in enumerate(zip(shots, starts)):
        sh.nf = (starts[k + 1] if k + 1 < len(shots) else n_total) - s0
        sh.t_start = s0 / FPS
    rng = np.random.default_rng(a.seed)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    tmp = a.out.replace(".mp4", "_video.mp4")
    vw = VideoWriter(tmp, W, H, FPS, crf=a.crf)
    strip, t0 = [], time.time()
    sw = int(round(135 * W / H))
    edl = []
    for k, (sh, s0) in enumerate(zip(shots, starts)):
        n = sh.nf
        ts = time.time()
        sh.setup()
        for j in range(n):
            img = sh.render(j, n)
            if sh.rgb_in and j < 3:
                img = rgb_split(img, 9 - 3 * j)
            if sh.flash_in and j < 4:
                img = flash(img, [0.95, 0.7, 0.4, 0.15][j])
            img = finish(img, rng, sh.bars)
            vw.write(img)
            if j == n // 2:
                strip.append(cv2.resize(img, (sw, 135), interpolation=cv2.INTER_AREA))
        src = sh.source(n)
        edl.append({"shot": k, "name": sh.name, "section": sh.section, "type": type(sh).__name__,
                    "start_frame": s0, "frames": n, "start_s": round(s0 / FPS, 3), "beats": sh.beats,
                    "source": src[0] if src else None,
                    "t0": None if not src or src[1] is None else round(src[1], 3),
                    "t1": None if not src or src[2] is None else round(src[2], 3)})
        if sh.others(n) is not None:                           # everyone but her, on their own clock
            edl[-1]["others_t0"], edl[-1]["others_t1"] = (round(v, 3) for v in sh.others(n))
        print(f"[trailer] {k:2d} {sh.section:8s} {sh.name:22s} {n:4d} frames  {time.time() - ts:5.1f}s", flush=True)
    vw.close()
    audio = load_music(a.music, n_total) if a.music else soundtrack(shots, starts, n_total, beat_s, a.seed)
    wav = a.out.replace(".mp4", ".wav")
    wavfile.write(wav, SR, (audio * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", a.out], check=True)
    os.remove(tmp)
    # review sheet: the middle frame of every shot
    cols = 8
    while len(strip) % cols:
        strip.append(np.zeros_like(strip[0]))
    sheet = np.vstack([np.hstack(strip[i:i + cols]) for i in range(0, len(strip), cols)])
    cv2.imwrite(a.out.replace(".mp4", "_frames.jpg"), sheet)
    json.dump({"edit": a.edit, "size": [W, H], "crf": a.crf, "bpm": a.bpm, "fps": FPS, "frames": n_total,
               "seconds": round(n_total / FPS, 2), "shots": edl},
              open(a.out.replace(".mp4", "_edl.json"), "w"), indent=1)
    print(f"[trailer] {n_total} frames ({n_total / FPS:.1f}s) in {time.time() - t0:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
