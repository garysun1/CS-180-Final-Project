"""Reality Melts: a 16-s one-take loop of the plaza in which other worlds grow out of the same frame.

One take of vtest 58-74 s (10 fps, people held on threes), framed high (crop_y 0.25) so the facades
and the sky are in, with no cuts and no letterbox. Each world grows out of the filmed frame through
its ladder (morph.plaza_chain: plate -> filter -> lower-strength SD images -> world), far pixels
first, and people take the world's colour as the front reaches their feet. Every frame is the
paper's equation:

    out = composite(F, R, a, S, w, P, None, Q=Q),  R = ladder.at(N*u),  u = morph.grow_map(far, p)
    P, Q = the people ladder at N*c,  c = u at each person's feet (smoothed per person, afresh on
        each new ladder: a hop's c = 0 is the world people are already in)
    w = smoothstep(u / 0.12) when a world grows from the photo: where u = 0 the output is the filmed
        frame, bit for bit (w = 1 between two worlds)

Van Gogh's swirl moves R only: people, their shadows (S) and Q (the plate as seen in their soft
edges) stay put, so people stay crisp and their edges stay exact.

The people ladder has one colour mapping per rung (a LocalAffineColor fit of plate -> rung; the
world's own person styler on the top rung), so P = mix(styler_k(F), styler_k+1(F)) and Q the same of
the plate: people walk through the same light as the ground at their feet. (A straight lerp from F
to the world's styler leaves a bright halo where the matte holds some ground, e.g. a shadow by the
feet, while the ground around it is a dark night rung.) At c = 1 it is the world's styler, as in
World.render; at c = 0 the filmed person.

    python -m crossover.trailer --edit melt --size 960x540 --crf 20 --out out/melt.mp4
    python -m crossover.trailer --edit melt --size 720x720 --crf 20 --out out/melt_square.mp4
    python scripts/melt_stills.py                     # out/review/melt_sheet.jpg, before a render

Storyboard (32 beats at 120 BPM = 480 frames = 16 s), STORY below:
    B0-2      real
    B2-6      winter settles far-first (plate, filter, world); snow starts to fall
    B6-6.5    rewind, near-first, torn
    B6.5-9    night falls; its last step (n5 -> world) lands on B8: the lamps and windows come on
    B9-9.5    rewind
    B9.5-13.5 four one-beat hops: autumn, 1920s, underwater, cyberpunk (in halftone dots), each
              arrival a one-frame halftone print
    B13.5-14  drop: a white blink, back to the photo, near-silence
    B14-22    Van Gogh melts in far-first through its whole chain, the world swirling (people do not)
    B22-26    hold on the true single image
    B26-30    wake, near-first
    B30-32    real; the last frames dissolve into frame 0 under a white blink (LoopTitle's trick)
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from . import morph
from . import trailer as T
from .colormap import LocalAffineColor
from .composite import composite
from .depth import smoothstep
from .effects import FeetTracker, blobs
from .styles import comic
from .video_io import to_float, to_uint8

BEATS = 32
SPAN = (58.0, 74.0)               # vtest source seconds: 6-9 walkers, she crosses at 61.2 s
CROP_Y = 0.25                     # the facades and sky in frame
PUSH = 0.04                       # the slow push: 1.00 -> 1.04, eased back out on the wake
PUSH_AT = (0.5, 0.45)             # where it pushes in (output fractions)
LEAD = 0.45                       # grow_map: how far the far pixels run ahead of the near ones
EDGE = 0.12                       # w = smoothstep(u / EDGE): the filmed frame fades into the plate first
HOP_MORPH = 0.6                   # beats a hop morphs for (then it holds)
# beats the front runs over, and its curve p = x**k (k < 1: under way on the beat, steady after)
GROW = {"winter": (2.0, 5.5, 0.85), "night": (6.5, 7.8, 1.0), "vangogh": (14.0, 22.0, 0.75)}
LIGHTS = (7.8, 8.0)               # night's last step (n5 -> world), landing on B8
SNOW_IN = (4.0, 5.0)              # beats the snowfall fades in over (times u)
SWIRL = (14.0, 22.0, 14.0)        # Van Gogh's swirl: sin^2 envelope over these beats, peak px (source)
FEET_EMA = 8                      # output frames the feet tracker is replayed over
LOOP = 3                          # the last frames dissolve into frame 0 (the very last is frame 0) ...
LOOP_BLINK = (0.85, 0.6)          # ... under this white blink, so no ghost shows outside it
DROP_BLINK = (0.85, 0.45)         # the drop's blink, frames 1-2 of the drop
PRINT_SPLIT = 10.0                # px of rgb_split on a hop's arrival print (at 960 wide)
REWIND_SPLIT = 8.0                # px of rgb_split at the start of a rewind
# hops whose whole picture, colour too, arrives in the ladder's halftone dots (dots that grow until
# they merge, like a print); in the two-band blend only the fine detail would, which barely shows
PRINT_HOPS = ("cyberpunk",)


@dataclass(frozen=True)
class Chapter:
    """One part of the storyboard, in beats; the shots of the edit are these chapters."""
    name: str
    b0: float
    b1: float
    kind: str                     # real | grow | rewind | hop | drop | hold | wake
    world: str = ""
    prev: str = ""                # a hop's world before it ("" = the filmed frame)
    chip: str = ""
    chip_from: float = 0.0        # beats after b0 the chip appears


STORY = (
    Chapter("real", 0.0, 2.0, "real"),
    Chapter("winter", 2.0, 6.0, "grow", "winter", chip="WINTER", chip_from=0.5),
    Chapter("rewind winter", 6.0, 6.5, "rewind", "winter"),
    Chapter("night", 6.5, 9.0, "grow", "night", chip="NIGHT", chip_from=0.5),
    Chapter("rewind night", 9.0, 9.5, "rewind", "night"),
    Chapter("autumn", 9.5, 10.5, "hop", "autumn", chip="AUTUMN", chip_from=0.2),
    Chapter("1920s", 10.5, 11.5, "hop", "1920s", prev="autumn", chip="1920", chip_from=0.2),
    Chapter("underwater", 11.5, 12.5, "hop", "underwater", prev="1920s", chip="UNDERWATER", chip_from=0.2),
    Chapter("cyberpunk", 12.5, 13.5, "hop", "cyberpunk", prev="underwater", chip="CYBERPUNK", chip_from=0.2),
    Chapter("drop", 13.5, 14.0, "drop"),
    Chapter("van gogh", 14.0, 22.0, "grow", "vangogh", chip="VAN GOGH", chip_from=1.0),
    Chapter("hold", 22.0, 26.0, "hold", "vangogh", chip="VAN GOGH"),
    Chapter("wake", 26.0, 30.0, "wake", "vangogh"),
    Chapter("real end", 30.0, 32.0, "real"),
)
CHIPS = tuple(dict.fromkeys(c.chip for c in STORY if c.chip))
WORLDS = tuple(dict.fromkeys(c.world for c in STORY if c.world))


def chapter_at(b: float) -> Chapter:
    """The chapter playing at beat b (clamped to the storyboard)."""
    for c in STORY:
        if b < c.b1:
            return c
    return STORY[-1]


def push_at(b: float) -> float:
    """The zoom at beat b: 1 while real, easing to 1 + PUSH by the hold, back to 1 over the wake."""
    if b <= 2.0 or b >= 30.0:
        return 1.0
    if b < 22.0:
        e = T.ease((b - 2.0) / 20.0)
    elif b < 26.0:
        e = 1.0
    else:
        e = 1.0 - T.ease((b - 26.0) / 4.0)
    return 1.0 + PUSH * e


def swirl_px(b: float) -> float:
    """Van Gogh's swirl amplitude at beat b (source px at 768 wide): sin^2, 0 at both ends."""
    b0, b1, peak = SWIRL
    if not b0 < b < b1:
        return 0.0
    return float(peak * np.sin(np.pi * (b - b0) / (b1 - b0)) ** 2)


