"""Stills of "Reality Melts" before the full render: four per transition (at p = .2/.4/.6/.8 of it),
the hold and the loop point, labelled, in one sheet.

    python scripts/melt_stills.py                               # out/review/melt_sheet.jpg
    python scripts/melt_stills.py --size 720x720 --out out/review/melt_sheet_square.jpg
    python scripts/melt_stills.py --only winter,night --dump /tmp/stills   # some rows; PNGs too

Each still is the frame as rendered (accents and chips included, before finish()); --plain leaves the
accents out. Run from the project root.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crossover import melt as M  # noqa: E402
from crossover import trailer as T  # noqa: E402

PS = (0.2, 0.4, 0.6, 0.8)


def rows(m: M.Melt) -> list[tuple[str, list[tuple[str, int]]]]:
    """(row title, [(still label, frame)]) for every transition, the hold and the loop point."""
    out = []
    for c in M.STORY:
        if c.kind in ("real", "hold"):
            continue
        if c.kind == "grow":
            a, b, _ = M.GROW[c.world]
            b = max(b, M.LIGHTS[1]) if c.world == "night" else b       # night: its lights too
        elif c.kind == "hop":
            a, b = c.b0, c.b0 + M.HOP_MORPH
        else:
            a, b = c.b0, c.b1
        out.append((c.name, [(f"p{p:.1f}", int(round((a + p * (b - a)) * m.fpb))) for p in PS]))
        if c.world == "night" and c.kind == "grow":                      # the lamps coming on
            a, b = M.LIGHTS
            out.append(("night lights", [(f"p{p:.2f}", int(round((a + p * (b - a)) * m.fpb)))
                                         for p in (0.25, 0.5, 0.75, 1.0)]))
    hold = next(c for c in M.STORY if c.kind == "hold")
    out.insert([r[0] for r in out].index("wake"),
               ("hold", [(f"B{b:g}", int(round(b * m.fpb))) for b in np.linspace(hold.b0 + 0.5, hold.b1 - 0.5, 4)]))
    n = m.n_frames
    out.append(("loop", [(f"f{j}" + (" = f0" if j == n - 1 else ""), j) for j in range(n - 4, n)]))
    return out


def label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    s = img.shape[1] / 480
    cv2.rectangle(out, (0, 0), (out.shape[1], int(22 * s)), (0, 0, 0), -1)
    cv2.putText(out, text, (int(6 * s), int(16 * s)), cv2.FONT_HERSHEY_SIMPLEX, 0.5 * s, (240, 240, 240),
                max(1, int(round(s))), cv2.LINE_AA)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="A sheet of Reality Melts stills, four per transition.")
    ap.add_argument("--size", default="960x540")
    ap.add_argument("--out", default="out/review/melt_sheet.jpg")
    ap.add_argument("--thumb", type=int, default=480, help="still width in the sheet")
    ap.add_argument("--only", help="comma list of row titles (chapter names, hold, loop)")
    ap.add_argument("--plain", action="store_true", help="leave out the accents (tears, prints, blinks)")
    ap.add_argument("--dump", help="also write every still as a PNG here")
    a = ap.parse_args(argv)
    T.W, T.H = T.parse_size(a.size)
    t0 = time.time()
    m = M.Melt()
    m.setup()
    print(f"[melt_stills] setup {time.time() - t0:.1f}s")
    sheet = []
    th = int(round(a.thumb * T.H / T.W))
    for title, stills in rows(m):
        if a.only and title not in a.only.split(","):
            continue
        cells = []
        for name, j in stills:
            img = m.frame(j, accents=not a.plain)
            if a.dump:
                os.makedirs(a.dump, exist_ok=True)
                cv2.imwrite(os.path.join(a.dump, f"{j:03d}_{title.replace(' ', '_')}.png"), img)
            st = m.state(j)
            tag = f"{title} {name}  B{m.beat(j):.2f} f{j}  u{float(st.prog(m.far).mean()):.2f}"
            cells.append(label(cv2.resize(img, (a.thumb, th), interpolation=cv2.INTER_AREA), tag))
        sheet.append(np.hstack(cells))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    cv2.imwrite(a.out, np.vstack(sheet), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"[melt_stills] {len(sheet) * len(PS)} stills in {time.time() - t0:.1f}s -> {a.out}")


if __name__ == "__main__":
    main()
