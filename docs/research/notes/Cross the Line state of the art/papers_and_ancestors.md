# Papers 2024-26 and classic ancestors

> Research sweep of 27 November 2026. Evidence marks: **read** (the page was opened), **snippet** (search-result text only), **memory** (unverified). Social and product sites were blocked in the session, so product facts are mostly snippets.

## Summary

This pass looked for the closest papers to what Cross the Line does today. That means painted regions of a fixed-camera video, a different generated world in each region, each world drawn once on the clean plate, and real people composited on top. Since July, the closest new paper is LociArt (arXiv 2610.36456, 27 Oct 2026). It does mask-specified local video stylization with several regions and several styles, using a 2B GRN model at 81 frames and 720p. It regenerates the whole video and does not paste non-target pixels back. Its benchmark sets the current state of the art and the baselines a reviewer will expect: LEAST, VACE-1.3B, UniVST, RegionRoute, StyleGallery, CoinVE-Edit and Seedance 2.5. Vera (arXiv 2606.23610, Jun 2026, Caltech/Netflix) is the closest layered editor. It generates an edit layer plus an alpha matte over the source video, so it keeps unedited pixels nearly exact (35.2 dB PSNR on background change). It costs about 8.3 min per clip on an A100. PAI-Studio (arXiv 2606.01399, May 2026) does cinematic background replacement on Wan 2.2-5B, using clean plates and Gemini-restyled backgrounds as references. It regenerates all 97 frames rather than compositing. HarmoVid (arXiv 2605.28811, Adobe/UNC, May 2026) is the 2026 neighbour for relighting a masked foreground video to match a new background. I found no paper that restyles a static background plate once and then composites the real people back per pixel with spatial region rules. That combination, and the zero-flicker background it gives by construction at CPU cost, is still ours. The individual pieces are classic. Wang and Adelson 1994 (layers), Irani's mosaics, Chuang et al. 2002 (background estimation for matting), Agarwala's Photomontage and Panoramic Video Textures, Cliplets and Selectively De-animating Video (still and live regions of tripod video chosen by user strokes) are all verified ancestors. Temporal consistency in 2026 papers is mostly adjacent-frame CLIP similarity (0.95–0.98) and VBench-style flicker scores. Vera's authors note these are saturated near 0.97–0.98, so we should report a pixel-level background-stability measure that our method wins by construction.

## Findings

### [LociArt: A Unified Paradigm for Free-Style Local Video Stylization (GRNStyle)](https://arxiv.org/abs/2610.36456) (2026-10)
*paper · evidence: read · relevance 5/5*

- **What:** Mask-specified local video stylization: 'where' comes from a mask, 'which style' from a reference. A 'polar style-aware mask' lets it do several regions with different styles even though it was trained on single-region pairs. It is a 2B model, fully fine-tuned from Generative Refinement Networks, trained on 8 H200s. Videos are 81 frames at 720p. Data and benchmark: LociArt-100K pairs, plus a benchmark of 80 source videos and 84 masks (168 foreground/background cases). Temporal consistency (CLIP similarity of adjacent frames): GRNStyle 0.983, Seedance 2.5 0.984, VACE-1.3B 0.981, UniVST 0.969, LEAST 0.953.
- **Relevance:** The closest academic neighbour to the PAINT tool: different styles in different masked regions of a video, background-only and foreground-only cases included. It came out a month ago.
- **How we differ:** It regenerates every pixel with a video model on an H200-class GPU, explicitly 'without hard-masking source features or output pixels', so people and unedited areas are not kept exact. Its masks are fixed per video and do not respond to people. It has no clean plate, and people do not switch style by where they stand. Ours: one image per world on a CPU, exact real pixels for people, and region membership decided per person by their feet.
- **What to take:** Cite it as the current state of the art for multi-region video stylization. Borrow its foreground/background case split and its adjacent-frame CLIP TC metric so our numbers are comparable. Its baseline list tells us what reviewers expect.

### [Vera: A Layered Diffusion Model for Content-Preserving Video Editing](https://arxiv.org/html/2606.23610) (2026-06)
*paper · evidence: read · relevance 5/5*

