# Roadmap: the rest of the product

The finished product is the interface plus a video of someone using it (see the README). Five pieces
make it up, listed in build order; each is small and lives mostly in `portal/`. The first two, Paint and
Export, are built.

## 1. Paint brush: any region, any world (the main selling point)

**What:** a **Paint** rule next to Line, Portal, Lens and Whole. Pick a world chip and paint where it
shows; the eraser paints reality back; **Clear** resets.

**How:**
- A mask canvas at the clip's resolution. Strokes are soft round dabs; the wheel sets the brush size.
- The mask is uploaded as a texture after each stroke, and the shader reads *w* from it. In
  `ruleWeight` (app.js) and the shader's rule switch (compositor.js), Paint is one new mode.
- Crossing works as for the other rules: someone whose feet enter a painted region crosses.
- **v1 (built, `portal/paint.js`):** one world, painted; people change by the paint under their feet; the
  brush's soft edge is the Morph band; a right-drag or the Eraser paints reality back; Delete clears.
- **v2 (built):** several worlds at once. There is one mask per world, and a stroke paints its world in
  while erasing the others under it, so the newest paint wins. Each painted world is drawn as one more
  full-frame pass, blended over the last by its mask, and people belong to the world under their feet.
  Undo (Ctrl+Z, or the Undo button) re-paints every stroke but the last.
- **Next:**
  - a softness setting, which would also set the width of the Morph band;
  - saving the painting with the scene, for the CLI.

**Test:**
- `test.cjs` paints a stroke and checks two things: outside the stroke the frame equals the camera
  exactly, and inside it differs.
- Erasing returns the frame to exact.
- Two worlds in two strokes each show where they were painted.

## 2. Export

**What:** an **Export** button (or V) that saves what you see as a video file: the whole clip, with the
current worlds, masks and paint.

**How (built, `portal/export.js`):**
- The clip is paused and stepped one frame at a time: seek to the frame, find the people, draw, and hand
  the canvas to the encoder. Nothing runs in real time, so no frame is dropped on a slow machine.
- Encoding is Mediabunny (MPL-2.0, vendored by `fetch_vendor.sh`, loaded on first use) on the browser's
  WebCodecs: H.264 in MP4, or VP9 in WebM where H.264 is missing.
- Effects that depend on time (the crossing burst, the pulse) follow the clip's clock while exporting,
  so they play at the same moments as in the file.
