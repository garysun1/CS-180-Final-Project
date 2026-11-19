"""A ~50 s showcase cut from existing outputs: title, the seam, seasons waves, walker trails, the depth
split, end card - with crossfades and captions.

    python scripts/showcase.py -o out/showcase.mp4
    python scripts/showcase.py -o out/showcase2.mp4 --segments segments.json   # [[video, start, end, speed, caption], ...]
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crossover.video_io import VideoWriter  # noqa: E402

W, H, FPS = 768, 576, 10.0
BG = (15, 18, 23)            # RGB, the page's background
INK, SEPIA, SEAM = (232, 235, 239), (212, 176, 122), (191, 233, 255)
FONT = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
FONT_REG = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans"))

SEGMENTS = [  # (video, start s, end s, speed, caption)
    ("out/vtest_gen_winter/final_matched.mp4", 46, 52, 1, "Cross the line, step into winter"),
    ("out/fx_seasons/seasons.mp4", 4.5, 70.5, 3, "Seasons roll in from the horizon"),
    ("out/fx_trails/trails.mp4", 30, 54, 2, "Walkers bring winter with them"),
    ("out/vtest_gen_1920s_depth/final_matched.mp4", 46, 53, 1, "Far away, it is 1920"),
]


def font(size, bold=True):
    return ImageFont.truetype(FONT if bold else FONT_REG, size)


def card(lines, glow_title=False):
    """A title / end card. lines = [(text, size, colour, bold)]."""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    sizes = [d.textbbox((0, 0), t, font=font(s, b)) for t, s, _, b in lines]
    total = sum(b[3] - b[1] for b in sizes) + 18 * (len(lines) - 1)
    y = (H - total) // 2
    for (t, s, c, b), bb in zip(lines, sizes):
        w = bb[2] - bb[0]
        x = (W - w) // 2
        if glow_title and lines.index((t, s, c, b)) == 0:
            # left half in ink, right half in sepia, split by a glowing seam
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).text((x, y - bb[1]), t, font=font(s, b), fill=255)
            m = np.array(mask, np.float32)[..., None] / 255
            arr = np.array(im, np.float32)
            colour = np.where(np.arange(W)[None, :, None] < W // 2, np.array(INK), np.array(SEPIA))
            arr = arr * (1 - m) + colour * m
            seam = np.exp(-((np.arange(W) - W / 2) / 2.0) ** 2)[None, :, None]
            band = (np.abs(np.arange(H) - (y + (bb[3] - bb[1]) / 2)) < (bb[3] - bb[1]) * 0.9)[:, None, None]
            arr = arr + seam * band * (np.array(SEAM) - arr) * 0.9
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
            d = ImageDraw.Draw(im)
        else:
            d.text((x, y - bb[1]), t, font=font(s, b), fill=c)
        y += (bb[3] - bb[1]) + 18
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def caption(frame, text):
    im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(im, "RGBA")
    f = font(22)
    bb = d.textbbox((0, 0), text, font=f)
    pad, x, y = 10, 16, H - 16 - (bb[3] - bb[1]) - 20
    d.rectangle((x, y, x + bb[2] - bb[0] + 2 * pad, y + bb[3] - bb[1] + 2 * pad), fill=(15, 18, 23, 190))
    d.text((x + pad, y + pad - bb[1]), text, font=f, fill=INK)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def fit(frame):
    """Letterbox any clip size into the W x H canvas."""
    h, w = frame.shape[:2]
    if (w, h) == (W, H):
        return frame
    s = min(W / w, H / h)
    small = cv2.resize(frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    canvas = np.full((H, W, 3), BG[::-1], np.uint8)
    y0, x0 = (H - small.shape[0]) // 2, (W - small.shape[1]) // 2
    canvas[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] = small
    return canvas


def clip_frames(path, start, end, speed, text):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start * fps))
    n = int((end - start) * fps)
    for k in range(n):
        ok, f = cap.read()
        if not ok:
            break
        if k % speed == 0:
            yield caption(fit(f), text)
    cap.release()


def still(img, seconds):
    for _ in range(int(seconds * FPS)):
        yield img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="out/showcase.mp4")
    ap.add_argument("--xfade", type=int, default=6, help="crossfade length in frames")
    ap.add_argument("--segments", help="JSON list of [video, start s, end s, speed, caption]")
    a = ap.parse_args()
    segments = [tuple(x) for x in json.load(open(a.segments))] if a.segments else SEGMENTS
    title = card([("Cross the Line", 64, INK, True),
                  ("a tripod video, restyled once by an image model", 22, (179, 187, 198), False)], glow_title=True)
    end = card([("Three clips, one generated image per world.", 28, INK, True),
                ("Stable Diffusion + ControlNet, depth from Depth Anything, all on a CPU.", 18, (179, 187, 198), False),
                ("CS180 / 280A final project", 18, (130, 140, 153), False)])
    segs = [still(title, 2.5)] + [clip_frames(*s) for s in segments] + [still(end, 3.0)]
    vw = VideoWriter(a.out, W, H, FPS)
    tail: list = []
    n = 0
    for si, seg in enumerate(segs):
        frames = list(seg)
        if si == 0:   # fade in from the background colour
            bgimg = np.full((H, W, 3), BG[::-1], np.uint8)
            for k in range(min(8, len(frames))):
                frames[k] = cv2.addWeighted(bgimg, 1 - k / 8, frames[k], k / 8, 0)
        if tail:      # crossfade the previous segment's last frames into this one's first
            for k in range(min(len(tail), len(frames))):
                t = (k + 1) / (len(tail) + 1)
                frames[k] = cv2.addWeighted(tail[k], 1 - t, frames[k], t, 0)
        keep = a.xfade if si < len(segs) - 1 else 0
        body, tail = (frames[:-keep], frames[-keep:]) if keep else (frames, [])
        for f in body:
            vw.write(f)
            n += 1
    vw.close()
    print(f"wrote {a.out}: {n} frames, {n / FPS:.1f} s")


if __name__ == "__main__":
    main()
