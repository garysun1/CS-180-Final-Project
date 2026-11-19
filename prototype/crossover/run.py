"""End-to-end pipeline.

    python -m crossover.run --video data/sample/vtest.avi --style century --perturb --out out/vtest_century

Writes the intermediate images, final videos, check-in figure and report.json / report.md to --out.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import cv2
import numpy as np

from .align import align
from .animate import make_animation
from .background import heatmap_image, median_background
from .composite import ShadowRatio, composite, glow_overlay
from .depth import (DEFAULT_MODEL, DepthSplit, contour_points, depth_vis, estimate_disparity, farness,
                    load_depth, refine)
from .figures import breakdown_tile, checkin_figure, seam_crops
from .line import Line, band_weight, side_weight
from .masks import BgDiffMasker, PngMasks
from .metrics import RoundTrip, seam_drift, seam_params, true_residual
from .perturb import make_perturbation
from .styles import STYLES, PersonStyler, apply_style
from .video_io import VideoWriter, iter_frames, probe, to_float, to_uint8


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Cross-the-line restyled video from a tripod clip.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    g = ap.add_argument_group("restyle")
    g.add_argument("--style", choices=STYLES, default="century", help="CPU stand-in restyle")
    g.add_argument("--restyled", help="restyled clean plate PNG (e.g. from the GPU notebook); overrides --style")
    g.add_argument("--style-name", help="label for --restyled images (default: file name)")
    g.add_argument("--perturb", action="store_true", help="inject known synthetic drift (tests alignment)")
    g.add_argument("--seed", type=int, default=0)
    g = ap.add_argument_group("alignment")
    g.add_argument("--align", choices=["auto", "sift", "ecc", "sift+ecc", "none"], default="auto")
    g.add_argument("--local-warp", action="store_true", help="dense flow refinement in a band around the line")
    g = ap.add_argument_group("people + composite")
    g.add_argument("--masks", help="dir of SAM 3 masks 00000.png ... (default: CPU background difference)")
    g.add_argument("--person-style", choices=["filmed", "matched", "both"], default="both")
    g.add_argument("--person-match", choices=["learned", "reinhard"], default="learned",
                   help="how people are matched to styles without an exact person function")
    g.add_argument("--no-shadow", action="store_true")
    g.add_argument("--no-anim", action="store_true", help="no procedural snow / caustics")
    g = ap.add_argument_group("seam")
    g.add_argument("--split", choices=["line", "depth"], default="line",
                   help="line: real | restyled across a line. depth: near real, far restyled (or --depth-near)")
    g.add_argument("--line", default="0.5,0,0.5,1", help="x0,y0,x1,y1 as fractions (default: vertical centre)")
    g.add_argument("--seam", choices=["hard", "feather", "glow"], default=None,
                   help="default: glow for --split line, feather for --split depth")
    g.add_argument("--feather", type=float, default=None, help="line seam feather width px (default 3 px @768w)")
    g.add_argument("--sweep", type=float, default=0.0,
                   help="animate the seam: line -> amplitude as fraction of width; depth -> in farness units")
    g.add_argument("--depth", default="auto", help="'auto' = Depth Anything V2 Small on the clean plate, "
                   "or a .npy/.png map (see --depth-kind)")
    g.add_argument("--depth-kind", choices=["disparity", "depth"], default="disparity")
    g.add_argument("--depth-model", default=DEFAULT_MODEL)
    g.add_argument("--depth-refine", action="store_true",
                   help="guided-filter the depth with the clean plate (off by default: it smeared thin objects)")
    g.add_argument("--depth-split", type=float, default=0.5, help="fraction of the plate (by depth) that is restyled")
    g.add_argument("--depth-band", type=float, default=0.08, help="softness of the depth transition (farness units)")
    g.add_argument("--depth-near", action="store_true", help="restyle what is NEAR the camera instead")
    g = ap.add_argument_group("clip")
    g.add_argument("--scale", type=float, default=1.0)
    g.add_argument("--max-frames", type=int, default=None)
    g.add_argument("--bg-samples", type=int, default=150)
    g.add_argument("--no-breakdown", action="store_true")
    g.add_argument("--roundtrip-every", type=int, default=5, help="evaluate the people round-trip every N frames")
    return ap.parse_args(argv)


def main(argv=None) -> dict:
    a = parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    P = lambda name: os.path.join(a.out, name)
    t0 = time.time()
    timings = {}
    info = probe(a.video, a.scale)
    W, H = info.width, info.height
    s = W / 768.0
    print(f"[crossover] {a.video}: {info.src_width}x{info.src_height} -> {W}x{H}, {info.n_frames} frames @ {info.fps:.2f} fps")

    # 1. clean plate ------------------------------------------------------------------------
    bg, heat, bg_meta = median_background(a.video, a.scale, a.bg_samples, a.masks, max_frames=a.max_frames)
    cv2.imwrite(P("clean_bg.png"), bg)
    cv2.imwrite(P("motion_heatmap.png"), heatmap_image(heat))
    timings["background_s"] = round(time.time() - t0, 2)

    # 1b. depth of the clean plate (depth split only) - computed ONCE, like the restyle -------
    ds, disp, depth_src = None, None, None
    if a.split == "depth":
        t = time.time()
        if a.depth == "auto":
            disp, depth_src = estimate_disparity(bg, a.depth_model), "Depth Anything V2 Small (ONNX, CPU)"
        else:
            disp, depth_src = load_depth(a.depth, (W, H), a.depth_kind), a.depth
        if a.depth_refine:
            disp = refine(disp, bg)
        ds = DepthSplit(farness(disp), a.depth_split, a.depth_band, a.depth_near)
        np.save(P("depth_disparity.npy"), disp)
        cv2.imwrite(P("depth.png"), depth_vis(ds.f, ds.tau))
        timings["depth_s"] = round(time.time() - t, 2)

    # 2. restyle once ----------------------------------------------------------------------
    t = time.time()
    if a.restyled:
        R_raw = cv2.imread(a.restyled)
        if R_raw is None:
            raise FileNotFoundError(a.restyled)
        style = a.style_name or os.path.splitext(os.path.basename(a.restyled))[0]
        if R_raw.shape[:2] != (H, W):
            ar_in, ar_bg = R_raw.shape[1] / R_raw.shape[0], W / H
            if abs(ar_in - ar_bg) > 0.01:
                print(f"[crossover] WARNING restyled aspect {ar_in:.3f} != clip aspect {ar_bg:.3f}; resizing anyway")
            R_raw = cv2.resize(R_raw, (W, H), interpolation=cv2.INTER_AREA if R_raw.shape[1] > W else cv2.INTER_CUBIC)
    else:
        style = a.style
        R_raw = apply_style(bg, style, a.seed)
    cv2.imwrite(P("restyled_raw.png"), R_raw)
    pert = make_perturbation(W, H, seed=a.seed) if a.perturb else None
    R_in = pert.apply(R_raw) if pert else R_raw
    if pert:
        cv2.imwrite(P("restyled_perturbed.png"), R_in)
    timings["restyle_s"] = round(time.time() - t, 2)

    # 3. re-align --------------------------------------------------------------------------
    t = time.time()
    line = Line.from_spec(a.line, W, H)
    if ds is not None:   # the seam is the depth contour: sample it, and build a band around it
        prm = seam_params(W)
        pts = contour_points(ds.f, ds.tau, prm["stride"], prm["patch"] / 2 + 1)
        rmask = ds.background_weight() >= 0.5
        edge = cv2.morphologyEx(rmask.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        band = band_weight(cv2.distanceTransform(1 - edge, cv2.DIST_L2, 5), 0.15 * W)
        sline = None
    else:
        pts, rmask, band, sline = None, None, None, line
    seam = {"before": seam_drift(bg, R_in, sline, points=pts)}
    truth = {"before": true_residual(pert, sline, W, H, points=pts)} if pert else None
    if a.align == "none":
        R, ares = R_in, None
    else:
        ares_g = align(R_in, bg, a.align, local_warp=False, line=sline)
        seam["after_global"] = seam_drift(bg, ares_g.apply(R_in), sline, points=pts)
        if truth is not None:
            truth["after_global"] = true_residual(pert, sline, W, H, ares_g, points=pts)
        ares = align(R_in, bg, a.align, local_warp=True, line=sline, band=band) if a.local_warp else ares_g
        R = ares.apply(R_in)
        if a.local_warp:
            seam["after_local"] = seam_drift(bg, R, sline, points=pts)
            if truth is not None:
                truth["after_local"] = true_residual(pert, sline, W, H, ares, points=pts)
    cv2.imwrite(P("restyled_aligned.png"), R)
    final_key = "after_local" if a.local_warp and a.align != "none" else ("after_global" if a.align != "none" else "before")
    crops = seam_crops(bg, R_in, R, sline, avoid=heat, mask=rmask, points=pts)
    cv2.imwrite(P("seam_crops_before_after.png"), crops)
    timings["align_s"] = round(time.time() - t, 2)

    # 4 + 5. people + composite, one pass over the clip -----------------------------------
    t = time.time()
    Bf, Rf = to_float(bg), to_float(R)
    masker = PngMasks(a.masks, clean_bg=bg) if a.masks else BgDiffMasker(bg)
    shadow = ShadowRatio(Bf)
    styler = PersonStyler(style if not a.restyled else "custom", bg, R, seed=a.seed, match=a.person_match)
    Qm = to_float(styler(bg))        # what the clean background looks like after the person-style
    feather = a.feather if a.feather is not None else 3.0 * s
    seam_mode = a.seam or ("glow" if a.split == "line" else "feather")
    anim = None if a.no_anim else make_animation(style, W, H, info.fps, a.seed)
    depth_glow = None
    want_f = a.person_style in ("filmed", "both")
    want_m = a.person_style in ("matched", "both")
    writers = {}
    if want_f:
        writers["filmed"] = VideoWriter(P("final.mp4"), W, H, info.fps)
    if want_m:
        writers["matched"] = VideoWriter(P("final_matched.mp4"), W, H, info.fps)
    if not a.no_breakdown:
        writers["breakdown"] = VideoWriter(P("breakdown.mp4"), 2 * (W // 2), 2 * (H // 2), info.fps)
    rt = RoundTrip()
    ones = np.ones((H, W), np.float32)
    static_d = line.signed_distance(W, H)
    n_total = info.n_frames if a.max_frames is None else min(info.n_frames, a.max_frames)
    best = {"score": -1.0}
    band_px = 12 * s
    for i, frame, alpha in masker.iter_alphas(iter_frames(a.video, a.scale, a.max_frames)):
        F = to_float(frame)
        if ds is not None:
            if a.sweep:
                ds.set_shift(a.sweep * np.sin(2 * np.pi * i / max(1, n_total)))
            wgt = ds.weight(alpha, i, disp)
            if seam_mode == "hard":
                wgt = (wgt >= 0.5).astype(np.float32)
            glow = None
            if seam_mode == "glow":
                if depth_glow is None or a.sweep:
                    depth_glow = glow_overlay(ds.contour_distance(), 2.0 * s)
                glow = depth_glow * (1 - alpha)[..., None]     # the contour does not cut through people
            d = None
        else:
            if a.sweep:
                off = a.sweep * W * np.sin(2 * np.pi * i / max(1, n_total))
                d = line.shifted(off * line.normal[0], off * line.normal[1]).signed_distance(W, H)
            else:
                d = static_d
            wgt = side_weight(d, "hard" if seam_mode == "hard" else "feather", feather)
            glow = glow_overlay(d, 2.0 * s) if seam_mode == "glow" else None
        S, near = (ones, ones) if a.no_shadow else shadow(F, alpha)
        gain = anim.plate_gain(i) if anim else None
        Rt = Rf * gain[..., None] if gain is not None else Rf
        front = anim.front_layer(i) if anim else None
        outs_f = {}
        if want_f:
            outs_f["filmed"] = composite(F, Rt, alpha, S, wgt, None, glow, Q=Bf)
        if want_m:
            outs_f["matched"] = composite(F, Rt, alpha, S, wgt, to_float(styler(frame)), glow, Q=Qm)
        outs = {}
        for k, o in outs_f.items():
            if front is not None:                              # e.g. snow, in front of people
                rgb, af = front
                o = o + (af * wgt)[..., None] * (rgb - o)
            outs[k] = to_uint8(o)
        for k, im in outs.items():
            writers[k].write(im)
        show = outs.get("matched", outs.get("filmed"))
        if "breakdown" in writers:
            writers["breakdown"].write(breakdown_tile(frame, bg, alpha, show))
        if i % a.roundtrip_every == 0:
            # plain alpha blend on purpose: with edge decontamination and R = B the result would be
            # F inside the mask no matter what alpha is, i.e. the test would be tautological
            rs = to_uint8(composite(F, Bf, alpha, S, ones))
            rn = to_uint8(composite(F, Bf, alpha, ones, ones))
            rt.add(frame, rs, rn, alpha, near > 0.5)
        if d is not None:
            score = float(alpha[np.abs(d) < band_px].sum())    # someone straddling the line
        else:                                                  # people both real and restyled
            score = float(np.sqrt((alpha * wgt).sum() * (alpha * (1 - wgt)).sum()))
        if score > best["score"]:
            best = {"score": score, "idx": i, "frame": frame.copy(), "alpha": alpha.copy(),
                    **{k: v.copy() for k, v in outs.items()}}
    for wr in writers.values():
        wr.close()
    timings["composite_s"] = round(time.time() - t, 2)

    # figures + report ---------------------------------------------------------------------
    for k in ("filmed", "matched"):
        if k in best:
            cv2.imwrite(P(f"composite_frame_{k}.png"), best[k])
    cv2.imwrite(P("composite_frame_original.png"), best["frame"])
    fmt = lambda d: "n/a" if d is None or d.get("median") is None else f"{d['median']:.2f} / {d['p90']:.2f}"
    rts = rt.summary()
    cap = [f"seam edge jump, px (median / p90):  before {fmt(seam['before'])}   after {fmt(seam[final_key])}"
           + ("" if seam[final_key].get("reliable", True) else "  [metric flagged unreliable]")]
    if truth:
        cap.append(f"true residual (known drift), px:     before {fmt(truth['before'])}   after {fmt(truth[final_key])}")
    if rts:
        cap.append(f"people round-trip PSNR: {rts['psnr_shadow']:.1f} dB with shadow ratio, {rts['psnr_noshadow']:.1f} dB without")
    dsum = ds.summary() if ds is not None else None
    if dsum:
        cap.append(f"depth: person height vs disparity at feet r = {dsum.get('height_vs_disparity_pearson_r')}"
                   f"   person-weight flicker {dsum.get('person_weight_flicker_raw')} -> "
                   f"{dsum.get('person_weight_flicker_ema')} (tracker EMA)")
    split_txt = "line" if ds is None else ("depth: near restyled" if a.depth_near else "depth: far restyled")
    title = f"Cross the line - style '{style}'" + (" (synthetic drift injected)" if pert else "") + \
        f"  |  {split_txt}  |  align: {ares.method if ares else 'none'}"
    panel_c = (depth_vis(ds.f, ds.base_tau), "(c) depth of the clean plate + split contour") if ds is not None else None
    checkin_figure(P("checkin_figure.png"), best["frame"], bg, R, crops,
                   best.get("matched", best.get("filmed")), title, "\n".join(cap), panel_c=panel_c,
                   composite_title="(e) composite: real | restyled" if ds is None else
                   ("(e) composite: near restyled | far real" if a.depth_near else "(e) composite: near real | far restyled"))

    report = {
        "video": a.video, "out": a.out, "style": style, "restyled_path": a.restyled, "perturb": bool(pert),
        "size": [W, H], "fps": info.fps, "frames_processed": n_total, "background": bg_meta,
        "split": a.split, "line": [line.x0, line.y0, line.x1, line.y1] if ds is None else None,
        "seam_mode": seam_mode, "depth": dict(dsum, source=depth_src) if dsum else None,
        "animation": None if anim is None else style,
        "alignment": ares.summary() if ares else None,
        "alignment_global_only": ares_g.summary() if a.align != "none" and a.local_warp else None,
        "seam_drift_px": {k: {kk: vv for kk, vv in v.items() if kk != "patches_xy_dx_dy_resp"} for k, v in seam.items()},
        "true_residual_px": truth, "seam_final_key": final_key,
        "people_roundtrip": rts, "masks": "sam3_png" if a.masks else "bg_difference",
        "person_match": {"mode": styler.mode, "color_fit_psnr_db": styler.fit_psnr,
                         "edit_explained_by_colour": styler.explained_frac},
        "showcase_frame": best.get("idx"), "timings": timings, "total_s": round(time.time() - t0, 2),
    }
    with open(P("report.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    with open(P("report.md"), "w") as fh:
        fh.write(report_md(report))
    print(report_md(report))
    return report


def report_md(r: dict) -> str:
    def row(name, d):
        if d is None or d.get("median") is None:
            return f"| {name} | n/a | n/a | {d.get('n', 0) if d else 0} |"
        rel = "" if d.get("reliable", True) else " (unreliable)"
        return f"| {name} | {d['median']:.2f} | {d['p90']:.2f} | {d['n']}{rel} |"
    L = [f"# {r['style']} - {os.path.basename(r['video'])}", ""]
    if r["alignment"]:
        al = r["alignment"]
        L += [f"Alignment: **{al['method']}**, SIFT inliers {al['n_inliers']}/{al['n_matches']}, "
              f"ECC cc {al['ecc_cc'] if al['ecc_cc'] is None else round(al['ecc_cc'], 3)}. Notes: {'; '.join(al['notes']) or '-'}", ""]
    L += ["| seam edge jump (measured) | median px | p90 px | patches |", "|---|---|---|---|"]
    for k, v in r["seam_drift_px"].items():
        L.append(row(k, v))
    if r["true_residual_px"]:
        L += ["", "| true residual (known drift) | median px | p90 px | points |", "|---|---|---|---|"]
        for k, v in r["true_residual_px"].items():
            L.append(row(k, v))
    rt = r["people_roundtrip"]
    if rt:
        L += ["", "| people round-trip (composite onto unedited plate vs original) | with shadow ratio | without |",
              "|---|---|---|",
              f"| PSNR dB | {rt['psnr_shadow']:.2f} | {rt['psnr_noshadow']:.2f} |",
              f"| mean abs err, near people (ring), 0-255 | {rt['mae_ring_shadow']:.2f} | {rt['mae_ring_noshadow']:.2f} |",
              f"| mean abs err, everywhere outside masks | {rt['mae_outside_shadow']:.2f} | {rt['mae_outside_noshadow']:.2f} |",
              f"| frames evaluated | {rt['n_frames']} | |"]
    if r.get("depth"):
        dd = r["depth"]
        L += ["", f"Depth split ({dd['source']}): tau {dd['tau']}, band {dd['band']}, near restyled {dd['near_restyled']}",
              "", "| depth check | value |", "|---|---|",
              f"| person height vs disparity at feet, Pearson r | {dd.get('height_vs_disparity_pearson_r')} "
              f"(n = {dd.get('height_vs_disparity_n')}) |",
              f"| person weight change per frame, raw | {dd.get('person_weight_flicker_raw')} |",
              f"| person weight change per frame, tracker EMA | {dd.get('person_weight_flicker_ema')} |"]
    L += ["", f"Timings: {r['timings']}, total {r['total_s']} s", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
