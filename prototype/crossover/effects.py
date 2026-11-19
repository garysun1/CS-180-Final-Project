"""Seam-free effects built on the same compositing: only the per-pixel weight w changes.

  seasons : the scene morphs through several generated worlds over time. Each new world arrives as a
            wave travelling from the horizon toward the camera (driven by the depth map), with a
            glowing wavefront. People change when the wave reaches the ground under their feet.
  trails  : every passer-by carries the other world with them and leaves a trail on the ground
            that slowly fades back to reality.
  shards  : the frame cracks into glowing glass shards; each shows a world and they flip one by one.
            A person walking across a crack is split between worlds.
  windows : the world stays as filmed, but every person is a cut-out window into another world.
  portal  : a glowing ring opens on the ground where people walk; inside is another world, and
            anyone whose feet are inside it changes.

    python -m crossover.effects seasons --out out/fx_seasons
    python -m crossover.effects trails --world winter --out out/fx_trails

Inputs default to the outputs of the demo scripts: the clean plate, the generated worlds listed in
out/gen/picks.txt, and the Depth Anything disparity of the clean plate.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import cv2
import numpy as np

from .animate import make_animation
from .composite import ShadowRatio, composite, glow_overlay
from .depth import DepthSplit, farness, smoothstep
from .figures import label
from .masks import BgDiffMasker
from .styles import PersonStyler
from .video_io import VideoWriter, iter_frames, probe, to_float, to_uint8

NAMES = {"real": "Today", "autumn": "Autumn", "winter": "Winter", "night": "Night", "1920s": "1920",
         "underwater": "Underwater", "cyberpunk": "Cyberpunk", "vangogh": "Van Gogh", "overgrown": "Overgrown",
         "anime": "Anime"}


class World:
    """One generated world: its plate, how people are recoloured into it, and its animation."""

    def __init__(self, name: str, bg: np.ndarray, plate: np.ndarray | None, fps: float):
        self.name = name
        self.real = plate is None
        if not self.real:
            self.Rf = to_float(plate)
            self.styler = PersonStyler("custom", bg, plate, match="learned")
            self.Q = to_float(self.styler(bg))
            self.anim = make_animation(name, bg.shape[1], bg.shape[0], fps)

    def render(self, i, F, frame, alpha, S, ones):
        """The whole frame in this world (people included). The real world is the filmed frame."""
        if self.real:
            return F
        R = self.Rf
        if self.anim is not None and self.anim.plate_gain(i) is not None:
            R = R * self.anim.plate_gain(i)[..., None]
        out = composite(F, R, alpha, S, ones, to_float(self.styler(frame)), None, Q=self.Q)
        if self.anim is not None and self.anim.front_layer(i) is not None:
            rgb, af = self.anim.front_layer(i)
            out = out + af[..., None] * (rgb - out)
        return out


def load_inputs(a):
    bg = cv2.imread(a.clean)
    picks = dict(l.split() for l in open(a.picks) if l.strip())
    disp = np.load(a.depth).astype(np.float32)
    return bg, picks, disp


def screen(img, glow):
    return 1 - (1 - img) * (1 - glow)


def run_seasons(a):
    bg, picks, disp = load_inputs(a)
    info = probe(a.video)
    W, H, fps = info.width, info.height, info.fps
    n = info.n_frames if a.max_frames is None else min(info.n_frames, a.max_frames)
    order = ["real"] + a.worlds.split(",")
    worlds = [World(w, bg, None if w == "real" else cv2.imread(os.path.join(a.gen, picks[w] + ".png")), fps)
              for w in order]
    f = farness(disp)
    ds = DepthSplit(f, band=a.band)
    T = len(worlds) - 1
    L = int(a.transition * fps)
    starts = [int((k + a.lead) * n / T) for k in range(T)]   # transition k: world k -> k+1
    masker, shadow = BgDiffMasker(bg), ShadowRatio(to_float(bg))
    ones = np.ones((H, W), np.float32)
    s = W / 768.0
    os.makedirs(a.out, exist_ok=True)
    vw = VideoWriter(os.path.join(a.out, "seasons.mp4"), W, H, fps)
    stills = {}
    t0 = time.time()
    for i, frame, alpha in masker.iter_alphas(iter_frames(a.video, 1.0, n)):
        F = to_float(frame)
        S, _ = shadow(F, alpha)
        k = max([j for j in range(T) if i >= starts[j]], default=-1)   # last transition that began
        if k == -1:
            out, cur = F, 0
        else:
            p = float(np.clip((i - starts[k]) / max(1, L), 0, 1))
            p = p * p * (3 - 2 * p)
            if p >= 1:
                out, cur = worlds[k + 1].render(i, F, frame, alpha, S, ones), k + 1
            else:
                ds.tau = 1.08 - 1.2 * p                   # the wavefront sweeps from far (f=1) to near (f=0)
                w = ds.weight(alpha, i, disp)
                A = worlds[k].render(i, F, frame, alpha, S, ones)
                B = worlds[k + 1].render(i, F, frame, alpha, S, ones)
                out = A + w[..., None] * (B - A)
                glow = glow_overlay(ds.contour_distance(), 2.2 * s, strength=0.75 * np.sin(np.pi * p))
                out = screen(out, glow * (1 - alpha)[..., None])
                cur = k + 1 if p >= 0.5 else k
        img = label(to_uint8(out), NAMES.get(order[cur], order[cur]))
        vw.write(img)
        if i in a.stills:
            stills[i] = img
    vw.close()
    for i, im in stills.items():
        cv2.imwrite(os.path.join(a.out, f"still_{i:04d}.png"), im)
    json.dump({"worlds": order, "transition_starts": starts, "transition_frames": L, "frames": n,
               "seconds": round(time.time() - t0, 1)}, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print(f"[seasons] {n} frames in {time.time() - t0:.0f}s -> {a.out}/seasons.mp4")


def feet(alpha: np.ndarray, min_area: float):
    """(foot x, foot y, blob height) for each person blob."""
    n, lab, st, _ = cv2.connectedComponentsWithStats((alpha > 0.5).astype(np.uint8), connectivity=8)
    out = []
    for k in range(1, n):
        x0, y0, bw, bh, area = st[k]
        if area < min_area:
            continue
        rows = max(2, int(0.08 * bh))
        ys, xs = np.nonzero(lab[y0 + bh - rows:y0 + bh, x0:x0 + bw] == k)
        fx = x0 + (float(np.median(xs)) if len(xs) else bw / 2)
        out.append((fx, float(y0 + bh - 1), float(bh)))
    return out


def trail_step(paint: np.ndarray, alpha: np.ndarray, decay: float, blur_px: float, min_area: float) -> np.ndarray:
    """One frame of the trail map: old trails fade by `decay`; each person stamps a soft ellipse on
    the ground at their feet, sized by their height (so perspective comes for free)."""
    stamp = np.zeros_like(paint)
    for fx, fy, bh in feet(alpha, min_area):
        cv2.ellipse(stamp, (int(fx), int(fy)), (max(2, int(0.55 * bh)), max(1, int(0.2 * bh))),
                    0, 0, 360, 1.0, -1, cv2.LINE_AA)
    stamp = cv2.GaussianBlur(stamp, (0, 0), blur_px)
    return np.maximum(paint * decay, stamp)


def run_trails(a):
    bg, picks, _ = load_inputs(a)
    info = probe(a.video)
    W, H, fps = info.width, info.height, info.fps
    n = info.n_frames if a.max_frames is None else min(info.n_frames, a.max_frames)
    world = World(a.world, bg, cv2.imread(os.path.join(a.gen, picks[a.world] + ".png")), fps)
    masker, shadow = BgDiffMasker(bg), ShadowRatio(to_float(bg))
    ones = np.ones((H, W), np.float32)
    s = W / 768.0
    decay = 0.5 ** (1.0 / (a.halflife * fps))
    paint = np.zeros((H, W), np.float32)
    rim_color = (1.0, 0.96, 0.85)
    os.makedirs(a.out, exist_ok=True)
    vw = VideoWriter(os.path.join(a.out, "trails.mp4"), W, H, fps)
    stills = {}
    t0 = time.time()
    for i, frame, alpha in masker.iter_alphas(iter_frames(a.video, 1.0, n)):
        F = to_float(frame)
        S, _ = shadow(F, alpha)
        paint = trail_step(paint, alpha, decay, 3.0 * s, 3e-4 * H * W)
        wb = smoothstep((paint - 0.35) / 0.35)                  # the trail on the ground
        w = alpha + (1 - alpha) * wb                            # walkers themselves are in the other world
        G = world.render(i, F, frame, alpha, S, ones)
        # fresh trail is bright (new snow), fading toward the generated ground as it thaws
        G = G + (a.fresh * paint * (1 - alpha))[..., None] * (1 - G)
        out = F + w[..., None] * (G - F)
        rim = np.exp(-((paint - 0.35) / 0.07) ** 2) * (paint > 0.05) * (1 - alpha)
        glow = (0.7 * rim)[..., None] * np.array(rim_color, np.float32)
        img = to_uint8(screen(out, glow))
        vw.write(img)
        if i in a.stills:
            stills[i] = img
    vw.close()
    for i, im in stills.items():
        cv2.imwrite(os.path.join(a.out, f"still_{i:04d}.png"), im)
    json.dump({"world": a.world, "halflife_s": a.halflife, "frames": n, "seconds": round(time.time() - t0, 1)},
              open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print(f"[trails] {n} frames in {time.time() - t0:.0f}s -> {a.out}/trails.mp4")


# ------------------------------------------------------------------------------- shared helpers
def blobs(alpha: np.ndarray, min_area: float):
    """Person blobs: list of (mask uint8, foot x, foot y, height, centroid x, centroid y)."""
    n, lab, st, cen = cv2.connectedComponentsWithStats((alpha > 0.5).astype(np.uint8), connectivity=8)
    out = []
    for k in range(1, n):
        x0, y0, bw, bh, area = st[k]
        if area < min_area:
            continue
        rows = max(2, int(0.08 * bh))
        ys, xs = np.nonzero(lab[y0 + bh - rows:y0 + bh, x0:x0 + bw] == k)
        fx = x0 + (float(np.median(xs)) if len(xs) else bw / 2)
        out.append(((lab == k).astype(np.uint8), fx, float(y0 + bh - 1), float(bh), cen[k][0], cen[k][1]))
    return out


class FeetTracker:
    """Smooths one value per person over time (nearest-centroid matching + EMA)."""

    def __init__(self, radius: float, ema: float = 0.35):
        self.radius, self.ema, self.tracks = radius, ema, []

    def update(self, items):
        """items: list of (cx, cy, value) -> smoothed values."""
        new, used, out = [], set(), []
        for cx, cy, v in items:
            best, bd = None, self.radius
            for j, (tx, ty, tv) in enumerate(self.tracks):
                d = np.hypot(tx - cx, ty - cy)
                if j not in used and d < bd:
                    best, bd = j, d
            if best is not None:
                used.add(best)
                v = (1 - self.ema) * self.tracks[best][2] + self.ema * v
            new.append((cx, cy, v))
            out.append(v)
        self.tracks = new
        return out


def load_worlds(a, names, bg, fps):
    picks = dict(l.split() for l in open(a.picks) if l.strip())
    return [World(n, bg, None if n == "real" else cv2.imread(os.path.join(a.gen, picks[n] + ".png")), fps)
            for n in names]


def frames_with_people(a, bg):
    info = probe(a.video)
    n = info.n_frames if a.max_frames is None else min(info.n_frames, a.max_frames)
    return info, n, BgDiffMasker(bg).iter_alphas(iter_frames(a.video, 1.0, n))


# ------------------------------------------------------------------------------- shards
def voronoi_cells(h: int, w: int, n: int, seed: int = 0):
    """Voronoi labels (HxW int32) from n stratified random seeds, and the seeds (n x 2, x/y)."""
    rng = np.random.default_rng(seed)
    gx = int(np.ceil(np.sqrt(n * w / h)))
    gy = int(np.ceil(n / gx))
    cells = [(i, j) for j in range(gy) for i in range(gx)]
    pick = rng.choice(len(cells), n, replace=False)
    pts = np.array([[(cells[c][0] + rng.uniform(0.15, 0.85)) * w / gx,
                     (cells[c][1] + rng.uniform(0.15, 0.85)) * h / gy] for c in pick], np.float32)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = (xs[None] - pts[:, 0, None, None]) ** 2 + (ys[None] - pts[:, 1, None, None]) ** 2
    return d2.argmin(0).astype(np.int32), pts


def cracks(labels: np.ndarray) -> np.ndarray:
    """1 on shard boundaries."""
    e = np.zeros(labels.shape, np.uint8)
    e[:, 1:] |= (labels[:, 1:] != labels[:, :-1]).astype(np.uint8)
    e[1:, :] |= (labels[1:, :] != labels[:-1, :]).astype(np.uint8)
    return e


def run_shards(a):
    bg, _, _ = load_inputs(a)
    info, n, frames = frames_with_people(a, bg)
    H, W, fps = info.height, info.width, info.fps
    names = ["real"] + a.worlds.split(",")
    worlds = load_worlds(a, names, bg, fps)
    labels, _ = voronoi_cells(H, W, a.shards, a.seed)
    K = a.shards
    rng = np.random.default_rng(a.seed + 1)
    order = rng.permutation(np.repeat(np.arange(K), max(1, int(np.ceil(n / fps / a.period / K)) + 1)))
    state = np.zeros(K, np.int32)                       # world index shown by each shard
    flips = []                                          # (start frame, shard, old, new)
    period, flip_len = max(1, int(a.period * fps)), max(1, int(0.5 * fps))
    for j, f0 in enumerate(range(int(1.0 * fps), n, period)):
        c = int(order[j % len(order)])
        new = int(rng.choice([w for w in range(len(names)) if w != state[c]]))
        flips.append((f0, c, int(state[c]), new))
        state[c] = new
    state[:] = 0
    s = W / 768.0
    crack = cracks(labels).astype(np.float32)
    crack_soft = cv2.GaussianBlur(cv2.dilate(crack, np.ones((2, 2), np.uint8)), (0, 0), 1.0 * s)
    edge_of = [cv2.GaussianBlur(cv2.dilate(((labels == c) & (crack > 0)).astype(np.float32),
                                           np.ones((3, 3), np.uint8)), (0, 0), 2.0 * s) for c in range(K)]
    glow_col = np.array([1.0, 0.95, 0.85], np.float32)
    shadow, ones = ShadowRatio(to_float(bg)), np.ones((H, W), np.float32)
    os.makedirs(a.out, exist_ok=True)
    vw = VideoWriter(os.path.join(a.out, "shards.mp4"), W, H, fps)
    stills, t0, fi = {}, time.time(), 0
    for i, frame, alpha in frames:
        while fi < len(flips) and flips[fi][0] + flip_len <= i:      # flips that finished
            state[flips[fi][1]] = flips[fi][3]
            fi += 1
        active = [fl for fl in flips[fi:] if fl[0] <= i < fl[0] + flip_len]
        old, new, t = state.copy(), state.copy(), np.zeros(K, np.float32)
        flash = np.zeros((H, W), np.float32)
        for f0, c, o, nw in active:
            p = (i - f0) / flip_len
            old[c], new[c], t[c] = o, nw, p * p * (3 - 2 * p)
            flash += edge_of[c] * (1 - p) * 2.5
        F = to_float(frame)
        S, _ = shadow(F, alpha)
        need = set(old.tolist()) | set(new.tolist())
        rend = {w: worlds[w].render(i, F, frame, alpha, S, ones) for w in need}
        po, pn, pt = old[labels], new[labels], t[labels]
        A = np.empty_like(F)
        B = np.empty_like(F)
        for w, img in rend.items():
            A[po == w] = img[po == w]
            B[pn == w] = img[pn == w]
        out = A + pt[..., None] * (B - A)
        glow = np.clip(crack_soft * 0.45 + flash, 0, 1)[..., None] * glow_col
        img = to_uint8(screen(out, glow))
        vw.write(img)
        if i in a.stills:
            stills[i] = img
    vw.close()
    for i, im in stills.items():
        cv2.imwrite(os.path.join(a.out, f"still_{i:04d}.png"), im)
    print(f"[shards] {n} frames, {len(flips)} flips, {time.time() - t0:.0f}s -> {a.out}/shards.mp4")


# ------------------------------------------------------------------------------- windows
def windows_frame(F: np.ndarray, R: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """People become cut-out windows into R; everything else stays as filmed."""
    return F + alpha[..., None] * (R - F)


def run_windows(a):
    bg, _, _ = load_inputs(a)
    info, n, frames = frames_with_people(a, bg)
    H, W, fps = info.height, info.width, info.fps
    names = a.worlds.split(",")
    worlds = load_worlds(a, names, bg, fps)
    period, fade = a.period * fps, 1.0 * fps
    rim_col = np.array([1.0, 0.97, 0.9], np.float32)
    os.makedirs(a.out, exist_ok=True)
    vw = VideoWriter(os.path.join(a.out, "windows.mp4"), W, H, fps)
    stills, t0 = {}, time.time()
    for i, frame, alpha in frames:
        k = int(i // period) % len(worlds)
        R = worlds[k].Rf
        into = i - (i // period) * period
        if into < fade and i >= period:                  # crossfade from the previous world
            Rp = worlds[(k - 1) % len(worlds)].Rf
            u = into / fade
            R = Rp + (u * u * (3 - 2 * u)) * (R - Rp)
        out = windows_frame(to_float(frame), R, alpha)
        rim = np.clip(alpha * (1 - alpha) * 4, 0, 1)
        out = screen(out, (0.8 * rim)[..., None] * rim_col)
        img = label(to_uint8(out), NAMES.get(names[k], names[k]))
        vw.write(img)
        if i in a.stills:
            stills[i] = img
    vw.close()
    for i, im in stills.items():
        cv2.imwrite(os.path.join(a.out, f"still_{i:04d}.png"), im)
    print(f"[windows] {n} frames, {time.time() - t0:.0f}s -> {a.out}/windows.mp4")


# ------------------------------------------------------------------------------- portal
def portal_q(h: int, w: int, cx: float, cy: float, r: float, squash: float) -> np.ndarray:
    """Normalised elliptical radius: <1 inside the ring, 1 on it."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.sqrt(((xs - cx) / max(r, 1e-3)) ** 2 + ((ys - cy) / max(r * squash, 1e-3)) ** 2)


