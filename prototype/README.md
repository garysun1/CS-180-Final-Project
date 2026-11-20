# Cross the line: prototype

A tripod video in which anyone who crosses a line in the frame steps into another version of the
same place (night, a century ago, a painting). Because the camera never moves, we restyle **one**
clean background image instead of every frame, so the new world cannot flicker. Then we put the
real people back.

This folder is a working proof of concept. It runs on a CPU with stand-in footage and stand-in
styles, and it produces the numbers and figures for the check-in.

```
real side (untouched)           |  restyled side
--------------------------------+---------------------------------------------
filmed frame F                  |  a·P + (1−a)·R·S
                                |  R = clean plate, restyled ONCE, re-aligned
                                |  a = person mask, P = person (as filmed or style-matched)
                                |  S = shadow ratio (people's shadows carried into the new world)
```

## Quick start

```bash
pip install -r requirements.txt
bash scripts/fetch_sample.sh             # stand-in tripod clip: OpenCV's vtest.avi (768x576, 795 frames)
python -m pytest -q tests                # 25 synthetic tests with exact known answers
python -m crossover.run --video data/sample/vtest.avi --style century --perturb --local-warp --out out/vtest_century
bash scripts/run_all_sample.sh           # century / night / painting / ink + a moving line (~6 min)
bash scripts/fetch_depth_model.sh        # Depth Anything V2 Small, ONNX, 99 MB (for --split depth)
bash scripts/run_style_demos.sh          # winter / underwater / thermal / neon / sketch + 3 depth demos + reel (~10 min)
pip install -r requirements-gen.txt      # optional: torch + diffusers, for real generative restyles on CPU
bash scripts/run_generative_demos.sh     # SD 1.5 + ControlNet restyles (~85 s each) + pipeline runs
```

On your own clip, with restyles and masks from the GPU notebook:

```bash
python -m crossover.run --video sather_gate.mp4 --scale 0.5 \
    --restyled restyled/night_sdxlcanny_s0.png --masks masks/ --local-warp --out out/sather_night
python -m crossover.score --clean out/sather_night/clean_bg.png --restyled restyled/*.png   # pick the best editor
```

Useful flags:
- `--style` picks a CPU stand-in: `night century painting ink winter underwater thermal neon sketch`.
  Winter gets falling snow and underwater gets moving caustics; `--no-anim` turns these off.
- `--line x0,y0,x1,y1` places the line, in fractions of width and height. It can be tilted, for
  example to follow a pillar of Sather Gate.
- `--split depth` replaces the line with depth: far is restyled and near stays real.
  - `--depth-near` reverses that.
  - `--depth-split 0.5` sets the fraction of the scene that is restyled.
  - `--depth-band 0.08` sets how soft the transition is.
  - `--depth PATH` loads your own depth map instead of running the model.
- `--seam hard|feather|glow` sets how the seam looks.
- `--sweep 0.3` makes the seam move back and forth: the line sways, or the depth threshold rolls
  toward and away from the camera.
- `--person-style filmed|matched|both` controls how people look on the restyled side.
- `--no-shadow` turns off the shadow ratio.
- `--align auto|sift|ecc|sift+ecc|none` picks the alignment method.
- `--max-frames N` limits how much of the clip is processed.

## The pipeline (one paragraph per step, for presenting it)

1. **Clean plate** (`background.py`). Each pixel shows the empty scene most of the time, and
   people only pass through. So the **per-pixel median** over ~150 evenly spaced frames is the
   empty scene. Frames are stored on disk (memmap) and processed in strips, so 4K fits in RAM. We
   also save a **motion heatmap**: the fraction of frames in which each pixel was covered. It
   shows where the median can fail: people who linger, flags, trees. With SAM 3 masks
   (`--masks`), person pixels are excluded from the median.

