"""Morph tests: the two-band blend and the ladder are exact at every rung, the threshold field stays in
[0.15, 0.85], grow fronts start far, and the plaza ladders use only filter-init rungs on each pick's own
schedule. Synthetic images have exact answers; the plaza checks are skipped when the plaza scene (out/clips/vtest) is absent."""
import json
import os
import re
import sys
import time

import cv2
import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from crossover import morph  # noqa: E402
from crossover.styles import apply_style  # noqa: E402

have_plaza = pytest.mark.skipif(
    not all(os.path.exists(os.path.join(ROOT, p)) for p in ("out/clips/vtest/gen/meta.json", "out/clips/vtest/gen/picks.txt", morph.PLAZA_PLATE)),
    reason="the plaza scene (out/clips/vtest) is missing")
have_ladder = pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "out/clips/vtest/gen_ladder/meta.json")),
                                 reason="out/clips/vtest/gen_ladder (the ladder fill) is missing")
SH, SW = 48, 64


def rand_rungs(n, seed=0, h=SH, w=SW):
    rng = np.random.default_rng(seed)
    return [rng.uniform(0, 255, (h, w, 3)).astype(np.float32) for _ in range(n + 1)]


def literal_two_band(A, B, f, th, soft=0.12):
    """The two-band formula exactly as written in the design."""
    lA, lB = morph.low_pass(A), morph.low_pass(B)
    t = np.clip((f - (th - soft)) / (2 * soft), 0, 1)
    s = (t * t * (3 - 2 * t))[..., None]
    return lA + np.asarray(f)[..., None] * (lB - lA) + (A - lA) + s * ((B - lB) - (A - lA))


# ============================================================================ the blend
@pytest.mark.parametrize("pattern", ["noise", "dots"])
def test_ladder_is_exact_at_every_rung(pattern):
    rungs = rand_rungs(4, seed=1)
    lad = morph.Ladder(rungs, pattern=pattern)
    assert lad.n == 4 and lad.labels == ["r0", "r1", "r2", "r3", "r4"]
    for k in range(lad.n + 1):
        for r in (k, float(k), np.full((SH, SW), k, np.float32)):
            out = lad.at(r)
            assert out.shape == (SH, SW, 3) and out.dtype == np.float32
            assert np.abs(out - rungs[k]).max() <= 1e-5
    # a map of whole numbers gives every pixel its own rung, untouched
    kmap = np.random.default_rng(2).integers(0, lad.n + 1, (SH, SW))
    want = np.take_along_axis(np.stack(rungs), kmap[None, :, :, None], 0)[0]
    assert np.abs(lad.at(kmap.astype(np.float32)) - want).max() <= 1e-5
    # out-of-range r is clipped to the ends
    assert np.abs(lad.at(-3.0) - rungs[0]).max() <= 1e-5
    assert np.abs(lad.at(np.full((SH, SW), 9.0)) - rungs[-1]).max() <= 1e-5


def test_two_band_is_exact_at_both_ends():
    A, B = rand_rungs(1, seed=3)
    lA, lB = morph.low_pass(A), morph.low_pass(B)
    for pattern in ("noise", "dots"):
        th = morph.threshold(SH, SW, seed=5, pattern=pattern)
        for f0, want in ((0.0, A), (1.0, B)):
            for f in (f0, np.full((SH, SW), f0, np.float32)):
                assert np.abs(morph.two_band(A, B, lA, lB, f, th) - want).max() <= 1e-5


def test_two_band_and_ladder_follow_the_formula():
    A, B = rand_rungs(1, seed=4)
    th = morph.threshold(SH, SW)                              # the ladder's own field (seed 0, noise)
    f = np.random.default_rng(6).uniform(0, 1, (SH, SW)).astype(np.float32)
    want = literal_two_band(A, B, f, th)
    assert np.abs(morph.two_band(A, B, morph.low_pass(A), morph.low_pass(B), f, th) - want).max() < 1e-3
    lad = morph.Ladder([A, B])
    assert np.abs(lad.at(f) - want).max() < 1e-3
    # a scalar r and the same value as a map agree; colour moves with f while detail waits for th
    assert np.abs(lad.at(0.37) - lad.at(np.full((SH, SW), 0.37, np.float32))).max() < 1e-3
    assert np.abs(lad.at(0.37) - literal_two_band(A, B, np.float32(0.37), th)).max() < 1e-3


