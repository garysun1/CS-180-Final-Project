"""Reality Melts tests: the storyboard (32 beats, the chips, the flash rate, the edit's chapter
frames), the push and swirl envelopes, the helpers (gather, lac_crop, swirl_maps), and a few frames of
the real take rendered at a small size: the real beats are the filmed frame bit for bit (before the
finish), the loop point is invisible, every chapter grows far first, the hold is the paper's equation
on the world image, the swirl leaves people untouched, and people keep their colour where a new
ladder starts. The plaza checks are skipped when its data is absent."""
import os
import sys

import cv2
import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from crossover import melt as M  # noqa: E402
from crossover import morph  # noqa: E402
from crossover import trailer as T  # noqa: E402
from crossover.colormap import LocalAffineColor  # noqa: E402
from crossover.effects import NAMES  # noqa: E402
from crossover.video_io import to_float  # noqa: E402

NEEDS = ("data/sample/vtest.avi", "out/vtest_century/clean_bg.png", "out/gen/picks.txt", "out/gen/meta.json",
         morph.PLAZA_DEPTH)
have_plaza = pytest.mark.skipif(not all(os.path.exists(os.path.join(ROOT, p)) for p in NEEDS),
                                reason="the plaza clip, plate, worlds or depth are missing")


# ============================================================================ the storyboard
def test_storyboard_is_32_contiguous_beats_with_the_seven_chips():
    assert M.STORY[0].b0 == 0 and M.STORY[-1].b1 == M.BEATS == 32
    for a, b in zip(M.STORY, M.STORY[1:]):
        assert a.b1 == b.b0, (a.name, b.name)
    assert M.CHIPS == ("WINTER", "NIGHT", "AUTUMN", "1920", "UNDERWATER", "CYBERPUNK", "VAN GOGH")
    assert M.CHIPS == tuple(NAMES[w].upper() for w in M.WORLDS)                # the project's display names
    assert [c.kind for c in M.STORY][:2] == ["real", "grow"] and M.STORY[-1].kind == "real"
    hops = [c for c in M.STORY if c.kind == "hop"]
    assert [c.world for c in hops] == ["autumn", "1920s", "underwater", "cyberpunk"]
    assert all(c.b1 - c.b0 == 1 for c in hops) and hops[0].prev == ""        # autumn grows from the photo
    assert all(h.prev == g.world for g, h in zip(hops, hops[1:]))             # each hop leaves the last world
    assert morph.PATTERN["cyberpunk"] == "dots"                               # cyberpunk's detail in dots
    assert M.chapter_at(0.0).name == "real" and M.chapter_at(8.0).name == "night"
    assert M.chapter_at(31.99).name == "real end" and M.chapter_at(99).name == "real end"


def test_edit_has_one_shot_per_chapter_on_mains_grid():
    shots = M.edit_melt()
    m = shots[0].melt
    assert [s.name for s in shots] == [c.name for c in M.STORY]
    assert sum(s.beats for s in shots) == pytest.approx(32) and m.n_frames == 480
    assert all(s.section == "melt" and not s.bars and s.melt is m for s in shots)
    t = 0.0                                                                   # trailer.main's start frames
    for s in shots:
        assert s.first == int(round(t * 15))
        t += s.beats
        # ... are where the chapter really starts (half-beat chapters too: 143, 173 and 203)
        assert M.chapter_at(m.beat(s.first)).name == s.name, s.name
        assert s.first == 0 or M.chapter_at(m.beat(s.first - 1)).name != s.name, s.name
    assert [s.first for s in shots if s.name in ("autumn", "underwater", "drop")] == [143, 173, 203]
    assert int(round(t * 15)) == 480


def test_push_and_swirl_envelopes():
    for b in np.linspace(0, 2, 9).tolist() + np.linspace(30, 32, 9).tolist():
        assert M.push_at(b) == 1.0                                            # real: no zoom at all
    zs = [M.push_at(b) for b in np.arange(0, 32, 1 / 15)]
    assert max(zs) == pytest.approx(1.0 + M.PUSH) and min(zs) == 1.0
    assert all(M.push_at(b) == pytest.approx(1.04) for b in (22, 24, 26))      # the hold
    assert M.swirl_px(14.0) == 0 and M.swirl_px(22.0) == 0 and M.swirl_px(10) == 0 and M.swirl_px(24) == 0
    sw = [M.swirl_px(b) for b in np.linspace(14, 22, 81)]
    assert max(sw) == pytest.approx(14.0) and abs(np.linspace(14, 22, 81)[int(np.argmax(sw))] - 18) < 0.11


