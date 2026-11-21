# Cross the Line: live portal kiosk

A webcam points at the booth. Anyone who crosses the line (or steps into the ring, or walks under the
lens) appears in another world, live, at full resolution, without flicker.

**How it works:**
- **Empty scene:** captured once as a masked temporal median.
- **Worlds:** made from that one image, either instantly in a shader or by Stable Diffusion
  running on the laptop.
- **People:** found every frame by Google's MediaPipe selfie segmenter, combined with a
  background-difference mask.
- **People's colour:** in a generated world, people get the paper's local colour field
  (`crossover/colormap.py`, strength 0.9): a smooth grid of 3×4 colour affines fitted from the empty
  scene to the world. Worlds built offline carry the grid. Worlds made on the spot use a robust
  global fit (`plate.js`), so people stay solid instead of turning into ghosts of the world's
  average colour.
- **Composite:** everything is combined on the GPU in a single WebGL2 shader. It is the same
  equation as `crossover/composite.py`.
- **Grow (on by default):** the rule is not a cut but a band where the world is still forming. It
  grows out of the filmed scene through the images that made it (below).
- **Hold to flood:** press and hold anywhere, and the world pours out from under your finger over the
  whole scene; each walker bursts as it reaches their feet (below).

Nothing leaves the laptop and nothing is recorded.

## Grow: the world grows instead of cutting

Every rule's seam, and the world-change wave, morph through the world's **ladder**:
- **The ladder:** the empty scene; the exact image Stable Diffusion's img2img started from (the
  world's colour filter of the empty scene); a lower-strength SD image of the same world (same seed
  and schedule, fewer denoising steps); then the world. All are pixel-aligned.
- **The walk:** the same two-band blend as `crossover/morph.py`. Colour (a mip-level-2.5 blur)
  crossfades between neighbouring rungs, while detail switches in 18-px noise patches, so nothing is
  double-exposed. A generated world named Cyberpunk or Comic switches in the halftone screen's dots
  instead. The blend is exact at every rung.
- **One-sided:** each rule gives u in [0, 1], and the background is the ladder at N·u:

  | Rule | u |
  |---|---|
  | Line | the distance past the line over the band (120 px at 768 wide) |
  | Lens | the outer half of the lens |
  | Portal | the ring becomes a pool: real at the rim, the full world at 40% of the radius |
  | Depth ("AI fog") | (farness − τ) / 0.25: near is real, far is fully dreamed |
  | Whole | 1 |

  Where u = 0 the page shows the camera pixel itself, bit for bit. The band starts as the camera
  frame, crossfades into the empty scene (the same scene) over its first 12%, then climbs the
  ladder.
- **People:** they keep the paper's equation. Their colour field is applied at strength c: u per
  pixel on the line and lens (a walker straddling the band warms across their body), u at their
  feet on the portal and depth rules, and in full inside a crossing burst. Crossings still use the
  exact rule, so whooshes and bursts fire at the line.
- **World change:** a 0.30-farness front rolls in from the horizon over 1.4 s. Behind it the old
  world unmakes back to the empty scene through its own ladder; beyond it the new world grows.
  People follow the ground: behind the front they keep the old world's colours (both colour fields
  share one texture for the 1.4 s), at the front they are themselves, and beyond it they take the new
  world's colours. The rim sits where the image is the filmed scene. (Cut keeps its old wave, where
  people take the new world's colours at once.)
- **Glow:** a 0.3× glint just inside the world on the line and lens, the ring's rim, and no contour
  on depth.
- **Cut:** the **Morph** chip (key `E`) or `?seam=cut` restores the exact 3-px seam: the same code
  path as before Grow. Scroll on the line to change the band width (24–420 px).
- **Ladders on the page:** `scripts/build_portal_artifact.py` writes `media/{scene}_{world}_r1.jpg`
  (the filter image) for every world, and for the plaza `_r2.jpg` (the SD rung nearest the middle,
  minus the rungs `morph.EXCLUDE` drops). That gives Night, 1920s, Autumn and Underwater n5 and Van
  Gogh n7. Winter (its n4 turns a rock on the lawn red) and Cyberpunk have no middle rung.
  `scenes.json` lists them as `worlds[i].ladder = [{src, n}]`. The 19 JPEGs (q85, or q80 above
  150 KB) add 1.51 MB, so the page is 11.72 MB.