2. **Restyle once** (`styles.py`, or `--restyled` with any PNG). The real project uses FLUX.2
   Klein, Qwen-Image-Edit, or SDXL + ControlNet (see `notebooks/`). The CPU stand-ins are:
   - `night` and `century`: pixelwise colour transforms.
   - `painting`: edge-preserving smoothing, a posterised palette, and canvas texture.
   - `ink`: a cartoon outline look, used as a stress test.
   - `winter`: grass and ground turn to snow, roads become wet slush, plus falling snow.
   - `underwater`: water absorbs red, haze grows with distance, plus moving caustics on the
     ground. This echoes the proposal mock-up.
   - `thermal`: the world is cold (dark end of the inferno colormap) and people are hot.
   - `neon`: a dark synthwave grade with glowing outlines traced from the clean plate's edges.
   - `sketch`: a pencil drawing on paper.

   Each style is a *plate* function (run once, may use neighbourhoods) plus an optional *person*
   function, which runs every frame and therefore must be pixelwise so people don't flicker.
   Animation (`animate.py`) is procedural and seeded by frame time. The plate is still one image.

   The stand-ins keep geometry perfectly still, but real editors nudge it. So `--perturb` warps the
   restyle with a random homography plus a smooth random displacement field (`perturb.py`). That
   gives an exact ground truth for checking the alignment.

3. **Re-align** (`align.py`).
   - **Global homography:** SIFT matches on contrast-normalised grey (CLAHE), fitted robustly
     with MAGSAC.
   - **ECC fallback:** if SIFT finds too few inliers (the style changed the image too much), we
     run coarse-to-fine **ECC** on *gradient-magnitude* images, because edges survive restyling
     better than colours. ECC starts from the identity, since editors only drift a few pixels.
   - **Plausibility check:** any estimate that moves a corner more than 8% of the width is
     rejected.
   - **Optional local warp (`--local-warp`):** dense DIS optical flow, heavily smoothed, applied
     only in a band around the line. It is kept only if the restyle still resembles the original
     (band edge correlation ≥ 0.6) *and* it improves that correlation.
   - Everything folds into one backward map, so the image is resampled once.

4. **Cut out people** (`masks.py`).
   - **CPU stand-in:** the colour difference from the clean plate in LAB, with brightness
     down-weighted so shadows stay *out* of the mask. Then morphology, removal of small blobs,
     hole filling, and a temporal check (a pixel must have support in a neighbouring frame).
   - **Real version:** SAM 3 with the text prompt "person" (notebook), saved as PNGs.
   - **Edge refinement (both sources):** the eroded mask counts as certain person. In a thin band
     around its edge, alpha comes from how different each pixel is from the clean plate. This is
     difference matting, possible only because we know the exact background.

5. **Depth split (optional, `depth.py`).** Instead of a line, *distance* decides what is restyled.
   - **Depth is estimated once on the clean plate**, using Depth Anything V2 Small (ONNX, about
     2 s on CPU). Like the restyle, it cannot flicker.
   - **Background:** w = smoothstep((f − τ)/band + ½), where f is "farness" (percentile-normalised
     disparity) and τ is chosen so that `--depth-split` of the scene is restyled. On flat ground the
     contour is a near-horizontal line, as ground-plane geometry predicts. Objects close to the
     camera (the lamp post, the tripod) keep their own depth, so they stay real even inside the
     restyled region.
   - **People get one weight each, from where they stand.** We read the plate's depth just below
     their feet (the bottom of their mask): a person is as far away as the ground under them. As
     they walk away they gradually take on the style.
   - **No flicker:** a tiny centroid tracker smooths each person's weight over time (an EMA).
   - **Sanity check (single-view metrology):** on a ground plane, image height ∝ 1/Z ∝ disparity.
     The run reports the correlation between person height and disparity at the feet.

6. **Composite** (`composite.py`). The equation is in the box above. In depth mode, w is per pixel:
   w = a·w_person + (1−a)·w_background.
   - **Real side:** literally the input frame.
   - **Shadows:** the mask leaves them out, but they still darken the ground. The ratio
     S = luma(frame) / luma(clean plate), clipped to ≤ 1 and only near people, multiplies the
     restyled plate. A shadow therefore appears on the painted ground in the painting's colours.
   - **Edge decontamination:** a soft edge still contains some *old* background, which shows as a
     daylight halo on a night side. Under the matting model F = a·FG + (1−a)·B we swap it for the
     new one: restyled side = P + (1−a)(R − Q)·S, where Q is the clean plate as it appears in P.
     This is clean-plate keying, like a green screen whose background we know.
   - **Matched person style:** for pixelwise styles, people get exactly the same colour
     transform. For other styles they get a Reinhard colour transfer whose statistics come from the
     two *still* plates. Statistics from stills are constant over time, so people do not flicker.

## Evaluation (`metrics.py`)