- The frame rate comes from the clip: written into `scenes.json` by the build, or read from the file's
  frame timestamps (your own video, the kiosk's recorded clip).
- The hosted page saves the file through the viewer's download prompt (the `downloads` capability);
  the kiosk uses a normal download link. A view that cannot save files shows no Export button.
- Pressing Export again stops it; playback resumes where it was. While it runs, the scene and your own
  video cannot be changed, and floods do not start.
- If the viewer turns the save down, the file is kept and the button reads **Save video**.

**Speed:** about 1 s per frame in the headless test browser (software WebGL); a laptop's GPU should be
several times faster (not yet measured). A 10 fps plaza clip of 3 min is 1,800 frames.

**Test:** `test.cjs` exports 2 s of the plaza and reads the file back: 20 frames at 10 fps, the canvas
size, 2 s long, playback resumed. A second export refuses a scene change and is stopped part-way. A save
turned down is offered again. Your own video exports at its file's frame rate. The kiosk smoke test
exports its recorded clip at the clip's 10 fps.

**Next:** an in/out range (today it is the whole clip), and a progress bar with time left.

## 3. AI worlds for your own video

**What:** after "Your video", the page asks for Stable Diffusion worlds of *your* empty scene, not
just colour filters.

**How:**
- The kiosk already does this. Its page posts the captured empty scene to `/api/plate` on
  `crossover.portal_server`, which generates worlds one by one (`generate.restyle_plate`).
- The hosted-page mode gets the same call when it is served by that server.
- On the static hosted demo, the button explains that generation needs the local server, which
  takes about 1–2 min per world on a CPU.

**Test:** the kiosk smoke test's fake-camera flow, run with an uploaded clip instead of the camera.

## 4. Our own footage and one command per scene

**Footage:** film Sather Gate and one more campus spot from a tripod, with exposure, focus and
white balance locked.

**One command per scene:** a single command that adds a clip:

```bash
python -m crossover.scene clip.mp4 --styles winter,night,vangogh
```

It does three things:
- runs `prepare` and `generate`;
- picks the first candidate per style;
- appends the clip to a `scenes.json` that `build_portal_artifact.py` reads, replacing today's
  hard-coded `SCENES`.

## 5. The demo video and the pitch

- **Recording:** screen-record the interface on a laptop with a GPU browser (smooth playback),
  following the README's shot list. Use 1080p, 60–90 s, with short captions.
- **Presentation:** the 2-minute talk is the README's pitch: the demo video plays during the "demo"
  beat.
- **Rehearsal:** time it twice.

## Later: depth and morph (early versions are already in the interface)

**Depth:** near stays real, far becomes the world.
- A depth-split slider, instead of tapping a point.
- Show the depth map in Layers.
- Check the rule on our own footage, where Depth Anything may struggle with arches and trees.

**Morph:** the world grows in through the model's own partial drawings.
- Generate a middle image for the Crowd and Street scenes (about 10 CPU-min each), so their worlds
  stop arriving in patches.
- Fix the night world's stray pool of light.
- Decide whether Morph or Cut is the default.

## Later: a moving camera (Meta Ray-Ban glasses)

The whole method assumes a tripod: one background shared by every frame. A head-worn camera breaks
that, so the first question is how far the idea stretches.

1. **Turning in place.** When the wearer mostly turns their head, frames are related by homographies.
   - Stitch them into one panorama (the course's mosaics project), with the median per panorama pixel.
   - Restyle the panorama once.
   - Warp it back into each frame with that frame's homography.
   - People still come from the difference to the warped empty scene.
2. **Walking.** Parallax breaks a single homography. Options, in order of effort:
   - local warps;
   - a layered video model (Neural Atlases, CoDeF) that learns the shared canvas;
   - falling back to a video model on short clips.
3. **First test:** 20 s from the glasses while turning slowly on the spot. Measure how far the stitched
   panorama drifts at the seams before adding anything else.

**What exists** (from the sweep; product facts are search snippets):
- Meta's Restyle already restyles glasses footage after capture, in clips of about 10 s, and it changes
  the people too.
- Decart XR restyles a Quest headset's camera view live, with about a second of lag.
- Neither keeps people as filmed or draws a stable world once, so that combination is still open.
- Record on the glasses and process afterwards: recorded clips are sharper than the developer
  toolkit's live stream.
- The Aria Everyday Activities dataset has head-worn clips to develop on before filming.

## Options from the state-of-the-art sweep (27 November)

Existing work we could build on, from [state of the art](state-of-the-art.md). Export is built; the rest
are not started. Each row says what it would add to the explanation of our method.

| Option | Built on | Adds to the explanation | Effort | Risk |
|---|---|---|---|---|
| **Export** as MP4, exact frames (built) | Mediabunny (MPL-2.0) on WebCodecs | Nothing: a product feature | 1–1.5 days | Medium: browser support; the hosted page may need a file-save permission |
| **Proof:** a per-frame Stable Diffusion baseline next to ours | The measures recent papers report: warp error (RAFT), frame-to-frame similarity (CLIP), PSNR on people | One number | 1 day | Low |
| **Click to paint** a whole region | SlimSAM (Apache-2.0), run once on the empty scene | One sentence: "Segment Anything, once, on the empty scene" | 1 day | Low |
| **Cleaner people** | BackgroundMattingV2 (MIT), which takes a frame plus a clean plate; or our archived edge-refined matte | One sentence: "a matting model that is given the empty scene" | 1.5–2 days | Medium: it was trained on people near the camera |
| **Sharper worlds** | SDXL + ControlNet-Union, or FLUX.2 Klein 4B, on a Colab GPU | Nothing: a better image model for the same step | 0.5–1.5 days | Medium: needs a GPU. Decided against for now |

Suggested order: Export (built) and Proof first, because neither adds anything to the method.

**Ideas for the demo video, borrowed from the sweep:**
- Open on a half-real, half-winter frame, with someone crossing within two seconds.
- Film one unbroken walk across a line, a ring and painted patches: "world jumping" in space instead
  of in time.
- Tagline: "The world changes. You don't."

## Timeline

| When | Done |
|---|---|
| Check-in 2 (11/30–12/4) | Paint with several worlds (done), the survey and the simple story (done), Export (done), a first cut of the demo video |
| By 12/6 | AI worlds for your own video, Sather Gate scene, final demo video |
| 12/8 or 12/10 | 2-minute presentation |
| 12/15 | Final report |
| After | Depth and Morph |
