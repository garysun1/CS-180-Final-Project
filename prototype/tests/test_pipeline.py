"""Synthetic-scene tests: every check has an exact known answer."""
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crossover.align import align  # noqa: E402
from crossover.background import median_background  # noqa: E402
from crossover.composite import composite  # noqa: E402
from crossover.line import Line, side_weight  # noqa: E402
from crossover.metrics import seam_drift, true_residual  # noqa: E402
from crossover.perturb import make_perturbation  # noqa: E402
from crossover.styles import apply_style  # noqa: E402
from crossover.video_io import to_float, to_uint8  # noqa: E402

W, H = 384, 288


def textured_scene(seed=0, w=W, h=H):
    """'Buildings': random rectangles and lines with texture - plenty of edges and corners."""
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


def walkers(bg, n_frames=31, seed=1):
    """Frames with 3 'people' (solid blobs) crossing the scene; plus exact masks."""
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, W, 3)
    ys = rng.integers(40, H - 80, 3)
    speeds = rng.choice([-1, 1], 3) * rng.integers(8, 14, 3)
    frames, masks = [], []
    for t in range(n_frames):
        f, m = bg.copy(), np.zeros((H, W), np.uint8)
        for k in range(3):
            x = int((starts[k] + speeds[k] * t) % W)
            cv2.rectangle(f, (x, int(ys[k])), (x + 18, int(ys[k]) + 50), (30, 40, 200 - 50 * k), -1)
            cv2.rectangle(m, (x, int(ys[k])), (x + 18, int(ys[k]) + 50), 1, -1)
        frames.append(f)
        masks.append(m)
    return frames, masks


@pytest.fixture(scope="module")
def scene():
    return textured_scene()


def test_median_recovers_background(tmp_path, scene):
    frames, _ = walkers(scene)
    for i, f in enumerate(frames):
        cv2.imwrite(str(tmp_path / f"{i:05d}.png"), f)
    bg, heat, meta = median_background(str(tmp_path / "%05d.png"), max_samples=31)
    assert meta["n_samples"] == 31
    err = np.abs(bg.astype(int) - scene.astype(int))
    assert (err == 0).mean() > 0.995, "median should reproduce the empty scene almost everywhere"
    assert heat.max() > 0  # the walkers were noticed


def test_known_homography_recovered(scene):
    pert = make_perturbation(W, H, seed=3, jitter_frac=0.02, local_amp_px=0.0)
    moved = pert.apply(scene)
    line = Line.from_spec("0.5,0,0.5,1", W, H)
    before = true_residual(pert, line, W, H)
    res = align(moved, scene, "auto")
    after = true_residual(pert, line, W, H, res)
    assert before["median"] > 1.5   # a corner-jitter homography moves the centre line less than corners
    assert after["max"] < 0.5, after


def test_ecc_fallback_recovers_when_sift_cannot(scene):
    # ink redraws edges: SIFT struggles, ECC from identity should still get close
    pert = make_perturbation(W, H, seed=4, jitter_frac=0.006, local_amp_px=0.0)
    moved = pert.apply(apply_style(scene, "ink"))
    line = Line.from_spec("0.5,0,0.5,1", W, H)
    res = align(moved, scene, "ecc")
    assert true_residual(pert, line, W, H, res)["median"] < 1.0


def test_seam_metric_tracks_truth(scene):
    pert = make_perturbation(W, H, seed=5, jitter_frac=0.01, local_amp_px=2.0)
    line = Line.from_spec("0.5,0,0.5,1", W, H)
    measured = seam_drift(scene, pert.apply(scene), line)
    truth = true_residual(pert, line, W, H)
    assert measured["reliable"]
    assert abs(measured["median"] - truth["median"]) < 0.75, (measured["median"], truth["median"])
    assert seam_drift(scene, scene, line)["median"] < 0.05


def test_roundtrip_onto_clean_plate_is_exact(scene):
    frames, masks = walkers(scene)
    B = to_float(scene)
    ones = np.ones((H, W), np.float32)
    for f, m in zip(frames[:5], masks[:5]):
        out = to_uint8(composite(to_float(f), B, m.astype(np.float32), ones, ones))
        assert np.array_equal(out, f)


def test_real_side_untouched(scene):
    frames, masks = walkers(scene)
    R = to_float(apply_style(scene, "night"))
    line = Line.from_spec("0.5,0,0.5,1", W, H)
    d = line.signed_distance(W, H)
    w = side_weight(d, "hard")
    f = frames[7]
    out = to_uint8(composite(to_float(f), R, masks[7].astype(np.float32), np.ones((H, W), np.float32), w))
    left = d < 0
    assert np.array_equal(out[left], f[left]), "real side must be exactly the filmed frame"
    assert not np.array_equal(out[~left], f[~left])


def test_line_sign_convention():
    line = Line.from_spec("0.5,0,0.5,1", 100, 50)
    d = line.signed_distance(100, 50)
    assert d[10, 90] > 0 and d[10, 10] < 0   # right of a top->bottom line is the restyled side


