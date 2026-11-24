"""Ladders and the two-band morph: the world grows out of the filmed scene through the images that
made it, instead of cutting.

A ladder is a list of pixel-aligned images of one scene, rung 0 to rung N:

    plate -> filter (the exact img2img start image) -> lower-strength SD images -> world

LCM img2img runs n = int(steps*strength) denoising steps, so a lower-strength image made from the
same filter start, seed and schedule (steps, guidance) is a less finished version of the same world.
Only those filter-init images ({style}f_s0_*) form a clean progression; photo-init ones never enter.

Ladder.at(r), with r in [0, N] a scalar or an HxW map, blends rungs k = floor(r) and k + 1 in two
bands (the multiband idea, applied over time): colour (a Gaussian low-pass) crossfades with
f = r - k, while detail (the rest) switches patch by patch where f passes a fixed threshold field
th in [0.15, 0.85] (18-px value-noise patches, or halftone dots) instead of double-exposing.
It is exact at every integer r: at(0) is the plate and at(N) the world, bit for bit.

Images are float32 BGR; chain() returns 0-255. two_band() and Ladder are linear in the images, so
0-1 floats (video_io.to_float) work the same.

    from crossover import morph
    lad = morph.plaza_ladder("night")                  # plate, filter, n5, world (N = 3)
    still = lad.at(1.5)                                # halfway from the filter to n5
    u = morph.grow_map(morph.plaza_farness(), 0.4)     # far pixels first
    frame_bg = lad.at(lad.n * u)                       # about 12-15 ms at 768x576

Plaza chains after the eye check (EXCLUDE): night, 1920s, underwater and autumn plate, filter, n5,
world; vangogh plate, filter, n7, world; winter and cyberpunk plate, filter, world.
exclude={} gives every SD rung back.

API
    sd_rungs(style, pick_stem, gen_dirs=GEN_DIRS, root=ROOT, pick_dir=None) -> [Rung]
    chain(style, plate, world, mids=()) -> (rungs, labels)
    plaza_picks() / plaza_mids(style) / plaza_chain(style) / plaza_ladder(style) / plaza_farness()
    two_band(A, B, lowA, lowB, f, th, soft=0.12)    low_pass(img, sigma=None)    crossfade(A, B, f)
    threshold(h, w, seed=0, pattern="noise"|"dots")    vnoise(h, w, cell, seed=0)
    Ladder(rungs, labels=None, sigma=None, seed=0, pattern="noise"): .n, .at(r), .labels, .rungs,
        .low, .high, .th, .switch(f)
    grow_map(far, p, lead=0.45, reverse=False)
    blur_dist(a, b, sigma=None), betweenness(prev, mid, nxt, sigma=None), mid_index(rungs, labels)

python -m crossover.morph prints the plaza chains, their betweenness numbers and the speed of at().
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAZA = "out/clips/vtest"                               # the plaza scene (python -m crossover.prepare)
GEN_DIRS = (f"{PLAZA}/gen", f"{PLAZA}/gen_ladder")      # gen_ladder: extra lower-strength rungs
PLAZA_GEN = f"{PLAZA}/gen"
PLAZA_PLATE = f"{PLAZA}/clean_bg.png"
PLAZA_DEPTH = f"{PLAZA}/depth_disparity.npy"
PATTERN = {"cyberpunk": "dots", "comic": "dots"}      # worlds whose detail arrives as halftone dots
# SD rungs left out of the plaza chains after the eye check, keyed by (folder, stem), never stem alone.
# Each one invents an object that neither chain neighbour has, so it would flash up and vanish.
EXCLUDE: dict[tuple[str, str], str] = {
    ("out/clips/vtest/gen_ladder", "vangoghf_s0_k55"): "n5 adds a white blob on the lawn at (249, 335) and whitens the stone "
                                           "at (39, 321); the filter, n7 and the world have plain lawn there",
    ("out/clips/vtest/gen_ladder", "vangoghf_s0_k85"): "n8 adds a bright orange diamond on the near lawn at (127, 399) that "
                                           "n7 and the world do not have",
    ("out/clips/vtest/gen_ladder", "cyberpunkf_s0_k65"): "n5 adds a magenta blob on the lawn at (250, 336) that the filter and "
                                             "the world do not have; betweenness 1.33 (> 1.3)",
    ("out/clips/vtest/gen", "winterf_s0_k60"): "n4 turns the rock on the lawn at (175, 262) bright red (mean RGB 121, 52, 54); "
                                   "the filter has a grey rock there and the world a snow-capped dark one",
}


# ============================================================================ rungs on disk
@dataclass(frozen=True)
class Rung:
    """One lower-strength SD image and the schedule it ran."""
    folder: str          # gen dir as given, e.g. "out/clips/vtest/gen_ladder"
    stem: str
    path: str
    n: int               # denoising steps actually run, int(steps*strength)
    steps: int
    guidance: float
    strength: float
    md5: str

    @property
    def key(self) -> tuple[str, str]:
        return self.folder, self.stem

    @property
    def label(self) -> str:
        return f"n{self.n}"


def n_steps(meta: dict) -> int:
    """Denoising steps LCM img2img ran: int(steps*strength), as diffusers' get_timesteps."""
    return min(int(meta["steps"] * meta["strength"]), int(meta["steps"]))


