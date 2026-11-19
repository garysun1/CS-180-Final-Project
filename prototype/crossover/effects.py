"""Seam-free effects built on the same compositing: only the per-pixel weight w changes.

  seasons : the scene morphs through several generated worlds over time. Each new world arrives as a
            wave travelling from the horizon toward the camera (driven by the depth map), with a
            glowing wavefront. People change when the wave reaches the ground under their feet.
  trails  : every passer-by carries the other world with them and leaves a trail on the ground
            that slowly fades back to reality.

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
         "underwater": "Underwater"}


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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seam-free effects: seasons waves, walker trails.")
    ap.add_argument("effect", choices=["seasons", "trails"])
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
    a = ap.parse_args(argv)
    a.stills = {int(x) for x in a.stills.split(",") if x.strip()}
    (run_seasons if a.effect == "seasons" else run_trails)(a)


if __name__ == "__main__":
    main()
