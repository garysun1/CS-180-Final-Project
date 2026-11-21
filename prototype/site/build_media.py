"""Build web media + data.json for the 'Cross the Line' artifact page from the project's real outputs."""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

SITE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(SITE)                     # the crossover project (site/ lives inside it)
sys.path.insert(0, PROJ)
from crossover.animate import make_animation  # noqa: E402
from crossover.composite import ShadowRatio, composite  # noqa: E402
from crossover.depth import farness  # noqa: E402
from crossover.masks import BgDiffMasker  # noqa: E402
from crossover.styles import PersonStyler  # noqa: E402
from crossover.video_io import iter_frames, to_float, to_uint8  # noqa: E402

MEDIA = os.path.join(SITE, "media")
INPUTS = os.path.join(SITE, "inputs")            # figure crops made by hand during development (versioned)
OUT = os.path.join(PROJ, "out")
VIDEO = os.path.join(PROJ, "data/sample/vtest.avi")
SHOW = 530                      # showcase frame (people on both sides of the line in every run)
LINE_STYLES = ["century", "night", "painting", "ink", "winter", "underwater", "thermal", "neon", "sketch"]
os.makedirs(MEDIA, exist_ok=True)


def jpg(img, name, maxw=1200, q=84):
    if img.shape[1] > maxw:
        img = cv2.resize(img, (maxw, int(img.shape[0] * maxw / img.shape[1])), interpolation=cv2.INTER_AREA)
    p = os.path.join(MEDIA, name)
    cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, q, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    return p


def need(p):
    im = cv2.imread(p)
    if im is None:
        raise FileNotFoundError(p)
    return im


# ---- stills ---------------------------------------------------------------------------------
bg = need(f"{OUT}/vtest_century/clean_bg.png")
jpg(bg, "clean_plate.jpg")
jpg(need(f"{OUT}/vtest_century/motion_heatmap.png"), "heatmap.jpg")
jpg(need(f"{OUT}/vtest_century/seam_crops_before_after.png"), "seam_crops.jpg", maxw=1000, q=90)
jpg(need(f"{OUT}/vtest_depth_century/depth.png"), "depth_map.jpg")

# halo: plain blend | + clean-plate keying | + edge refinement (final 5 px inner band)
h3, ic = need(f"{INPUTS}/halo3_couple.png"), need(f"{INPUTS}/inner_cmp.png")
pw = (h3.shape[1] - 16) // 3
panels = [h3[:, 0:pw], h3[:, pw + 8:2 * pw + 8], ic[:, pw + 8:2 * pw + 8]]
sep = np.full((h3.shape[0], 10, 3), 14, np.uint8)
jpg(np.hstack([panels[0], sep, panels[1], sep, panels[2]]), "halo_fix.jpg", maxw=1100, q=88)

# the failed first painting vs the structure-preserving one, around the lamp post
def first_painting(img):
    """Our first 'painting' stand-in, exactly as originally written (oil filter + stylization)."""
    size = max(3, int(round(5 * img.shape[1] / 768)))
    out = cv2.stylization(cv2.xphoto.oilPainting(img, size, 1), sigma_s=40, sigma_r=0.35)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