- **What:** Generates an edit layer plus an alpha matte and composites them over the source video. It extends Wan2.1 into a Mixture-of-Transformers with one DiT per layer, trained on a 486K-frame layered dataset. On background change: 35.2 dB PSNR, 0.993 SSIM, 0.010 LPIPS. It runs 49 frames at 832x480 in about 8.3 min on one A100 (21.8 GB) for the 1.3B model, about 3x VACE-1.3B. VBench-style temporal flickering is 0.97–0.98, which the authors call 'nearly saturated'.
- **Relevance:** The closest learned version of our 'keep the real pixels, add a generated layer' compositing idea.
- **How we differ:** It learns the alpha matte and regenerates the edit layer for every frame, at minutes per clip on a GPU. Ours computes alpha from a plate difference, generates the world once, and composites in real time in a browser with spatial rules. Vera has no notion of regions that people cross.
- **What to take:** Use its framing ('content-preserving' and 'retain source pixels outside alpha support') and its PSNR-on-preserved-region metric. Its remark that the flicker metrics are saturated supports adding our own background-stability metric.

### [PAI-Studio: Cinematic Video Background Replacement with Camera-Aware Motion](https://arxiv.org/html/2606.01399) (2026-05)
*paper · evidence: read · relevance 4/5*

- **What:** Takes a green-screen foreground (SAM3) plus 1–3 background reference images and generates a new video with the background replaced. Built on Wan 2.2-5B with a LoRA, 97 frames at 1080p, 8 H200s. Its benchmarks use clean plates from the source video (Cine-Restore) and Gemini-restyled backgrounds (Cine-NBG). Motion consistency (CoTracker3): 0.717 vs Kling O1 0.646, VACE 0.595, Runway Aleph 0.413.
- **Relevance:** Clean plates plus a restyled background plus the original people is our pipeline's recipe, done generatively.
- **How we differ:** It regenerates the whole video, people included, in one DiT pass. It handles a moving camera but uses datacenter GPUs. It has no regions and no switching. Ours keeps the people's own pixels, assumes a static camera, and the background cannot flicker.
- **What to take:** Its Cine-NBG idea (restyle a plate with an image model, then use it as a reference) is exactly our step 2 and validates it. It also gives us numbers on Aleph and VACE to cite as video-model baselines.

### [HarmoVid: Relightful Video Portrait Harmonization](https://arxiv.org/html/2605.28811) (2026-05)
*paper · evidence: read · relevance 4/5*

- **What:** Relights a masked foreground video to match a target background (shadows, colour, intensity). Per-frame Relightful Harmonization output is deflickered, then used to train a CogVideoX DiT. Handles more than 85 frames with temporal MultiDiffusion. Inference 168 s and 17.4 GB, vs RelightVid 199 s and Light-A-Video 1,822 s. Metrics: adjacent-frame CLIP, RAFT motion preservation, boundary sharpness, and a 33-person user study.
- **Relevance:** The 2026 state of the art for our weak point 'people are only tinted, not relit'.
- **How we differ:** It needs a GPU and minutes per clip, and no code release is mentioned. Ours is a fitted grid of affine colour transforms plus a shadow ratio, real-time on a CPU.
- **What to take:** Cite it as the upgrade path. Its 'per-frame harmonizer plus deflicker' recipe could be run offline on our person layer on Colab.

### [Selectively De-animating Video (Bai, Agarwala, Agrawala, Ramamoorthi)](https://research.adobe.com/publication/selectively-de-animating-video/) (2012 (ACM TOG 31(4), SIGGRAPH))
*paper · evidence: snippet · relevance 4/5*