def test_flashes_stay_at_three_a_second_or_fewer():
    m = M.Melt()
    ev = m.flashes()
    kinds = [e["kind"] for e in ev]
    assert kinds.count("print") == 4 and kinds.count("blink") == 2 and kinds.count("tear") == 2
    prints = m.prints()
    assert np.all(np.diff(prints) >= 15)                                     # hop prints: at most 2 a second
    frames = np.array([e["frame"] for e in ev])
    n = m.n_frames
    per_second = [int(((frames - s) % n < 30).sum()) for s in range(n)]      # every 1-s window, looping
    assert max(per_second) <= 3, max(per_second)
    # the EDL carries the same events, split over the chapters main() cuts
    shots, got, t = M.edit_melt(), [], 0.0
    for k, s in enumerate(shots):
        nf = int(round((t + s.beats) * 15)) - int(round(t * 15))
        t += s.beats
        fl = s.edl_extra(nf)["flashes"]
        got += fl
        if s.name.startswith("rewind"):                                       # a tear spans its whole chapter
            assert fl == [{"frame": s.first, "kind": "tear", "frames": nf}], (s.name, fl, nf)
    assert got == ev


# ============================================================================ helpers
def test_gather_is_exact_at_rungs_and_linear_between():
    rng = np.random.default_rng(0)
    st = rng.uniform(0, 1, (4, 6, 8, 3)).astype(np.float32)
    for k in range(4):
        assert np.abs(M.gather(st, np.full((6, 8), k, np.float32)) - st[k]).max() <= 1e-6
    r = rng.uniform(0, 3, (6, 8)).astype(np.float32)
    k = np.minimum(r.astype(int), 2)
    f = (r - k)[..., None]
    want = np.take_along_axis(st, k[None, ..., None], 0)[0] * (1 - f) + np.take_along_axis(st, k[None, ..., None] + 1, 0)[0] * f
    assert np.abs(M.gather(st, r) - want).max() < 1e-5


def test_lac_crop_matches_apply():
    rng = np.random.default_rng(1)
    B = rng.integers(0, 255, (48, 64, 3)).astype(np.uint8)
    R = np.clip(B.astype(int) * [0.6, 0.9, 1.2] + 20, 0, 255).astype(np.uint8)
    lac = LocalAffineColor(strength=0.9).fit(B, R)
    F = rng.integers(0, 255, (48, 64, 3)).astype(np.uint8)
    box = (5, 40, 10, 50)
    assert np.array_equal(M.lac_crop(lac, to_float(F), box), to_float(lac.apply(F))[5:40, 10:50])


def test_swirl_maps_are_bounded_and_vanish_at_zero():
    v = M.curl_fields(60, 80, 20.0, seed=3)
    assert v.shape == (2, 60, 80, 2) and np.sqrt((v ** 2).sum(-1)).max() == pytest.approx(1.0, abs=1e-5)
    gy, gx = np.mgrid[0:60, 0:80].astype(np.float32)
    mx, my = M.swirl_maps(v[0], 0.0)
    assert np.array_equal(mx, gx) and np.array_equal(my, gy)
    mx, my = M.swirl_maps(v[0], 14.0)
    d = np.hypot(mx - gx, my - gy)
    assert d.max() <= 14.0 + 1e-4 and d.max() > 7                             # moves, never more than amp
    mx, my = M.swirl_maps(v[0], 14.0, np.zeros((60, 80), np.float32))
    assert np.array_equal(mx, gx) and np.array_equal(my, gy)                   # weight 0: nothing moves
    div = np.gradient(v[0][..., 0], axis=1) + np.gradient(v[0][..., 1], axis=0)
    assert np.abs(div[2:-2, 2:-2]).mean() < 0.05 * np.abs(np.gradient(v[0][..., 0], axis=0)).mean()


