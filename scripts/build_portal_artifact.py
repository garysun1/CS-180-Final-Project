"""Build the hosted demo of the portal kiosk: the page, the kiosk's own JS, and recorded scenes. Each
scene has its clean plate, Stable Diffusion worlds made offline (each with the paper's local colour
field for people), a depth map for the depth rule, and what Stable Diffusion was given. The camera and
the world server are off; people come from the kiosk's background-difference mask.

Each world also gets its ladder for the page's Grow seam (crossover/morph.py): media/{sid}_{style}_r1.jpg,
the exact image img2img started from (the world's colour filter of the plate), and, where lower-strength
SD images of the world are on disk (the plaza), media/{sid}_{style}_r2.jpg, the one nearest the middle
of the filter-to-world distance. scenes.json lists them as worlds[i].ladder = [{src, n}].

    python scripts/build_portal_artifact.py OUT_DIR [--harness]

Needs the clips (scripts/fetch_sample.sh, scripts/fetch_clips.sh), their clean plates, depth maps and
generated worlds in out/clips/<clip>/ (crossover.prepare, crossover.generate), and ffmpeg. --harness also writes harness.html (the
page wrapped like a published artifact, with a similar content security policy) and, for the colour
parity test, media/*_lacref.png. Neither is published: publish.json lists the files to publish.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crossover import morph  # noqa: E402
from crossover.colormap import LocalAffineColor  # noqa: E402
from crossover.depth import farness  # noqa: E402

PORTAL = os.path.join(ROOT, "portal")
LABELS = {"vangogh": "Van Gogh", "cyberpunk": "Cyberpunk", "winter": "Winter", "night": "Night",
          "1920s": "1920s", "autumn": "Autumn", "underwater": "Underwater", "overgrown": "Overgrown",
          "anime": "Anime", "comic": "Comic"}
ORDER = ["vangogh", "cyberpunk", "winter", "night", "1920s", "autumn", "underwater", "overgrown"]
# start: where the clip is cut from the source; start_time: where the page starts playing it (clip time).
# The plaza opens 5 s before a walker crosses the line (vtest 59.4 s, found with by hand).
# ladder: the gen dirs searched for lower-strength SD rungs of each world (default: gen alone).
SCENES = [
    dict(id="plaza", name="Plaza", video="data/sample/vtest.avi", start=35, dur=40, start_time=19.4,
         plate="out/clips/vtest/clean_bg.png", gen="out/clips/vtest/gen",
         depth="out/clips/vtest/depth_disparity.npy", start_world="Winter", tau=0.45,
         portal=dict(x=0.62, y=0.45, r=0.2), ladder=morph.GEN_DIRS),
    dict(id="crowd", name="Crowd", video="data/clips/crowd04.mp4", start=0, dur=None, start_time=2.0,
         plate="out/clips/crowd04/clean_bg.png", gen="out/clips/crowd04/gen",
         depth="out/clips/crowd04/depth_disparity.npy", start_world="Cyberpunk", tau=0.5,
         portal=dict(x=0.5, y=0.75, r=0.2)),
    dict(id="street", name="Street", video="data/clips/cartraffic01.mp4", start=0, dur=None, start_time=0.0,
         plate="out/clips/cartraffic01/clean_bg.png", gen="out/clips/cartraffic01/gen",
         depth="out/clips/cartraffic01/depth_disparity.npy", start_world="Cyberpunk", tau=0.5,
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
NOT_PUBLISHED = ("harness.html", "page.html", "publish.json")


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


def world_image(sc: dict, style: str, stem: str, size: tuple[int, int]) -> np.ndarray:
    """The generated world (gen/<stem>.png, as listed in gen/picks.txt), at the page's size."""
    img = cv2.imread(os.path.join(ROOT, sc["gen"], stem + ".png"))
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


def colour_field(plate: np.ndarray, world: np.ndarray) -> tuple[dict, LocalAffineColor]:
    """The paper's person colour mapping (PersonStyler 'learned' = LocalAffineColor at strength 0.9),
    exported as an RGB tile grid for the shader: {gx, gy, a: gy*gx*3*4 floats, explained}."""
    lac = LocalAffineColor(strength=0.9).fit(plate, world)
    a = lac.export_rgb()
    return {"gx": lac.gx, "gy": lac.gy, "a": [round(float(v), 4) for v in a.reshape(-1)],
            "explained": lac.explained_frac}, lac


