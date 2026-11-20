"""Write a QR code as a PNG: dark modules on white, with a quiet zone (crossover.trailer.make_qr).

    python scripts/make_qr.py                                   # the project page, out/qr.png
    python scripts/make_qr.py https://example.org -o out/qr_example.png --px 10
"""
import argparse
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crossover.trailer import URL, make_qr  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write a QR code PNG (dark modules on white, with a quiet zone).")
    ap.add_argument("text", nargs="?", default=URL, help=f"what to encode (default: {URL})")
    ap.add_argument("-o", "--out", default="out/qr.png")
    ap.add_argument("--px", type=int, default=8, help="pixels per module")
    ap.add_argument("--quiet", type=int, default=2, help="extra white modules beyond the usual 2-module margin")
    a = ap.parse_args(argv)
    img = make_qr(a.text, a.px, a.quiet)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    cv2.imwrite(a.out, img)
    ok = cv2.QRCodeDetector().detectAndDecode(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))[0] == a.text
    print(f"{a.out}: {img.shape[1]}x{img.shape[0]} px, {img.shape[0] // a.px} modules across, decodes: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