def curl_fields(h: int, w: int, cell: float, seed: int = 0, n: int = 2) -> np.ndarray:
    """n divergence-free flows (n, H, W, 2) with unit peak speed: the curl (d/dy, -d/dx) of blurred
    white noise, so the swirl turns around vortices instead of pushing the picture one way. (Value
    noise would leave its lattice in the flow: its gradient vanishes on every lattice line.)"""
    rng = np.random.default_rng(seed + 31)
    out = []
    for _ in range(n):
        psi = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), cell / 2.5)
        gy, gx = np.gradient(psi)
        v = np.stack([gy, -gx], -1)
        out.append(v / max(float(np.sqrt((v * v).sum(-1)).max()), 1e-12))
    return np.stack(out).astype(np.float32)


def lac_crop(lac: LocalAffineColor, Ff: np.ndarray, box) -> np.ndarray:
    """lac.apply() on the box (y0, y1, x0, x1) of a float frame only, quantised as apply() does."""
    y0, y1, x0, x1 = box
    A, f = lac.field[y0:y1, x0:x1], Ff[y0:y1, x0:x1]
    out = (A[..., :3] * f[..., None, :]).sum(-1) + A[..., 3]
    return to_float(to_uint8(np.clip(lac.strength * out + (1 - lac.strength) * f, 0, 1)))


