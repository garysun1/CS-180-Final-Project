# Roadmap: the rest of the product

The finished product is the interface plus a video of someone using it (see the README). Five pieces
are missing. They are listed in build order; each is small and lives mostly in `portal/`.

## 1. Paint brush: any region, any world (the main selling point)

**What:** a **Paint** rule next to Line, Portal, Lens and Whole. Pick a world chip and paint where it
shows; the eraser paints reality back; **Clear** resets.

**How:**
- A mask canvas at the clip's resolution. Strokes are soft round dabs; the wheel sets the brush size.
- The mask is uploaded as a texture after each stroke, and the shader reads *w* from it. In
  `ruleWeight` (app.js) and the shader's rule switch (compositor.js), Paint is one new mode.
- Crossing works as for the other rules: someone whose feet enter a painted region crosses.
- **v1:** one world, painted.
- **v2:** up to four worlds at once. The mask becomes RGBA, one channel per world, and the worlds go
  in a texture array, so winter can sit on the lawn while night fills the sky.

**Test:**
- `test.cjs` paints a stroke and checks two things: outside the stroke the frame equals the camera
  exactly, and inside it differs.
- Erasing returns the frame to exact.
- Two worlds in two strokes each show where they were painted.

## 2. Export

**What:** an **Export** button that saves what you see as a video file.

**How:**
- **v1:** `canvas.captureStream()` with `MediaRecorder` records one pass of the clip, from the start
  with the current settings, as WebM, then offers it as a download. It records in real time, so it
  needs a machine that plays the page smoothly.
- **v2 (if v1 drops frames):** step the clip frame by frame, render each one, and encode with
  WebCodecs. This is slower than real time but never drops a frame.

**Test:** `test.cjs` exports 2 s and checks that the file is non-empty and decodes with the expected
size and duration.

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

## Timeline

| When | Done |
|---|---|
| Check-in 2 (11/30–12/4) | Paint v1, Export v1, a first cut of the demo video |
| By 12/6 | Paint v2 (several worlds), AI worlds for your own video, Sather Gate scene, final demo video |
| 12/8 or 12/10 | 2-minute presentation |
| 12/15 | Final report |
| After | Depth and Morph |