old_paint = first_painting(bg)
new_paint = need(f"{OUT}/vtest_painting/restyled_raw.png")
crop = lambda im: cv2.resize(im[120:340, 300:520], None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
sep = np.full((440, 10, 3), 14, np.uint8)
jpg(np.hstack([crop(bg), sep, crop(old_paint), sep, crop(new_paint)]), "painting_fail.jpg", maxw=1100, q=86)

# depth: raw network output vs our guided-filter 'refinement' (2x2 grid: [bg, raw], [refined, overlay])
dc = need(f"{INPUTS}/depth_cmp.jpg")
h, w = dc.shape[0] // 2, dc.shape[1] // 2
sep = np.full((h, 10, 3), 14, np.uint8)
jpg(np.hstack([dc[:h, w:], sep, dc[h:, :w]]), "depth_refine.jpg", maxw=1100)

# ---- 'drag the line' frames: original + fully restyled showcase frame per style -----------
alpha_show = frame_show = None
for i, f, a in BgDiffMasker(bg).iter_alphas(iter_frames(VIDEO, max_frames=SHOW + 2)):
    if i == SHOW:
        frame_show, alpha_show = f, a
        break
jpg(frame_show, "frame_original.jpg", q=88)
F, Bf = to_float(frame_show), to_float(bg)
ones = np.ones(bg.shape[:2], np.float32)
S, _ = ShadowRatio(Bf)(F, alpha_show)
for st in LINE_STYLES:
    R = need(f"{OUT}/vtest_{st}/restyled_aligned.png")
    styler = PersonStyler(st, bg, R, match="reinhard")      # as used when these runs were made
    Rf = to_float(R)
    anim = make_animation(st, bg.shape[1], bg.shape[0], 10.0)
    if anim is not None and anim.plate_gain(SHOW) is not None:
        Rf = Rf * anim.plate_gain(SHOW)[..., None]
    out = composite(F, Rf, alpha_show, S, ones, to_float(styler(frame_show)), None, Q=to_float(styler(bg)))
    if anim is not None and anim.front_layer(SHOW) is not None:
        rgb, af = anim.front_layer(SHOW)
        out = out + af[..., None] * (rgb - out)
    jpg(to_uint8(out), f"frame_{st}.jpg", q=88)

# ---- generative (SD 1.5 + ControlNet) restyles ---------------------------------------------
SD = ["winter", "night", "1920s", "autumn", "underwater", "vangogh", "cyberpunk"]
FILTER_OF = {"winter": "winter", "night": "night", "1920s": "century", "autumn": "autumn", "underwater": "underwater",
             "vangogh": "painting", "cyberpunk": "neon"}
PICKS = dict(l.split() for l in open(f"{OUT}/gen/picks.txt") if l.strip())
from crossover.styles import apply_style  # noqa: E402
for st in SD:
    R = need(f"{OUT}/vtest_gen_{st}/restyled_aligned.png")
    styler = PersonStyler("custom", bg, R, match="learned")
    Rf = to_float(R)
    anim = make_animation(st, bg.shape[1], bg.shape[0], 10.0)
    if anim is not None and anim.plate_gain(SHOW) is not None:
        Rf = Rf * anim.plate_gain(SHOW)[..., None]
    out = composite(F, Rf, alpha_show, S, ones, to_float(styler(frame_show)), None, Q=to_float(styler(bg)))
    if anim is not None and anim.front_layer(SHOW) is not None:
        rgb, af = anim.front_layer(SHOW)
        out = out + af[..., None] * (rgb - out)
    jpg(to_uint8(out), f"frame_sd_{st}.jpg", q=88)
    gen = need(f"{OUT}/gen/{PICKS[st]}.png")
    jpg(gen, f"plate_sd_{st}.jpg", q=88)
    filt = apply_style(bg, FILTER_OF[st])
    sep = np.full((bg.shape[0], 12, 3), 14, np.uint8)
    jpg(np.hstack([bg, sep, filt, sep, gen]), f"compare_{st}.jpg", maxw=1500, q=86)

from crossover.figures import mask_overlay  # noqa: E402
jpg(mask_overlay(frame_show, alpha_show), "mask_overlay.jpg", q=88)

# ---- depth widget inputs ---------------------------------------------------------------------
disp = np.load(f"{OUT}/vtest_depth_century/depth_disparity.npy")
fz = farness(disp)
cv2.imwrite(os.path.join(MEDIA, "farness.png"), (fz * 255).round().astype(np.uint8))
for st in ["century", "night", "winter", "thermal"]:
    jpg(need(f"{OUT}/vtest_{st}/restyled_raw.png"), f"plate_{st}.jpg", q=88)


# ---- videos ----------------------------------------------------------------------------------
def video(src, name, start=None, dur=None, crf=27, poster_t=1.0, speed=1.0, width=None):
    dst = os.path.join(MEDIA, name)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", src]
    if dur is not None:
        cmd += ["-t", str(dur)]
    vf = []
    if speed != 1.0:
        vf.append(f"setpts=PTS/{speed}")
    if width:
        vf.append(f"scale={width}:-2")
    if vf:
        cmd += ["-filter:v", ",".join(vf)]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-an", dst]
    subprocess.run(cmd, check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(poster_t), "-i", dst, "-frames:v", "1",
                    "-q:v", "4", dst.replace(".mp4", "_poster.jpg")], check=True)
    return dst


