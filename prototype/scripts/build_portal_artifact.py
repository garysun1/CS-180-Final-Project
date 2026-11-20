"""Build the hosted demo of the portal kiosk: the page, the kiosk's own JS, and recorded scenes, each
with its clean plate and Stable Diffusion worlds made offline. The camera and the world server are
off; people come from the kiosk's background-difference mask.

    python scripts/build_portal_artifact.py OUT_DIR [--harness]

Needs the clips (scripts/fetch_sample.sh, scripts/fetch_clips.sh), their clean plates and generated
worlds in out/ (run_generative_demos.sh), and ffmpeg. --harness also writes harness.html, the page
wrapped like a published artifact with a similar content security policy, for local testing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTAL = os.path.join(ROOT, "portal")
LABELS = {"vangogh": "Van Gogh", "cyberpunk": "Cyberpunk", "winter": "Winter", "night": "Night",
          "1920s": "1920s", "autumn": "Autumn", "underwater": "Underwater", "overgrown": "Overgrown",
          "anime": "Anime", "comic": "Comic"}
ORDER = ["vangogh", "cyberpunk", "winter", "night", "1920s", "autumn", "underwater", "overgrown"]
SCENES = [
    dict(id="plaza", name="Plaza", video="data/sample/vtest.avi", start=0, dur=40,
         plate="out/vtest_gen_1920s/clean_bg.png", gen="out/gen", start_world="Van Gogh",
         portal=dict(x=0.62, y=0.45, r=0.15)),
    dict(id="crowd", name="Crowd", video="data/clips/crowd04.mp4", start=0, dur=None,
         plate="out/clips/crowd04/clean_bg.png", gen="out/clips/crowd04/gen", start_world="Van Gogh",
         portal=dict(x=0.5, y=0.75, r=0.18)),
    dict(id="street", name="Street", video="data/clips/cartraffic01.mp4", start=0, dur=None,
         plate="out/clips/cartraffic01/clean_bg.png", gen="out/clips/cartraffic01/gen", start_world="Cyberpunk",
         portal=dict(x=0.55, y=0.62, r=0.2)),
]
JS = ["app.js", "compositor.js", "plate.js", "audio.js"]      # segment.js is not needed: no segmenter here
CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net/npm/ "
       "https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
       "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; worker-src blob:")
SKELETON = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,'
            'initial-scale=1,viewport-fit=cover"><meta http-equiv="Content-Security-Policy" content="{csp}"><style>'
            ':root{{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}}'
            'body{{margin:0;font:14px system-ui}}img{{max-width:100%}}[hidden]{{display:none!important}}'
            '</style></head><body>{page}</body></html>')


def picks(gen_dir: str) -> list[tuple[str, str]]:
    """(style, file stem) pairs from picks.txt, in a fixed order."""
    with open(os.path.join(gen_dir, "picks.txt")) as f:
        rows = [ln.split() for ln in f if ln.strip()]
    found = {style: stem for style, stem in rows}
    return [(s, found[s]) for s in ORDER if s in found]


def encode_clip(src: str, dst: str, w: int, h: int, start: float, dur: float | None) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-i", src]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-vf", f"scale={w}:{h}:flags=lanczos,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "slow",
            "-crf", "24", "-profile:v", "high", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)


def build(out: str, harness: bool = False) -> dict:
    media = os.path.join(out, "media")
    os.makedirs(media, exist_ok=True)
    for name in JS:
        shutil.copy(os.path.join(PORTAL, name), os.path.join(out, name))
    shutil.copy(os.path.join(PORTAL, "artifact", "page.html"), os.path.join(out, "page.html"))
    scenes = []
    for sc in SCENES:
        plate = cv2.imread(os.path.join(ROOT, sc["plate"]))
        if plate is None:
            raise SystemExit(f"missing clean plate {sc['plate']}")
        h, w = plate.shape[:2]
        clip = f"media/{sc['id']}.mp4"
        encode_clip(os.path.join(ROOT, sc["video"]), os.path.join(out, clip), w, h, sc["start"], sc["dur"])
        cv2.imwrite(os.path.join(out, f"media/{sc['id']}_plate.jpg"), plate, [cv2.IMWRITE_JPEG_QUALITY, 92])
        worlds = []
        for style, stem in picks(os.path.join(ROOT, sc["gen"])):
            img = cv2.imread(os.path.join(ROOT, sc["gen"], stem + ".png"))
            img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
            rel = f"media/{sc['id']}_{style}.jpg"
            cv2.imwrite(os.path.join(out, rel), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
            worlds.append({"name": LABELS.get(style, style), "src": rel})
        scenes.append({"id": sc["id"], "name": sc["name"], "clip": clip, "plate": f"media/{sc['id']}_plate.jpg",
                       "worlds": worlds, "startWorld": sc["start_world"], "portal": sc["portal"],
                       "line": dict(x=0.5, y=0.5, angle=0)})
    with open(os.path.join(out, "scenes.json"), "w") as f:
        json.dump(scenes, f, indent=1)
    if harness:
        with open(os.path.join(out, "page.html")) as f:
            page = f.read()
        with open(os.path.join(out, "harness.html"), "w") as f:
            f.write(SKELETON.format(csp=CSP, page=page))
    sizes = {}
    for dp, _, fs in os.walk(out):
        for fn in fs:
            p = os.path.join(dp, fn)
            sizes[os.path.relpath(p, out)] = os.path.getsize(p)
    return sizes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("--harness", action="store_true")
    a = ap.parse_args(argv)
    sizes = build(a.out, a.harness)
    total = sum(sizes.values())
    for k in sorted(sizes):
        print(f"{sizes[k] / 1e6:7.2f} MB  {k}")
    print(f"{total / 1e6:7.2f} MB  total, largest {max(sizes.values()) / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