- **What:** The user strokes regions to hold still. The video is warped, and a graph cut composites the warped regions with still frames, optionally looping.
- **Relevance:** A Berkeley ancestor (Bai's EECS PhD, Agrawala and Ramamoorthi): user strokes choose which regions follow which source. That is our paint tool, with 'still vs live' in place of 'world A vs world B'.
- **How we differ:** Its sources are the input's own frames, not generated worlds. It uses a graph-cut seam rather than per-person region membership.
- **What to take:** Cite it as the ancestor of the paint tool. Its graph-cut composite could also clean up our painted seams.

### [Cliplets: Juxtaposing Still and Dynamic Imagery (Joshi et al.)](https://hhoppe.com/proj/cliplets/) (2012 (UIST, Best Paper))
*paper · evidence: snippet · relevance 4/5*

- **What:** An interactive system that juxtaposes still and video segments in space and time (cinemagraph-like) from handheld video. It uses alignment, looping optimization and Laplacian blending.
- **Relevance:** An HCI ancestor of 'paint where each source shows' in a fixed-view video, at UIST.
- **How we differ:** It mixes still and moving copies of the same footage. It has no generated worlds and no people-triggered switching.
- **What to take:** Cite it, and borrow its spatiotemporal-mapping vocabulary (source region plus time mapping) to describe our rules.

### [Interactive Digital Photomontage (Agarwala et al.)](https://grail.cs.washington.edu/projects/photomontage/) (2004 (ACM TOG 23(3), SIGGRAPH))
*paper · evidence: memory · relevance 4/5*

- **What:** The user paints strokes to pick which source image supplies each pixel. Graph-cut seams and gradient-domain fusion produce the composite.
- **Relevance:** The ancestor of 'one mask per world, painted by hand'. Our worlds are its source images, aligned by construction because they share the plate's geometry.
- **How we differ:** Stills only, and the sources are photographs. Ours is video, generated sources and live people.
- **What to take:** Cite it as the direct ancestor of the paint tool. Graph cut plus Poisson blending is a possible soft-seam mode next to our morph.

### [Representing Moving Images with Layers (Wang and Adelson)](https://persci.mit.edu/pub_abstracts/wang_tr279_abs.html) (1994 (IEEE TIP 3(5):625–638))
*paper · evidence: snippet · relevance 4/5*

- **What:** Represents video as ordered layers, each with intensity, alpha and motion maps. Designed for compression.
- **Relevance:** The root of our model: one static background layer (the plate) plus moving foreground layers (people) with alpha.
- **How we differ:** It is for analysis and coding. We swap the background layer for generated worlds.
- **What to take:** The opening citation for 'video = plate + people'.

### [VideoGrain: Modulating Space-Time Attention for Multi-grained Video Editing](https://arxiv.org/abs/2502.17258) (2025-02 (ICLR 2025))
*paper · evidence: snippet · relevance 3/5*

- **What:** Zero-shot class-, instance- and part-level editing with text grounded to regions by modulating cross- and self-attention. Evaluated on 16 frames on one A6000.
- **Relevance:** The canonical multi-region text-grounded video editor; different prompts for different regions.
- **How we differ:** Short clips, every frame regenerated, and regions tied to objects rather than to ground areas. Unedited pixels are not exact.
- **What to take:** Cite it as the multi-grained editing baseline.

### [PRIMEdit / MIVE: instance-aware multi-object video editing with a benchmark](https://arxiv.org/pdf/2412.12877) (2024-12 (revised later))
*paper · evidence: snippet · relevance 3/5*

- **What:** Multi-instance video editing with probability redistribution and per-instance masks, plus the MIVE benchmark of 200 videos. It argues that earlier multi-instance methods lack explicit local control.
- **Relevance:** Mask-local, multi-instance editing; a benchmark source.
- **How we differ:** It edits objects, not regions of a static ground plane, and regenerates frames. I did not confirm that the MIVE name and the retitling to PRIMEdit are the same work.
- **What to take:** Cite it with VideoGrain for multi-instance editing.

### [VIRES: Video Instance Repainting via Sketch and Text Guided Generation](https://arxiv.org/abs/2411.16199) (2024-11 (rev. 2025-04, CVPR 2025 per memory))
*paper · evidence: snippet · relevance 3/5*

- **What:** Repaints, replaces, generates or removes instances using sketch (structure) and text (appearance) on a video DiT. Introduces VireSet (85K training clips, 1K eval).
- **Relevance:** Sketch- or brush-guided region repainting in video.
- **How we differ:** It works per instance and regenerates frames on a GPU. Our brush picks ground regions for whole-plate worlds.
- **What to take:** Cite it under 'sketch-grounded local editing'.

### [VideoPainter: Any-length Video Inpainting and Editing with Plug-and-Play Context Control](https://arxiv.org/html/2503.05639v2) (2025-03 (SIGGRAPH 2025 per memory))
*paper · evidence: snippet · relevance 3/5*

- **What:** Mask-based video inpainting and editing with a lightweight context encoder (6% of DiT parameters). For long videos it appends inpainted-region tokens from earlier clips to keep identity over any length.
- **Relevance:** Mask-driven editing and the long-clip problem.
- **How we differ:** It generates content inside the masks for every frame. We generate one still per world and never generate frames.
- **What to take:** Its 'any length' trick shows how far generative methods go to fight drift. Our single plate image sidesteps the problem.

### [UniVST: training-free localized video style transfer](https://arxiv.org/html/2410.20084v5) (2024-10)
*paper · evidence: snippet · relevance 3/5*

- **What:** Training-free localized style transfer with latent optical-flow propagation of a stylized keyframe and a masked region. CLIP TC of 0.969 in LociArt's table.
- **Relevance:** Localized video stylization; already mentioned in our notes in one line, but it is a direct baseline.
- **How we differ:** It propagates along optical flow, so it drifts under occlusion. It handles one region at a time.
- **What to take:** Use it as a baseline. Its code is open (memory), so we could try it on Colab.

### [Video indexing / compression based on mosaic representations (Irani, Anandan et al.)](https://www.wisdom.weizmann.ac.il/~irani/abstracts/mbc.html) (1996–1998 (Signal Processing: Image Communication / IEEE Proc., per memory))
*paper · evidence: snippet · relevance 3/5*

- **What:** Builds a scene mosaic, a single background image for the whole shot, and codes or indexes video as mosaic plus residual moving objects.
- **Relevance:** The ancestor of a single background image shared by all frames. With MPEG-4 sprite coding it is also the path to our moving-camera roadmap (restyle the mosaic once).
- **How we differ:** For compression and indexing, not restyling.
- **What to take:** Cite it for the moving-camera future: restyle one panorama or mosaic and warp it back.

### [Video Matting of Complex Scenes (Chuang, Agarwala, Curless, Salesin, Szeliski)](https://grail.cs.washington.edu/projects/digital-matting/video-matting/) (2002 (ACM TOG 21(3):243–248))
*paper · evidence: snippet · relevance 3/5*

- **What:** Video matting built on natural-image matting, optical flow and background estimation (a recovered clean background).
- **Relevance:** Its use of an estimated background plate for matting is the principled version of our plate-difference person mask.
- **How we differ:** It relies on trimaps from keyframes and offline optimization. Ours is a threshold plus morphology.
- **What to take:** Cite it with Background Matting (already in our notes) for 'plate-assisted matting'.

### [Webcam Clip Art: Appearance and Illuminant Transfer from Time-lapse Sequences (Lalonde, Efros, Narasimhan)](https://www.cs.cmu.edu/~jlalonde/webcamClipArt/) (2009 (SIGGRAPH Asia, ACM TOG 28(5)), per memory)
*paper · evidence: memory · relevance 3/5*

- **What:** Uses fixed webcams' time-lapse to estimate illumination and then relights and composites objects (such as people) into the scene consistently.
- **Relevance:** An Efros-lab ancestor in the course's own lineage: a static camera exploited to composite people believably under new lighting.
- **How we differ:** Real lighting changes over time, not generated worlds. Non-diffusion.
- **What to take:** Cite it as the instructor-lineage precedent for relighting composited people in fixed-camera footage. Verify the URL and venue by hand.

### [MAST: Mask-Guided Attention Control for Training-Free Regional Multi-Style Transfer](https://arxiv.org/html/2604.12281) (2026-04)
*paper · evidence: snippet · relevance 3/5*

- **What:** Training-free image method that pairs each style reference with a spatial mask inside one diffusion pass.
- **Relevance:** The image analogue of our multi-world painted plate, all in one generation pass.
- **How we differ:** Image only. Styles blend inside one generation, whereas we generate full worlds and choose per pixel and per person at composite time.
- **What to take:** Optional: generate a single multi-region world with MAST-style masked attention, so seams are drawn by the model, as a 'painted world' variant.

### [Wan-Alpha (CVPR 2026) and Wan-Alpha++ (2026): RGBA video generation](https://arxiv.org/html/2509.24979) (2025-09 / CVPR 2026; Wan-Alpha++ 2026-10 (arXiv 2610.26189))
*paper · evidence: snippet · relevance 2/5*

- **What:** Generates transparent (RGBA) video by learning shiftable RGB-alpha distributions on Wan. Wan-Alpha++ extends this to image-conditioned RGBA animation. Related: TransPixeler (alpha branch with cross-RGBA attention), LayerFlow, LayerT2V, UniRGBA (arXiv 2611.09069).
- **Relevance:** The layered-generation line: foreground and background as separate generated layers.
- **How we differ:** It generates new transparent content. We decompose real footage into a plate and real people and generate only the background.
- **What to take:** Cite it in one sentence as the generative counterpart of our two-layer model. Wan-Alpha++ could make animated RGBA overlays (snow, bubbles) for a world.

### [Panoramic Video Textures (Agarwala et al.)](https://grail.cs.washington.edu/projects/panovidtex) (2005 (ACM TOG 24(3):821–827))
*paper · evidence: snippet · relevance 2/5*

- **What:** Builds a looping panoramic video from a single panning camera by min-cut stitching of video fragments.
- **Relevance:** An ancestor of exploiting a fixed or controlled camera to treat the background as a reusable texture.
- **How we differ:** Its goal is looping a background, not restyling it.
- **What to take:** Cite it only if space allows.

### [Video SnapCut (Bai, Wang, Simons, Sapiro)](https://research.adobe.com/publication/video-snapcut-robust-video-object-cutout-using-localized-classifiers/) (2009 (ACM TOG 28(3), SIGGRAPH; shipped as After Effects Roto Brush))
*paper · evidence: snippet · relevance 2/5*

- **What:** Interactive video object cutout with localized classifiers propagated along the object boundary.
- **Relevance:** The ancestor of brush-based selection in video (Roto Brush). SAM 2/3 are its modern successors.
- **How we differ:** It selects objects to cut out. Our brush selects static ground regions.
- **What to take:** One-line citation for brush interfaces in video.

### [Motion-I2V (motion brush) and Follow-Your-Click (regional animation)](https://arxiv.org/pdf/2401.15977v2.pdf) (2024-01 (SIGGRAPH 2024 per memory); Follow-Your-Click arXiv 2403.08268, AAAI 2025)
*paper · evidence: snippet · relevance 2/5*

- **What:** Motion-I2V's 'motion brush' animates user-painted image areas. Follow-Your-Click animates a clicked region with a short motion prompt. Kling ships a Motion Brush product.
- **Relevance:** The generative-video form of 'paint to choose what changes'.
- **How we differ:** It paints where motion happens. We paint where a style shows, and people choose by moving.
- **What to take:** Cite it as the closest UI precedent in generative video.

### [HorizonRelight: Relighting Long-horizon Videos Consistently via DiTs](https://arxiv.org/abs/2606.29095) (2026-06)
*paper · evidence: snippet · relevance 2/5*

- **What:** Chunked long-video relighting that carries target-domain latents across chunk boundaries to avoid seams and drift. Authors include NVIDIA researchers (per author list).
- **Relevance:** 2026 relighting; shows that long-clip drift is still an open problem for video models.
- **How we differ:** It relights whole frames. We never regenerate frames.
- **What to take:** Cite it as evidence that long-clip relighting is still hard.

### [Everybody Dance Now (Chan, Ginosar, Zhou, Efros)](https://arxiv.org/abs/1808.07371) (2018 (ICCV 2019))
*paper · evidence: memory · relevance 1/5*

- **What:** Video-to-video motion transfer that renders a target person dancing like a source.
- **Relevance:** Instructor (Efros, Berkeley) work on generating video of people. It contrasts with our choice to keep people real.
- **How we differ:** It generates people. We never generate people.
- **What to take:** Optional one-liner in the course-lineage paragraph.

### [I2VControl: Disentangled and Unified Video Motion Synthesis Control](https://arxiv.org/html/2411.17765v3) (2024-11)
*paper · evidence: snippet · relevance 1/5*

- **What:** Unifies motion brush, camera control and drag as point trajectories. It notes conflicts such as a brushed background moving under a camera tilt.
- **Relevance:** Region-brush control in generation.
- **How we differ:** Motion control only.

## Ideas to borrow

- **Report a background-stability metric our design wins by construction: mean per-pixel temporal standard deviation (or warping error) over background pixels (plate mask), alongside the adjacent-frame CLIP TC that LociArt and HarmoVid use. Expected values: our background std is 0 except under people's shadows. LociArt-style video methods score 0.95–0.98 CLIP TC, which barely separates methods.** Source: LociArt https://arxiv.org/html/2610.36456v1 ; Vera https://arxiv.org/html/2606.23610. Vera's authors say temporal flickering and CLIP consistency are saturated. A pixel-level background metric turns our main claim into a number. *Effort: hours; CPU only (numpy over exported frames)*
- **Measure preservation the way Vera does: PSNR, SSIM and LPIPS between the source and our output on person pixels. With w = 0 on people who have not crossed, this should be infinite or exact. Run the same on a VACE-1.3B output for contrast.** Source: Vera https://arxiv.org/html/2606.23610. Shows plainly that 'the real people stay real' while learned layered editors only come close (35 dB). *Effort: hours for ours; one Colab GPU session for the VACE-1.3B comparison (2.4 min per clip on an A100 per Vera)*
- **Run the LociArt foreground/background split as an evaluation: for a few clips, paint background-only, ground-region-only and whole-frame masks. Show the same masks fed to a video model (VACE) next to ours.** Source: LociArt https://arxiv.org/abs/2610.36456. Puts us on the same axis as the newest state of the art, using their task definition. *Effort: days; Colab GPU for the baseline*
- **Add an optional graph-cut seam for painted regions, as in Photomontage and De-animating: snap the brush boundary to low-gradient paths shared by both worlds before compositing.** Source: Agarwala et al. 2004 https://grail.cs.washington.edu/projects/photomontage/ ; Bai et al. 2012 https://research.adobe.com/publication/selectively-de-animating-video/. Rough hand-painted edges are a visible weak point. Classic, cheap and in-scope for CS180 (it echoes the blending projects). *Effort: days; CPU (can be precomputed once per mask, since the plate is static)*
- **Generate one 'painted world' in a single pass with mask-conditioned regional styles (MAST-style masked attention, or SD inpainting per region with a shared seed), so the model draws the seams itself. Offer it next to the per-pixel switch.** Source: MAST https://arxiv.org/html/2604.12281. Gives a seamless multi-world plate and still costs one image per layout, so there is still no flicker. *Effort: days; Colab GPU, or slow on CPU with LCM*
- **Use HarmoVid's recipe offline for the person layer: run a per-frame harmonizer (IC-Light fbc) on the cut-out person against each world, then temporally smooth the result (deflicker) before compositing.** Source: HarmoVid https://arxiv.org/html/2605.28811. Addresses 'people are only tinted, not relit' for the exported-video path, without needing a video model. *Effort: days; Colab GPU*
- **Moving-camera roadmap through mosaics: build an Irani or MPEG-4-style background mosaic (panorama) from a panning clip, restyle the mosaic once, and warp it back per frame by homography.** Source: Irani et al. mosaics https://www.wisdom.weizmann.ac.il/~irani/abstracts/mbc.html ; Panoramic Video Textures https://grail.cs.washington.edu/projects/panovidtex. Extends 'draw once, never flicker' to pan and tilt shots, and reuses CS180 Proj 3 (autostitching). *Effort: weeks; CPU*
- **Use a PAI-Studio-style restyled-plate reference as a bridge to video models: feed our generated world plus the original people to a video model (Wan VACE) and compare against our composite in the paper's baseline figure.** Source: PAI-Studio https://arxiv.org/html/2606.01399. PAI-Studio's own numbers show Aleph and VACE lose motion consistency (0.41 to 0.60 vs 0.72). It gives a cited reason to expect our composite to win on stability. *Effort: days; Colab GPU*

## Not reached or not verified

- LociArt's inference latency, code release and full multi-region results were not read (beyond 100K characters of its HTML). Check https://higherhu.github.io/lociart/ by hand.
- I did not open EditVerse, Lucy Edit, StableV2V, EVA, Ground-A-Video, VACE masks or Señorita in this pass. They are standard mask- or instruction-based editors and are best cited from LociArt's and Vera's related-work sections.
- Generative Omnimatte, OmnimatteZero, IC-Light, Light-A-Video, RelightVid and TC-Light are already in our notes and were not re-verified. DiffusionRenderer (NVIDIA, CVPR 2025) and UniRelight (2025) were not searched; both are from memory.
- No paper was found that restyles a static background plate once and composites the real people back with spatial region rules. This is a negative result from about six searches, not proof. Try by hand on Google Scholar: 'clean plate' stylization, 'background plate' diffusion composite, 'static camera' video stylization.
- HCI venues: no UIST, CHI or SIGGRAPH 2025–26 paper on region-brush generative video stylization turned up. Search the ACM DL directly (UIST 2025, CHI 2026, SIGGRAPH 2026 Labs and Real-Time Live) for 'brush', 'region' and 'generative video'.
- Not verified this session (memory only): Interactive Digital Photomontage URL; Webcam Clip Art URL and venue; MPEG-4 sprite coding citation (Lee et al., IEEE TCSVT 1997); Irani mosaic venue and year (1996 SPIC vs 1998 IEEE Proc.); Everybody Dance Now venue; Ren Ng (light fields) work relevant to us (I found none worth citing).
- Typical warping-error values for per-frame vs video methods in 2026 papers were not collected. Only CLIP TC (LociArt 0.953–0.984), VBench-style TF (Vera 0.97–0.98) and CoTracker motion consistency (PAI-Studio 0.41–0.79) were found.
- Several arXiv IDs above (2610.x, 2611.x) are from autumn 2026. LociArt, Vera, PAI-Studio, HarmoVid and ReMoVe were fetched; HorizonRelight, MAST, Wan-Alpha++ and UniRGBA are snippet-only.

## Notes

## What changed between July and November 2026

- **LociArt** (arXiv 2610.36456, 27 Oct 2026) is the new state of the art for local video stylization and the paper our PAINT tool must cite. [fetched]
  - What it does: masks say *where*, style references say *which*, and the model renders several regions with different styles in one go.
  - Model and data:
    - 2B GRNStyle at 81 frames and 720p, trained on 8 H200s.
    - Its benchmark has 80 videos and 84 masks, giving 168 foreground/background cases.
  - It does **not** hard-paste non-target pixels. Baselines that do (LEAST, StyleGallery) are excluded from PSNR for that reason.
  - Temporal consistency (CLIP cosine of adjacent frames):

| Method | TC |
|---|---|
| Seedance 2.5 | 0.984 |
| GRNStyle | 0.983 |
| CoinVE-Edit | 0.983 |
| VACE-1.3B | 0.981 |
| UniVST | 0.969 |
| StyleGallery | 0.957 |
| RegionRoute | 0.955 |
| LEAST | 0.953 |

  - Its related-work list (PickStyle, MoStyle, DreamStyle, TeleStyle, CoinVE, DynVFX, RegionRoute, StyleGallery, LEAST) is the bibliography a reviewer will expect.
- **Vera** (arXiv 2606.23610, 22 Jun 2026, Caltech/Netflix) is the content-preserving layered editor. [fetched]
  - Method: an edit layer plus alpha over the source; outside the alpha support the source pixels are kept.
  - Results on background change: 35.2 dB PSNR, 0.993 SSIM.
  - Cost: 8.3 min and 21.8 GB on one A100 for 1.3B; 14.9 min on four A100s for 14B.
  - The authors say temporal flickering and the other consistency metrics are near-saturated (0.97–0.98).
- **PAI-Studio** (arXiv 2606.01399, 31 May 2026) replaces the background behind a SAM3-matted foreground using 1–3 reference images, on Wan 2.2-5B, 97 frames at 1080p. [fetched]
  - Its Cine-NBG benchmark uses Gemini-restyled plates, which is effectively our step 2.
  - Motion consistency (CoTracker3):

| Method | Score |
|---|---|
| PAI-Studio | 0.717 |
| Kling O1 | 0.646 |
| VACE | 0.595 |
| Runway Aleph | 0.413 |

- **HarmoVid** (arXiv 2605.28811, 27 May 2026, Adobe/UNC) relights a masked foreground to a target background video. [fetched]
  - Built on CogVideoX. Inference takes 168 s and 17.4 GB, against RelightVid at 199 s and Light-A-Video at 1,822 s.
  - Metrics: adjacent-frame CLIP, RAFT motion preservation, boundary sharpness, and a 33-person user study.
- Other 2026 work, from snippets only:
  - HorizonRelight (2606.29095): long-video relighting with chunk carry-over.
  - LightCrafter (2607.08016).
  - RGBA generation: Wan-Alpha++ (2610.26189), UniRGBA (2611.09069), and Wan-Alpha at CVPR 2026.
  - MAST (2604.12281): image regional multi-style transfer.

## Honest positioning

What already exists:
- Multi-region, multi-style video stylization from masks (LociArt).
- Content-preserving layered editing (Vera).
- Plate-referenced background replacement behind real foregrounds (PAI-Studio).
- Learned foreground relighting (HarmoVid).

All of these regenerate frames with 1–14B video DiTs on A100/H200 GPUs, at minutes per clip and capped near 81–97 frames.

Still ours:
1. The background is generated **once** per world. Background flicker is zero by construction, not 0.98 CLIP TC, and clip length is unlimited.
2. People's pixels are exactly the input wherever w = 0.
3. Region membership is decided **per person, by their feet**, so a whole person "crosses" as a unit. In LociArt and the others, masks are fixed pixel regions.
4. It runs live in a browser on a CPU, including the webcam kiosk.

What we should concede:
- Our worlds are lower fidelity (SD 1.5).
- Our people are tinted, not relit.
- We require a fixed camera.

## Classic ancestors (for the CS180 paper)

- **Wang and Adelson 1994**, IEEE TIP 3(5):625–638. Layers carrying intensity, alpha and motion. This is the plate-plus-people model. [snippet]
- **Irani, Anandan et al.** Mosaic-based video representation: one background image for a shot, plus residual moving objects. This is also our moving-camera path. [snippet; year and venue unverified]
- **MPEG-4 sprite coding.** The industrial version of the same idea. [memory]
- **Chuang et al. 2002**, TOG 21(3):243–248. Video matting that uses background estimation, the principled form of our plate difference. [snippet]
- **Agarwala et al. 2004, Interactive Digital Photomontage.** Paint strokes choose a source per pixel, with a graph cut plus gradient fusion. This is the paint tool's direct ancestor. [memory]
- **Agarwala et al. 2005, Panoramic Video Textures**, TOG 24(3):821–827. [snippet]
- **Rav-Acha, Kohli, Rother, Fitzgibbon 2008, Unwrap Mosaics**, TOG 27(3). Edit one texture map and propagate it through video. This is "edit once, reuse everywhere" for moving objects. [snippet]
- **Bai, Wang, Simons, Sapiro 2009, Video SnapCut**, TOG 28(3), later Roto Brush. Brush selection in video. [snippet]
- **Joshi et al. 2012, Cliplets** (UIST Best Paper). Still and live regions mixed spatially. [snippet]
- **Bai, Agarwala, Agrawala, Ramamoorthi 2012, Selectively De-animating Video**, TOG 31(4). Berkeley; user strokes choose regions, then graph-cut compositing. [snippet]
- **Instructor lineage:**
  - Lalonde, Efros, Narasimhan 2009, "Webcam Clip Art": a static camera exploited to relight and insert objects. [memory]
  - Photo Clip Art and pix2pix/CycleGAN are already in our notes.
  - Kanazawa: I found no directly relevant paper. Her 4D human work is only tangential.
  - Ng: nothing relevant found.

## Temporal-consistency measurement in 2025–26

| Measure | Used by | Values |
|---|---|---|
| Adjacent-frame CLIP similarity (from AVID) | LociArt, HarmoVid | 0.95–0.98 |
| VBench temporal flickering and subject consistency | Vera | 0.96–0.98, saturated |
| Trajectory-based motion consistency (CoTracker3) | PAI-Studio | 0.41–0.79 |
| RAFT flow discrepancy (motion preservation) | HarmoVid | not recorded |
| User studies | HarmoVid (33 people) | n/a |

Recommendation:
- Report CLIP TC for comparability.
- Add a background-region temporal standard deviation or warping error, where we are exactly zero.
- Add preserved-region PSNR as Vera does, where we are exact on people who have not crossed.
