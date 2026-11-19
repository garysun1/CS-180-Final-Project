"""Synthetic test object for the depth seam: a ball rolling through a still scene.

The ball is placed in 3D on the fitted ground plane, so its true distance is
known. It is drawn with correct perspective size, hidden where the scene depth
is nearer (it passes behind pillars), and takes on the style as its distance
passes through the band.

    python depth/ball_demo.py REAL --depth depth.npz --styled a.jpg b.jpg ... --out OUTDIR
"""
import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np

from blend import band, blend_multiband
from people import fit_ground
from people_demo import apply_color, fit_color

R = 0.45  # ball radius, metres
# path on the ground: (metres right of camera, metres forward)
WAYPOINTS = [(0, 4.5), (0, 20), (4.5, 20), (-4.5, 20), (0, 20), (0, 4.5)]
PALETTE = np.array([[40, 40, 230], [245, 245, 245], [30, 200, 250], [245, 245, 245]], np.float32)  # BGR


class Scene:
    def __init__(self, z, focal):
        self.z, self.focal = z, focal
        self.h, self.w = z.shape
        n, c = fit_ground(z, focal)
        if c < 0:
            n, c = -n, -c
        self.up = -n
        self.origin = n * c  # ground point under the camera
        ez = np.array([0, 0, 1.0])
        self.fwd = ez - (ez @ n) * n
        self.fwd /= np.linalg.norm(self.fwd)
        self.right = np.cross(self.fwd, self.up)

    def ground(self, x, y):
        return self.origin + x * self.right + y * self.fwd

    def project(self, P):
        return (self.focal * P[0] / P[2] + (self.w - 1) / 2, self.focal * P[1] / P[2] + (self.h - 1) / 2)


def path(n_frames):
    pts = np.array(WAYPOINTS, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, s[-1], n_frames)
    return np.c_[np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], t