- **Worlds made on the spot** (kiosk server worlds, dropped images) have no ladder and grow straight
  from the empty scene (one step). Filter worlds, the shader's Comic among them, have no ladder
  either: they fade in over the empty scene, with no patches or dots.
- **GPU:** the current world's ladder and the previous one's share one mipmapped 2D-array texture
  (unit 8). The plate is layer 0, and two slots of three layers hold the rungs above it. The mip
  chain is regenerated after every upload, including a plate recapture.

## Hold to flood

Press and hold on the picture: a ring opens on the ground under your finger and the world pours out
until it covers the scene. It is the trailer's Flood shot (`trailer.Flood.ring_at`), played by hand.
- **The gesture:** a press held for 280 ms without moving more than 8 px starts a flood. On a walker
  (inside their box) it starts from their feet. Moving first drags the line as before, a tap still
  places it (on release), and moving while held steers the flood. A hold also waits for 3 drawn
  frames: moves arrive with frames, so on a slow page (SwiftShader, 1-3 fps) a drag stays a drag;
  at 60 fps this adds nothing.
- **The ring:** u = time held / 1.4 s. The radius is (rMax + 160 px)·(1 − (1 − u)^2.2), where rMax is
  the distance to the farthest corner, and the squash goes from 0.38 (a ring on the ground) to 1. It
  has no breathing.
- **Letting go:** it drains back into your finger over 0.6 s. A flood held full for 0.5 s stays
  until the next tap (or `O`).
- **The rule:** the flood is a ring of its own over the current rule. It takes the rule over in its
  first 0.3 s, which then recedes (in Grow, back down its ladder), and gives it back as it drains, so
  neither end pops. Held, it is the portal rule with that ring:
  - In Grow its front is a morph band 160 px wide (the outer 60% of the ring while it is small).
  - In Cut it is a 3-px edge.
  - Its rim is measured in px, so it stays thin as the ring grows, and it stays behind people.
- **People:** everyone goes by their feet, as on the portal. The per-person weights are recomputed
  every frame from the moving front, so colour follows it even with the clip paused. Crossings use
  the flood too, so each walker crosses, with a whoosh and a burst, as the front reaches their feet;
  while it is open, each walker's smoothed weight follows it twice as fast (0.7 per analysed frame
  instead of 0.35), since the front moves fast and one way.
  The existing limits (one whoosh per 600 ms, one burst per 900 ms, 2 s per person) keep it
  flash-safe.
- **Pixels that are not a person:** alpha also covers the mask's fading trail and filled holes. In
  Grow, those pixels follow the ground's level, not 0, so no box of empty scene shows around walkers
  on the feet rules (portal, depth, flood). The per-person texture holds each person's value and
  where people are. Cut's portal and depth read the value exactly as before.
- **Sound:** band-passed noise rising from 300 to 3300 Hz that swells with u while the flood grows.
  When it covers everything the rush ends in a whoosh and fades out, so a full flood, held or kept,
  is quiet; the rush comes back, falling, as the flood drains. It starts only once sound is on.
- **Phones:** the canvas has `-webkit-touch-callout: none` and `user-select: none`, and its context
  menu is suppressed, so a long press shows no callout and selects nothing.
- **Hint:** on the hosted page, a one-time toast "Hold to flood." after the first crossing.
- **Kiosk:** hold `O` for a flood from the centre of the frame.
- **Test hooks:** `__portal.flood(x, y, u)` holds a flood at phase u (the rule taken over);
  `flood(null)` lets it drain. `floodGain()` is the rush's gain now (0 when none plays).
  `compareBox(x0, x1, y0, y1)` compares a box with the camera.
  `reanalyse(n)` analyses the current frame again n times, so a paused frame's mask settles (its
  fading trail goes, as in motion) before a screenshot.

## Run it

```bash
bash portal/fetch_vendor.sh                 # once: MediaPipe (Apache-2.0) + segmenter models, ~29 MB
python -m crossover.portal_server           # http://localhost:8000  (camera needs localhost or https)
```

Open <http://localhost:8000> in Chrome, click **Start the portal**, allow the camera, and step aside
for three seconds while the empty scene is captured. People may stay in view: they are masked out.