- **Seam edge jump** (main metric). In patches centred on the line we phase-correlate the
  gradient magnitude of the clean plate against the restyled plate, and report |shift| in px
  (median and p90).
  - Patches whose correlation peak is weak (< 0.15) are dropped. At zero true drift, those are
    exactly the patches that report garbage.
  - If fewer than 60% of textured patches survive, the number is flagged *unreliable*.
- **True residual**: with `--perturb` we know the exact warp, so we also report the exact
  remaining error at the same seam points. This validates the metric itself.
- **People round trip**: we composite people back onto the *unedited* clean plate (plain alpha
  blend) and compare with the original footage (PSNR, plus mean absolute error near people with
  and without the shadow ratio).
  - It catches missed person pixels and shadow errors.
  - It cannot catch masks that are too *fat*: on the unedited plate, extra background looks
    correct. Fat masks only show as a rim on the restyled side, so judge them in the videos.

Each run writes `report.json`, `report.md` and `checkin_figure.png`, plus these files:
- images: `clean_bg.png`, `motion_heatmap.png`, `restyled_{raw,perturbed,aligned}.png`,
  `seam_crops_before_after.png`
- videos: `final.mp4` (people as filmed), `final_matched.mp4` (people restyled), and
  `breakdown.mp4` (a 2×2 "how it was made" view)

## Results on the stand-in clip (`bash scripts/run_all_sample.sh`)

Stand-in footage: OpenCV's `vtest.avi` (768×576, 795 frames). Every run injects the same known
synthetic drift (`--perturb`) and uses `--local-warp`. All values are in px at 768 px width; the
target is < 2 px.

| style | alignment | SIFT inliers | seam jump before (med / p90) | after global | after local | true residual after (med / p90) | metric reliable |
|---|---|---|---|---|---|---|---|
| century | sift+local | 1281 | 3.73 / 6.33 | 0.90 | 0.13 | 0.17 / 0.23 | True |
| night | sift+local | 1053 | 3.63 / 6.24 | 0.73 | 0.16 | 0.13 / 0.21 | True |
| painting | sift+local | 339 | 3.18 / 5.98 | 0.85 | 0.47 | 0.51 / 1.09 | True |
| ink | ecc(init=identity) | 8 | 3.73 / 9.04 | 2.33 | (rejected) | 1.26 / 1.57 | True |

| people round trip (same for every style) | with shadow ratio | without |
|---|---|---|
| PSNR vs original footage, dB | 35.09 | 34.88 |
| mean abs error near people (0-255) | 4.38 | 4.76 |
| frames evaluated | 159 | |

![contact sheet](out/contact_sheet.png)

### What we learned (check-in material)

1. **One homography is not quite enough; homography + local warp is.** With realistic drift
   (3.9 px median, 6 px p90 at the line), a global homography leaves 0.7–0.9 px, because the
   editor's drift is not purely projective. Adding a smoothed flow field near the line brings it to
   0.13–0.5 px, comfortably under the 2 px target.
2. **The seam metric agrees with ground truth when styles stay close.** For century, night and
   painting, the measured edge jump is within 0.12 px of the true residual, at every stage. With
   zero drift it reads 0.04 px (night), 0.13 px (century) and 0.30 px (painting): that is the
   metric's floor.
3. **...but it over-reports across a big style gap.** On `ink`, which redraws every edge, it reads
   2.3 px while the true error is 1.3 px. Its floor at zero drift is already 2.2 px, as large as the
   error it is trying to measure. Two fixes were needed to get the metric that far:
   - Dropping weak phase-correlation peaks (< 0.15). At zero drift, those were exactly the
     patches reporting 7–30 px of garbage.
   - Using larger, smoother patches.

   Takeaway: for very different looks, judge the seam crops by eye too.
4. **Structure-destroying edits break feature matching, and ECC rescues them.** SIFT gets only 8
   inliers on `ink`. Starting ECC from SIFT's (wrong) guess converged to a **130 px** error;
   starting from the identity (editors only drift a few px) gives 1.3 px. A sanity check now rejects
   any estimate that moves a corner more than 8% of the width.
5. **Local flow can make things worse.** On `ink` it raised edge correlation (0.42 → 0.47) but
   *increased* the true error (p90 1.6 → 2.9 px). It now runs only when the restyle still resembles
   the original (band correlation ≥ 0.6). This threshold is a heuristic from 5 synthetic cases.
6. **Our first "painting" was a bad stand-in.** Oil filter + stylisation erased the lamp post, so
   nothing could be aligned or measured. The editor must preserve structure, which is an argument
   for SDXL + ControlNet edges, or for prompting the editors to keep geometry.