def gather(stack: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Per-pixel linear interpolation in a stack (K, H, W, 3) at positions r (H, W) in [0, K - 1]."""
    n, h, w = stack.shape[0] - 1, stack.shape[1], stack.shape[2]
    k = np.minimum(r.astype(np.intp), n - 1)
    f = (r - k)[..., None].astype(np.float32)
    flat, idx = stack.reshape(-1, 3), k.reshape(-1) * (h * w) + np.arange(h * w)
    a = np.take(flat, idx, axis=0).reshape(h, w, 3)
    b = np.take(flat, idx + h * w, axis=0).reshape(h, w, 3)
    return a + f * (b - a)


def swirl_maps(v: np.ndarray, amp: float, weight: np.ndarray | None = None, steps: int = 4):
    """cv2.remap maps that carry each pixel `amp` px along the flow v (H, W, 2) in `steps` Euler steps
    (curved paths, so it swirls), scaled per pixel by weight (0..1). No pixel moves more than amp."""
    h, w = v.shape[:2]
    my, mx = np.mgrid[0:h, 0:w].astype(np.float32)
    k = np.float32(amp / steps)
    k = k if weight is None else (k * weight).astype(np.float32)
    for _ in range(steps):
        s = cv2.remap(v, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        mx += k * s[..., 0]
        my += k * s[..., 1]
    return mx, my


@dataclass
class State:
    """What frame j shows: a ladder and how far up it each pixel is, and whose colours people take."""
    ch: Chapter
    lad: morph.Ladder | None = None    # None: the filmed frame
    p: float = 0.0                     # the front's progress (grow_map's p)
    reverse: bool = False              # near pixels leave first
    lights: float | None = None        # night: its last step (n5 -> world), whole frame at once
    src: str | None = None             # the world the ladder starts from (None: the filmed frame) ...
    dst: str | None = None             # ... and the one it ends in
    swirl: float = 0.0                 # px
    dots: bool = False                 # the picture switches in the ladder's dots (PRINT_HOPS)
    snow: float = 0.0                  # the snowfall's level (times u)
    lead: float = LEAD

    def prog(self, far: np.ndarray) -> np.ndarray:
        """How far up the ladder each pixel is, 0 (the filmed frame, or src's world) .. 1 (dst's)."""
        far = np.asarray(far, np.float32)
        if self.lad is None:
            return np.zeros(far.shape, np.float32)
        if self.lights is not None:                 # night: plate -> n5 far-first, then the lights
            n = self.lad.n
            return ((n - 1) * morph.grow_map(far, self.p, self.lead) + np.float32(self.lights)) / np.float32(n)
        return morph.grow_map(far, self.p, self.lead, self.reverse)


class Melt:
    """The whole take, frame by frame (render order does not matter: every frame is computed from its
    own index). frame(j) is output frame j before finish(); composed(j) is the paper's equation at
    source size. Plaza-only: the ladders, farness and worlds are the plaza's."""

    def __init__(self, video: str = T.VTEST, clean: str = T.CLEAN, span=SPAN, bpm: float = 120.0,
                 crop_y: float = CROP_Y, lead: float = LEAD, seed: int = 0):
        self.video, self.clean, self.span = video, clean, span
        self.crop_y, self.lead, self.seed = crop_y, lead, seed
        self.fpb = T.FPS * 60.0 / bpm                # frames per beat (15 at 120 BPM)
        self.n_frames = int(round(BEATS * self.fpb))
        self.ready = False

    # ------------------------------------------------------------------ setup
    def setup(self):
        if self.ready:
            return
        self.feed = T.feed(self.video, self.clean, *self.span)
        self.fps = T.Reader.get(self.video).fps
        bg = self.feed.bg
        self.h, self.w = bg.shape[:2]
        self.s = self.w / 768.0
        self.Bf = to_float(bg)
        far = morph.plaza_farness()
        if far.shape != (self.h, self.w):
            far = cv2.resize(far, (self.w, self.h), interpolation=cv2.INTER_LINEAR)
        # the front runs on the ground's farness: the depth map makes thin things (the lamp post, the
        # tripod, the sign) much nearer than the ground they stand on, and they would lag behind it
        r = max(1, int(round(9 * self.s)))
        far = cv2.dilate(far, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        self.far = cv2.GaussianBlur(far, (0, 0), 3.0 * self.s)
        self.wo = {k: T.world_obj(k, self.clean, T.plate_path(k)) for k in WORLDS}
        self.lad = {k: morph.plaza_ladder(k, seed=i) for i, k in enumerate(("winter", "night", "autumn", "vangogh"))}
        pick = {k: self.lad[k].rungs[-1] if k in self.lad else cv2.imread(T.plate_path(k)).astype(np.float32)
                for k in WORLDS}
        self.hop = {}
        for i, c in enumerate(STORY):
            if c.kind == "hop":
                self.hop[c.name] = (self.lad[c.world] if not c.prev else
                                    morph.Ladder([pick[c.prev], pick[c.world]], [c.prev, c.world], seed=10 + i,
                                                 pattern=morph.PATTERN.get(c.world, "noise")))
        # the people ladder of every ladder: a colour mapping per rung (None: as filmed) and the plate
        # as each one sees it (Q)
        self.people = {}
        for name, lad in self.lad.items():
            lacs = [None] + [LocalAffineColor(strength=0.9, seed=0).fit(bg, np.clip(np.rint(r), 0, 255).astype(np.uint8))
                             for r in lad.rungs[1:-1]] + [self.wo[name].styler.lac]
            self.people[id(lad)] = self._people_ladder(lacs)
        for c in STORY:
            if c.kind == "hop" and c.prev:
                self.people[id(self.hop[c.name])] = self._people_ladder([self.wo[c.prev].styler.lac,
                                                                        self.wo[c.world].styler.lac])
        self.curl = curl_fields(self.h, self.w, 110.0 * self.s, self.seed)
        self.dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        self.min_area = 3e-4 * self.h * self.w
        self.feet_r = max(2, int(round(3 * self.s)))
        self._src, self._sty, self._blobs, self._summ, self._box = {}, {}, {}, {}, {}
        self._first = None
        self.ready = True

    def _people_ladder(self, lacs):
        """(colour mappings, Q stack (K, H, W, 3)): the plate in each rung's colours."""
        return lacs, np.stack([self.Bf if lac is None else to_float(lac.apply(self.feed.bg)) for lac in lacs])

    # ------------------------------------------------------------------ time
    def beat(self, j: int) -> float:
        return j / self.fpb

    def src_index(self, j: int) -> int:
        """The source frame shown at output frame j (10 fps held on threes)."""
        return int((self.span[0] + j / T.FPS) * self.fps + 1e-6)

    def state(self, j: int) -> State:
        b = self.beat(j)
        c = chapter_at(b)
        if c.kind in ("real", "drop"):
            return State(c, lead=self.lead)
        if c.kind == "hop":
            p = T.ease((b - c.b0) / HOP_MORPH)
            return State(c, self.hop[c.name], p, src=c.prev or None, dst=c.world, lead=self.lead,
                         dots=bool(c.prev) and c.world in PRINT_HOPS)
        lad = self.lad[c.world]
        if c.kind == "grow":
            g0, g1, k = GROW[c.world]
            p = float(np.clip((b - g0) / (g1 - g0), 0.0, 1.0)) ** k
            lights = T.ease((b - LIGHTS[0]) / (LIGHTS[1] - LIGHTS[0])) if c.world == "night" else None
            snow = T.ease((b - SNOW_IN[0]) / (SNOW_IN[1] - SNOW_IN[0])) if c.world == "winter" else 0.0
            return State(c, lad, p, lights=lights, dst=c.world,
                         swirl=swirl_px(b) * self.s if c.world == "vangogh" else 0.0, snow=snow, lead=self.lead)
        if c.kind == "hold":
            return State(c, lad, 1.0, dst=c.world, lead=self.lead)
        q = (b - c.b0) / (c.b1 - c.b0)                               # rewind (linear) or wake (eased)
        q = q if c.kind == "rewind" else T.ease(q)
        return State(c, lad, q, reverse=True, dst=c.world, snow=1.0 if c.world == "winter" else 0.0,
                     lead=self.lead)

    def u_map(self, j: int) -> np.ndarray:
        """Per-pixel progress (0 the filmed frame or the world left behind .. 1 the arriving world)."""
        return self.state(j).prog(self.far)

    # ------------------------------------------------------------------ events
    def first_frame_at(self, b: float) -> int:
        """The first output frame at or after beat b."""
        return int(np.ceil(b * self.fpb - 1e-6))

    def prints(self) -> list[int]:
        """Frames of the hops' arrival prints (one each, one beat apart)."""
        return [self.first_frame_at(c.b0 + HOP_MORPH) for c in STORY if c.kind == "hop"]

    def blinks(self) -> dict[int, float]:
        """White blinks, frame -> amount: the drop's and the loop's."""
        d = self.first_frame_at(next(c.b0 for c in STORY if c.kind == "drop"))
        n = self.n_frames
        return {d: DROP_BLINK[0], d + 1: DROP_BLINK[1], n - 3: LOOP_BLINK[0], n - 2: LOOP_BLINK[1]}

    def flashes(self) -> list[dict]:
        """Every flash-like event (a print, a blink, a torn rewind), each counted once, by frame."""
        ev = [{"frame": f, "kind": "print", "frames": 1} for f in self.prints()]
        bl = sorted(self.blinks())
        ev += [{"frame": f, "kind": "blink", "frames": 2} for f in bl[::2]]
        for c in STORY:
            if c.kind == "rewind":
                a, b = self.first_frame_at(c.b0), self.first_frame_at(c.b1)
                ev.append({"frame": a, "kind": "tear", "frames": b - a})
        return sorted(ev, key=lambda e: e["frame"])

    def chip(self, j: int) -> str:
        b = self.beat(j)
        c = chapter_at(b)
        return c.chip if c.chip and b >= c.b0 + c.chip_from else ""

    # ------------------------------------------------------------------ people
    def _get(self, i: int):
        """(frame, F, alpha, S) of source frame i (the last two kept)."""
        if i not in self._src:
            if len(self._src) > 1:
                self._src.pop(next(iter(self._src)))
            self._src[i] = self.feed.get(i)
        return self._src[i]

    def _people(self, i: int):
        """Person blobs of source frame i (the last two kept), as effects.blobs."""
        if i not in self._blobs:
            if len(self._blobs) > 1:
                self._blobs.pop(next(iter(self._blobs)))
            self._blobs[i] = blobs(self._get(i)[2], self.min_area)
        return self._blobs[i]

    def _summary(self, i: int):
        """[(centroid x, y, farness at the feet)] of each blob of source frame i (cached)."""
        if i not in self._summ:
            f, a = self.feed.items[int(np.clip(i, self.feed.lo, self.feed.hi))]
            r, out = self.feet_r, []
            for _, fx, fy, _, cx, cy in blobs(a.astype(np.float32), self.min_area):
                ya, yb = int(min(self.h - 1, fy)), int(min(self.h, fy + 2 * r + 1))
                xa, xb = int(max(0, fx - r)), int(min(self.w, fx + r + 1))
                out.append((float(cx), float(cy), float(np.median(self.far[ya:yb, xa:xb]))))
            self._summ[i] = out
        return self._summ[i]

    def feet_values(self, j: int) -> list[float]:
        """Each person's progress at frame j: the front's u at their feet, smoothed per person by a
        FeetTracker (as Flood.render) replayed over the last FEET_EMA frames, so any frame can be
        rendered on its own and comes out the same. The replay starts where frame j's ladder does: on
        another ladder c means progress toward another world (a hop starts at c = 0, the old world)."""
        tr = FeetTracker(40.0 * self.s)
        vals: list[float] = []
        lad, j0 = self.state(j).lad, j
        while j0 > max(0, j - FEET_EMA) and self.state(j0 - 1).lad is lad:
            j0 -= 1
        for jj in range(j0, j + 1):
            st, summ = self.state(jj), self._summary(self.src_index(jj))
            if not summ:
                vals = tr.update([])
                continue
            u = st.prog(np.array([ff for _, _, ff in summ], np.float32))
            vals = tr.update([(cx, cy, float(v)) for (cx, cy, _), v in zip(summ, u)])
        return vals

    def _boxes(self, i: int):
        """Boxes (y0, y1, x0, x1) around the matte's support in source frame i (cached): P and Q are
        only read there (composite() uses R*S elsewhere)."""
        if i not in self._box:
            m = cv2.dilate((self._get(i)[2] > 0.004).astype(np.uint8), np.ones((5, 5), np.uint8))
            _, _, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
            self._box[i] = [(int(y), int(y + h), int(x), int(x + w)) for x, y, w, h, _ in st[1:]]
        return self._box[i]

    def _rung_colour(self, lac, i: int) -> np.ndarray:
        """Source frame i in one rung's colours inside the people boxes (the filmed frame elsewhere)."""
        F = self._get(i)[1]
        if lac is None:
            return F
        key = (id(lac), i)
        if key not in self._sty:
            if len(self._sty) > 8:
                self._sty.pop(next(iter(self._sty)))
            P = F.copy()
            for y0, y1, x0, x1 in self._boxes(i):
                P[y0:y1, x0:x1] = lac_crop(lac, F, (y0, y1, x0, x1))
            self._sty[key] = P
        return self._sty[key]

    def people_colour(self, lad: morph.Ladder, i: int, c: np.ndarray):
        """(P, Q): people in the colours of the people ladder at position n*c (per pixel), and the
        plate as seen in them."""
        lacs, Qs = self.people[id(lad)]
        r = np.clip(c * np.float32(lad.n), 0, lad.n).astype(np.float32)
        return gather(np.stack([self._rung_colour(lac, i) for lac in lacs]), r), gather(Qs, r)

    # ------------------------------------------------------------------ the picture
    def composed(self, j: int, parts: bool = False):
        """The paper's equation at source size, float32 HxWx3 in [0, 1]; None when the whole frame is
        the filmed one. parts=True returns a dict with the intermediate maps too."""
        st = self.state(j)
        i = self.src_index(j)
        f, F, a, S = self._get(i)
        if st.lad is None:
            return {"state": st, "out": None, "F": F, "alpha": a} if parts else None
        u = st.prog(self.far)
        if st.dots:                                        # two_band with one low band: a pure dot switch
            lad = st.lad
            R = morph.two_band(lad.rungs[0], lad.rungs[1], lad.low[0], lad.low[0], u, lad.th)
        else:
            R = st.lad.at(u * np.float32(st.lad.n))
        R *= np.float32(1 / 255)
        if st.swirl > 0:                                   # the world swirls; people, Q and S do not
            b0, b1, _ = SWIRL
            th = 0.5 * np.pi * (self.beat(j) - b0) / (b1 - b0)
            v = np.float32(np.cos(th)) * self.curl[0] + np.float32(np.sin(th)) * self.curl[1]
            v /= np.float32(max(float(np.sqrt((v * v).sum(-1)).max()), 1e-12))
            mx, my = swirl_maps(v, st.swirl, u)
            R = cv2.remap(R, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if "underwater" in (st.src, st.dst):               # caustics where the underwater world is
            k = u if st.dst == "underwater" else 1 - u
            g = self.wo["underwater"].anim.plate_gain(j / T.FPS * 10.0)
            R *= (1 + (g - 1) * k)[..., None]
        # people: each takes the progress at their feet; anything outside a blob, the ground's
        c = u.copy()
        for (m, *_), v in zip(self._people(i), self.feet_values(j)):
            c[cv2.dilate(m, self.dil).astype(bool)] = v
        P, Q = self.people_colour(st.lad, i, c)
        w = smoothstep(u / np.float32(EDGE)) if st.src is None else self.feed.ones
        out = composite(F, R, a, S, w, P, None, Q=Q)
        if st.snow > 0:                                    # snow falls where winter is, over everyone
            rgb, af = self.wo["winter"].anim.front_layer(j / T.FPS * 10.0)
            out = out + (af * u * np.float32(st.snow))[..., None] * (rgb - out)
        if parts:
            return {"state": st, "out": out, "F": F, "alpha": a, "S": S, "R": R, "P": P, "Q": Q, "u": u, "c": c,
                    "w": w}
        return out

    def plain(self, j: int) -> np.ndarray:
        """Output frame j with the push but before any accent, chip or the loop dissolve (uint8)."""
        out = self.composed(j)
        img = self._get(self.src_index(j))[0] if out is None else to_uint8(out)
        return T.zoom(T.fit(img, self.crop_y), push_at(self.beat(j)), *PUSH_AT)

    def first(self) -> np.ndarray:
        if self._first is None:
            self._first = self.plain(0)
        return self._first

    def frame(self, j: int, accents: bool = True) -> np.ndarray:
        """Output frame j (uint8 W x H) before finish(). The last frame is exactly the first, and the
        ones before it dissolve into it under a white blink, so the loop point does not show."""
        self.setup()
        n = self.n_frames
        j = int(np.clip(j, 0, n - 1))
        if j == n - 1:
            return self.first().copy()
        img = self.plain(j)
        if j >= n - LOOP:
            p = T.ease((j - (n - 1 - LOOP)) / LOOP)
            img = cv2.addWeighted(img, 1 - p, self.first(), p, 0)
        if accents:
            img = self._accents(j, img)
        text = self.chip(j)
        return T.mono_label(img, text) if text else img

    def _accents(self, j: int, img: np.ndarray) -> np.ndarray:
        st = self.state(j)
        k = T.W / 960.0
        if st.ch.kind == "rewind":                        # torn, colour-split, easing off
            q = (self.beat(j) - st.ch.b0) / (st.ch.b1 - st.ch.b0)
            rng = np.random.default_rng(1000 * self.seed + j)
            img = T.tear(img, rng, 5, shift=int(round(40 * k)))
            img = T.rgb_split(img, REWIND_SPLIT * k * (1 - 0.6 * q))
        if j in self.prints():                            # a one-frame halftone print
            img = T.rgb_split(comic(img), PRINT_SPLIT * k)
        amt = self.blinks().get(j, 0.0)
        return T.flash(img, amt) if amt > 0 else img

    # ------------------------------------------------------------------ the edit
    def src_t(self, j: int) -> float:
        return round(self.span[0] + j / T.FPS, 3)

    def edl_extra(self, first: int, n: int, name: str) -> dict:
        c = next(c for c in STORY if c.name == name)
        ev = [e for e in self.flashes() if first <= e["frame"] < first + n]
        return {"kind": c.kind, "world": c.world or None, "beats_span": [c.b0, c.b1], "chip": c.chip or None,
                "flashes": ev}


@dataclass
class MeltShot(T.Shot):
    """One chapter of the melt in the edit decision list. All chapters draw from one shared Melt by
    their frame index in the whole piece, so the take never cuts."""
    melt: Melt | None = None
    first: int = 0                     # the chapter's first frame in the whole piece
    bars: bool = False

    def setup(self):
        self.melt.setup()

    def render(self, j, n):
        return self.melt.frame(self.first + j)

    def source(self, n):
        return self.melt.video, self.melt.src_t(self.first), self.melt.src_t(self.first + n)

    def edl_extra(self, n):
        return self.melt.edl_extra(self.first, n, self.name)


def edit_melt(bpm: float = 120.0) -> list[T.Shot]:
    """The melt as one shot per chapter (the review sheet and the EDL get one entry each). A shot's
    beats are its chapter's frames over frames per beat, so the start frames main() rounds from them
    are the chapters' own first frames (a chapter on a half beat starts on the frame after it, as
    chapter_at has it); the storyboard's beats are in the EDL as beats_span."""
    m = Melt(bpm=bpm)
    f = [m.first_frame_at(c.b0) for c in STORY] + [m.n_frames]
    return [MeltShot((f[k + 1] - f[k]) / m.fpb, "melt", name=c.name, melt=m, first=f[k])
            for k, c in enumerate(STORY)]


# ============================================================================ sound
def melt_soundtrack(shots, starts, n_frames, beat_s, seed=0):
    """The melt's mix on the beat grid: heartbeat kicks while real, a riser per chapter, a reverse
    whoosh and a tape-stop per rewind, the lamps' kick and ring on B8, a groove under the hops (a kick
    a beat, hats 8ths then 16ths, a blip per arrival), near-silence on the drop, a braam, crash and sub
    on the Van Gogh entry and a pad under it, a riser into the hold, the pad's decay on the wake, and a
    ~20 ms fade at the tail so the loop point does not click."""
    SR = T.SR
    rng = np.random.default_rng(seed)
    n_out = int(round(n_frames / T.FPS * SR))
    N = n_out + SR
    music, fx, bed = (np.zeros(N, np.float32) for _ in range(3))

    def add(track, x, b, g=1.0):                         # at beat b
        s = int(round(b * beat_s * SR))
        if 0 <= s < N:
            e = min(N, s + len(x))
            track[s:e] += g * x[: e - s]

    def heartbeat(b):
        add(music, T.kick(rng, 0.35, 90, 45), b, 0.6)
        add(music, T.kick(rng, 0.3, 75, 38), b + 0.34, 0.35)          # lub-dub
    for b in (0, 1, 30, 31):
        heartbeat(b)
    # winter: a riser up to the rewind, whose top tape-stops into it, under a soft wind
    x = T.riser(rng, 3.5 * beat_s, hold=0.4)
    cut = int(3.5 * beat_s * SR)
    add(bed, x[:cut], 2.5, 0.6)
    add(bed, T.tape_stop(x[cut:], 0.45), 6.0, 0.6)
    nw = int(4.0 * beat_s * SR)
    wind = T._bp(T._noise(nw, rng), 250, 1800) * np.sin(np.linspace(0, np.pi, nw)) ** 2
    add(bed, wind.astype(np.float32), 2.0, 0.3)
    add(fx, T.kick(rng, 0.5, 80, 35), 2.0, 0.45)
    # night: a riser into B8, where the lamps come on (kick and ring), then a rewind
    add(bed, T.riser(rng, 1.5 * beat_s), 6.5, 0.45)
    add(fx, T.kick(rng, 0.6, 100, 35), 8.0, 0.8)
    add(fx, T.ring(1.1 * beat_s), 8.0, 0.55)
    for b in (6.0, 9.0):                                              # the rewinds
        add(fx, T.whoosh(rng, 0.5 * beat_s + 0.1, rev=True), b - 0.1, 0.55)
    x = T.riser(rng, 0.5 * beat_s, hold=0.4)
    add(bed, T.tape_stop(x[int(0.5 * beat_s * SR):], 0.4), 9.0, 0.4)
    # the hops: a groove on the hop starts, hats 8ths then 16ths, a blip on every arrival
    roots = [55, 65.4, 49, 73.4]
    for k in range(4):
        b = 9.5 + k
        add(music, T.kick(rng), b, 0.95)
        if k % 2 == 1:
            add(music, T.snare(rng), b + 0.5, 0.6)
        for q in ((0.0, 0.5) if k < 2 else (0.0, 0.25, 0.5, 0.75)):
            add(music, T.hat(rng), b + q, 0.45)
        n = int(beat_s / 2 * SR)
        tt = np.arange(n) / SR
        for e in (0.0, 0.5):
            add(music, (np.sin(2 * np.pi * roots[k] * tt) * T._env(n, 0.003, 0.12)).astype(np.float32), b + e, 0.5)
        add(fx, T.whoosh(rng, 0.16), b - 0.16, 0.3)
        add(fx, T.blip(rng), b + HOP_MORPH, 0.6)
    # Van Gogh: the entry hit, a pad under the melt and the hold, a riser into the hold
    add(fx, T.braam(rng, 3.0), 14.0, 0.85)
    add(fx, T.crash(rng, 1.4), 14.0, 0.6)
    add(fx, T.kick(rng, 0.8, 120, 30), 14.0, 1.0)
    dur = 16.5 * beat_s
    pd = T.pad(dur, [174.6, 220.0, 261.6, 329.6], rng)
    t = np.arange(len(pd)) / SR
    env = np.exp(t / (dur * 0.9))                                    # undo pad()'s own decay ...
    env *= 1 - smoothstep(np.float32((t - 11.5 * beat_s) / (4.5 * beat_s)))   # ... and decay on the wake
    add(bed, (pd * env).astype(np.float32), 14.5, 0.9)
    add(bed, T.riser(rng, 4 * beat_s), 18.0, 0.35)
    add(fx, T.kick(rng, 0.6, 80, 35), 22.0, 0.5)
    add(fx, T.crash(rng, 1.0), 22.0, 0.25)
    add(fx, T.ring(4 * beat_s, 659.3), 22.0, 0.25)
    add(fx, T.whoosh(rng, 1.0, rev=True), 30.0 - 1.0 / beat_s, 0.4)  # into the real plaza again
    mix = 0.8 * T.reverb(music, rng, 0.8, 0.12) + T.reverb(fx, rng, 1.6, 0.35) + 0.9 * bed
    T._hush(mix, 14.0 * beat_s, beat_s)                               # the drop lands on nothing
    mix = mix[:n_out]
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-6) * 1.4) * 0.89
    k = int(0.02 * SR)                                                # the loop point: no click
    mix[-k:] *= np.linspace(1, 0, k)
    mix[:int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))
    return np.stack([mix, mix], 1).astype(np.float32)