def test_edge_decontamination_swaps_background_exactly(scene):
    """Under the matting model F = a*FG + (1-a)*B, the soft edge must end up as a*FG + (1-a)*R."""
    B = to_float(scene)
    R = to_float(apply_style(scene, "night"))
    FG = np.zeros_like(B)
    FG[..., 2] = 0.9                                              # a red "person"
    m = np.zeros((H, W), np.float32)
    cv2.circle(m, (W // 2, H // 2), 40, 1.0, -1)
    a = cv2.GaussianBlur(m, (0, 0), 4.0)                          # soft edge
    F = a[..., None] * FG + (1 - a[..., None]) * B
    ones = np.ones((H, W), np.float32)
    out = composite(F, R, a, ones, ones, Q=B)
    want = a[..., None] * FG + (1 - a[..., None]) * R
    assert np.abs(out - want).max() < 0.005   # exact except where a < support_eps (< 1 grey level)
    plain = composite(F, R, a, ones, ones)                        # without: old background leaks in
    assert np.abs(plain - want).max() > 0.05


# ------------------------------------------------------------------ styles, animation, depth split
from crossover.animate import make_animation  # noqa: E402
from crossover.depth import DepthSplit, contour_points  # noqa: E402
from crossover.styles import STYLES, PersonStyler  # noqa: E402


def test_every_style_and_person_function_shape(scene):
    for name in STYLES:
        R = apply_style(scene, name)
        assert R.shape == scene.shape and R.dtype == np.uint8, name
        P = PersonStyler(name, scene, R)(scene)
        assert P.shape == scene.shape and P.dtype == np.uint8, name


def test_animation_layers_deterministic():
    for style in ("winter", "underwater"):
        a1, a2 = make_animation(style, W, H, 10.0), make_animation(style, W, H, 10.0)
        for i in (0, 7):
            l1 = a1.front_layer(i) if a1.front else a1.plate_gain(i)
            l2 = a2.front_layer(i) if a2.front else a2.plate_gain(i)
            for x, y in zip(l1 if isinstance(l1, tuple) else (l1,), l2 if isinstance(l2, tuple) else (l2,)):
                assert np.array_equal(x, y)
    assert make_animation("night", W, H, 10.0) is None


def _ramp():
    """Ground-plane-like farness: 0 at the bottom row (near), 1 at the top (far)."""
    return np.repeat(np.linspace(1, 0, H, dtype=np.float32)[:, None], W, axis=1)


def test_depth_split_quantile_and_monotone():
    f = _ramp()
    ds = DepthSplit(f, split=0.3, band=0.05)
    wb = ds.background_weight()
    assert abs((wb >= 0.5).mean() - 0.3) < 0.01               # 30% of the image restyled
    col = wb[:, W // 2]
    assert np.all(np.diff(col) <= 1e-6)                        # farther (higher up) -> more restyled
    wn = DepthSplit(f, split=0.3, band=0.05, near=True).background_weight()
    assert abs((wn >= 0.5).mean() - 0.3) < 0.01              # near: the NEAREST 30% is restyled
    assert wn[-1, W // 2] > 0.99 and wn[0, W // 2] < 0.01      # bottom row (near) restyled, top real


def test_person_weight_comes_from_the_feet():
    f = _ramp()
    ds = DepthSplit(f, split=0.5, band=0.2)
    a = np.zeros((H, W), np.float32)
    a[60:200, 100:130] = 1.0                                   # tall person: head far up, feet at y=199
    Wp = ds.person_weights(a, 0)
    feet_f = float(np.median(f[199:206, 112:119]))
    assert abs(Wp[100, 115] - float(ds.weight_of(feet_f))) < 1e-6
    assert abs(Wp[65, 115] - Wp[195, 115]) < 1e-6              # one weight for the whole person
    assert abs(Wp[100, 115] - float(ds.weight_of(f[65, 115]))) > 0.1   # not the depth at the head


def test_tracker_ema_reduces_flicker():
    f = _ramp()
    ds = DepthSplit(f, split=0.5, band=0.3, ema=0.35)
    rng = np.random.default_rng(0)
    for t in range(40):
        a = np.zeros((H, W), np.float32)
        y1 = 150 + int(rng.integers(-6, 7))                    # noisy foot position, same person
        a[y1 - 60:y1, 100 + t:130 + t] = 1.0
        ds.person_weights(a, t)
    raw, ema = np.mean(ds.stats["flicker_raw"]), np.mean(ds.stats["flicker_ema"])
    assert ema < 0.7 * raw, (raw, ema)


def test_depth_mode_keeps_near_pixels_exact(scene):
    frames, masks = walkers(scene)
    ds = DepthSplit(_ramp(), split=0.4, band=0.05)
    f = frames[3]
    a = masks[3].astype(np.float32)
    w = ds.weight(a, 0)
    R = to_float(apply_style(scene, "night"))
    out = to_uint8(composite(to_float(f), R, a, np.ones((H, W), np.float32), w, Q=to_float(scene)))
    real = w == 0
    assert real.any() and np.array_equal(out[real], f[real])


def test_contour_points_lie_on_the_split():
    f = _ramp()
    tau = 0.5
    pts = contour_points(f, tau, stride=16, margin=10)
    assert len(pts) > 5
    assert np.all(np.abs(f[pts[:, 1].astype(int), pts[:, 0].astype(int)] - tau) < 0.02)


# ------------------------------------------------------------------ learned colour mapping for people
from crossover.colormap import LocalAffineColor  # noqa: E402
from crossover.metrics import psnr  # noqa: E402


def _affine_field(h, w):
    """A smooth, spatially varying colour transform: warm on the left, cold and dark on the right."""
    t = np.linspace(0, 1, w, dtype=np.float32)[None, :, None] * np.ones((h, 1, 1), np.float32)
    gain = np.concatenate([0.6 + 0.6 * t, 0.9 - 0.2 * t, 1.2 - 0.6 * t], axis=2)   # BGR
    off = np.concatenate([0.05 * t, 0.02 + 0 * t, 0.08 * (1 - t)], axis=2)
    return gain, off


def test_colormap_recovers_spatially_varying_transform(scene):
    gain, off = _affine_field(H, W)
    R = to_uint8(np.clip(to_float(scene) * gain + off, 0, 1))
    lac = LocalAffineColor(grid=(12, 9)).fit(scene, R)
    assert lac.fit_psnr > 30, lac.fit_psnr
    # a NEW image (people) gets the same position-dependent transform
    frames, _ = walkers(scene)
    f = frames[5]
    want = to_uint8(np.clip(to_float(f) * gain + off, 0, 1))
    assert psnr(want, lac.apply(f, strength=1.0)) > 30


def test_colormap_ignores_content_swaps(scene):
    """A pure global regrade plus a region whose content was REPLACED (like snow on grass): the
    learned mapping must stay close to the regrade there, not learn 'anything -> white'."""
    A = lambda x: np.clip(x * np.array([0.7, 0.8, 1.1], np.float32) + 0.05, 0, 1)
    Rf = A(to_float(scene))
    Rf[150:260, 40:200] = 0.97                                   # new content: snow
    lac = LocalAffineColor().fit(scene, to_uint8(Rf))
    got = lac.apply_float(to_float(scene), strength=1.0)[150:260, 40:200]
    want = A(to_float(scene))[150:260, 40:200]
    assert np.abs(got - want).mean() < 0.04
    assert np.array_equal(lac.apply(scene), lac.apply(scene))   # deterministic


# ------------------------------------------------------------------ seam-free effects
from crossover.effects import feet, trail_step  # noqa: E402


def test_trail_stamps_at_the_feet_and_fades_by_half():
    a = np.zeros((H, W), np.float32)
    a[100:200, 150:170] = 1.0                                     # person: feet at y = 199
    (fx, fy, bh), = feet(a, 50)
    assert abs(fy - 199) < 1 and abs(fx - 159.5) < 2 and bh == 100
    paint = trail_step(np.zeros((H, W), np.float32), a, decay=1.0, blur_px=2.0, min_area=50)
    assert paint[199, 160] > 0.5 and paint[20, 20] == 0.0         # on the ground at the feet, nowhere else
    fps, halflife = 10, 3.0
    decay = 0.5 ** (1 / (halflife * fps))
    p0 = paint[199, 160]
    empty = np.zeros_like(a)
    for _ in range(int(halflife * fps)):
        paint = trail_step(paint, empty, decay, 2.0, 50)
    assert abs(paint[199, 160] - 0.5 * p0) < 1e-3                 # half gone after one half-life


def test_depth_wave_endpoints():
    ds = DepthSplit(_ramp(), band=0.05)
    ds.tau = 1.08                                                 # wave not started: nothing changes
    assert ds.background_weight().max() < 1e-6
    ds.tau = -0.12                                                # wave has passed the camera: everything changed
    assert ds.background_weight().min() > 1 - 1e-6


from crossover.effects import portal_q, portal_weight, voronoi_cells, windows_frame  # noqa: E402


def test_shards_are_nearest_seed_and_deterministic():
    lab, pts = voronoi_cells(H, W, 14, seed=3)
    for k, (x, y) in enumerate(pts):
        assert lab[int(y), int(x)] == k                          # a seed lies in its own shard
    lab2, _ = voronoi_cells(H, W, 14, seed=3)
    assert np.array_equal(lab, lab2)
    assert len(np.unique(lab)) == 14


def test_portal_inside_outside_and_rim():
    q = portal_q(H, W, W / 2, H / 2, 60, 0.4)
    w = portal_weight(q)
    assert w[H // 2, W // 2] == 1.0 and w[5, 5] == 0.0
    assert abs(q[H // 2, W // 2 + 60] - 1.0) < 0.02              # the ring is at radius r
    assert abs(q[H // 2 + 24, W // 2] - 1.0) < 0.05              # ... and r * squash vertically


def test_windows_show_other_world_only_inside_people(scene):
    frames, masks = walkers(scene)
    F, R = to_float(frames[4]), to_float(apply_style(scene, "night"))
    a = masks[4].astype(np.float32)
    out = windows_frame(F, R, a)
    assert np.array_equal(out[a == 0], F[a == 0]) and np.allclose(out[a == 1], R[a == 1])