7. **People need clean-plate keying.** Pasting filmed people onto a night plate left a bright halo
   of daylight ground. Swapping the old background for the new one inside the soft edge
   (P + (1−a)(R−Q)S), plus refining mask edges against the clean plate, removes most of it.
   A darker silhouette around the feet remains with CPU masks; SAM 3 should fix most of it.
8. **The shadow ratio helps a little.** Error near people drops about 8% (4.76 → 4.38 grey
   levels), and PSNR rises 34.9 → 35.1 dB on the round trip.
9. **The median needs the whole clip.** With 12 s of footage a lingering person was baked into the
   clean plate; with 80 s they were gone. The barrier tape that flaps in the wind is never fully
   clean (see `motion_heatmap.png`). Sather Gate's flags and trees will behave the same way.

### Next experiments
- Shoot Sather Gate. Run the notebook's three editors × 2 seeds per style, rank them with
  `crossover.score`, and see whether real editor drift looks like our synthetic drift.
- Replace CPU masks with SAM 3 and check the feet/shadow region and the masked median.
- Depth split on the real clip (now implemented, see below): does Depth Anything hold up at Sather
  Gate (steps, the arch, trees)? If not, compute a bigger model's depth on Colab and pass `--depth`.

## More styles and the depth split (`bash scripts/run_style_demos.sh`)

The same stand-in clip, the same injected drift, and `--local-warp` (px at 768 px width):

| style | split | alignment | SIFT inliers | seam jump before (med / p90) | after global | after local | true residual after (med / p90) | metric reliable |
|---|---|---|---|---|---|---|---|---|
| winter | line | sift+local | 1293 | 3.97 / 6.25 | 1.02 | 0.53 | 0.25 / 0.84 | True |
| underwater | line | sift+local | 1073 | 3.64 / 6.19 | 0.76 | 0.14 | 0.14 / 0.19 | True |
| thermal | line | sift+local | 738 | 3.79 / 6.19 | 0.84 | 0.15 | 0.13 / 0.23 | True |
| neon | line | sift | 173 | 2.69 / 10.45 | 1.24 | (rejected) | 1.10 / 2.01 | True |
| sketch | line | sift+local | 775 | 3.47 / 6.14 | 0.65 | 0.26 | 0.12 / 0.42 | True |
| century | depth (far) | sift+local | 1281 | 5.28 / 6.79 | 0.86 | 0.15 | 0.17 / 0.29 | True |

![styles](out/contact_sheet_styles.png)
![depth](out/contact_sheet_depth.png)

The 45 s reel `out/demo_reel.mp4` plays the same 5 s from every style and depth demo. The other
depth demos:
- `out/vtest_depth_night_sweep/`: the depth threshold rolls toward and away from the camera.
- `out/vtest_depth_thermal_near/`: people close to the camera turn into heat signatures.

### What we learned (round 2)

1. **All five new styles meet the 2 px target on the median**, and four of them land at
   0.12–0.25 px true error.
   - **Neon is the weak one: 1.1 px median, and its p90 (2.01 px) just misses.** Its glowing outlines replace the
     original edges, so band edge correlation drops to 0.37 and the local warp is (correctly)
     refused, leaving only the global homography.
   - **On winter the seam metric over-reports** (0.53 px vs 0.25 px true): the snow changes
     ground texture, the same failure mode as ink.
2. **Monocular depth is good enough on this clip.** Depth Anything V2 Small runs once on the clean
   plate in about 2 s on CPU and gets the ground plane, the buildings and thin near objects right.
   **Our "edge-aware" guided-filter refinement made it worse**: it smeared the lamp post into a
   blob. It is off by default (`--depth-refine` turns it on).
3. **"Read depth at the feet" is validated by single-view metrology.** On a ground plane, a
   person's image height ∝ 1/Z ∝ disparity. Across 4,154 person detections, bounding-box height
   vs disparity at the feet gives **r = 0.80**. The depth under someone's feet agrees with how big
   they look.
4. **On flat ground the depth seam is just a near-horizontal line**, as the geometry predicts. The
   interesting part is anything that sticks up: the lamp post, sign and tripod are near, so they
   **stay real inside the restyled region**.
5. **People morph gradually.** Each person gets one weight from their feet, smoothed by a tiny
   tracker. The weight changes 0.016 per frame raw and 0.014 with the EMA on the full clip, and
   0.037 → 0.025 on a short noisy test. Ground depth is smooth, so raw flicker was already low.
