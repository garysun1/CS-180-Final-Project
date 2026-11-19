"""One markdown table across runs: python scripts/summarize.py out/vtest_*"""
import json
import os
import sys


def f(d, k="median"):
    return "n/a" if not d or d.get(k) is None else f"{d[k]:.2f}"


def main(runs):
    print("| style | split | alignment | SIFT inliers | seam jump before (med / p90) | after global | after local | "
          "true residual after (med / p90) | metric reliable |")
    print("|---|---|---|---|---|---|---|---|---|")
    rt = None
    for r in runs:
        p = os.path.join(r, "report.json")
        if not os.path.exists(p):
            continue
        m = json.load(open(p))
        sd, tr = m["seam_drift_px"], m["true_residual_px"] or {}
        key = m["seam_final_key"]
        al = m["alignment"] or {}
        loc = sd.get("after_local") if "+local" in al.get("method", "") else None
        split = m.get("split", "line")
        if split == "depth":
            split += " (near)" if (m.get("depth") or {}).get("near_restyled") else " (far)"
        print(f"| {m['style']} | {split} | {al.get('method', 'none')} | {al.get('n_inliers', 0)} | "
              f"{f(sd['before'])} / {f(sd['before'], 'p90')} | {f(sd.get('after_global'))} | "
              f"{f(loc) if loc else '(rejected)' if 'after_local' in sd else '-'} | "
              f"{f(tr.get(key))} / {f(tr.get(key), 'p90')} | {sd[key].get('reliable')} |")
        rt = rt or m["people_roundtrip"]
    if rt:
        print()
        print("| people round trip (same for every style) | with shadow ratio | without |")
        print("|---|---|---|")
        print(f"| PSNR vs original footage, dB | {rt['psnr_shadow']:.2f} | {rt['psnr_noshadow']:.2f} |")
        print(f"| mean abs error near people (0-255) | {rt['mae_ring_shadow']:.2f} | {rt['mae_ring_noshadow']:.2f} |")
        print(f"| frames evaluated | {rt['n_frames']} | |")


if __name__ == "__main__":
    main(sys.argv[1:])
