"""A ~55 s movie-trailer cut: rapid beat-synced cuts, one story, and a style-glitch climax where a
walker flashes through art styles frame by frame.

    python -m crossover.trailer --out out/trailer.mp4
    python -m crossover.trailer --out out/trailer_draft.mp4 --sections cold,drop,montage   # quick draft
    python -m crossover.trailer --out out/trailer.mp4 --music track.mp3 --bpm 120          # your own music

Every shot length is a whole number of beats (120 BPM = 15 frames at 30 fps), and the synthesized
soundtrack is built on the same grid, so cuts, flashes and hits line up exactly.
Inputs are the outputs of the other scripts (generated worlds, effect renders, clean plates).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field

import cv2
import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
from scipy import signal
from scipy.io import wavfile

from .composite import ShadowRatio, glow_overlay
from .depth import farness, smoothstep
from .effects import World, blobs, screen
from .masks import BgDiffMasker
from .styles import century, comic, ink, neon, sketch, thermal_person
from .video_io import VideoWriter, iter_frames, to_float, to_uint8

W, H, FPS = 960, 540, 30
SR = 44100
INK, SEPIA, SEAM = (239, 235, 232), (122, 176, 212), (255, 233, 191)          # BGR
FONT_B = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
FONT_R = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans"))
OUT = "out"
VTEST = "data/sample/vtest.avi"


# ============================================================================ frame helpers
def fit(img: np.ndarray, crop_y: float = 0.5) -> np.ndarray:
    """Crop to 16:9 (keeping the band at crop_y) and resize to W x H."""
    h, w = img.shape[:2]
    if w / h < W / H - 0.01:
        ch = int(round(w * H / W))
        y0 = int((h - ch) * crop_y)
        img = img[y0:y0 + ch]
    elif w / h > W / H + 0.01:
        cw = int(round(h * W / H))
        x0 = (w - cw) // 2
        img = img[:, x0:x0 + cw]
    interp = cv2.INTER_CUBIC if img.shape[1] < W else cv2.INTER_AREA
    return cv2.resize(img, (W, H), interpolation=interp)


def zoom(img: np.ndarray, z: float, cx: float = 0.5, cy: float = 0.5) -> np.ndarray:
    if abs(z - 1) < 1e-3:
        return img
    px, py = cx * W, cy * H
    M = np.float32([[z, 0, px * (1 - z)], [0, z, py * (1 - z)]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def crop_zoom(img: np.ndarray, z: float, cx: float, cy: float) -> np.ndarray:
    """Zoom in by z on the point (cx, cy) (fractions), keeping the window inside the frame."""
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


_VIG = None


def finish(img: np.ndarray, rng: np.random.Generator, bars: bool = True) -> np.ndarray:
    """Letterbox, vignette, film grain."""
    global _VIG
    if _VIG is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2
        _VIG = (1 - 0.28 * np.clip(r2 / 2, 0, 1))[..., None]
    f = img.astype(np.float32) * _VIG + rng.normal(0, 3.2, (H, W, 1)).astype(np.float32)
    out = np.clip(f, 0, 255).astype(np.uint8)
    if bars:
        out[:30] = 0
        out[-30:] = 0
    return out


def desaturate(img: np.ndarray, k: float) -> np.ndarray:
    g = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(img, 1 - k, g, k, 0)


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


# ============================================================================ shots
@dataclass
class Shot:
    beats: float
    section: str = ""
    flash_in: bool = False
    rgb_in: bool = False
    bars: bool = True
    name: str = ""

    def setup(self):
        pass

    def render(self, j: int, n: int) -> np.ndarray:
        raise NotImplementedError


@dataclass
class Clip(Shot):
    path: str = ""
    start: float = 0.0
    speed: float = 1.0
    crop_y: float = 0.5
    z: tuple = (1.0, 1.0)
    center: tuple = (0.5, 0.5)
    line: bool = False
    desat: float = 0.0
    fade_to: str | None = None         # crossfade the footage into this still (people vanish)
    fade_from_black: int = 0

    def render(self, j, n):
        r = Reader.get(self.path)
        t = self.start + j / FPS * self.speed
        img = r.frame(int(t * r.fps)).copy()
        if self.fade_to is not None:
            p = float(smoothstep(np.float32((j - 0.25 * n) / (0.6 * n))))
            img = cv2.addWeighted(img, 1 - p, cv2.imread(self.fade_to), p, 0)
        if self.line:
            d = (np.arange(img.shape[1], dtype=np.float32) - img.shape[1] / 2)[None, :] * np.ones((img.shape[0], 1), np.float32)
            img = to_uint8(screen(to_float(img), glow_overlay(d, 2.0 * img.shape[1] / 768)))
        img = fit(img, self.crop_y)
        u = j / max(1, n - 1)
        img = zoom(img, self.z[0] + (self.z[1] - self.z[0]) * u, *self.center)
        if self.desat:
            img = desaturate(img, self.desat)
        if self.fade_from_black and j < self.fade_from_black:
            img = (img * (j / self.fade_from_black)).astype(np.uint8)
        return img


def _text_size(draw, text, font, spacing):
    w = sum(font.getlength(c) for c in text) + spacing * (len(text) - 1)
    bb = draw.textbbox((0, 0), "HG", font=font)
    return w, bb[3] - bb[1], bb[1]


def draw_spaced(img: Image.Image, text: str, size: int, y: int, fill, spacing: float, bold=True):
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_B if bold else FONT_R, size)
    w, h, top = _text_size(d, text, font, spacing)
    x = (img.width - w) / 2
    for c in text:
        d.text((x, y - top), c, font=font, fill=fill)
        x += font.getlength(c) + spacing
    return h


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
        img = zoom(self.base, 1.06 - 0.06 * float(smoothstep(np.float32(u * 1.4))))
        return rgb_split(img, max(0, 8 - 4 * j)) if j < 2 else img


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
    """One tracked walker flashes through styles, faster and faster; the world tears around them."""
    video: str = VTEST
    clean: str = ""
    start_frame: int = 640
    target: tuple = (360.0, 453.0)
    worlds: tuple = ("vangogh", "cyberpunk", "1920s", "night", "winter")
    person_styles: tuple = ("comic", "world:vangogh", "thermal", "ink", "world:cyberpunk", "sketch", "pixel",
                            "world:1920s", "neon", "negative", "oil", "sepia", "world:night", "world:winter")
    crop_y: float = 1.0
    seed: int = 7
    switch_frames: list = field(default_factory=list)
    accents: list = field(default_factory=list)

    def setup(self):
        self.bg = cv2.imread(self.clean)
        h, w = self.bg.shape[:2]
        n_src = int(np.ceil(self.beats * 15 / 3)) + 2
        picks = dict(l.split() for l in open(f"{OUT}/gen/picks.txt") if l.strip())
        self.W = {k: World(k, self.bg, cv2.imread(f"{OUT}/gen/{picks[k]}.png"), 10.0) for k in
                  set(self.worlds) | {s.split(":")[1] for s in self.person_styles if s.startswith("world:")}}
        self.src = []                                  # (frame, alpha, person mask float, bbox)
        cx, cy = self.target
        prev = None
        masker = BgDiffMasker(self.bg)
        frames = (f for k, f in enumerate(iter_frames(self.video, 1.0, self.start_frame + n_src + 1))
                  if k >= self.start_frame - 1)
        for i, (_, f, a) in enumerate(masker.iter_alphas(frames)):
            bl = blobs(a, 3e-4 * h * w)
            pick = min(bl, key=lambda b: np.hypot(b[4] - cx, b[5] - cy), default=None)
            if pick is not None and np.hypot(pick[4] - cx, pick[5] - cy) < 70:
                m = pick[0]
                cx, cy = pick[4], pick[5]
                prev = m
            else:
                m = prev if prev is not None else np.zeros((h, w), np.uint8)
            m = cv2.dilate(m, np.ones((5, 5), np.uint8))
            soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
            ys, xs = np.nonzero(m)
            bbox = (max(0, xs.min() - 12), max(0, ys.min() - 12), min(w, xs.max() + 13), min(h, ys.max() + 13)) \
                if len(xs) else (0, 0, 1, 1)
            self.src.append((f, a, soft, bbox))
            if len(self.src) >= n_src:
                break
        # a follow-cam on the walker: bbox centres in output (fit) coordinates, smoothed
        ch = int(round(w * H / W))
        oy = int((h - ch) * self.crop_y)
        sc = W / w
        cen = np.array([[(b[0] + b[2]) / 2 * sc / W, ((b[1] + b[3]) / 2 - oy) * sc / H] for _, _, _, b in self.src])
        k = np.ones(7) / 7
        self.cam = np.stack([np.convolve(np.pad(cen[:, i], 3, mode="edge"), k, "valid") for i in range(2)], 1)
        self.shadow = ShadowRatio(to_float(self.bg))
        self.ones = np.ones((h, w), np.float32)
        self._wcache = {}
        # schedule (in output frames): every 4 -> 2 -> 1 frames, then chaos
        n = int(round(self.beats * 15))
        b = lambda x: int(round(x * 15))
        sched, k = [], 0
        while k < n:
            sched.append(k)
            k += 4 if k < b(6) else 2 if k < b(12) else 1
        self.switch_frames = sched
        self.accents = sorted({b(x) for x in (2, 4, 6, 8, 10, 11, 12, 13, 14, 15, 16)} | set(range(b(17), n)))
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
            self._wcache[key] = to_uint8(self.W[name].render(si, F, f, a, S, self.ones))
        return self._wcache[key]

    def person(self, si: int, style: str) -> np.ndarray:
        f, _, _, (x0, y0, x1, y1) = self.src[si]
        if style.startswith("world:"):
            img = self.world_frame(si, style.split(":")[1])
            return img
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
        img = fit(img, self.crop_y)
        cx, cy = self.cam[si]
        img = crop_zoom(img, 1.9 + 0.5 * j / max(1, n - 1), cx, cy)
        chaos = j >= int(round(17 * 15))
        if chaos:
            alts = [crop_zoom(fit(self.world_frame(si, w), self.crop_y), 2.2, cx, cy) for w in self.worlds[:3]]
            img = tear(img, self.rng, 7, alts, shift=50)
        elif j in self.bgworld:
            img = tear(img, self.rng, 3, (), shift=24)
        elif just == 0 and self.rng.random() < 0.35:
            img = tear(img, self.rng, 2, (), shift=16)
        img = rgb_split(img, (10 if just == 0 else 5 if just == 1 else 1.5) * (1.5 if chaos else 1))
        if j >= n - 3:
            img = flash(img, (j - (n - 4)) / 3)
        return img


# ============================================================================ the edit
def edit() -> list[Shot]:
    gen = lambda s: f"{OUT}/vtest_gen_{s}/final_matched.mp4"
    lv = f"{OUT}/clips/crowd04/run_line_vangogh/final_matched.mp4"
    bgv = f"{OUT}/vtest_century/clean_bg.png"
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
        # the drop: the couple walks to the line... and crosses
        Clip(3, "drop", path=VTEST, start=57.7, line=True, crop_y=1.0, z=(1.0, 1.15), center=(0.47, 0.5), name="approach"),
        Clip(4, "drop", path=gen("winter"), start=59.2, crop_y=1.0, z=(1.15, 1.06), center=(0.47, 0.5), flash_in=True,
             rgb_in=True, name="crossing"),
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
        Glitch(20, "glitch", clean=bgv, name="glitch"),
        Clip(6, "resolve", path=lv, start=12.6, speed=0.5, flash_in=True, name="slow crossing"),
        Card(1, "resolve", text="ONE IMAGE.", size=60, name="card"),
        Card(1, "resolve", text="EVERY FRAME.", size=60, name="card"),
        Card(8, "title", text="CROSS THE LINE", size=84, title=True, name="title"),
        Card(4, "title", text="CS180 / 280A", size=40, sub="DECEMBER 2026", name="subtitle"),
        Black(2, "title", name="black"),
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


def riser(rng, dur):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
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


def reverb(x, rng, secs=1.6, mix=0.3):
    ir = _noise(int(secs * SR), rng) * np.exp(-np.arange(int(secs * SR)) / (0.35 * SR))
    ir = _lp(ir, 5000) / np.sqrt((ir ** 2).sum())
    return x + mix * signal.fftconvolve(x, ir)[: len(x)].astype(np.float32)


def soundtrack(shots, starts, n_frames, beat_s, seed=0):
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
    if "drop" in sec:
        a, b = sec["drop"]
        add(bed, riser(rng, 3 * beat_s - 0.05), a - 0.0, 0.7)
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
    # glitch: stuttered beat, a blip on every style switch
    for sh, s0 in zip(shots, starts):
        if isinstance(sh, Glitch):
            a = s0 / FPS
            nb = int(sh.beats)
            for k in range(nb):
                t = a + k * beat_s
                add(music, kick(rng, 0.3), t, 0.9)
                if k % 2 == 1:
                    add(music, snare(rng), t, 0.6)
                reps = 2 if k < 6 else 4 if k < 12 else 8
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
    # hits on cuts: impacts on cards and the drop, small thuds on clip cuts
    for sh, s0 in zip(shots, starts):
        t = s0 / FPS
        if sh.section in ("cold", "trick") and isinstance(sh, Card):
            add(fx, kick(rng, 0.6, 80, 35), t, 0.7)
            add(fx, whoosh(rng, 0.3, rev=True), t - 0.3, 0.35)
        elif sh.name == "crossing" or sh.name == "slow crossing":
            add(fx, braam(rng, 3.0), t, 1.0)
        elif sh.name == "title":
            add(fx, braam(rng, 4.0, 41.2), t, 1.1)
        elif sh.name == "subtitle":
            add(fx, kick(rng, 0.8, 70, 30), t, 0.8)
        elif sh.section == "montage" and isinstance(sh, Card):
            add(fx, braam(rng, 0.9), t, 0.55)
        elif sh.section == "montage" and sh.beats >= 1:
            add(fx, whoosh(rng, 0.18), t - 0.09, 0.3)
    mix = 0.8 * reverb(music, rng, 0.8, 0.12) + reverb(fx, rng, 1.6, 0.35) + 0.9 * bed
    # silence the beat right before the drop, for the impact to land
    for sh, s0 in zip(shots, starts):
        if sh.name == "crossing":
            t = s0 / FPS
            a, b = int((t - beat_s * 0.5) * SR), int(t * SR)
            mix[a:b] *= np.linspace(1, 0.03, b - a)
    mix = mix[: int(n_frames / FPS * SR)]
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-6) * 1.4) * 0.89
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
def main(argv=None):
    ap = argparse.ArgumentParser(description="Movie-trailer cut with beat-synced cuts and a style-glitch climax.")
    ap.add_argument("--out", default=f"{OUT}/trailer.mp4")
    ap.add_argument("--bpm", type=float, default=120.0)
    ap.add_argument("--music", help="use this track instead of the synthesized one (set --bpm to its tempo)")
    ap.add_argument("--sections", help="comma list to render only some sections (a quick draft)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    beat_s = 60.0 / a.bpm
    fpb = FPS * beat_s
    shots = edit()
    if a.sections:
        keep = set(a.sections.split(","))
        shots = [s for s in shots if s.section in keep]
    starts, t = [], 0.0
    for s in shots:
        starts.append(int(round(t * fpb)))
        t += s.beats
    n_total = int(round(t * fpb))
    rng = np.random.default_rng(a.seed)
    tmp = a.out.replace(".mp4", "_video.mp4")
    vw = VideoWriter(tmp, W, H, FPS)
    strip, t0 = [], time.time()
    edl = []
    for k, (sh, s0) in enumerate(zip(shots, starts)):
        n = (starts[k + 1] if k + 1 < len(shots) else n_total) - s0
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
                strip.append(cv2.resize(img, (240, 135)))
        edl.append({"shot": k, "name": sh.name, "section": sh.section, "type": type(sh).__name__,
                    "start_frame": s0, "frames": n, "start_s": round(s0 / FPS, 3), "beats": sh.beats})
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
    json.dump({"bpm": a.bpm, "fps": FPS, "frames": n_total, "seconds": round(n_total / FPS, 2), "shots": edl},
              open(a.out.replace(".mp4", "_edl.json"), "w"), indent=1)
    print(f"[trailer] {n_total} frames ({n_total / FPS:.1f}s) in {time.time() - t0:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