def test_soundtrack_loops_cleanly():
    x = M.melt_soundtrack([], [], 480, 0.5, seed=0)
    assert x.shape == (16 * T.SR, 2) and np.abs(x).max() <= 0.89
    assert abs(x[0, 0]) < 1e-6 and abs(x[-1, 0]) < 1e-6                     # the loop point does not click
    drop = x[int(6.80 * T.SR):int(7.0 * T.SR), 0]                            # the drop's half beat
    loud = x[int(7.0 * T.SR):int(7.5 * T.SR), 0]                             # the Van Gogh hit
    assert np.sqrt((drop ** 2).mean()) < 0.05 * np.sqrt((loud ** 2).mean())


# ============================================================================ the real take
@pytest.fixture(scope="module")
def melt():
    if not all(os.path.exists(os.path.join(ROOT, p)) for p in NEEDS):
        pytest.skip("the plaza clip, plate, worlds or depth are missing")
    old, cwd = (T.W, T.H), os.getcwd()
    T.W, T.H = 320, 180
    os.chdir(ROOT)
    m = M.Melt()
    m.setup()
    yield m
    T.W, T.H = old
    os.chdir(cwd)


@have_plaza
def test_real_beats_are_the_filmed_frame(melt):
    for j in (0, 1, 14, 29, 450, 463, 475, 476):                              # 476: no ghost before the blink
        assert melt.state(j).ch.kind == "real" and melt.composed(j) is None
        f = melt._get(melt.src_index(j))[0]
        assert np.array_equal(melt.frame(j), T.fit(f, M.CROP_Y)), j
    assert melt.src_index(0) == 580 and melt.src_index(3) == 581 and melt.src_index(479) == 739   # on threes


@have_plaza
def test_loop_point_is_the_first_frame(melt):
    n = melt.n_frames
    first, last = melt.frame(0).astype(int), melt.frame(n - 1).astype(int)
    assert np.abs(first - last).mean() < 1.5 and np.array_equal(first, last)
    # the frames before it dissolve into it under the blink (white), the one before them does not
    assert melt.blinks()[n - 3] > 0.5 and melt.blinks()[n - 2] > 0.5 and n - 4 not in melt.blinks()
    d = [np.abs(melt.frame(j, accents=False).astype(int) - first).mean() for j in range(n - 5, n)]
    assert d[-1] == 0 and all(a >= b for a, b in zip(d[1:], d[2:])), d       # closing in on frame 0