def test_ladder_walks_between_the_right_rungs():
    rungs = rand_rungs(3, seed=7)
    lad = morph.Ladder(rungs, ["a", "b", "c", "d"])
    r = np.full((SH, SW), 1.6, np.float32)
    r[:, : SW // 2] = 0.3
    out = lad.at(r)
    th = lad.th
    want_left = literal_two_band(rungs[0], rungs[1], np.float32(0.3), th, lad.soft)
    want_right = literal_two_band(rungs[1], rungs[2], np.float32(1.6 - 1), th, lad.soft)
    assert np.abs(out[:, : SW // 2] - want_left[:, : SW // 2]).max() < 1e-3
    assert np.abs(out[:, SW // 2:] - want_right[:, SW // 2:]).max() < 1e-3
    assert np.allclose(lad.high, lad.rungs - lad.low)


def test_ladder_rejects_bad_input():
    rungs = rand_rungs(2)
    with pytest.raises(ValueError):
        morph.Ladder(rungs[:1])
    with pytest.raises(ValueError):
        morph.Ladder(rungs, labels=["x"])
    with pytest.raises(ValueError):
        morph.Ladder(rungs).at(np.zeros((SH + 1, SW), np.float32))
    with pytest.raises(ValueError):
        morph.threshold(8, 8, pattern="stripes")


def test_ladder_at_map_is_fast():
    lad = morph.Ladder(rand_rungs(5, h=576, w=768))
    r = np.tile(np.linspace(0, lad.n, 768, dtype=np.float32), (576, 1))
    lad.at(r)
    best = min(_timed(lambda: lad.at(r)) for _ in range(5))
    assert best < 0.1, f"Ladder.at on 768x576, N = 5 took {best * 1000:.0f} ms"   # about 12 ms on 4 cores


def _timed(fn):
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


# ============================================================================ threshold and noise
@pytest.mark.parametrize("pattern", ["noise", "dots"])
def test_threshold_stays_in_range_and_is_deterministic(pattern):
    for h, w in ((576, 768), (540, 960), (37, 51)):
        for seed in (0, 1, 7):
            th = morph.threshold(h, w, seed, pattern)
            assert th.shape == (h, w) and th.dtype == np.float32
            assert th.min() >= 0.15 and th.max() <= 0.85
    assert np.array_equal(morph.threshold(64, 80, 3, pattern), morph.threshold(64, 80, 3, pattern))


def test_noise_threshold_spreads_the_switch_over_the_step():
    th = morph.threshold(576, 768)
    assert not np.array_equal(th, morph.threshold(576, 768, seed=1))
    hist = np.histogram(th, bins=7, range=(0.15, 0.85))[0] / th.size
    assert hist.min() > 0.08                                     # roughly even, not piled up at 0.5
    t = np.clip((0.5 - (th - 0.12)) / 0.24, 0, 1)
    s = t * t * (3 - 2 * t)
    assert np.mean((s > 0.1) & (s < 0.9)) < 0.3                  # few half-switched pixels mid-step


def _hash(x):
    x &= 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x7FEB352D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x846CA68B) & 0xFFFFFFFF
    return x ^ (x >> 16)


def test_vnoise_follows_its_portable_recipe():
    v = morph.vnoise(40, 50, 0.5, seed=9)                        # cell 0.5: pixel centres sit on lattice points
    for y, x in ((0, 0), (3, 17), (39, 49), (20, 2)):
        i, j = 2 * x + 1, 2 * y + 1
        assert v[y, x] == (_hash(i + _hash(j + _hash(9))) >> 8) / 2 ** 24
    n = morph.vnoise(200, 300, 18.0, seed=2)
    assert n.min() >= 0 and n.max() < 1
    assert np.abs(np.diff(n, axis=1)).max() < 0.15               # smooth: no jumps between neighbours


# ============================================================================ fronts and checks
def test_grow_map_ends_and_far_first():
    far = np.tile(np.linspace(0, 1, 101, dtype=np.float32), (3, 1))
    assert np.all(morph.grow_map(far, 0.0) == 0) and np.all(morph.grow_map(far, 1.0) == 1)
    ps = np.linspace(0, 1, 41)
    us = [morph.grow_map(far, p) for p in ps]
    for u in us:
        assert u.min() >= 0 and u.max() <= 1
        assert np.all(np.diff(u[0]) >= 0)                        # a farther pixel is never behind a nearer one
    assert all(np.all(b >= a) for a, b in zip(us, us[1:]))       # and nothing goes back while p grows
    assert morph.grow_map(far, 0.56)[0, -1] == 1                 # the farthest pixel is done by p = 1 - lead
    assert morph.grow_map(far, 0.44)[0, 0] == 0                  # the nearest has not started before p = lead
    # reverse: p = 0 is the whole world, p = 1 all real, near pixels leave first
    assert np.all(morph.grow_map(far, 0.0, reverse=True) == 1)
    assert np.all(morph.grow_map(far, 1.0, reverse=True) == 0)
    ur = morph.grow_map(far, 0.25, reverse=True)
    assert ur[0, 0] < ur[0, -1] and np.array_equal(ur, morph.grow_map(far, 0.75))


def test_betweenness_and_mid_index():
    A, B = rand_rungs(1, seed=8, h=60, w=80)
    on_way = morph.betweenness(A, 0.5 * (A + B), B)
    assert abs(on_way["ratio"] - 1) < 1e-3
    assert abs(on_way["d_prev"] + on_way["d_next"] - on_way["d_span"]) < 1e-2
    detour = morph.betweenness(A, 0.5 * (A + B) + 60, B)
    assert detour["ratio"] > 1.3
    rungs = [A, A + 1, *(A + t * (B - A) for t in (0.2, 0.55, 0.9)), B]
    labels = ["plate", "filter", "n2", "n4", "n6", "world"]
    assert morph.mid_index(rungs, labels) == 3
    assert morph.mid_index([A, A + 1, B], ["plate", "filter", "world"]) is None


# ============================================================================ chains
def test_chain_has_plate_filter_mids_world():
    rng = np.random.default_rng(10)
    plate = rng.integers(0, 256, (SH, SW, 3), dtype=np.uint8)
    world = rng.integers(0, 256, (SH, SW, 3), dtype=np.uint8)
    mid = rng.uniform(0, 255, (SH, SW, 3)).astype(np.float32)
    rungs, labels = morph.chain("winter", plate, world, [("n4", mid)])
    assert labels == ["plate", "filter", "n4", "world"]
    assert all(r.dtype == np.float32 and r.shape == (SH, SW, 3) for r in rungs)
    assert np.array_equal(rungs[0], plate.astype(np.float32)) and np.array_equal(rungs[-1], world.astype(np.float32))
    assert np.array_equal(rungs[1], apply_style(plate, "winter").astype(np.float32))      # the img2img start
    assert morph.chain("no-such-style", plate, world)[1] == ["plate", "world"]
    with pytest.raises(ValueError):
        morph.chain("winter", plate, world, [np.zeros((SH, SW + 2, 3), np.float32)])


def _write_gen(folder, entries):
    """A fake gen folder: entries = {stem: (meta, image)}."""
    os.makedirs(folder, exist_ok=True)
    meta = {}
    for stem, (m, img) in entries.items():
        cv2.imwrite(os.path.join(folder, stem + ".png"), img)
        meta[stem] = m
    with open(os.path.join(folder, "meta.json"), "w") as fh:
        json.dump(meta, fh)


def _m(k, steps=8, g=1.5, init="filter", seed=0):
    return dict(style="snow", init=init, seed=seed, strength=k, steps=steps, guidance=g)


def test_sd_rungs_keep_one_filter_rung_per_n_on_the_pick_schedule(tmp_path):
    rng = np.random.default_rng(11)
    img = [rng.integers(0, 256, (8, 8, 3), dtype=np.uint8) for _ in range(8)]
    m = _m
    _write_gen(tmp_path / "a", {
        "snowf_s0_k90": (m(0.9), img[0]),                 # the pick: n = 7
        "snowf_s0_k40": (m(0.4), img[1]),                 # n = 3: kept
        "snowf_s0_k45": (m(0.45), img[2]),                # n = 3 again: one per n
        "snowf_s0_k60": (m(0.6), img[3]),                 # n = 4: kept
        "snowf_s0_k75": (m(0.75), img[3]),                # n = 6 but the same bytes as k60: dropped
        "snowf_s0_k95": (m(0.95), img[4]),                # n = 7, not below the pick
        "snow_s0_k50": (m(0.5, init="clean"), img[5]),    # photo init: never
        "snowf_s1_k50": (m(0.5, seed=1), img[6]),         # another seed
        "snowf_s0_k55": (m(0.55, steps=10, g=2.0), img[7]),   # another schedule
    })
    _write_gen(tmp_path / "b", {
        "snowf_s0_k70": (m(0.7), img[0]),                 # n = 5 but the pick's own bytes: dropped
        "snowf_s0_k65": (m(0.65), img[6]),                # n = 5: kept (from the second folder)
        "snowf_s0_k50": (m(0.5), img[2]),                 # n = 4: the first folder already has one
    })
    rungs = morph.sd_rungs("snow", "snowf_s0_k90", gen_dirs=("a", "b"), root=str(tmp_path))
    assert [(r.folder, r.stem, r.n) for r in rungs] == [("a", "snowf_s0_k40", 3), ("a", "snowf_s0_k60", 4),
                                                        ("b", "snowf_s0_k65", 5)]
    assert [r.label for r in rungs] == ["n3", "n4", "n5"]
    assert all(r.steps == 8 and r.guidance == 1.5 for r in rungs)
    with pytest.raises(KeyError):
        morph.sd_rungs("snow", "snowf_s0_k11", gen_dirs=("a", "b"), root=str(tmp_path))


@have_plaza
def test_cyberpunk_rungs_leave_out_the_md5_twin():
    keys = [r.key for r in morph.sd_rungs("cyberpunk", "cyberpunkf_s0_k85")]
    assert ("out/clips/vtest/gen", "cyberpunkf_s0_k75") not in keys          # byte-identical to the pick (6 steps both)
    if os.path.exists(os.path.join(ROOT, "out/clips/vtest/gen_ladder/cyberpunkf_s0_k65.png")):
        assert keys == [("out/clips/vtest/gen_ladder", "cyberpunkf_s0_k65")]


@have_plaza
def test_plaza_chains_use_only_filter_init_rungs_on_the_pick_schedule():
    metas = {}
    for d in morph.GEN_DIRS:
        p = os.path.join(ROOT, d, "meta.json")
        metas[d] = json.load(open(p)) if os.path.exists(p) else {}
    picks = morph.plaza_picks()
    assert set(picks) == {"winter", "night", "1920s", "underwater", "autumn", "vangogh", "cyberpunk"}
    for style, stem in picks.items():
        pm = metas["out/clips/vtest/gen"][stem]
        for rung in morph.sd_rungs(style, stem):                 # before the eye-check exclusions
            assert re.fullmatch(rf"{re.escape(style)}f_s0_k\d+", rung.stem), rung   # never winter_s0_* etc.
            m = metas[rung.folder][rung.stem]
            assert m.get("init", "filter") == "filter"
            assert (m["steps"], m["guidance"]) == (pm["steps"], pm["guidance"])
            assert rung.n < morph.n_steps(pm)
        mids = morph.plaza_mids(style)
        assert [r.n for r in mids] == sorted({r.n for r in mids})
        assert not any(r.key in morph.EXCLUDE for r in mids)


@have_plaza
def test_vangogh_rungs_run_the_picks_ten_steps():
    rungs = morph.sd_rungs("vangogh", "vangoghf_s0_k95")
    assert all(r.steps == 10 and r.guidance == 2.0 and r.n < 9 for r in rungs)
    assert ("out/clips/vtest/gen", "vangoghf_s0_k75") not in [r.key for r in rungs]   # 8 steps, guidance 1.5
    if os.path.exists(os.path.join(ROOT, "out/clips/vtest/gen_ladder/meta.json")):
        assert [(r.folder, r.n) for r in rungs] == [("out/clips/vtest/gen_ladder", 5), ("out/clips/vtest/gen_ladder", 7), ("out/clips/vtest/gen_ladder", 8)]


@have_plaza
@have_ladder
def test_excluded_rungs_are_real_and_explained():
    picks = morph.plaza_picks()
    for (folder, stem), why in morph.EXCLUDE.items():
        style = stem.split("f_s")[0]
        assert os.path.exists(os.path.join(ROOT, folder, stem + ".png")) and len(why) > 20
        assert (folder, stem) in [r.key for r in morph.sd_rungs(style, picks[style])]


@have_plaza
def test_winter_ladder_moves_steadily_away_from_the_plate():
    lad = morph.plaza_ladder("winter")
    assert lad.labels[0] == "plate" and lad.labels[1] == "filter" and lad.labels[-1] == "world"
    plate = cv2.imread(os.path.join(ROOT, morph.PLAZA_PLATE)).astype(np.float32)
    world = cv2.imread(os.path.join(ROOT, "out/clips/vtest/gen", morph.plaza_picks()["winter"] + ".png")).astype(np.float32)
    assert np.array_equal(lad.at(0), plate) and np.array_equal(lad.at(lad.n), world)
    d = [float(np.abs(lad.at(r) - plate).mean()) for r in np.arange(0, lad.n + 1e-6, 0.5)]
    assert all(b >= a for a, b in zip(d, d[1:])), d


@have_plaza
def test_plaza_farness_feeds_grow_map():
    far = morph.plaza_farness()
    assert far.shape == (576, 768) and far.min() >= 0 and far.max() <= 1
    assert far[:100].mean() > far[-100:].mean()                  # the top of the frame is far away
    u = morph.grow_map(far, 0.4)
    assert u[:150].mean() > u[-150:].mean()                      # so it grows first