def draw_ball(img, scene, M, xy, roll, center, width, ss=2):
    """Composite the ball (and a contact shadow) into img in place. Returns its distance."""
    G = scene.ground(*xy)
    C = G + R * scene.up
    dist = float(np.linalg.norm(C))
    strength = float(band(np.array(dist), center, width).squeeze())
    f, h, w = scene.focal, scene.h, scene.w

    # contact shadow: flattened dark blob on the ground under the ball
    gu, gv = scene.project(G)
    rx = f * R / G[2] * 1.15
    ry = max(rx * abs(scene.origin @ scene.up) / np.linalg.norm(G) * 1.6, 1.5)
    x0, x1 = int(max(gu - 3 * rx, 0)), int(min(gu + 3 * rx, w))
    y0, y1 = int(max(gv - 3 * ry, 0)), int(min(gv + 3 * ry, h))
    if x1 > x0 and y1 > y0:
        uu, vv = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
        a = 0.55 * np.exp(-(((uu - gu) / rx) ** 2 + ((vv - gv) / ry) ** 2) * 1.2)
        a *= scene.z[y0:y1, x0:x1] > G[2] - 1.0  # hidden if something nearer is in the way
        img[y0:y1, x0:x1] *= (1 - a)[..., None]

    # the ball itself, ray-traced over its bounding box at ss x supersampling
    cu, cv_ = scene.project(C)
    rp = f * R / C[2] * 1.05 + 2
    x0, x1 = int(max(cu - rp, 0)), int(min(cu + rp + 1, w))
    y0, y1 = int(max(cv_ - rp, 0)), int(min(cv_ + rp + 1, h))
    if x1 <= x0 or y1 <= y0:
        return dist, strength
    us = (np.arange(x0 * ss, x1 * ss) + 0.5) / ss - 0.5
    vs = (np.arange(y0 * ss, y1 * ss) + 0.5) / ss - 0.5
    uu, vv = np.meshgrid(us, vs)
    d = np.stack([(uu - (w - 1) / 2) / f, (vv - (h - 1) / 2) / f, np.ones_like(uu)], -1)
    dd, dc = (d * d).sum(-1), d @ C
    disc = dc**2 - dd * (C @ C - R * R)
    hit = disc > 0
    t = (dc - np.sqrt(np.maximum(disc, 0))) / dd
    P = d * t[..., None]
    nrm = (P - C) / R
    zs = cv2.resize(scene.z[y0:y1, x0:x1], (uu.shape[1], uu.shape[0]), interpolation=cv2.INTER_NEAREST)
    vis = hit & (t < zs + 0.3)

    # beach-ball segments that rotate as it rolls
    ca, sa = np.cos(roll), np.sin(roll)
    ny = nrm @ scene.up * ca + nrm @ scene.fwd * sa
    nz = -(nrm @ scene.up) * sa + nrm @ scene.fwd * ca
    seg = (np.floor((np.arctan2(ny, nz) + np.pi) / (2 * np.pi) * 8).astype(int)) % 4
    light = np.array([0.45, -0.75, -0.5])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.75 * np.clip(nrm @ light, 0, 1)
    col = np.clip(PALETTE[seg] * shade[..., None], 0, 255)
    col = apply_color(col, M, strength)

    a = cv2.resize(vis.astype(np.float32), (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)[..., None]
    col = cv2.resize((col * vis[..., None]).astype(np.float32), (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + col
    return dist, strength


def label(img, text, org, scale=1.0):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 6, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--depth", required=True)
    ap.add_argument("--styled", nargs="+", required=True, help="restyled images already aligned to IMAGE")
    ap.add_argument("--out", required=True)
    ap.add_argument("--center", type=float, default=10)
    ap.add_argument("--object-band", type=float, default=4, help="metres over which the ball changes style")
    ap.add_argument("--frames", type=int, default=420)
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    real = cv2.imread(args.image)
    dd = np.load(args.depth)
    scene = Scene(dd["z"], float(dd["focal"]))
    r = dd["r"]
    xy, travelled = path(args.frames)

    names, bgs, maps = [], [], []
    for p in args.styled:
        styled = cv2.imread(p)
        names.append(Path(p).stem.replace("_aligned", ""))
        bgs.append(blend_multiband(real, styled, r, args.center).astype(np.float32))
        maps.append(fit_color(real, styled))

    # stills: several ball positions in one frame per style
    for name, bg, M in zip(names, bgs, maps):
        img, tags = bg.copy(), []
        for x, y in [(0.3, 23), (3.6, 20), (1.2, 17), (2.6, 13), (1.2, 11), (-0.3, 9), (-1.7, 7), (-3.0, 5.2)]:
            dist, _ = draw_ball(img, scene, M, (x, y), y / R, args.center, args.object_band)
            u, v = scene.project(scene.ground(x, y) + 2.4 * R * scene.up)
            if (x, y) != (3.6, 20):
                tags.append((f"{dist:.0f} m", (int(u) - 40, int(v))))
        img = img.astype(np.uint8)
        for text, org in tags:
            label(img, text, org, 0.9)
        cv2.imwrite(str(out / f"ball_positions_{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])

    # video: up to four styles side by side
    cols = 2 if len(names) > 1 else 1
    rows_ = int(np.ceil(len(names) / cols))
    cw, ch = 960, int(960 * scene.h / scene.w)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{cw * cols}x{ch * rows_}",
           "-r", str(args.fps), "-i", "-", "-pix_fmt", "yuv420p", "-crf", "21", str(out / "ball.mp4")]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(args.frames):
        grid = np.zeros((ch * rows_, cw * cols, 3), np.uint8)
        for j, (name, bg, M) in enumerate(zip(names, bgs, maps)):
            img = bg.copy()
            dist, s = draw_ball(img, scene, M, xy[k], travelled[k] / R, args.center, args.object_band)
            cell = cv2.resize(img.astype(np.uint8), (cw, ch), interpolation=cv2.INTER_AREA)
            label(cell, f"{name}   ball at {dist:4.1f} m   style {100 * s:3.0f}%", (16, 40), 0.9)
            grid[(j // cols) * ch:(j // cols + 1) * ch, (j % cols) * cw:(j % cols + 1) * cw] = cell
        ff.stdin.write(grid.tobytes())
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main()
