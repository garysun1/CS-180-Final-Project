"""Trailer tests: walker tracking, the approach's line, the freeze / scan / flood shots (with the
frozen world carried through the scan), the teaser's loop point, the end card's QR code, the bundled
fonts and the crop mapping. Synthetic scenes have exact answers; the checks on the real plaza footage
are skipped when the data is absent."""
import os
import sys

import cv2
import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from crossover import trailer as T  # noqa: E402
from crossover.styles import apply_style  # noqa: E402
from crossover.video_io import to_float  # noqa: E402

SW, SH = 384, 288
VTEST = os.path.join(ROOT, "data/sample/vtest.avi")
VCLEAN = os.path.join(ROOT, "out/vtest_century/clean_bg.png")
have_vtest = pytest.mark.skipif(not (os.path.exists(VTEST) and os.path.exists(VCLEAN)),
                                reason="data/sample/vtest.avi or out/vtest_century/clean_bg.png is missing")


def textured_scene(seed=0, w=SW, h=SH):
    """'Buildings': random rectangles and lines with texture (as in test_pipeline.py)."""
    rng = np.random.default_rng(seed)
    img = np.full((h, w, 3), 120, np.uint8)
    for _ in range(70):
        x0, y0 = rng.integers(0, w - 10), rng.integers(0, h - 10)
        x1, y1 = x0 + rng.integers(8, 90), y0 + rng.integers(8, 70)
        cv2.rectangle(img, (int(x0), int(y0)), (int(x1), int(y1)), rng.integers(0, 255, 3).tolist(), -1)
    for _ in range(25):
        p = rng.integers(0, [w, h, w, h])
        cv2.line(img, (int(p[0]), int(p[1])), (int(p[2]), int(p[3])), rng.integers(0, 255, 3).tolist(), 2)
    noise = rng.normal(0, 6, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8)


def make_walk(tmp_path, n=14):
    """A PNG sequence: 'her' walking right and 'him' walking left on a textured scene, never touching.
    Returns (sequence pattern, clean plate path, her boxes (x0, y0, x1, y1), her masks, his masks)."""
    bg = textured_scene()
    cv2.imwrite(str(tmp_path / "clean.png"), bg)
    boxes, hers, his = [], [], []
    for t in range(n):
        f = bg.copy()
        ax, ay, bx, by = 60 + 9 * t, 150, 300 - 7 * t, 40
        ma, mb = np.zeros((SH, SW), np.uint8), np.zeros((SH, SW), np.uint8)
        for img, col in ((f, (40, 30, 200)), (ma, 1)):
            cv2.rectangle(img, (ax, ay), (ax + 21, ay + 69), col, -1)
        for img, col in ((f, (200, 70, 30)), (mb, 1)):
            cv2.rectangle(img, (bx, by), (bx + 17, by + 55), col, -1)
        cv2.imwrite(str(tmp_path / f"{t:05d}.png"), f)
        boxes.append((ax, ay, ax + 22, ay + 70))
        hers.append(ma)
        his.append(mb)
    return str(tmp_path / "%05d.png"), str(tmp_path / "clean.png"), boxes, hers, his


