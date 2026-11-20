# Cross the Line: live portal kiosk

A webcam points at the booth. Anyone who crosses the line (or steps into the ring, or walks under the
lens) appears in another world, live, at full resolution, without flicker.

**How it works:**
- **Empty scene:** captured once as a masked temporal median.
- **Worlds:** made from that one image, either instantly in a shader or by Stable Diffusion
  running on the laptop.
- **People:** found every frame by Google's MediaPipe selfie segmenter, combined with a
  background-difference mask.
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
- **Scenes:** the plaza, crowd and street clips, each with its clean plate and Stable Diffusion
  worlds made offline.
- **No camera, server or segmenter there:** people come from the background-difference mask alone,
  which is also what finds distant people in the kiosk.
- **Your own video:** you can load a fixed-camera video; its empty scene is captured from the first
  frames.
- **Controls:** on-screen buttons and touch work too.

The page is `artifact/page.html`. Build the folder with:

```bash
python scripts/build_portal_artifact.py OUT_DIR --harness
```

`harness.html` wraps the page with a similar content security policy for local testing.

## Controls

| Key | Action |
|---|---|
| `1`–`9`, `N`, `Space` | choose a world, next world, auto-cycle every 6 s |
| `M` | rule: line → portal ring → lens → whole frame |
| drag / scroll | move the line or ring (the lens follows the pointer); scroll resizes |
| `[` `]`, `←` `→` | tilt or move the line |
| `C` | recapture the empty scene |
| `G`, `X` | glitch burst; auto-glitch on every crossing (on by default) |
| `B` | **fallback:** switch to the recorded clip through the same pipeline |
| `R` `F` `S` `D` `T` `H` | mirror, fullscreen, sound, debug, hole filling, help |

**Rules:**
- **Line:** pixels split at the line, so a person straddling it is half in each world.
- **Portal:** each person changes as a whole, by where their feet are, so stepping into the ring
  changes you.
- **Crossings** (a person going from real to the other world) trigger a whoosh, a flash, and a
  short style glitch.
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
- `compositor.js`: the WebGL2 shader (worlds, rules, glitch).
- `segment.js`: MediaPipe segmenter (GPU delegate, CPU fallback).
- `plate.js`: empty-scene capture; colour matching for generated worlds (least-squares affine).
- `audio.js`: Web Audio sound.
- `smoke_test.cjs`: end-to-end test with a fake webcam. Run
  `node portal/smoke_test.cjs http://localhost:8765/ clip.y4m outdir` against
  `python -m crossover.portal_server --no-generate --port 8765`.
- Server: `crossover/portal_server.py`; generation: `crossover/generate.py:restyle_plate`.

**Measured here:** headless Chromium with CPU-only rendering (SwiftShader), 640×480 fake webcam.
- No console errors; GPU delegate active.
- The real side matches the camera (mean difference 6/255, from motion between reads); the world
  side differs (82/255).
- Line crossings were detected automatically.
- About 4 fps at 70 ms per mask on this CPU-only renderer. A laptop GPU is much faster; measure it
  with `?debug=1`.
