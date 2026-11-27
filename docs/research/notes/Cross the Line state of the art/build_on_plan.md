# What to build on: the planner's synthesis

> Research sweep of 27 November 2026. Evidence marks: **read** (the page was opened), **snippet** (search-result text only), **memory** (unverified). Social and product sites were blocked in the session, so product facts are mostly snippets.

## 1. State of the art in one page

As of 27 November 2026, every piece of our pitch exists somewhere. Keeping a real person while AI redraws the world is a taught creator skill (Higgsfield's Seedance course) and a one-click template (FXjutsu, ComfyUI). Painting regions with different styles exists for stills (MAST, Krita) and, since October, for video (LociArt). All of these redraw every frame with a video model on a GPU, on clips of 5–30 s. Offline models barely flicker by the usual metrics (0.97–0.98), and they beat us on fidelity, moving cameras, mattes and relighting.

We did not find the combination: a fixed camera, a world drawn once, the camera's own pixels for people, regions that people cross as a whole, and live compositing in a browser on a CPU. Most product and social sites were blocked, so this is "not found", not "first".

| Approach | Best examples | Better than us | Only ours |
|---|---|---|---|
| Whole-clip video-to-video | Runway Aleph 2.0 (2026), Luma Modify (2025), Meta Restyle (2025) | Fidelity, moving camera, moving worlds | Exact pixels for people, any length, CPU |
| Masked multi-region video editing | LociArt (2026), EditCtrl (2026), Wan VACE + SAM 3 (2025) | Click or text selection, motion inside regions | Regions that people cross as a whole |
| Layered editing that keeps the source | Vera (2026), PAI-Studio (2026), AnyPortal (2025), FXjutsu (2026) | Learned mattes, relit people | Median plate, one still per world, real time |
| Generate once, composite live | Teams Decorate (2024), Zoom, Meet | Polish, robust person masks | The room and its twin in one frame |
| Live per-frame restyle | Decart Mirage and Lucy (2025–26), StreamDiffusionV2 (2026) | Any motion, any prompt | No GPU per frame, stable world, untouched people |
| Painted styles in stills | MAST (2026), Krita AI Diffusion Regions | Seams drawn by the model | Video, people, switching at run time |
| Mattes and relighting | SAM 3.1, MatAnyone 2, HarmoVid, Beeble SwitchX (all 2026) | Hair-level alpha, true relighting | Shadows carried over, live on a CPU |
| Painted layers on tripod video, before AI | Cliplets (2012), Photomontage (2004) | Graph-cut and Laplacian seams | Generated worlds, people choosing by their feet |

Evidence: papers and repos were fetched; every product row rests on search snippets.

## 2. The ten closest things

1. **Teams "Decorate your background"**, 2024, [link](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705). Your own room generated once, you live in front (snippet; mechanism undocumented). Delta: one theme everywhere, nothing to cross.
2. **FXjutsu "Toon World"**, 2026, [link](https://github.com/audriu/fxjutsu). Same order: clean plate, restyle it, real people on top (fetched). Delta: needs LTX-2.5 on a 24 GB GPU, 5-s clips, no zones, not live.
3. **LociArt**, Oct 2026, [link](https://arxiv.org/abs/2610.36456). Closest to Paint: a different style per masked video region (fetched; multi-region shown only qualitatively). Delta: redraws every pixel; masks ignore people.
4. **EditCtrl**, Feb 2026, [link](https://arxiv.org/abs/2602.15031). Mask-local, multi-region, "real-time" video editing (abstract fetched; no latency given). Delta: generates each frame on a GPU.
5. **Vera**, Jun 2026, [link](https://arxiv.org/abs/2606.23610). A generated layer plus alpha over the source; 35.2 dB on kept pixels, 8.3 min per 49 frames (fetched). Delta: our kept pixels are exact, in real time.
6. **PAI-Studio**, May 2026, [link](https://arxiv.org/abs/2606.01399). Background replacement guided by clean plates and restyled backgrounds (abstract fetched; plate detail snippet). Delta: it regenerates and relights the people.
7. **AnyPortal**, ICCV 2025, [link](https://arxiv.org/abs/2509.07472). Zero-shot background replacement, foreground kept and relit (fetched). Delta: a new place, not the same room; no zones.
8. **Higgsfield "walking location swap"**, 2026, [link](https://higgsfield.ai/academy/courses/ai-vfx-real-footage/swap-the-world-the-walking-location-swap). Person kept, world swapped by Seedance (snippet; corrected: the swap fires at a finger snap, in time). Delta: ours fires in space, in one take.
9. **Runway "World jumping"**, 2023, [link](https://academy.runwayml.com/gen1/gen1-world-jumping). The format's origin, after Martin Haerlin (snippet). Delta: cuts in time, and the person is restyled.
10. **Xia et al.**, 2020, [link](https://arxiv.org/abs/2010.10056). Scribbled video regions, several styles, real time (fetched). Delta: stylises people too; no plate, no crossing.

Dropped as unconfirmed: Teams theme names, Tom's Guide's Meta Restyle details, Aleph's price, Higgsfield's "one drive, many worlds".

## 3. Adopt

Paths are relative to `/home/user/cs-180-final-project/`. Ordered by visible gain per day.

| # | Build on | Licence, hardware | In our code | Days | Risk | Gain on screen |
|---|---|---|---|---|---|---|
| 1 | **Sharper worlds.** First, 4 seeds per world on Colab, keep the best (no new code). Then SDXL + [ControlNet-Union](https://huggingface.co/xinsir/controlnet-union-sdxl-1.0), same depth and canny | Apache-2.0; SDXL OpenRAIL++ (fetched). T4, fp16 (untimed) | `crossover/generate.py`: SDXL branch in `load_pipeline`; `restyle`, `control_images` unchanged | 0.5 + 1 | Medium: re-check geometry with `score.py` (branch `archive/prototype-full`) | Every frame: the world is most of the picture |
| 2 | **Clean people.** [BackgroundMattingV2](https://github.com/PeterL1n/BackgroundMattingV2): frame + our plate gives alpha. Colab ceiling: SAM 3.1, then MatAnyone 2 | MIT, ONNX (fetched); CPU untimed. SAM 3.1 gated; MatAnyone 2 non-commercial (fetched) | New `crossover/matte.py`. `scripts/build_portal_artifact.py: encode_clip` packs alpha as a grey strip in the clip (frame-exact). `portal/app.js: combineMasks` reads it; the difference stays for cars and "Your video" | 1.5–2 | Medium: trained on people; shadows; exposure drift | No fringes or trails, in every shot |
| 3 | **Click to paint a region.** [SlimSAM](https://huggingface.co/Zigeng/SlimSAM-uniform-77) once per plate, offline; ship a label map | Apache-2.0, CPU (fetched). Not in the page: its CSP is `connect-src 'self'`, budget 12.5 MB | `build_portal_artifact.py: build` writes `{sid}_segments.png`. `portal/paint.js`: `Painting.fill()`, kept in `strokes` so `undo` replays it. `ruleWeight`, `drawPainted` unchanged | 1 | Low: segments too fine or coarse; the brush remains | Three clicks paint building, lawn and path, seams on real edges |
| 4 | **Proof.** Baselines: per-frame SD 1.5 and [Wan VACE-1.3B](https://huggingface.co/Wan-AI/Wan2.1-VACE-1.3B). Metrics: RAFT warp error, adjacent-frame CLIP (as LociArt), PSNR on people (as Vera) | Apache-2.0 (fetched), T4 (memory); RAFT BSD-3 (fetched) | New `scripts/flicker_eval.py`; baseline through `generate.restyle` | 1 | Low | A 5-s side-by-side and one number in the talk |
| 5 | **Plate repair.** Masked median, then [LaMa](https://github.com/advimman/lama) where nobody ever leaves | Apache-2.0 (fetched); CPU (memory) | `crossover/background.py: median_background(masks_dir=…)` exists: pass it the mattes from 2 | 0.5 | Low | No ghosts baked into every world |
| 6 | **Export.** [Mediabunny](https://www.npmjs.com/package/mediabunny) 1.66.5 | MPL-2.0, browser, WebCodecs (fetched) | Replaces roadmap Export v2: new `portal/export.js`; `render` and `onVideoFrame` take the frame as an argument | 1–1.5 | Medium: Firefox H.264; MediaRecorder v1 may be enough | The Export beat; exact frames for 4 |
| 7 | **Relit people.** [IC-Light](https://github.com/lllyasviel/IC-Light) on 3–5 keyframes; fit our colour grid to the result | Apache-2.0 (fetched); Colab GPU | `crossover/colormap.py: LocalAffineColor.fit`, via `build_portal_artifact.py: colour_field` | 1–2 | High: keyframes may change faces | People lit by night or neon, still no flicker |
| 8 | **Turning camera.** Panorama plate from course homographies ([OpenCV stitching](https://docs.opencv.org/4.x/d1/d46/group__stitching.html) as reference) | Apache-2.0, CPU (memory) | New `crossover/pano.py`: median per panorama pixel, `restyle_plate` once, warp back | 2–4 | High: parallax, 100° lens | A glasses shot beside Meta Restyle; after the demo video |

Order: 2 before 5, 6 before 4, 7–8 only if days remain. Needs your OK: a hosted editor for the worlds, about $1 for 14 images at aggregator prices (unverified); geometry may shift.

## 4. Borrowed ideas

1. Film one unbroken walk across a line, a ring and painted patches: "world jumping" in space. Source: Runway Academy, 2023 (snippet).
2. Open on a half-real, half-winter frame; someone crosses within two seconds. Source: CapCut "split reality" tutorial (snippet).
3. One-sentence explanation: "like the yellow first-down line, the world is painted under the players, never on them." Source: Sportvision 1st & Ten, 1998 (snippet).
4. One row per painted world: show, opacity, feather. Source: Cliplets, 2012 (snippet); Krita AI Diffusion Regions (fetched).
5. "Generate more": several candidates per world, pick one. Source: Teams Decorate (snippet).
6. A checkerboard preset, so a walker changes world tile by tile. Source: NYU ITP "Interactive Sound Walk", 2015 (snippet).
7. Toggle the shadow in Layers; creators single out the contact shadow. Source: Higgsfield course (snippet).
8. Tagline: "The world changes. You don't." Source: the inverse of the 2025 outfit-transition trend, Kapwing (snippet).

## 5. Positioning

Yes, slightly: lead with the crossing, because that is the part we did not find anywhere. "AI world, real people" and "paint where each style shows" are now established, so present them as what we build on. Say "flicker" only about live and per-frame tools.

> Film from a tripod, paint AI worlds onto the scene, and watch real people walk from one into the next. Each world is drawn once, so it cannot flicker.

- **Weaker:** an AI world behind real people (Teams, FXjutsu, Higgsfield, AnyPortal); painted regions with different styles (LociArt, EditCtrl, MAST, Xia 2020); "AI video flickers" and the README's "buildings shimmer" (offline models score 0.97–0.98).
- **Stronger:** people change world as a whole, by their feet (not found); people are the camera's exact pixels (Vera reaches 35 dB; Lucy Edit's card admits identity drift); no clip cap and no GPU (rivals: 5–30 s); Higgsfield calls locked-off shots the video model's weak case (snippet).

## 6. Cite

1. LociArt, 2026. https://arxiv.org/abs/2610.36456 (fetched)
2. Vera, 2026. https://arxiv.org/abs/2606.23610 (fetched)
3. EditCtrl, 2026. https://arxiv.org/abs/2602.15031 (fetched)
4. PAI-Studio, 2026. https://arxiv.org/abs/2606.01399 (fetched)
5. AnyPortal, ICCV 2025. https://arxiv.org/abs/2509.07472 (fetched)
6. HarmoVid, 2026. https://arxiv.org/abs/2605.28811 (fetched)
7. MAST, 2026. https://arxiv.org/abs/2604.12281 (fetched)
8. Xia et al., 2020. https://arxiv.org/abs/2010.10056 (fetched)
9. FXjutsu, 2026. https://github.com/audriu/fxjutsu (fetched)
10. BackgroundMattingV2, 2020. https://github.com/PeterL1n/BackgroundMattingV2 (fetched)
11. Agarwala et al., Interactive Digital Photomontage, 2004. https://grail.cs.washington.edu/projects/photomontage/ (memory)
12. Joshi et al., Cliplets, UIST 2012. https://hhoppe.com/proj/cliplets/ (snippet)
13. Bai et al., Selectively De-animating Video, 2012. https://research.adobe.com/publication/selectively-de-animating-video/ (snippet)
14. Wang and Adelson, Representing Moving Images with Layers, 1994. https://persci.mit.edu/pub_abstracts/wang_tr279_abs.html (snippet)
15. Runway Academy, "World jumping", 2023. https://academy.runwayml.com/gen1/gen1-world-jumping (snippet)

The proposal also omits two tools the pipeline uses: Depth Anything V2 and LCM-LoRA.

## 7. Gaps

- Every product fact is snippet-only (clip caps, prices, the Teams mechanism, Higgsfield quotes). Open the pages before quoting them in the talk.
- Not searched: effect galleries inside TikTok, CapCut and Instagram; Reddit; X, including Martin Haerlin's original post. Try "split reality", "real vs AI line", "clean plate restyle".
- Unchecked venues: SIGGRAPH 2026 Real-Time Live (a text-prompted live-background demo), Ars Electronica, past CS180 and CMU 16-726 project galleries.
- Nothing is timed on our hardware: BackgroundMattingV2 and SlimSAM on 4 cores, SDXL + ControlNet-Union on a T4. Time 30 frames and one image first.
- Licences: SAM 3.1 needs manual approval (request today); FLUX.3 Klein's terms are unread; hosted-API prices come from aggregators.
- Unknown: LociArt's code release and multi-region numbers; EditCtrl's latency; whether the hosted page's sandbox allows a file download for Export.

### Critical Files for Implementation
- /home/user/cs-180-final-project/crossover/generate.py
- /home/user/cs-180-final-project/portal/app.js
- /home/user/cs-180-final-project/portal/paint.js
- /home/user/cs-180-final-project/scripts/build_portal_artifact.py
- /home/user/cs-180-final-project/crossover/background.py