def _md5(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def _meta(folder: str, root: str) -> dict:
    path = os.path.join(root, folder, "meta.json")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


def sd_rungs(style: str, pick_stem: str, gen_dirs=GEN_DIRS, root: str = ROOT, pick_dir: str | None = None) -> list[Rung]:
    """The lower filter-init SD images of a pick on its own schedule: stem {style}f_s{seed}_k*, same
    seed, steps and guidance as the pick, n < n_pick, md5 duplicates (and the pick's own bytes)
    dropped, one per n (the first in gen_dirs order), sorted by n. pick_dir: the folder holding the
    pick (default: the first of gen_dirs whose meta.json has it)."""
    metas = {d: _meta(d, root) for d in gen_dirs}
    if pick_dir is None:
        pick_dir = next((d for d in gen_dirs if pick_stem in metas[d]), None)
    pm = None
    if pick_dir is not None:
        pm = (metas[pick_dir] if pick_dir in metas else _meta(pick_dir, root)).get(pick_stem)
    if pm is None:
        raise KeyError(f"{pick_stem} is not in meta.json of {pick_dir or gen_dirs}")
    n_pick = n_steps(pm)
    pat = re.compile(rf"^{re.escape(style)}f_s{int(pm['seed'])}_k\d+$")
    cands = []
    for order, d in enumerate(gen_dirs):
        for stem, m in metas[d].items():
            if not pat.match(stem) or m.get("style") != style or m.get("init", "filter") != "filter":
                continue
            if m["seed"] != pm["seed"] or m["steps"] != pm["steps"] or abs(m["guidance"] - pm["guidance"]) > 1e-6:
                continue
            path = os.path.join(root, d, stem + ".png")
            if n_steps(m) < n_pick and os.path.exists(path):
                cands.append((n_steps(m), order, m["strength"], d, stem, path, m))
    seen, out = {_md5(os.path.join(root, pick_dir, pick_stem + ".png"))}, []
    for n, _, k, d, stem, path, m in sorted(cands):
        md5 = _md5(path)
        if md5 in seen or (out and out[-1].n == n):
            continue
        seen.add(md5)
        out.append(Rung(d, stem, path, n, int(m["steps"]), float(m["guidance"]), float(k), md5))
    return out


def chain(style: str, plate: np.ndarray, world: np.ndarray, mids=()) -> tuple[list[np.ndarray], list[str]]:
    """[plate, filter, *mids, world] as float32 BGR 0-255 arrays, and their labels
    ("plate", "filter", "n5", ..., "world"). The filter is the exact img2img start image,
    styles.apply_style(plate, generate.INIT_FILTER[style]); a style without one has no filter rung.
    mids: Rung records (read from disk, labelled n{n}), (label, image) pairs or bare images."""
    from .generate import INIT_FILTER
    from .styles import apply_style

    plate = np.asarray(plate)
    p8 = plate if plate.dtype == np.uint8 else np.clip(np.rint(plate), 0, 255).astype(np.uint8)
    rungs, labels = [plate.astype(np.float32)], ["plate"]
    if style in INIT_FILTER:
        rungs.append(apply_style(p8, INIT_FILTER[style]).astype(np.float32))
        labels.append("filter")
    for i, m in enumerate(mids):
        if isinstance(m, Rung):
            label, img = m.label, cv2.imread(m.path)
        elif isinstance(m, tuple):
            label, img = m
        else:
            label, img = f"mid{i + 1}", m
        rungs.append(np.asarray(img).astype(np.float32))
        labels.append(label)
    rungs.append(np.asarray(world).astype(np.float32))
    labels.append("world")
    for label, img in zip(labels, rungs):
        if img.shape != rungs[0].shape:
            raise ValueError(f"rung {label!r} is {img.shape}, the plate {rungs[0].shape}: resize or align it first")
    return rungs, labels


def plaza_picks(root: str = ROOT) -> dict[str, str]:
    """style -> stem of the plaza world (gen/picks.txt)."""
    with open(os.path.join(root, PLAZA_GEN, "picks.txt")) as fh:
        return dict(ln.split()[:2] for ln in fh if ln.strip())


def plaza_mids(style: str, root: str = ROOT, exclude: dict | None = None) -> list[Rung]:
    """The SD mid rungs of a plaza world: sd_rungs of its pick minus EXCLUDE."""
    exclude = EXCLUDE if exclude is None else exclude
    rungs = sd_rungs(style, plaza_picks(root)[style], GEN_DIRS, root, pick_dir=PLAZA_GEN)
    return [r for r in rungs if r.key not in exclude]


def plaza_chain(style: str, root: str = ROOT, exclude: dict | None = None) -> tuple[list[np.ndarray], list[str]]:
    """The full plaza ladder of a world (all worlds there were kept unwarped, so rungs are aligned)."""
    plate = cv2.imread(os.path.join(root, PLAZA_PLATE))
    world = cv2.imread(os.path.join(root, PLAZA_GEN, plaza_picks(root)[style] + ".png"))
    return chain(style, plate, world, plaza_mids(style, root, exclude))


def plaza_ladder(style: str, root: str = ROOT, exclude: dict | None = None, **kw) -> "Ladder":
    """Ladder(plaza_chain(style)) with the world's pattern (dots for Cyberpunk); kw go to Ladder."""
    kw.setdefault("pattern", PATTERN.get(style, "noise"))
    return Ladder(*plaza_chain(style, root, exclude), **kw)


def plaza_farness(root: str = ROOT) -> np.ndarray:
    """Farness of the plaza plate (0 near .. 1 far), HxW float32, for grow_map."""
    from .depth import farness
    return farness(np.load(os.path.join(root, PLAZA_DEPTH)).astype(np.float32))


# ============================================================================ the blend
def low_pass(img: np.ndarray, sigma: float | None = None) -> np.ndarray:
    """The colour band: GaussianBlur with sigma = 3*W/768 px by default."""
    img = np.ascontiguousarray(img, np.float32)
    return cv2.GaussianBlur(img, (0, 0), 3.0 * img.shape[1] / 768 if sigma is None else sigma)


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def two_band(A, B, lowA, lowB, f, th, soft: float = 0.12) -> np.ndarray:
    """lowA + f*(lowB - lowA) + (A - lowA) + s*((B - lowB) - (A - lowA)), s = smoothstep(th - soft,
    th + soft, f): colour crossfades, detail switches where f passes th. f, th: scalars or HxW maps.
    Evaluated as the equal sum (1 - s)*A + s*B + (f - s)*(lowB - lowA), which is exactly A at f = 0
    and exactly B at f = 1 (th in [0.15, 0.85] keeps s at 0 and 1 there)."""
    f, th = np.asarray(f, np.float32), np.asarray(th, np.float32)
    s = _smoothstep(th - soft, th + soft, f)
    s3 = s[..., None] if s.ndim else s
    f3 = f[..., None] if f.ndim else f
    return ((1 - s3) * A + s3 * B + (f3 - s3) * (np.asarray(lowB) - lowA)).astype(np.float32)


def crossfade(A, B, f) -> np.ndarray:
    """Plain (1 - f)*A + f*B, for comparison figures. f: scalar or HxW map."""
    f = np.asarray(f, np.float32)
    f3 = f[..., None] if f.ndim else f
    return ((1 - f3) * np.asarray(A, np.float32) + f3 * np.asarray(B, np.float32)).astype(np.float32)


def _hash(x: np.ndarray) -> np.ndarray:
    """lowbias32 integer hash on uint32 (wrapping); the same ops on GLSL uint give the same bits."""
    with np.errstate(over="ignore"):
        x = x ^ (x >> np.uint32(16))
        x = x * np.uint32(0x7FEB352D)
        x = x ^ (x >> np.uint32(15))
        x = x * np.uint32(0x846CA68B)
        return x ^ (x >> np.uint32(16))


def vnoise(h: int, w: int, cell: float, seed: int = 0) -> np.ndarray:
    """Smooth value noise in [0, 1), HxW float32. Pixel (x, y) (y down) reads the lattice at
    p = ((x + 0.5)/cell, (y + 0.5)/cell), smoothstep-interpolated between the four corners of
    floor(p); corner (i, j) holds (hash(i + hash(j + hash(seed))) >> 8) / 2^24 (uint32 wrap)."""
    def axis(n):
        p = (np.arange(n, dtype=np.float32) + 0.5) / np.float32(cell)
        i = np.floor(p)
        t = p - i
        return i.astype(np.intp), t * t * (3 - 2 * t)
    ix, wx = axis(w)
    iy, wy = axis(h)
    gi = np.arange(ix[-1] + 2, dtype=np.uint32)
    gj = np.arange(iy[-1] + 2, dtype=np.uint32)
    with np.errstate(over="ignore"):
        rows = _hash(gj + _hash(np.array([seed & 0xFFFFFFFF], np.uint32)))
        lat = (_hash(gi[None, :] + rows[:, None]) >> np.uint32(8)).astype(np.float32) / np.float32(1 << 24)
    a, b = lat[iy], lat[iy + 1]
    top = a[:, ix] + (a[:, ix + 1] - a[:, ix]) * wx
    bot = b[:, ix] + (b[:, ix + 1] - b[:, ix]) * wx
    return (top + (bot - top) * wy[:, None]).astype(np.float32)


def threshold(h: int, w: int, seed: int = 0, pattern: str = "noise", cell: float = 5.0) -> np.ndarray:
    """Where each pixel's detail switches, HxW float32 in [0.15, 0.85] (so every rung stays exact).
    'noise': n = 0.65*vnoise(18 px, 2*seed) + 0.35*vnoise(6 px, 2*seed + 1) (cells scaled by w/768),
    then th = 0.15 + 0.7/(1 + exp(-10*(n - 0.5))). The logistic spreads th evenly over the range
    (n alone has std 0.16, so most pixels would switch together near f = 0.5: 46% half-switched
    there, against 18% here), so patches flip one after another through the whole step.
    'dots': 0.15 + 0.7*d, d = distance to the nearest dot centre of the 45-degree halftone screen
    (0 at a centre, 1 between dots; cell*max(1, w/768) px, as the portal's halftone()), so detail
    arrives as dots that grow until they merge. Deterministic; dots ignore the seed."""
    s = w / 768.0
    if pattern == "noise":
        n = 0.65 * vnoise(h, w, 18 * s, 2 * seed) + 0.35 * vnoise(h, w, 6 * s, 2 * seed + 1)
        n = 1.0 / (1.0 + np.exp(-10.0 * (n - 0.5)))
    elif pattern == "dots":
        c = cell * max(1.0, s)
        y, x = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
        du = np.mod((x + y) * np.float32(0.70710678) / c, 1.0) - 0.5
        dv = np.mod((x - y) * np.float32(0.70710678) / c, 1.0) - 0.5
        n = np.sqrt(du * du + dv * dv) / np.float32(0.70710678)
    else:
        raise ValueError(f"unknown pattern {pattern!r}: 'noise' or 'dots'")
    return np.clip(0.15 + 0.7 * n, 0.15, 0.85).astype(np.float32)


class Ladder:
    """Rungs 0..N of one world and the two-band walk between them.

    at(r): r a scalar or an HxW map, clipped to [0, N]; k = min(floor(r), N - 1), f = r - k, and
    two_band(rung k, rung k + 1) with the fixed threshold field th. at(k) == rung k exactly.
    Holds rungs and low (N+1, H, W, 3) float32 and their differences; high is rungs - low."""

    def __init__(self, rungs, labels=None, sigma: float | None = None, seed: int = 0, pattern: str = "noise",
                 soft: float = 0.12):
        R = np.stack([np.asarray(r, np.float32) for r in rungs])
        if R.ndim != 4 or R.shape[-1] != 3 or len(R) < 2:
            raise ValueError("a ladder needs at least 2 HxWx3 rungs of one size")
        self.rungs, self.n = R, len(R) - 1
        self.h, self.w = R.shape[1:3]
        self.labels = list(labels) if labels is not None else [f"r{k}" for k in range(len(R))]
        if len(self.labels) != len(R):
            raise ValueError(f"{len(self.labels)} labels for {len(R)} rungs")
        self.low = np.stack([low_pass(r, sigma) for r in R])
        self.dlow = self.low[1:] - self.low[:-1]
        self.th, self.soft = threshold(self.h, self.w, seed, pattern), soft
        self._e0, self._inv = self.th - np.float32(soft), np.float32(0.5 / soft)
        self._flat, self._dflat = R.reshape(-1, 3), self.dlow.reshape(-1, 3)
        self._pix = np.arange(self.h * self.w, dtype=np.intp)

    @property
    def high(self) -> np.ndarray:
        """Detail band of every rung, rung - low (computed on access)."""
        return self.rungs - self.low

    def switch(self, f) -> np.ndarray:
        """s = smoothstep(th - soft, th + soft, f), HxW: how far each pixel's detail has switched."""
        t = (np.asarray(f, np.float32) - self._e0) * self._inv
        np.clip(t, 0.0, 1.0, out=t)
        return t * t * (3.0 - 2.0 * t)

    def at(self, r) -> np.ndarray:
        """The image at ladder position r (scalar or HxW map), HxWx3 float32."""
        N, hw = self.n, self.h * self.w
        if np.ndim(r) == 0:
            r = min(max(float(r), 0.0), float(N))
            k = min(int(r), N - 1)
            f = np.float32(r - k)
            if f == 0 or f == 1:
                return self.rungs[k + int(f)].copy()
            A, B, D = self.rungs[k], self.rungs[k + 1], self.dlow[k]
        else:
            r = np.clip(np.asarray(r, np.float32), 0, N)
            if r.shape != (self.h, self.w):
                raise ValueError(f"r map is {r.shape}, the ladder {(self.h, self.w)}")
            k = np.minimum(r.astype(np.intp), N - 1)                      # r >= 0: truncation is floor
            f = r - k.astype(np.float32)
            idx = k.reshape(-1) * hw + self._pix
            A = np.take(self._flat, idx, axis=0).reshape(self.h, self.w, 3)
            B = np.take(self._flat, idx + hw, axis=0).reshape(self.h, self.w, 3)
            D = np.take(self._dflat, idx, axis=0).reshape(self.h, self.w, 3)
        s = self.switch(f)
        fs = f - s
        s3, fs3 = cv2.merge([s, s, s]), cv2.merge([fs, fs, fs])
        out = cv2.multiply(A, 1.0 - s3)                                   # (1-s)A + sB + (f-s)(lowB-lowA)
        cv2.add(out, cv2.multiply(B, s3), dst=out)
        cv2.add(out, cv2.multiply(D, fs3), dst=out)
        return out


# ============================================================================ fronts and checks
def grow_map(far: np.ndarray, p: float, lead: float = 0.45, reverse: bool = False) -> np.ndarray:
    """Per-pixel progress u in [0, 1] of a front that grows the world far pixels first.
    far: HxW farness (0 nearest .. 1 farthest, depth.farness). Forward (reverse=False):
        u = clip((p - lead*(1 - far)) / (1 - lead), 0, 1)
    p = 0 gives all 0 and p = 1 all 1; the farthest pixels grow over p in [0, 1 - lead], the nearest
    over [lead, 1]. Running p from 1 back to 0 replays it, so near pixels leave first.
    reverse=True is that replay with p running forward: u = forward(1 - p), so p = 0 is the whole
    world, p = 1 all real, and near pixels leave first (the world retreats to the horizon).
    p is a scalar. For a world that grows from the camera outwards, pass 1 - far."""
    q = 1.0 - float(p) if reverse else float(p)
    far = np.asarray(far, np.float32)
    if q <= 0.0 or q >= 1.0:                                              # exact ends
        return np.full(far.shape, 0.0 if q <= 0.0 else 1.0, np.float32)
    return np.clip((np.float32(q) - np.float32(lead) * (1 - far)) / np.float32(1 - lead), 0, 1).astype(np.float32)


def blur_dist(a: np.ndarray, b: np.ndarray, sigma: float | None = None) -> float:
    """Mean |a - b| (0-255 levels) after a Gaussian blur of sigma px (default 6*W/768)."""
    s = 6.0 * a.shape[1] / 768 if sigma is None else sigma
    return float(np.abs(low_pass(a, s) - low_pass(b, s)).mean())


def betweenness(prev: np.ndarray, mid: np.ndarray, nxt: np.ndarray, sigma: float | None = None) -> dict:
    """Is mid on the way from prev to nxt? d = blur_dist; ratio = (d(prev, mid) + d(mid, nxt)) /
    d(prev, nxt) is 1 on the way and grows with the detour. A rung is kept at ratio <= about 1.3."""
    d1, d2, d0 = blur_dist(prev, mid, sigma), blur_dist(mid, nxt, sigma), blur_dist(prev, nxt, sigma)
    return {"d_prev": d1, "d_next": d2, "d_span": d0, "ratio": (d1 + d2) / max(d0, 1e-6)}


def mid_index(rungs, labels) -> int | None:
    """Index of the SD rung (between the filter and the world) nearest the middle of the
    filter-to-world blurred distance, or None when the chain has no SD rung."""
    i0 = labels.index("filter") if "filter" in labels else 0
    cand = range(i0 + 1, len(rungs) - 1)
    if not cand:
        return None
    half = blur_dist(rungs[i0], rungs[-1]) / 2
    return min(cand, key=lambda i: abs(blur_dist(rungs[i0], rungs[i]) - half))


def _main() -> None:
    import time
    for style in plaza_picks():
        rungs, labels = plaza_chain(style)
        print(f"{style:11s} {' -> '.join(labels)}   (N = {len(rungs) - 1}, mid rung {mid_index(rungs, labels)})")
        for i in range(1, len(rungs) - 1):
            b = betweenness(rungs[i - 1], rungs[i], rungs[i + 1])
            print(f"    {labels[i]:7s} d(prev)={b['d_prev']:5.1f} d(next)={b['d_next']:5.1f} "
                  f"d(span)={b['d_span']:5.1f} ratio={b['ratio']:.2f}  d(plate)={blur_dist(rungs[0], rungs[i]):5.1f}")
    far = plaza_farness()
    for lad in (plaza_ladder("night"), plaza_ladder("vangogh", exclude={})):           # N = 3, and N = 5
        r = lad.n * grow_map(far, 0.5)
        lad.at(r)
        t = time.perf_counter()
        for _ in range(20):
            lad.at(r)
        print(f"Ladder.at(map) on {lad.w}x{lad.h}, N = {lad.n}: {(time.perf_counter() - t) / 20 * 1000:.1f} ms")


if __name__ == "__main__":
    _main()
