"""Restyle one background image in several styles and composite each with the depth seam.

Stand-in for the team's restyle step, used to judge how the depth seam looks.
No re-alignment is done, so any geometry drift from the editor shows at the seam.

    python depth/restyle.py IMAGE --depth OUT/depth.npz --out OUTDIR --dist 16
"""
import argparse
import base64
import io
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image

ENDPOINT = os.environ.get(
    "FLUX_EDIT_URL",
    "https://hackutd-wm-garysun.openai.azure.com/openai/deployments/flux-kontext-pro/images/edits"
    "?api-version=2025-04-01-preview",
)
KEEP = (" Keep the exact same composition and camera angle, with the gate, pillars, railings,"
        " trees and pavement in exactly the same positions and shapes.")
STYLES = {
    "night": "Change the scene to night with a deep starry sky and the globe lamps glowing warm.",
    "winter": "Change the season to deep winter: snow on the ground, trees and gate, overcast sky.",
    "autumn": "Change the season to peak autumn: orange and red foliage, fallen leaves on the ground.",
    "1900s": "Make this look like a photograph from 1905: sepia toned, soft, grainy, aged print.",
    "oil_painting": "Turn this into a thick impasto impressionist oil painting with visible brush strokes.",
    "watercolor": "Turn this into a loose, delicate watercolor painting on textured paper.",
    "underwater": "Make the scene underwater: blue-green water, light rays from above, fish, coral growing on the stone.",
    "cyberpunk": "Make this a rainy cyberpunk night: neon signs, wet reflective ground, purple and teal light.",
}


def restyle(image_path, prompt, size):
    with open(image_path, "rb") as f:
        r = requests.post(
            ENDPOINT,
            headers={"api-key": os.environ.get("AZURE_API_KEY", "dummy")},
            files={"image": ("plate.jpg", f, "image/jpeg")},
            data={"model": "flux-kontext-pro", "prompt": prompt + KEEP, "size": size},
            timeout=300,
        )
    r.raise_for_status()
    png = base64.b64decode(r.json()["data"][0]["b64_json"])
    return Image.open(io.BytesIO(png)).convert("RGB")


def composite(real, styled, d, t, band=0.0):
    if band > 0:
        a = np.clip((d - (t - band / 2)) / band, 0, 1)
        a = a * a * (3 - 2 * a)
    else:
        a = (d > t).astype(np.float32)
    a = cv2.GaussianBlur(a, (0, 0), 0.7)[..., None]  # anti-alias the cut
    return (real * (1 - a) + styled * a).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--depth", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dist", type=float, nargs="+", default=[16])
    ap.add_argument("--size", default="1024x768")
    ap.add_argument("--styles", nargs="+", default=list(STYLES))
    args = ap.parse_args()
    out = Path(args.out)
    (out / "styled").mkdir(parents=True, exist_ok=True)

    real = np.asarray(Image.open(args.image).convert("RGB"))
    h, w = real.shape[:2]
    r = np.load(args.depth)["r"]

    def one(name):
        path = out / "styled" / f"{name}.jpg"
        if not path.exists():
            img = restyle(args.image, STYLES[name], args.size)
            print(name, "returned", img.size)
            img.resize((w, h), Image.LANCZOS).save(path, quality=95)
        return name

    with ThreadPoolExecutor(4) as ex:
        for name in ex.map(one, args.styles):
            styled = np.asarray(Image.open(out / "styled" / f"{name}.jpg"))
            for t in args.dist:
                Image.fromarray(composite(real, styled, r, t)).save(out / f"{name}_{t:g}m.jpg", quality=92)


if __name__ == "__main__":
    main()