6. **The seam metric works on a curved seam too.** Along the depth contour it drops from 5.3 px
   to 0.15 px after alignment (true residual 0.17 px).
7. **Bug found and fixed:** `--depth-near` used the far-side quantile, so it restyled 55% of the
   scene instead of the requested 45%. A test now checks both directions.

Known limits of the depth split:
- A person whose feet are hidden or cut off by the frame gets the depth of the lowest visible row.
- A person on stairs or a ledge gets the ground depth below them.
- With CPU masks, two people who touch merge into one blob and share a weight.

## Generative restyles (round 3: `bash scripts/run_generative_demos.sh`)

The colour filters above only regrade the same pixels, so they look like an overlay. This round
replaces them with an image model that changes the scene's *content*, run on CPU.

- **Model:** Stable Diffusion 1.5 img2img with two ControlNets that hold the geometry:
  - **depth:** our own Depth Anything map of the clean plate;
  - **canny:** structural edges only (thresholds 100/200).
- **Speed:** LCM-LoRA, 8 steps, guidance 1.5, at 768×576. About 85 s per image on 4 CPU cores,
  9.8 GB peak RAM. Our design needs **one** image per style, so this is affordable without a GPU.
- **Setup:**
  - `pip install -r requirements-gen.txt`, with Hugging Face reachable.
  - Generate with `python -m crossover.generate ... --init filter`.
  - Then run `crossover.run --restyled out/gen/<pick>.png`.

| style | picked candidate | img2img start | strength | s / image | alignment decision | measured seam jump (unreliable) | edit explained by colour |
|---|---|---|---|---|---|---|---|
| winter | `winterf_s0_k75` | our filter | 0.75 | 80 | kept unwarped | 1.13 px | 19% |
| night | `nightf_s0_k80` | our filter | 0.8 | 90 | kept unwarped | 0.64 px | 69% |
| 1920s | `1920sf_s0_k80` | our filter | 0.8 | 92 | kept unwarped | 0.33 px | 53% |
| underwater | `underwaterf_s0_k80` | our filter | 0.8 | 93 | kept unwarped | 0.93 px | 57% |
| autumn | `autumnf_s0_k80` | our filter | 0.8 | 97 | kept unwarped | 1.35 px | 48% |

All five runs: people round trip 35.1 dB; people matched with the learned colour mapping; winter
gets falling snow and underwater gets caustics.

### What we learned (round 3)

1. **Start from the filter, not the photo.**
   - Img2img from the raw plate kept the lawns green: SD 1.5 at LCM's low guidance does not
     overrule a strong colour.
   - Starting from our colour-filter version fixed it: the filter supplies the colour layout and
     diffusion supplies the content. Winter lawns became textured snow, autumn lawns filled with
     fallen leaves, 1920s lawns became cobblestones, and night got lit windows and lamp pools.
   - This is the `--init filter` option.
2. **ControlNet holds the geometry; our aligner nearly made it worse.** With so much new content,
   SIFT keeps only 8–18 inlier matches. ECC then fitted noise: a 3.6 px corner shift for an edge
   correlation gain of 0.003, and the measured seam got worse.
   - New rule: keep a global warp only if it raises edge correlation by at least 0.02. Correcting
     real ~4 px drift gains 0.05 (neon) to 0.49 (century), so the filter styles are unaffected.
   - Every generated plate is now **kept unwarped**. Seam crops before and after alignment look
     the same.
3. **The seam metric cannot judge content-changing edits.** Every generated plate is flagged
   unreliable, so the seam crops are the evidence.
4. **People matching is learned from the plate pair.** `colormap.py` fits a smooth field of local
   3×4 affine colour transforms from the clean plate to the restyle, with robust weights so
   content swaps (snow replacing grass) don't teach "green → white". It is applied to people per
   pixel position, so it cannot flicker.
   - It explains 98% of the night *filter* but only 19–69% of the generated edits.
   - That number is a nice measure of how much new content an editor added.
5. **What failed or is partial:**
   - **Painting:** SD 1.5 at guidance 1.5 barely paints; it only smooths.
   - **Underwater:** mostly colour plus some sandy texture, no coral.
   - **Hallucinations:** the generator repaves part of the night lawn, removes the traffic cones,
     and redraws the buildings slightly more generically.

   FLUX.2 Klein or Qwen-Image-Edit on a GPU should do better. The same `--restyled` path takes
   their output unchanged.

