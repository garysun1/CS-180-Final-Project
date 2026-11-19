"""Generative restyles of the clean plate on CPU: Stable Diffusion 1.5 + ControlNet (depth + canny)
+ LCM-LoRA (few-step sampling).

Unlike the colour-filter stand-ins in styles.py, a diffusion model actually changes scene content
(snow on roofs, lit windows, leaves on the lawn). Two ControlNets hold the geometry in place:
  * depth  - our own Depth Anything V2 map of the clean plate (crossover/depth.py),
  * canny  - edges of the clean plate.
Whatever drift remains is exactly what align.py exists to remove; the seam metric measures it.

    python -m crossover.generate --clean out/vtest_century/clean_bg.png \
        --depth out/vtest_depth_century/depth_disparity.npy --styles night,winter --out out/gen

Needs the optional requirements in requirements-gen.txt. One image takes about a minute on 4 cores.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import cv2
import numpy as np

BASE = "stable-diffusion-v1-5/stable-diffusion-v1-5"
CN_DEPTH = "lllyasviel/control_v11f1p_sd15_depth"
CN_CANNY = "lllyasviel/control_v11p_sd15_canny"
LCM_LORA = "latent-consistency/lcm-lora-sdv1-5"

KEEP = "same viewpoint, same buildings, empty plaza, no people"
PROMPTS = {
    "night": "the same campus plaza at night, street lamp switched on with a warm glow, lit office windows, "
             "wet pavement reflecting the lights, dark blue night sky, photograph, realistic",
    "winter": "the same campus plaza after heavy snowfall, thick white snow covering the grass lawns, the rooftops "
              "and the cars, snowy pavement with footprints, overcast winter day, photograph, realistic",
    "1920s": "the same campus plaza photographed in 1920, antique sepia photograph, cobblestone pavement, "
             "old brick buildings, period street lamp, film grain, scratches",
    "autumn": "the same campus plaza in autumn, orange and red leaves covering the lawns, autumn trees, "
              "golden hour sunlight, long shadows, photograph, realistic",
    "underwater": "the same campus plaza deep under the sea, sunken, seaweed and coral growing on the ground, "
                  "blue-green water, light rays from above, fish swimming",
    "painting": "impressionist oil painting of the campus plaza, thick visible brush strokes, Claude Monet style, "
                "vivid colors",
    "cyberpunk": "the same campus plaza as a cyberpunk city at night, glowing pink and cyan neon signs, holographic "
                 "billboards on the buildings, wet reflective pavement, rain, cinematic",
    "vangogh": "the same campus plaza as a Vincent van Gogh oil painting, swirling thick impasto brush strokes, "
               "starry night style, vivid blue and yellow",
    "overgrown": "the same campus plaza fifty years after people left, overgrown with vines, moss and tall wild grass, "
                 "cracked pavement, small trees growing through the ground, photograph, realistic",
    "anime": "the same campus plaza as a Studio Ghibli anime background painting, soft watercolor, hand-drawn, "
             "clean lines, bright summer day",
}
NEGATIVE = "people, person, crowd, pedestrians, blurry, distorted, deformed, text, watermark, frame"
# --init filter: start img2img from our colour-filter version instead of the raw plate. The filter
# gives the colour layout the model would not invent from a green lawn (white snow, dark night,
# sepia); diffusion then adds the real content (snow texture, lit windows, period details).
INIT_FILTER = {"winter": "winter", "night": "night", "1920s": "century", "underwater": "underwater",
               "painting": "painting", "autumn": "autumn", "cyberpunk": "neon", "vangogh": "painting",
               "anime": "painting", "overgrown": "overgrown"}


def control_images(clean_bgr: np.ndarray, disparity: np.ndarray):
    """(depth control, canny control) as RGB PIL images the size of the plate."""
    from PIL import Image

    lo, hi = np.percentile(disparity, [1, 99])
    d = np.clip((disparity - lo) / (hi - lo + 1e-6), 0, 1)                 # near = bright, as ControlNet expects
    depth = Image.fromarray(np.repeat((d * 255).astype(np.uint8)[..., None], 3, axis=2))
    g = cv2.GaussianBlur(cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2GRAY), (0, 0), 1.0)
    # structural edges only: dense texture edges (grass) would pin the old surface in place
    canny = Image.fromarray(np.repeat(cv2.Canny(g, 100, 200)[..., None], 3, axis=2))
    return depth, canny


def load_pipeline(threads: int | None = None):
    import torch
    from diffusers import ControlNetModel, LCMScheduler, StableDiffusionControlNetImg2ImgPipeline

    torch.set_num_threads(threads or os.cpu_count() or 4)
    kw = dict(torch_dtype=torch.float32, variant="fp16")                    # fp16 files, upcast for CPU
    cns = [ControlNetModel.from_pretrained(CN_DEPTH, **kw), ControlNetModel.from_pretrained(CN_CANNY, **kw)]
    pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
        BASE, controlnet=cns, safety_checker=None, requires_safety_checker=False, **kw)
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    pipe.load_lora_weights(LCM_LORA)
    pipe.fuse_lora()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def restyle(pipe, clean_bgr: np.ndarray, depth_img, canny_img, prompt: str, seed: int, strength: float,
            steps: int = 8, guidance: float = 1.5, cn_scales=(0.9, 0.45), init_bgr: np.ndarray | None = None) -> np.ndarray:
    """init_bgr: starting image for img2img (default: the clean plate). Controls always come from the
    clean plate, so geometry is anchored to the real scene either way."""
    import torch
    from PIL import Image

    h, w = clean_bgr.shape[:2]
    W8, H8 = w - w % 8, h - h % 8
    start = clean_bgr if init_bgr is None else init_bgr
    src = Image.fromarray(cv2.cvtColor(start[:H8, :W8], cv2.COLOR_BGR2RGB))
    out = pipe(prompt=f"{prompt}, {KEEP}", negative_prompt=NEGATIVE, image=src,
               control_image=[depth_img.crop((0, 0, W8, H8)), canny_img.crop((0, 0, W8, H8))],
               strength=strength, num_inference_steps=steps, guidance_scale=guidance,
               controlnet_conditioning_scale=list(cn_scales),
               generator=torch.Generator("cpu").manual_seed(seed)).images[0]
    rgb = np.array(out)
    if (W8, H8) != (w, h):
        rgb = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generative restyles of the clean plate (SD 1.5 + ControlNet, CPU).")
    ap.add_argument("--clean", required=True, help="clean plate PNG")
    ap.add_argument("--depth", required=True, help="disparity .npy of the clean plate (near = high)")
    ap.add_argument("--styles", default=",".join(PROMPTS), help=f"comma list from {list(PROMPTS)}")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--strengths", default="0.75")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--guidance", type=float, default=1.5)
    ap.add_argument("--init", choices=["clean", "filter"], default="clean",
                    help="img2img start: the clean plate, or our colour-filter version of it (when one exists)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-existing", action="store_true",
                    help="skip candidates already in meta.json with a PNG on disk (resume after an interruption)")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    clean = cv2.imread(a.clean)
    disp = np.load(a.depth).astype(np.float32)
    if disp.shape != clean.shape[:2]:
        disp = cv2.resize(disp, (clean.shape[1], clean.shape[0]), interpolation=cv2.INTER_LINEAR)
    depth_img, canny_img = control_images(clean, disp)
    depth_img.save(os.path.join(a.out, "control_depth.png"))
    canny_img.save(os.path.join(a.out, "control_canny.png"))
    t = time.time()
    pipe = load_pipeline()
    print(f"[generate] pipeline loaded in {time.time() - t:.0f}s", flush=True)
    meta_path = os.path.join(a.out, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    from .styles import apply_style
    for style in a.styles.split(","):
        init = apply_style(clean, INIT_FILTER[style]) if a.init == "filter" and style in INIT_FILTER else None
        tag = "f" if init is not None else ""
        for seed in [int(s) for s in a.seeds.split(",")]:
            for k in [float(s) for s in a.strengths.split(",")]:
                name = f"{style}{tag}_s{seed}_k{int(round(k * 100))}"
                if a.skip_existing and name in meta and os.path.exists(os.path.join(a.out, name + ".png")):
                    print(f"[generate] {name}: exists, skipped", flush=True)
                    continue
                t = time.time()
                img = restyle(pipe, clean, depth_img, canny_img, PROMPTS[style], seed, k, a.steps, a.guidance,
                              init_bgr=init)
                cv2.imwrite(os.path.join(a.out, name + ".png"), img)
                dt = time.time() - t
                meta[name] = {"style": style, "init": "filter" if init is not None else "clean",
                              "seed": seed, "strength": k, "steps": a.steps, "guidance": a.guidance,
                              "prompt": PROMPTS[style], "negative": NEGATIVE, "seconds": round(dt, 1),
                              "base": BASE, "controlnets": [CN_DEPTH, CN_CANNY], "lora": LCM_LORA}
                with open(meta_path + ".tmp", "w") as fh:
                    json.dump(meta, fh, indent=1)
                os.replace(meta_path + ".tmp", meta_path)
                print(f"[generate] {name}: {dt:.0f}s", flush=True)


if __name__ == "__main__":
    main()