- **With the server running**, the captured scene is sent to it, and generated worlds appear one
  by one as they finish: Van Gogh, cyberpunk, winter, night, 1920s. Each takes seconds on an NVIDIA
  GPU and longer on Apple Silicon (not measured). On this container's CPU the first world took
  12 min, including the model load, while the browser shared the CPU; plan on a GPU laptop.
  - Needs `pip install -r requirements-gen.txt`, the depth model (`bash scripts/fetch_depth_model.sh`)
    and Hugging Face access the first time.
- **Without generation** (`--no-generate`), the six shader worlds work instantly. You can also drop
  any image of this exact view onto the page to add it as a world.

`?source=clip` starts on the recorded fallback clip (`clips/fallback.mp4`, or `?clip=path.mp4`).
`?mirror=0` turns off the selfie mirror. `?debug=1` shows the mask, fps and timings.

## Hosted demo (no install)

The same code also runs as a web page on recorded scenes. The page is
<https://claude.ai/artifact/X5CC9ZXuQ7xwdemQcU9apw>; it is private until shared.
- **Scenes:** the plaza, crowd and street clips. Each has its clean plate, Stable Diffusion worlds
  made offline (each with its colour field), a depth map, and the depth and edge images Stable
  Diffusion was given.
- **Opening:** the plaza opens 5 s before a walker crosses the line (vtest 59.4 s, found with
  `scripts/find_moments.py`).
- **No camera, server or segmenter there:** people come from the background-difference mask alone,
  which is also what finds distant people in the kiosk.
- **Your own video:** you can load a fixed-camera video; its empty scene is captured from the first
  frames.
- **Controls:** on-screen buttons and touch work too.

The page is `artifact/page.html`. Build and test it:

```bash
python scripts/build_portal_artifact.py OUT_DIR --harness
```
```bash
(cd OUT_DIR && python -m http.server 8770) &
```
```bash
node portal/artifact/test.cjs http://127.0.0.1:8770/harness.html fixed_camera_clip.mp4 TEST_OUT
```

- `harness.html` wraps the page with a similar content security policy.
- `publish.json` lists the files to publish (the harness and the `*_lacref.png` test references
  are left out).