video(f"{OUT}/demo_reel.mp4", "reel.mp4", crf=27, poster_t=17.0)
subprocess.run([sys.executable, f"{PROJ}/scripts/demo_reel.py"] + [f"{OUT}/vtest_gen_{s}" for s in SD] +
               [f"{OUT}/vtest_gen_1920s_depth", "-o", f"{OUT}/demo_reel_sd.mp4", "--start", "48", "--dur", "5"],
               check=True, stdout=subprocess.DEVNULL)
video(f"{OUT}/demo_reel_sd.mp4", "reel_sd.mp4", crf=26, poster_t=2.5)
video(f"{OUT}/vtest_gen_1920s_depth/final_matched.mp4", "depth_sd_1920s.mp4", start=40, dur=25, poster_t=13.0)
# the trailer (python -m crossover.trailer): a web encode that keeps its soundtrack; the poster is her
# moment on the line, the middle of the 'scan' shot in the trailer's edit list
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{OUT}/trailer.mp4", "-c:v", "libx264", "-preset", "slow",
                "-crf", "28", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                os.path.join(MEDIA, "trailer.mp4")], check=True)
edl = json.load(open(f"{OUT}/trailer_edl.json"))
scan = next((s for s in edl["shots"] if s["name"] == "scan"), None)
poster_t = scan["start_s"] + 0.5 * scan["frames"] / edl["fps"] if scan else 15.3
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{poster_t:.2f}", "-i", os.path.join(MEDIA, "trailer.mp4"),
                "-frames:v", "1", "-q:v", "3", os.path.join(MEDIA, "trailer_poster.jpg")], check=True)
# the 15-second loop (python -m crossover.trailer --edit teaser): the page's muted hero
video(f"{OUT}/teaser_wide.mp4", "teaser_wide.mp4", crf=27, poster_t=4.6)
video(f"{OUT}/fx_crowd04_shards/shards.mp4", "fx_london_shards.mp4", crf=28, poster_t=12.0, width=768)
video(f"{OUT}/fx_car_seasons/seasons.mp4", "fx_highway.mp4", crf=28, poster_t=15.0, speed=1.5, width=768)
video(f"{OUT}/fx_vtest_windows/windows.mp4", "fx_windows.mp4", start=0, dur=32, crf=28, poster_t=10.0, speed=2.0)
video(f"{OUT}/fx_vtest_portal/portal.mp4", "fx_portal.mp4", start=10, dur=40, crf=28, poster_t=8.0, speed=2.0)
video(f"{OUT}/fx_vtest_shards/shards.mp4", "fx_plaza_shards.mp4", start=10, dur=36, crf=28, poster_t=9.0, speed=2.0)
# Reality Melts (python -m crossover.trailer --edit melt): the one-take loop where each world grows in
video(f"{OUT}/melt.mp4", "fx_melt.mp4", crf=28, poster_t=8.2)
video(f"{OUT}/fx_trails/trails.mp4", "fx_trails.mp4", start=28, dur=26, crf=28, poster_t=12.0)
video(f"{OUT}/vtest_century/breakdown.mp4", "breakdown.mp4", start=40, dur=25, poster_t=12.0)
video(f"{OUT}/vtest_depth_night_sweep/final_matched.mp4", "depth_sweep.mp4", crf=28, poster_t=58.0)
video(f"{OUT}/vtest_depth_thermal_near/final_matched.mp4", "depth_thermal_near.mp4", start=40, dur=25, poster_t=10.0)

