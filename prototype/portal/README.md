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

Nothing leaves the laptop and nothing is recorded.

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
  opening crossing; that a burst changes only pixels inside its box; Layers; Depth; the world wave;
  all scenes; your own video; and a phone layout.

## Controls

| Key | Action |
|---|---|
| `1`–`9`, `N`, `Space` | choose a world (generated worlds first), next world, auto-cycle every 6 s |
| `M` | rule: line → portal ring → lens → depth → whole frame |
| drag / scroll | move the line or ring (the lens follows the pointer); in depth, the contour goes to the distance you point at; scroll resizes |
| `L` | Layers: filmed + mask, empty scene, the world, people, the rule, the result; tap a tile for full size |
| `[` `]`, `←` `→` | tilt or move the line |
| `C` | recapture the empty scene |
| `G`, `X` | glitch the whole frame; the crossing burst on or off (on by default) |
| `B` | **fallback:** switch to the recorded clip through the same pipeline |
| `R` `F` `S` `D` `T` `H` | mirror, fullscreen, sound, debug, hole filling, help |

**Rules:**
- **Line:** pixels split at the line, so a person straddling it is half in each world.
- **Portal:** each person changes as a whole, by where their feet are, so stepping into the ring
  changes you.
- **Depth:** everything farther than a chosen distance is the other world. People follow the depth
  at their feet, so walking away turns you into the world.
- **Crossings** (a person going from real to the other world) trigger a whoosh. For an upright,
  person-sized track (not a car or a merged crowd), they also trigger a 0.9 s Spider-Verse burst on
  that person only: their style flashes faster and faster, with an ink outline and misregistered
  cyan/magenta edges, then lands in the world. Nothing else on screen changes. A figure covering
  more than 10% of the frame switches at most 3 times a second.
- **World change:** the new world rolls in from the horizon (the depth map; top-down without one).
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