- **The test checks:** no errors or CSP violations; colour parity (the page's person colour of the
  empty scene matches Python's `LocalAffineColor` within 3 levels for every generated world); the
  opening crossing; the real side against the world side, on a paused frame (with the clip playing,
  `compare()` can read a newer video frame than the one drawn, 2–6 levels in either seam, so that
  reading is only reported); that a burst changes only pixels inside its box; Layers; Depth; the
  world wave; all scenes; your own video; and a phone layout.
- **Grow checks** (video paused, Winter, line at 0.5, band 120 px):
  - the real side equals the camera exactly;
  - the step across the line is under 6 levels (Cut: 80–95, depending on the paused frame);
  - the world forms across the band: each column band's difference from the camera, divided by
    the full world's (Cut) over the same columns, rises from 0.52–0.56 to 0.60–0.66 to 0.75–0.98
    (≈ 1);
  - every plaza world's ladder has the rungs `scenes.json` lists and matches its JPEGs at every
    rung, within 1.5 levels, and at least one world has an SD middle rung;
  - depth at τ 0.45: rows nearer than 0.40 all along the row equal the camera exactly;
  - Cut still passes today's sides check;
  - the Morph chip, key `E` and the band wheel work.

  Test hooks: `__portal.setSeam`, `setBand`, `rungView(k, ref)`, `compareRows(y0, y1)` and
  `renderNow()`.
- **Flood checks** (Hold to flood):
  - held at phases (video paused, Winter, line at 0.5), in Grow and Cut: at u = 0.15 the ground
    near the press differs from the camera and the far corner equals it; at u = 1 the real side and
    both the top and bottom bands differ; after the drain the real side is the camera again (exactly,
    in Grow);
  - the mouse: held still for 700 ms it floods (here, where 3 frames can take longer, the test
    waits for the hold); on release it is gone within 900 ms (timed on the page's clock) and the
    line has not moved; a quick click still moves the line;
  - with the clip playing (a busy stretch, with the line at the right edge so the walkers start in
    the filmed scene), a held full flood: at least one crossing, bursts at least 900 ms apart, and it
    stays after the release until a tap lets it go;
  - its sound (sound on, clip paused): the rush rises while the flood grows, and once the flood is
    kept, and after it is let go, no rush plays (`floodGain()` is 0);
  - the phone: a 700-ms touch press floods and drains, a tap still moves the line, and nothing on
    the page is selected.

## Controls

| Key | Action |
|---|---|
| `1`–`9`, `N`, `Space` | choose a world (generated worlds first), next world, auto-cycle every 6 s |
| `M` | rule: line → portal ring → lens → depth → whole frame |
| drag / scroll | move the line or ring (the lens follows the pointer); in depth, the contour goes to the distance you point at; scroll resizes (on the line: the morph band) |
| press and hold, `O` | flood from where you press (on a walker: from their feet), or with `O` from the centre; move to steer; let go to drain; held full, it stays until the next tap or `O` |
| `L` | Layers: filmed + mask, empty scene, the world, people, the rule, the result; tap a tile for full size |
| `E` | Morph: Grow (the world grows through its ladder; scroll on the line for the band width) or Cut |
| `[` `]`, `←` `→` | tilt or move the line |
| `C` | recapture the empty scene |
| `G`, `X` | glitch the whole frame; the crossing burst on or off (on by default) |
| `B` | **fallback:** switch to the recorded clip through the same pipeline |
| `R` `F` `S` `D` `T` `H` | mirror, fullscreen, sound, debug, hole filling, help |

**Rules:**
- **Line:** pixels split at the line, so a person straddling it is half in each world. In Grow the
  world forms over a band past the line instead (see Grow above).
- **Portal:** each person changes as a whole, by where their feet are, so stepping into the ring
  changes you.
- **Depth:** everything farther than a chosen distance is the other world. People follow the depth
  at their feet, so walking away turns you into the world.
- **Flood** (press and hold, on any rule but the whole frame): a ring from your finger that grows
  over the whole scene, over the current rule. People change, and cross, as it reaches their feet.
- **Crossings** (a person going from real to the other world) trigger a whoosh. For an upright,
  person-sized track (not a car or a merged crowd), they also trigger a 0.9 s Spider-Verse burst on
  that person only: their style flashes faster and faster, with an ink outline and misregistered
  cyan/magenta edges, then lands in the world. Nothing else on screen changes. A figure covering
  more than 10% of the frame switches at most 3 times a second.
- **World change:** the new world rolls in from the horizon (the depth map; top-down without one).
  In Grow the old world unmakes back to the empty scene ahead of the new one growing.
- **Sound:** a pad chord for the world swells with the share of people across.

## On the day

- **Fallback ladder:** live camera → `B` (recorded clip, same code) → the trailer video.
  Rehearse switching.
- **Lighting:** fix the lights. After capture the page asks the camera to lock exposure and white
  balance (Chrome, driver-dependent) and compensates global brightness drift. Press `C` after any
  lighting change.
- **Floor line:** tape a line on the floor where the on-screen line is, and put the screen facing
  the aisle. Have a teammate cross every so often: people join in when someone is already playing.
- **Sign:** *"Live camera. Nothing is recorded or stored. Step across the line to enter another
  world."* Check filming rules with course staff.

## Files

- `index.html`, `app.js`: UI, the loop, rules, crossings, keys, server polling, recorded scenes.
- `artifact/page.html`: the hosted page (on-screen controls; config in `window.PORTAL_CONFIG`).
- `compositor.js`: the WebGL2 shader (worlds, colour fields, rules, depth, wave, burst, layers).
- `segment.js`: MediaPipe segmenter (GPU delegate, CPU fallback).
- `plate.js`: empty-scene capture; the robust global colour fit for worlds made on the spot.
- `audio.js`: Web Audio sound. It starts only after a user gesture.
- `smoke_test.cjs`: end-to-end test with a fake webcam. Run
  `node portal/smoke_test.cjs http://localhost:8765/ clip.y4m outdir [autostart]` against
  `python -m crossover.portal_server --no-generate --port 8765`. `autostart` checks that
  `?autostart=1` starts without a click and that sound waits for a gesture.
- `artifact/test.cjs`: the hosted page's test (above).
- Server: `crossover/portal_server.py`; generation: `crossover/generate.py:restyle_plate`.

**Measured here:** headless Chromium with CPU-only rendering (SwiftShader), 640×480 fake webcam.
- No console errors; GPU delegate active.
- The real side matches the camera (mean difference 6/255, from motion between reads); the world
  side differs (82/255).
- Line crossings were detected automatically.
- About 4 fps at 70 ms per mask on this CPU-only renderer. A laptop GPU is much faster; measure it
  with `?debug=1`.