# ---- data.json (every number on the page comes from here) -----------------------------------
def r2(x):
    return None if x is None else round(float(x), 2)


rows = []
for st in LINE_STYLES + ["depth_century"]:
    m = json.load(open(f"{OUT}/vtest_{st}/report.json"))
    sd, tr, key, al = m["seam_drift_px"], m["true_residual_px"] or {}, m["seam_final_key"], m["alignment"] or {}
    local_kept = "+local" in al.get("method", "")
    rows.append({
        "id": st, "style": m["style"], "split": m.get("split", "line"),
        "method": al.get("method"), "sift_inliers": al.get("n_inliers"),
        "seam_before": r2(sd["before"]["median"]), "seam_before_p90": r2(sd["before"]["p90"]),
        "seam_global": r2(sd["after_global"]["median"]),
        "seam_local": r2(sd["after_local"]["median"]) if local_kept else None,
        "seam_final": r2(sd[key]["median"]), "seam_final_p90": r2(sd[key]["p90"]),
        "true_before": r2(tr.get("before", {}).get("median")),
        "true_final": r2(tr.get(key, {}).get("median")), "true_final_p90": r2(tr.get(key, {}).get("p90")),
        "local_kept": local_kept, "notes": al.get("notes", []),
    })
meta = json.load(open(f"{OUT}/gen/meta.json"))
sd_rows = []
for st in SD:
    m = json.load(open(f"{OUT}/vtest_gen_{st}/report.json"))
    g = meta[PICKS[st]]
    al = m["alignment"]
    sd_rows.append({"id": "sd_" + st, "style": st, "pick": PICKS[st], "init": g["init"],
                    "init_filter": FILTER_OF[st], "strength": g["strength"], "seconds": round(g["seconds"]),
                    "kept_unwarped": al["method"].startswith("none"), "sift_inliers": al["n_inliers"],
                    "notes": al["notes"], "seam_measured": r2(m["seam_drift_px"]["before"]["median"]),
                    "explained": m["person_match"]["edit_explained_by_colour"],
                    "fit_psnr": m["person_match"]["color_fit_psnr_db"], "prompt": g["prompt"]})
from crossover.colormap import LocalAffineColor  # noqa: E402
night_filter_explained = LocalAffineColor().fit(bg, need(f"{OUT}/vtest_night/restyled_raw.png")).explained_frac
rt = json.load(open(f"{OUT}/vtest_century/report.json"))["people_roundtrip"]
dep = json.load(open(f"{OUT}/vtest_depth_century/report.json"))["depth"]
data = {
    "rows": rows,
    "sd": sd_rows,
    "night_filter_explained": night_filter_explained,
    "roundtrip": {k: r2(v) for k, v in rt.items()},
    "depth": {"r": dep["height_vs_disparity_pearson_r"], "n": dep["height_vs_disparity_n"],
              "flicker_raw": dep["person_weight_flicker_raw"], "flicker_ema": dep["person_weight_flicker_ema"],
              "tau": dep["tau"], "band": dep["band"]},
    "frames": {"n": 795, "fps": 10, "w": int(bg.shape[1]), "h": int(bg.shape[0]), "showcase": SHOW},
}
json.dump(data, open(os.path.join(SITE, "data.json"), "w"), indent=1)

total = 0
for fn in sorted(os.listdir(MEDIA)):
    sz = os.path.getsize(os.path.join(MEDIA, fn))
    total += sz
    print(f"{fn:32s} {sz / 1024:8.0f} KB")
print(f"total media folder {total / 1048576:.1f} MB (make_page.py checks what the page references)")