@have_plaza
def test_every_chapter_grows_far_first(melt):
    h = melt.h
    for c in M.STORY:
        if c.kind not in ("grow", "rewind", "hop", "wake"):
            continue
        a, b = (M.GROW[c.world][:2] if c.kind == "grow" else
                (c.b0, c.b0 + M.HOP_MORPH) if c.kind == "hop" else (c.b0, c.b1))
        u = melt.u_map(int(round((a + b) / 2 * melt.fpb)))
        top, bottom = u[:h // 3].mean(), u[-h // 3:].mean()
        assert top >= bottom and 0 < u.mean() < 1, (c.name, top, bottom)
        if c.kind in ("grow", "hop"):
            assert top > bottom + 0.1, (c.name, top, bottom)                   # the far end leads
    assert melt.u_map(int(24 * melt.fpb)).min() == 1.0                        # the hold: all world
    assert melt.u_map(int(13.8 * melt.fpb)).max() == 0.0                      # the drop: all photo


@have_plaza
def test_hold_is_the_paper_equation_on_the_world_image(melt):
    j = int(24 * melt.fpb)
    p = melt.composed(j, parts=True)
    world = cv2.imread(T.plate_path("vangogh")).astype(np.float32) / 255
    assert p["state"].swirl == 0 and np.abs(p["R"] - world).max() < 1e-6     # the true single image
    away = (p["alpha"] <= 0.004)
    assert np.abs(p["out"] - world * p["S"][..., None])[away].max() < 1e-5    # R*S off people
    # people: their feet are in the world, so they take the world's own person styler
    f = melt._get(melt.src_index(j))[0]
    sty = to_float(melt.wo["vangogh"].styler(f))
    solid = p["alpha"] == 1.0
    assert solid.sum() > 500 and np.abs(p["P"] - sty)[solid].max() < 1e-5
    assert np.abs(p["out"] - sty)[solid].max() < 1e-5                         # out = P where a = 1


@have_plaza
def test_swirl_moves_the_world_not_the_people(melt):
    j = int(18 * melt.fpb)
    p = melt.composed(j, parts=True)
    assert p["state"].swirl == pytest.approx(14.0)
    flat = p["state"].lad.at(p["u"] * np.float32(p["state"].lad.n)) / 255
    moved = np.abs(p["R"] - flat).max(-1)
    assert np.percentile(moved, 90) > 0.02                                    # the world swirls ...
    solid = (p["alpha"] == 1.0) & (p["w"] == 1.0)
    assert solid.sum() > 500 and np.abs(p["out"] - p["P"])[solid].max() < 1e-5   # ... people do not


@have_plaza
def test_cyberpunk_arrives_in_dots_without_a_double_exposure(melt):
    c = next(c for c in M.STORY if c.world == "cyberpunk")
    p = melt.composed(int(round((c.b0 + M.HOP_MORPH / 2) * melt.fpb)), parts=True)
    lad = p["state"].lad
    assert p["state"].dots and lad.labels == ["underwater", "cyberpunk"] and 0.2 < p["u"].mean() < 0.8
    s = lad.switch(p["u"])                                                    # the dots, 0 old .. 1 new
    assert (s < 0.02).mean() > 0.15 and (s > 0.98).mean() > 0.15              # both worlds are there ...
    assert ((s > 0.1) & (s < 0.9)).mean() < 0.5                               # ... mostly one or the other
    # R is that switch of the two whole images (no colour crossfade), times the fading caustics
    base = ((1 - s)[..., None] * lad.rungs[0] + s[..., None] * lad.rungs[1]) / 255
    ok = base.min(-1) > 0.08
    k = p["R"][ok] / base[ok]
    assert np.abs(k - k.mean(-1, keepdims=True)).max() < 1e-3 and k.min() >= 1 - 1e-4


@have_plaza
def test_people_take_the_progress_at_their_feet(melt):
    j = int(4.0 * melt.fpb)                                                   # winter, mid-grow
    p = melt.composed(j, parts=True)
    vals = melt.feet_values(j)
    people = melt._people(melt.src_index(j))
    assert len(vals) == len(people) >= 4 and all(0 <= v <= 1 for v in vals)
    for (m, *_), v in zip(people, vals):
        assert np.median(p["c"][m > 0]) == pytest.approx(v, abs=1e-6)
    # far walkers are further into winter than near ones
    feet_y = np.array([fy for _, _, fy, *_ in people])
    assert np.corrcoef(feet_y, vals)[0, 1] < -0.5
    # a frame does not depend on what was rendered before it
    for k in list(range(j - 12, j)) + [300, 30]:
        melt.composed(k)
    assert np.array_equal(melt.composed(j), p["out"])


@have_plaza
def test_people_keep_their_colour_when_the_ladder_changes(melt):
    # where a new ladder starts, people start from u at their feet (a hop: 0, the world they are in),
    # not from the last ladder's values
    for c in M.STORY:
        j = melt.first_frame_at(c.b0)
        st = melt.state(j)
        if st.lad is None or st.lad is melt.state(j - 1).lad:
            continue
        summ = melt._summary(melt.src_index(j))
        u = st.prog(np.array([ff for *_, ff in summ], np.float32))
        assert np.abs(np.array(melt.feet_values(j)) - u).max() < 1e-6, c.name
    # so a hop starts without a colour jump on people (the same source frame on both sides)
    for c in M.STORY:
        if c.kind != "hop" or not c.prev:
            continue
        j = melt.first_frame_at(c.b0)
        assert melt.src_index(j - 1) == melt.src_index(j)
        a, b = melt.composed(j - 1, parts=True), melt.composed(j, parts=True)
        solid = a["alpha"] == 1.0
        assert solid.sum() > 500 and np.abs(a["out"] - b["out"])[solid].mean() < 1.5 / 255, c.name