def far_png(disparity: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, float]:
    """Farness (0 near .. 1 far) as 16 bits in R/G and its gradient magnitude in B, so the page can
    draw a constant-width contour. Stored at half the frame size (the page filters it up); the
    gradient is per FRAME pixel. Returns the BGR image for cv2.imwrite and the B scale."""
    half = (size[0] // 2, size[1] // 2)
    f = farness(cv2.resize(disparity.astype(np.float32), half, interpolation=cv2.INTER_AREA))
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3) / 8
    g = cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 1.0) / 2         # per frame pixel
    gmax = float(max(1e-4, np.percentile(g, 99.9)))
    q = np.round(np.clip(f, 0, 1) * 65535).astype(np.uint32)
    hi, lo = (q >> 8).astype(np.uint8), (q & 255).astype(np.uint8)
    b = np.round(np.clip(g / gmax, 0, 1) * 255).astype(np.uint8)
    return np.dstack([b, lo, hi]), gmax


def gen_meta(sc: dict, stem: str) -> dict | None:
    path = os.path.join(ROOT, sc["gen"], "meta.json")
    if not os.path.exists(path):
        return None
    m = json.load(open(path)).get(stem)
    if not m:
        return None
    return {"seconds": round(float(m.get("seconds", 0))), "strength": m.get("strength"), "steps": m.get("steps"),
            "guidance": m.get("guidance")}


def ladder_rungs(sc: dict, style: str, stem: str, plate: np.ndarray, world: np.ndarray) -> list[tuple[str, object, np.ndarray]]:
    """The page's rungs between the plate and a world, as (tag, n, image): ('r1', 'filter', the exact
    img2img start image, styles.apply_style(plate, INIT_FILTER[style]) via morph.chain), then, if the
    scene has lower-strength SD images of the world (same seed and schedule, minus morph.EXCLUDE),
    ('r2', n, the one nearest the middle of the filter-to-world blurred distance, morph.mid_index)."""
    dirs = tuple(sc.get("ladder", (sc["gen"],)))
    try:
        mids = [r for r in morph.sd_rungs(style, stem, dirs, ROOT, pick_dir=sc["gen"]) if r.key not in morph.EXCLUDE]
    except KeyError:                                   # no meta.json entry for the pick: filter rung only
        mids = []
    rungs, labels = morph.chain(style, plate, world, mids)
    out = []
    if "filter" in labels:
        out.append(("r1", "filter", rungs[labels.index("filter")]))
    i = morph.mid_index(rungs, labels)
    if i is not None:
        out.append(("r2", int(labels[i][1:]), rungs[i]))
    return out


def write_rung(path: str, img: np.ndarray) -> int:
    """JPEG q85, or q80 when a grainy rung would pass 150 KB. Returns the file size."""
    img = np.clip(np.rint(img), 0, 255).astype(np.uint8)
    for q in (85, 80):
        cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if os.path.getsize(path) <= 150_000:
            break
    return os.path.getsize(path)


def thumb(src: str, dst: str, width: int = 320) -> bool:
    img = cv2.imread(src)
    if img is None:
        return False
    img = cv2.resize(img, (width, round(img.shape[0] * width / img.shape[1])), interpolation=cv2.INTER_AREA)
    cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return True