## Seam-free effects and the showcase cut

The same compositing with a different per-pixel weight w, using the generated worlds above (no new
image generation):

- **Seasons roll in** (`python -m crossover.effects seasons --out out/fx_seasons`):
  - The plaza morphs Today → Autumn → Winter → Night → 1920.
  - Each new world arrives as a depth wave from the horizon toward the camera, with a glowing
    wavefront.
  - People switch when the wave reaches the ground under their feet.
- **Footsteps paint the world** (`python -m crossover.effects trails --world winter --out out/fx_trails`):
  - Every walker carries winter with them and stamps it on the ground at their feet (sized by their
    height).
  - Trails are bright when fresh and thaw back to today with a 6 s half-life.
- **Showcase** (`python scripts/showcase.py -o out/showcase.mp4`): a 50 s cut with title card, seam,
  seasons, trails, depth split and end card.

## More clips, styles and effects

- **New clips** (`bash scripts/fetch_clips.sh`, MIT-licensed public footage):
  - `python -m crossover.prepare <video> --name <n>` normalises a clip and builds its clean plate and
    depth.
  - It also checks that the camera is really fixed (`static.json`). Of 10 clips only 2 passed: a
    London night street (`crowd04`) and a highway (`cartraffic01`). The others are handheld or
    panning, which this method cannot handle.
- **New styles:** `cyberpunk`, `vangogh`, `overgrown` and `anime` in `crossover/generate.py`.
  - Cyberpunk and Van Gogh work well. Van Gogh needs strength 0.95 and guidance 2.0.
  - Anime and overgrown barely change the scene.
- **New effects** (`python -m crossover.effects shards|windows|portal ...`):
  - **shards:** glass shards that each show a world and flip one by one.
  - **windows:** people are cut-out windows into another world.
  - **portal:** a ring on the ground; whoever's feet are inside changes.
  - Windows needs clean masks: on the busy night street the CPU masks catch shop-front clutter.
- **Showcase:** `python scripts/showcase.py -o out/showcase2.mp4 --segments segments.json` builds a
  cut from any list of clips.

## Trailer and the 15-second loop

`python -m crossover.trailer --out out/trailer.mp4` builds a 54.5 s trailer: 960×540 at 30 fps, with a
soundtrack synthesized in code. Every shot is a whole number of beats at 120 BPM (15 frames), so cuts,
flashes and hits line up.

- **Story (v2):**
  - The real plaza, then "the camera never moves": the walkers vanish into the empty scene, and
    winter sweeps in from the horizon.
  - **The signature crossing: freeze, scan, flood.**
    - *Freeze:* a woman walks to the glowing line while everyone else freezes mid-stride, and the
      music tape-stops.
    - *Scan:* the line slides back across her body, turning each part of her to winter, under a
      cold scan light and a single ring.
    - *Flood:* on the downbeat she steps through, and winter floods outward from her feet as a
      ring until the whole plaza has crossed.
    - Timings come from `scripts/find_moments.py`. Her centroid crosses x = 384 at 61.3 s, and the
      frozen walkers keep their 59.7 s poses through the scan.
  - A montage ("any city / any era / any world") of the effects on three clips.
  - A 6-second **style-glitch climax** on one walker: their figure flashes through comic, thermal,
    ink, Van Gogh, cyberpunk and more, every 4 → 2 → 1 frames. The world tears only in the last
    two beats.
  - A slow-motion London crossing, the title, and an **end card**: course, team names, the
    project page's link and a QR code.
- **The loop:** `python -m crossover.trailer --edit teaser --size 960x540 --crf 23 --out out/teaser_wide.mp4`
  (also `--size 720x720`). It is 15 s and seamless: she walks to the line, is scanned, and winter
  floods out; the plaza flips through eight worlds on the beat; a line uncovers Van Gogh over
  Leicester Square; "ONE IMAGE. EVERY FRAME." appears in letters cut out of the painted world; then
  the title. Its last frame is exactly its first. The project page uses it as its muted hero.
- **Options:**
  - `--names "A · B · C · D"` fills the end card. The default is a marked placeholder.
  - `--music track.mp3 --bpm N` swaps in a real track; cuts snap to its beat.
  - `--sections cold,drop,glitch` renders a quick draft of some sections.
  - `--crf` sets the encode quality; `--size WxH` sets the frame size.