def portal_weight(q: np.ndarray, soft: float = 0.06) -> np.ndarray:
    return smoothstep((1 - q) / soft + 0.5)


def run_portal(a):
    from .background import median_background
    bg, _, _ = load_inputs(a)
    info, n, frames = frames_with_people(a, bg)
    H, W, fps = info.height, info.width, info.fps
    world = load_worlds(a, [a.world], bg, fps)[0]
    # centre the ring where people walk most, on the lower part of the frame (the ground)
    _, heat, _ = median_background(a.video, max_frames=n)
    heat = cv2.GaussianBlur(heat, (0, 0), 0.04 * W)
    heat[: int(0.35 * H)] = 0
    cy, cx = np.unravel_index(int(heat.argmax()), heat.shape)
    r0 = a.radius * W
    tracker = FeetTracker(40 * W / 768.0)
    dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    shadow, ones = ShadowRatio(to_float(bg)), np.ones((H, W), np.float32)
    ring_col = np.array([float(c) for c in a.ring_color.split(",")], np.float32)
    os.makedirs(a.out, exist_ok=True)
    vw = VideoWriter(os.path.join(a.out, "portal.mp4"), W, H, fps)
    stills, t0 = {}, time.time()
    for i, frame, alpha in frames:
        tsec, tend = i / fps, (n - 1 - i) / fps
        open_ = smoothstep(np.float32(min(tsec / 2.0, tend / 1.5)))
        r = r0 * float(open_) * (1 + 0.06 * np.sin(2 * np.pi * tsec / 3.0))
        q = portal_q(H, W, cx, cy, r, a.squash)
        wb = portal_weight(q)
        wp = np.zeros((H, W), np.float32)
        bl = blobs(alpha, 3e-4 * H * W)
        if bl:
            qf = [float(q[int(min(fy, H - 1)), int(min(fx, W - 1))]) for _, fx, fy, _, _, _ in bl]
            vals = tracker.update([(cx_, cy_, float(portal_weight(np.float32(v)))) for (_, _, _, _, cx_, cy_), v in zip(bl, qf)])
            for (m, *_), v in zip(bl, vals):
                wp[cv2.dilate(m, dil).astype(bool)] = v
        w = alpha * wp + (1 - alpha) * wb
        F = to_float(frame)
        S, _ = shadow(F, alpha)
        G = world.render(i, F, frame, alpha, S, ones)
        G = G * (1 - 0.3 * np.exp(-((q - 1) / 0.15) ** 2) * (q < 1))[..., None]   # depth at the rim
        out = F + w[..., None] * (G - F)
        rim = np.exp(-((q - 1) / 0.035) ** 2) * float(open_) * (1 - alpha)          # behind people
        out = screen(out, np.clip(rim * 0.9, 0, 1)[..., None] * ring_col)
        img = to_uint8(out)
        vw.write(img)
        if i in a.stills:
            stills[i] = img
    vw.close()
    for i, im in stills.items():
        cv2.imwrite(os.path.join(a.out, f"still_{i:04d}.png"), im)
    print(f"[portal] {n} frames at ({cx},{cy}) r={r0:.0f}, {time.time() - t0:.0f}s -> {a.out}/portal.mp4")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seam-free effects: seasons waves, walker trails.")
    ap.add_argument("effect", choices=["seasons", "trails", "shards", "windows", "portal"])
    ap.add_argument("--video", default="data/sample/vtest.avi")
    ap.add_argument("--clean", default="out/vtest_century/clean_bg.png")
    ap.add_argument("--depth", default="out/vtest_depth_century/depth_disparity.npy")
    ap.add_argument("--gen", default="out/gen")
    ap.add_argument("--picks", default="out/gen/picks.txt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--stills", default="", help="comma list of frame indices to save as PNG")
    ap.add_argument("--worlds", default="autumn,winter,night,1920s", help="seasons: order after the real world")
    ap.add_argument("--transition", type=float, default=5.0, help="seasons: seconds per wave")
    ap.add_argument("--lead", type=float, default=0.3, help="seasons: where in each segment the wave starts (0-1)")
    ap.add_argument("--band", type=float, default=0.05, help="seasons: softness of the wavefront")
    ap.add_argument("--world", default="winter", help="trails: which world the walkers carry")
    ap.add_argument("--halflife", type=float, default=6.0, help="trails: seconds for a trail to fade halfway")
    ap.add_argument("--fresh", type=float, default=0.35, help="trails: how much brighter freshly painted ground is")
    ap.add_argument("--period", type=float, default=1.5, help="shards: seconds between flips; windows: per world")
    ap.add_argument("--shards", type=int, default=14, help="shards: number of glass shards")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--radius", type=float, default=0.16, help="portal: ring radius as a fraction of width")
    ap.add_argument("--squash", type=float, default=0.38, help="portal: vertical squash of the ring (perspective)")
    ap.add_argument("--ring-color", default="0.75,0.92,1.0", help="portal: ring colour, BGR 0-1")
    a = ap.parse_args(argv)
    a.stills = {int(x) for x in a.stills.split(",") if x.strip()}
    {"seasons": run_seasons, "trails": run_trails, "shards": run_shards, "windows": run_windows,
     "portal": run_portal}[a.effect](a)


if __name__ == "__main__":
    main()