def build(out: str, harness: bool = False) -> tuple[dict, list, dict]:
    """Returns the size of every file written, the files to publish, and the ladder rungs' sizes."""
    media = os.path.join(out, "media")
    os.makedirs(media, exist_ok=True)
    for name in JS:
        shutil.copy(os.path.join(PORTAL, name), os.path.join(out, name))
    shutil.copy(os.path.join(PORTAL, "artifact", "page.html"), os.path.join(out, "page.html"))
    scenes, rung_sizes = [], {}
    for sc in SCENES:
        plate = cv2.imread(os.path.join(ROOT, sc["plate"]))
        if plate is None:
            raise SystemExit(f"missing clean plate {sc['plate']}")
        h, w = plate.shape[:2]
        sid = sc["id"]
        clip = f"media/{sid}.mp4"
        encode_clip(os.path.join(ROOT, sc["video"]), os.path.join(out, clip), w, h, sc["start"], sc["dur"])
        cv2.imwrite(os.path.join(out, f"media/{sid}_plate.jpg"), plate, [cv2.IMWRITE_JPEG_QUALITY, 92])
        worlds = []
        for style, stem in picks(os.path.join(ROOT, sc["gen"])):
            img = world_image(sc, style, stem, (w, h))
            rel = f"media/{sid}_{style}.jpg"
            cv2.imwrite(os.path.join(out, rel), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
            colour, lac = colour_field(plate, img)
            world = {"name": LABELS.get(style, style), "src": rel, "colour": colour, "gen": gen_meta(sc, stem)}
            ladder = []
            for tag, n, rung in ladder_rungs(sc, style, stem, plate, img):
                rrel = f"media/{sid}_{style}_{tag}.jpg"
                rung_sizes[rrel] = write_rung(os.path.join(out, rrel), rung)
                ladder.append({"src": rrel, "n": n})
            if ladder:
                world["ladder"] = ladder
            if morph.PATTERN.get(style) == "dots":     # its detail grows in halftone dots
                world["pattern"] = "dots"
            worlds.append(world)
            if harness:      # the person colour of the plate, for the page's colour parity test
                cv2.imwrite(os.path.join(media, f"{sid}_{style}_lacref.png"), lac.apply(plate))
        entry = {"id": sid, "name": sc["name"], "clip": clip, "plate": f"media/{sid}_plate.jpg", "worlds": worlds,
                 "startWorld": sc["start_world"], "startTime": sc["start_time"], "portal": sc["portal"],
                 "line": dict(x=0.5, y=0.5, angle=0), "tau": sc["tau"]}
        disp_path = os.path.join(ROOT, sc["depth"])
        if os.path.exists(disp_path):
            img, gmax = far_png(np.load(disp_path), (w, h))
            cv2.imwrite(os.path.join(media, f"{sid}_far.png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            entry.update(far=f"media/{sid}_far.png", farGmax=round(gmax, 6))
        gd = os.path.join(ROOT, sc["gen"])
        if thumb(os.path.join(gd, "control_depth.png"), os.path.join(media, f"{sid}_sd_depth.jpg")) and \
                thumb(os.path.join(gd, "control_canny.png"), os.path.join(media, f"{sid}_sd_canny.jpg")):
            entry["sd"] = {"depth": f"media/{sid}_sd_depth.jpg", "canny": f"media/{sid}_sd_canny.jpg"}
        scenes.append(entry)
    with open(os.path.join(out, "scenes.json"), "w") as f:
        json.dump(scenes, f, separators=(",", ":"))
    if harness:
        with open(os.path.join(out, "page.html")) as f:
            page = f.read()
        with open(os.path.join(out, "harness.html"), "w") as f:
            f.write(SKELETON.format(csp=CSP, page=page))
    sizes, publish = {}, []
    for dp, _, fs in os.walk(out):
        for fn in fs:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, out)
            sizes[rel] = os.path.getsize(p)
            if rel not in NOT_PUBLISHED and not rel.endswith("_lacref.png"):
                publish.append(rel)
    with open(os.path.join(out, "publish.json"), "w") as f:
        json.dump(sorted(publish), f, indent=1)
    return sizes, sorted(publish), rung_sizes


PUBLISH_BUDGET = 12.5e6     # bytes; the artifact limit is 16 MB


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("--harness", action="store_true")
    a = ap.parse_args(argv)
    sizes, publish, rungs = build(a.out, a.harness)
    total = sum(sizes.values())
    for k in sorted(sizes):
        print(f"{sizes[k] / 1e6:7.2f} MB  {k}")
    print(f"{total / 1e6:7.2f} MB  total, largest {max(sizes.values()) / 1e6:.2f} MB")
    print(f"{sum(rungs.values()) / 1e6:7.2f} MB  added by {len(rungs)} ladder rungs "
          f"(largest {max(rungs.values(), default=0) / 1e3:.0f} KB)")
    pub = sum(sizes[k] for k in publish)
    print(f"{pub / 1e6:7.2f} MB  published in {len(publish)} files (budget {PUBLISH_BUDGET / 1e6:.1f} MB)")
    if pub > PUBLISH_BUDGET:
        print("over the page budget: drop rungs or re-encode")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