- **Outputs:**
  - `*_frames.jpg`: one frame per shot, for review;
  - `*_edl.json`: shot timings and source times;
  - `*.wav`: the soundtrack.
  - v1 is kept as `out/trailer_v1.mp4`.
- **Helpers:**
  - `scripts/find_moments.py`: crossings of a line, with time, direction, track and size;
  - `scripts/make_qr.py`: a printable QR code of the page.
  - Fonts: Inter and JetBrains Mono, OFL, in `crossover/assets/fonts`.
- **`comic` style:** a posterised print with a screen-fixed halftone and ink lines. It works pixel
  by pixel on people too, so it doesn't flicker.

## Live portal kiosk (`portal/`)

The research report's top idea, built. A webcam watches the booth, and anyone who crosses the line,
steps into the ring or walks under the lens appears in another world, live.
- **Empty scene:** a masked temporal median.
- **People:** MediaPipe's selfie segmenter plus a background-difference mask, in the browser.
- **Composite:** a WebGL2 shader using the same equation as `composite.py`.
- **Worlds:** six instant shader worlds. `python -m crossover.portal_server` also generates Stable
  Diffusion worlds from the captured scene, and they appear as they finish.
- **Setup:** `bash portal/fetch_vendor.sh`, then `python -m crossover.portal_server`, then open
  http://localhost:8000. Keys, the fallback ladder and setup tips are in `portal/README.md`.
- **Hosted demo:** the same code runs in the browser on three recorded scenes with their generated
  worlds (no camera, no server). Build it with `python scripts/build_portal_artifact.py OUT_DIR`.
- **On both:**
  - people take the paper's local colour field;
  - only the person who crosses glitches;
  - **Layers** takes the picture apart into the filmed frame and mask, the empty scene, the one
    generated image, the people, the rule and the result;
  - **Depth** turns everything farther than a tapped distance into the other world, and new worlds
    roll in from the horizon.
- **Project page:** the source is in `site/`. `python site/build_media.py && python site/make_page.py`
  rebuilds it and checks the 16 MB page budget.

## Shooting checklist for the real clips

- Tripod. Lock **exposure, focus and white balance** (on iPhone, long-press for AE/AF lock; set
  white balance manually in a pro camera app). Turn off stabilisation if it crops or drifts.
- Shoot 1–3 min. More passers-by is fine, but nobody should stand still in one spot for more than
  about a third of the clip. Check `motion_heatmap.png`.
- Avoid moving background (flags, tree branches, the barrier tape in the sample clip). The median
  only partly removes it.
- Put the line where people actually cross, and where edges cross it (cornices, steps, paving
  joints). Those edges are what make misalignment visible, and what the metric measures.

## Layout

```
crossover/  video_io  background  styles  animate  perturb  align  masks  depth  composite  line  metrics  figures  run  score  generate  colormap  effects  prepare  trailer  portal_server
crossover/assets/fonts/   Inter, JetBrains Mono (OFL) for the trailer's type
portal/     the live kiosk (index.html) and the hosted demo (artifact/page.html): one WebGL2 app, with browser tests
site/       the project page: build_media.py, make_page.py, template.html, inputs/
notebooks/gpu_restyle_and_sam3.ipynb   Colab: FLUX.2 Klein / Qwen-Image-Edit / SDXL+ControlNet restyles, SAM 3 masks (UNTESTED)
scripts/    fetch_sample.sh  fetch_depth_model.sh  fetch_clips.sh  run_all_sample.sh  run_style_demos.sh  run_generative_demos.sh
            contact_sheet.py  demo_reel.py  summarize.py  showcase.py  build_portal_artifact.py  find_moments.py  make_qr.py
tests/      test_pipeline.py  test_trailer.py
```

## Known limitations

- **Speed.** Compositing is about 0.15 s/frame at 768×576 on one CPU core. That scales to roughly
  0.7 s/frame at 1080p and 3 s/frame at 4K, so iterate with `--scale 0.5`.
- **Untested notebook.** It was written without GPU or Hugging Face access. Pipeline and argument
  names follow the model cards and may need small fixes.
- **Mask quality.** Background-difference masks miss people whose clothes match the background and
  include anything else that moves. SAM 3 is the real answer.
- **Global lighting.** The shadow ratio is only applied near people. Lighting changes over the
  whole frame (clouds) are not carried into the restyled world.
