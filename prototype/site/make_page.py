"""Render index.html from template.html + data.json. Every {{key}} is filled from the run reports."""
import json
import os
import re

SITE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(SITE, "data.json")))
R = {r["id"]: r for r in data["rows"]}
rt, dp = data["roundtrip"], data["depth"]


def px(x):
    return f"{x:.2f}"


V = {
    "data_json": json.dumps(data, separators=(",", ":")),
    "c_before": px(R["century"]["seam_before"]), "c_global": px(R["century"]["seam_global"]),
    "c_local": px(R["century"]["seam_local"]), "c_true": px(R["century"]["true_final"]),
    "c_true_before": px(R["century"]["true_before"]),
    "ink_meas": px(R["ink"]["seam_final"]), "ink_true": px(R["ink"]["true_final"]),
    "neon_true": px(R["neon"]["true_final"]), "neon_p90": px(R["neon"]["true_final_p90"]),
    "win_meas": px(R["winter"]["seam_final"]), "win_true": px(R["winter"]["true_final"]),
    "d_before": px(R["depth_century"]["seam_before"]), "d_after": px(R["depth_century"]["seam_final"]),
    "d_true": px(R["depth_century"]["true_final"]),
    "psnr_s": f"{rt['psnr_shadow']:.1f}", "psnr_n": f"{rt['psnr_noshadow']:.1f}",
    "ring_s": f"{rt['mae_ring_shadow']:.2f}", "ring_n": f"{rt['mae_ring_noshadow']:.2f}",
    "ring_pct": f"{100 * (1 - rt['mae_ring_shadow'] / rt['mae_ring_noshadow']):.0f}",
    "r": f"{dp['r']:.2f}", "rn": f"{dp['n']:,}",
    "fl_raw": f"{dp['flicker_raw']:.4f}", "fl_ema": f"{dp['flicker_ema']:.4f}",
    "good_lo": px(min(R[s]["true_final"] for s in ("century", "night", "underwater", "thermal", "sketch", "winter"))),
    "good_hi": px(max(R[s]["true_final"] for s in ("century", "night", "underwater", "thermal", "sketch", "winter"))),
    "n_frames": str(data["frames"]["n"]),
    "sd_n": str(len(data["sd"])),
    "sd_sec_lo": str(min(r["seconds"] for r in data["sd"])), "sd_sec_hi": str(max(r["seconds"] for r in data["sd"])),
    "sd_expl_lo": f"{100 * min(r['explained'] for r in data['sd']):.0f}",
    "sd_expl_hi": f"{100 * max(r['explained'] for r in data['sd']):.0f}",
    "sd_inl_lo": str(min(r["sift_inliers"] for r in data["sd"])), "sd_inl_hi": str(max(r["sift_inliers"] for r in data["sd"])),
    "sd_unwarped": str(sum(r["kept_unwarped"] for r in data["sd"])),
    "night_filter_expl": f"{100 * data['night_filter_explained']:.0f}",
}
tpl = open(os.path.join(SITE, "template.html")).read()
missing = set(re.findall(r"\{\{(\w+)\}\}", tpl)) - set(V)
if missing:
    raise SystemExit(f"template keys without values: {missing}")
html = re.sub(r"\{\{(\w+)\}\}", lambda m: V[m.group(1)], tpl)
open(os.path.join(SITE, "index.html"), "w").write(html)
print("wrote index.html", len(html) // 1024, "KB")