def centre(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def dilate(m, r):
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0


@pytest.fixture
def small_output(monkeypatch):
    """Render at the synthetic source size (4:3 = W:H, so fit() is a plain copy)."""
    monkeypatch.setattr(T, "W", SW)
    monkeypatch.setattr(T, "H", SH)


# ------------------------------------------------------------------ tracking
def test_track_walker_follows_one_rectangle(tmp_path):
    seq, clean, boxes, _, _ = make_walk(tmp_path)
    start, n = 2, 10
    src = T.track_walker(seq, clean, start, n, centre(boxes[start]), pad=0)
    assert len(src) == n
    for i, (f, alpha, soft, bbox) in enumerate(src):
        assert np.array_equal(f, cv2.imread(seq % (start + i)))          # no warm-up frame: src[i] = start + i
        assert alpha.shape == soft.shape == (SH, SW)
        err = np.abs(np.array(bbox) - np.array(boxes[start + i])).max()
        assert err <= 3, (i, bbox, boxes[start + i])


@have_vtest
def test_track_walker_vtest_her_walk(monkeypatch):
    """She is followed from 58.8 s to 63.0 s without a jump to anyone else (a merge or a switch moves
    the centre 43-59 px). Each step is under 20 px for what the shots consume, the smoothed follow-cam
    centre (cam_path), and for her mask centroid (at most ~11 px). The raw padded bbox's centre moves
    21 px once (58.8 -> 58.9 s, when her hand swings forward and the box widens by 25 px): a secondary
    check holds it to 25 px."""
    monkeypatch.setattr(T, "W", 960)
    monkeypatch.setattr(T, "H", 540)
    src = T.track_walker(VTEST, VCLEAN, 588, 43, (271, 510))           # 58.8 - 63.0 s
    assert len(src) == 43
    _, _, cw, ch = T.fit_window(768, 576, 0.5, 1.0)
    cam = T.cam_path(src, 0.5, 1.0) * np.array([cw, ch])                # back to source px
    cam_steps = np.hypot(*np.diff(cam, axis=0).T)
    assert cam_steps.max() < 20, cam_steps.round(1)
    cen = np.array([np.argwhere(soft > 0.5)[:, ::-1].mean(0) for _, _, soft, _ in src])
    steps = np.hypot(*np.diff(cen, axis=0).T)
    assert steps.max() < 20, steps.round(1)
    box = np.array([centre(b) for *_, b in src])
    box_steps = np.hypot(*np.diff(box, axis=0).T)
    assert box_steps.max() < 25, box_steps.round(1)
    assert abs(cen[0][0] - 271) < 3 and abs(cen[24][0] - 382) < 4      # 58.8 s and 61.2 s (find_moments.py)
    x0, _, x1, _ = src[612 - 588][3]                                     # at 61.2 s she straddles the line
    assert x0 < 384 < x1


# ------------------------------------------------------------------ freeze, scan, flood
def test_freeze_holds_everyone_but_her(tmp_path, small_output):
    seq, clean, boxes, hers, his = make_walk(tmp_path)
    fps = T.Reader.get(seq).fps
    start = 1
    fr = T.Freeze(3, video=seq, clean=clean, track=(start, 12, centre(boxes[start])), t0=3 / fps, t1=10 / fps,
                  crop_y=0.5)
    fr.setup()
    n = int((fr.t1 - fr.t0) * T.FPS)
    shown = [start + fr._k(fr.t0 + j / T.FPS) for j in range(n)]
    assert shown[0] == 3 and shown[-1] > 6
    outs = [fr.composed(j, n).astype(int) for j in range(n)]
    for j in range(1, n):
        near_her = dilate(hers[shown[0]], 8) | dilate(hers[shown[j]], 8)
        d = np.abs(outs[j] - outs[0]).max(axis=2)
        assert d[~near_her].max() <= 1, j                                # the world is frozen...
    him = his[shown[0]] > 0
    assert not np.array_equal(his[shown[0]], his[shown[-1]])             # ...although he kept walking
    assert np.abs(outs[-1] - outs[0]).max(axis=2)[him & ~dilate(hers[shown[-1]], 8)].max() <= 1
    her_now = hers[shown[-1]] > 0
    assert np.abs(outs[-1] - outs[0]).max(axis=2)[her_now].mean() > 20  # and she walks on


def _scan_flood(tmp_path):
    seq, clean, boxes, hers, _ = make_walk(tmp_path)
    plate = str(tmp_path / "night.png")
    cv2.imwrite(plate, apply_style(cv2.imread(clean), "night"))
    fps = T.Reader.get(seq).fps
    start, k1 = 1, 6
    track = (start, 12, centre(boxes[start]))
    sc = T.Scan(3, video=seq, clean=clean, track=track, t1=k1 / fps, world="night", plate=plate,
                line_from=centre(boxes[k1])[0], crop_y=0.5, z=(1.0, 1.1))
    fl = T.Flood(5, video=seq, clean=clean, track=track, t2=k1 / fps, world="night", plate=plate,
                 crop_y=0.5, z=(sc.z[1], 1.0))
    sc.setup()
    fl.setup()
    return sc, fl, hers[k1] > 0


def test_scan_share_of_her_in_the_world_grows(tmp_path, small_output):
    sc, _, her = _scan_flood(tmp_path)
    n = 45
    share = [float((sc.weight(j, n) * her).sum() / her.sum()) for j in range(n)]
    assert np.all(np.diff(share) >= -1e-6), share
    assert 0.2 < share[0] < 0.8 and share[-1] > 0.97                   # half of her had crossed already
    w = sc.weight(n - 1, n)
    assert w[~dilate(her, 8)].max() < 1e-3                               # only she changes
    # the scan light: on her where the line crosses her while it moves, off when the line rests
    light = [sc.light_at(j, n) for j in range(n)]
    assert light[0] == 0 and light[-1] == 0 and max(light) > 0.5
    jm = int(np.argmax(light))
    lit = sc.composed(jm, n).astype(int)
    sc.light = 0.0
    plain = sc.composed(jm, n).astype(int)
    near_line = her & (np.abs(np.arange(T.W)[None, :] - sc.line_at(jm, n)) < 5)
    assert (lit - plain).max(axis=2)[near_line].mean() > 30
    assert np.array_equal(lit[~dilate(her, 8)], plain[~dilate(her, 8)])  # nobody and nothing else is lit


def test_flood_starts_where_the_scan_ends_and_covers_everything(tmp_path, small_output):
    sc, fl, _ = _scan_flood(tmp_path)
    ns, nf = 45, 75
    assert np.array_equal(sc.render(ns - 1, ns), fl.render(0, nf))     # no pop at the cut
    k = fl._k(fl.t2 + (nf - 1) / T.FPS * fl.speed)
    f, alpha, _, _ = fl.tr[k]
    F = to_float(f)
    world = T.to_uint8(fl.wo.render(0, F, f, alpha, fl.shadow(F, alpha)[0], fl.ones))
    last = fl.render(nf - 1, nf)
    d = np.abs(last.astype(int) - world.astype(int)).max(axis=2)
    assert np.percentile(d, 99) <= 3, np.percentile(d, 99)                # the world, edge to edge


def test_others_stay_frozen_through_the_scan_and_resume_in_the_flood(tmp_path, small_output):
    """The trailer's Scan and Flood run everyone else on the Freeze's clock: in the Scan he is where
    the Freeze stopped him (t0) and she is at t1, her old place is the clean plate; in the Flood both
    clocks run together from there, and the Scan -> Flood cut is still exact."""
    seq, clean, boxes, hers, his = make_walk(tmp_path)
    plate = str(tmp_path / "night.png")
    cv2.imwrite(plate, apply_style(cv2.imread(clean), "night"))
    fps = T.Reader.get(seq).fps
    start, k0, k1 = 1, 3, 6
    track = (start, 12, centre(boxes[start]))
    kw = dict(video=seq, clean=clean, track=track, world="night", plate=plate, crop_y=0.5, others_t=k0 / fps)
    fr = T.Freeze(3, video=seq, clean=clean, track=track, t0=k0 / fps, t1=k1 / fps, crop_y=0.5)
    sc = T.Scan(3, t1=k1 / fps, line_from=centre(boxes[k1])[0], z=(1.0, 1.1), **kw)
    fl = T.Flood(5, t2=k1 / fps, z=(1.1, 1.0), **kw)
    for s in (fr, sc, fl):
        s.setup()
    assert (sc.k, sc.ko) == (k1 - start, k0 - start)
    f, _, _, _ = sc._plaza(sc.k, sc.ko)
    f, bg = f.astype(int), cv2.imread(clean).astype(int)
    frame0, frame1 = (cv2.imread(seq % k).astype(int) for k in (k0, k1))
    him0, him1, her0, her1 = his[k0] > 0, his[k1] > 0, hers[k0] > 0, hers[k1] > 0
    assert np.abs(f - frame0)[him0].max() <= 1                          # he is where the freeze stopped him
    assert np.abs(f - bg)[him1 & ~him0].max() <= 1                      # ...not where he walked on to
    assert np.abs(f - frame1)[her1].max() <= 1                          # she is at t1
    assert np.abs(f - bg)[her0 & ~dilate(her1, 20)].max() <= 1          # her old place is the clean plate
    # the Scan's frozen world is the Freeze's (both drained by 30%), except around her
    fz = fr.composed(0, 45).astype(int)
    scn = sc.composed(0, 45).astype(int)
    xs = np.arange(T.W)[None, :]                                         # output = source px here
    away = ~(dilate(her0, 20) | dilate(her1, 20)) & (np.abs(xs - fr.line_x) > 12) & (np.abs(xs - sc.line_at(0, 45)) > 12)
    assert np.abs(fz - scn).max(axis=2)[away].max() <= 2
    # the Flood: both clocks advance together from the scan's frame (until her track ends: this short
    # sequence plays at 25 fps), and the cut has no pop
    steps = [fl.kk(j) for j in range(75)]
    live = [(k, ko) for k, ko in steps if k < len(fl.tr) - 1]
    assert len({ko for _, ko in live}) >= 4
    assert all(k - ko == k1 - k0 for k, ko in live)
    assert steps[0] == (sc.k, sc.ko)
    assert np.array_equal(sc.render(44, 45), fl.render(0, 75))


def test_approach_line_fades_in_after_the_crossing(tmp_path, small_output):
    """Clip(line_ramp=(t_on, t_full)): no line before t_on (someone else is crossing it), the full
    line from t_full on, rising monotonically in between."""
    seq, _, _, _, _ = make_walk(tmp_path)
    fps = T.Reader.get(seq).fps
    kw = dict(path=seq, start=0.0, crop_y=0.5)
    ramp = T.Clip(2, line=True, line_ramp=(4 / fps, 7 / fps), **kw)
    off, on = T.Clip(2, **kw), T.Clip(2, line=True, **kw)
    n = 60
    j_off, j_on = int(3.5 / fps * T.FPS), int(np.ceil(7 / fps * T.FPS)) + 1
    assert np.array_equal(ramp.render(j_off, n), off.render(j_off, n))
    assert np.array_equal(ramp.render(j_on, n), on.render(j_on, n))
    s = [ramp.line_strength(j / T.FPS) for j in range(n)]
    assert s[0] == 0 and s[-1] == 0.55 and np.all(np.diff(s) >= 0)


def test_bundled_fonts_are_present():
    """The cards use the bundled OFL fonts (a missing file falls back to DejaVu with a warning)."""
    for name in ("Inter-Black.otf", "Inter-Light.otf", "JetBrainsMono-Medium.ttf", "OFL.txt"):
        assert os.path.isfile(os.path.join(T.FONT_DIR, name)), name
    for f in (T.FONT_B, T.FONT_L, T.FONT_M):
        assert os.path.dirname(f) == T.FONT_DIR, f


# ------------------------------------------------------------------ the teaser's loop point
def test_teaser_loop_point_synthetic(tmp_path, small_output):
    seq, clean, boxes, _, _ = make_walk(tmp_path)
    fps = T.Reader.get(seq).fps
    real = T.Walk(3, video=seq, clean=clean, track=(1, 12, centre(boxes[1])), t0=2 / fps, crop_y=0.5)
    title = T.LoopTitle(4, text="CROSS THE LINE", size=40, title=True, loop_to=real)
    title.setup()
    assert np.array_equal(real.render(0, real.frames()), title.render(59, 60))
    assert not np.array_equal(title.render(0, 60), title.render(59, 60))


@have_vtest
def test_teaser_loop_point_real(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(T, "W", 720)
    monkeypatch.setattr(T, "H", 720)
    shots = T.edit_teaser()
    real, title = shots[0], shots[-1]
    assert real.name == "real" and title.name == "title" and sum(s.beats for s in shots) == 30
    title.setup()
    n = title.frames()
    assert np.array_equal(real.render(0, real.frames()), title.render(n - 1, n))


# ------------------------------------------------------------------ the end card
def test_end_card_qr_decodes(monkeypatch):
    monkeypatch.setattr(T, "W", 960)
    monkeypatch.setattr(T, "H", 540)
    card = T.EndCard(6, names=T.NAMES_PLACEHOLDER)
    card.setup()
    img = T.finish(card.render(10, 90), np.random.default_rng(1), card.bars)
    txt, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    assert txt == T.URL
    x, y, qs = card.qr_box
    assert qs // 37 >= 5                                                 # >= 5 px per module


def test_make_qr_plate():
    q = T.make_qr(T.URL, 5)
    assert q.shape == (37 * 5, 37 * 5)                                   # version 3 (29) + 2 * (2 + 2) quiet
    assert (q[:20] == 255).all() and (q[-20:] == 255).all() and (q[:, :20] == 255).all() and (q[:, -20:] == 255).all()
    assert q[20:25, 20:25].max() == 0                                    # a dark finder module, not inverted
    assert cv2.QRCodeDetector().detectAndDecode(cv2.cvtColor(q, cv2.COLOR_GRAY2BGR))[0] == T.URL


# ------------------------------------------------------------------ the crop mapping
@pytest.mark.parametrize("out_size,src_size,crop", [
    ((720, 720), (768, 576), (0.5, 0.5)),       # 4:3 into a square: columns are cropped
    ((720, 720), (768, 576), (0.2, 0.5)),
    ((960, 540), (1280, 720), (0.5, 0.5)),      # 16:9 into 16:9: a plain resize
    ((960, 540), (768, 576), (0.5, 1.0)),       # 4:3 into 16:9: rows are cropped (the glitch's case)
])
def test_src_to_out_matches_fit(monkeypatch, out_size, src_size, crop):
    monkeypatch.setattr(T, "W", out_size[0])
    monkeypatch.setattr(T, "H", out_size[1])
    sw, sh = src_size
    x0, y0, cw, ch = T.fit_window(sw, sh, *crop)
    ys, xs = np.mgrid[0:sh, 0:sw].astype(np.float32)
    for fx, fy in ((0.5, 0.5), (0.12, 0.2), (0.85, 0.9)):
        x, y = x0 + fx * cw, y0 + fy * ch
        blob = np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / (2 * 4.0 ** 2)).astype(np.float32)
        out = np.clip(T.fit(blob, crop_y=crop[1], crop_x=crop[0]), 0, None)
        oy, ox = np.mgrid[0:out.shape[0], 0:out.shape[1]]
        got = ((out * ox).sum() / out.sum(), (out * oy).sum() / out.sum())
        want = T.src_to_out(x, y, sw, sh, *crop)
        assert abs(got[0] - want[0]) < 0.5 and abs(got[1] - want[1]) < 0.5, (got, want)
