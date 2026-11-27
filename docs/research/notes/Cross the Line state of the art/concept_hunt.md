# Adversarial hunt for our exact concept

> Research sweep of 27 November 2026. Evidence marks: **read** (the page was opened), **snippet** (search-result text only), **memory** (unverified). Social and product sites were blocked in the session, so product facts are mostly snippets.

## Summary

I assumed someone had already built Cross the Line and tried to prove it, across six concepts (about 25 searches and fetches on 27 Nov 2026). Concept A, restyling the clean plate once and compositing the real people back, is clearly FOUND. Microsoft Teams Decorate and FXjutsu Toon World were already known. This round adds ComfyUI templates (a MiniMax H3 video restyle, Bria background change), the LTX-2.3 Clean Plate IC-LoRA (July 2026) and AnyPortal (ICCV 2025), which replaces a video's background zero-shot and claims "precise foreground preservation". No public repo does our exact chain (temporal-median plate, one SD image per world, composite), but it is easy to assemble, so it cannot be claimed. Concept B, painted regions with different styles, is PARTLY found. Xia et al. (2020) stylise user-scribbled video regions with several styles at once in real time. MAST (April 2026) and the regional-prompting tools (Regional Prompter, ComfyUI mask conditioning, Krita AI Diffusion "Regions" with live painting) assign styles to painted regions, but only in still images. OpenArt's video inpainting lets you brush what to keep. None of these switches the people by where they stand. Concept C has strong non-generative ancestors. The yellow first-down line (1998) draws on the ground under real players using per-pixel keying. Virtual perimeter ads replace the world behind players. An NYU ITP piece (2015) tracked a walker on a 5x5 floor of projected tiles, each a different environment. None restyles the person who enters a zone. Concepts D and E are NOT FOUND, with caveats: AI mirror activations (Atomic Digital for PSG in 2025, Groove Jones) and a SIGGRAPH 2026 Real-Time Live demo that changes backgrounds live from a text prompt come closest, but none shows the visitor unaltered inside a restyled copy of the same room with spatial zones, and I found no course gallery project like ours. Concept F is PARTLY found: Morphic and Magicshot "portal" templates and the Instagram "falling through" trend show a person stepping into another AI world, but every one regenerates the whole frame and the person with a video model. What is still ours: painted, per-pixel zones over one pixel-aligned pair (the real frame and one stable generated plate), people switching as a whole by the zone under their feet, CPU-only generation and a live browser kiosk. Most items rest on search snippets; several key hosts (blog.siggraph.org, contra.com, cs231n.stanford.edu) were blocked.

## Findings

### [Microsoft Teams Premium 'Decorate your background' (already known)](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705) (2023-11 / GA 2024)
*product · evidence: snippet · relevance 5/5*

- **What:** Takes a snapshot of the room, removes the user, fills the hole, restyles the image once with img2img, and shows the live user in front.
- **Relevance:** Concept A and the kiosk: the same architecture. Confirmed again; nothing new found this round.
- **How we differ:** Whole background, no zones, crossing or depth, no recolouring of the person.
- **What to take:** The 'generate once' citation.

### [FXjutsu 'Toon World' (already known)](https://github.com/audriu/fxjutsu) (2026)
*repo · evidence: memory · relevance 5/5*

- **What:** An LTX ComfyUI preset: clean plate, then restyle the empty plate, then real people back on top ('the world becomes anime, people stay real').
- **Relevance:** Concept A: the same order, offline, on a GPU.
- **How we differ:** Re-generates the whole clip with a video model, has a person-matte boundary only, and no zones or live mode.

### [AnyPortal: Zero-Shot Consistent Video Background Replacement (Gao, Lan, Yang)](https://arxiv.org/abs/2509.07472) (2025-09)
*paper · evidence: read · relevance 4/5*

- **What:** A training-free method that replaces a video's background. It combines a video diffusion prior with image-diffusion relighting (IC-Light), plus a 'Refinement Projection Algorithm' that the authors say gives 'precise foreground preservation'. They say it runs on consumer GPUs (no timings given). Project page: gaowenshuo.github.io/AnyPortal.
- **Relevance:** Concept A: the state of the art for 'new background, same person' in academia, and it relights the person, which we do not. It does not use a restyled copy of the same room, has no spatial zones, and is not live.
- **How we differ:** It generates a background that changes over time and relights the foreground. We keep one restyled image of the actual room, which cannot flicker, add line, ring and painted zones, and composite live on a CPU.
- **What to take:** Cite it as the heavy 'how it is done today' for A and C7, with relighting as the upgrade we skip.

### [Real-time Localized Photorealistic Video Style Transfer (Xia, Xue, Lai, Sun, Chang, Kulis, Chen)](https://arxiv.org/abs/2010.10056) (2020-10)
*paper · evidence: read · relevance 4/5*

- **What:** Feed-forward photorealistic style transfer for video, applied to local regions chosen by video segmentation or user scribbles. It can put different styles on several objects at once and transition between styles over time, in real time.
- **Relevance:** Concept B: the closest prior work for 'paint regions and give each its own style' in video. It is not diffusion and has no fixed-camera plate.
- **How we differ:** It stylises the selected objects frame by frame, including people, and uses photorealistic colour or texture styles. We paint regions of the static scene, and each region shows a pre-generated world. People stay real and switch world by the region under their feet.
- **What to take:** Related-work citation for the Paint tool. Its idea of styles transitioning over time matches our Morph.

### [MAST: Mask-Guided Attention Control for Training-Free Regional Multi-Style Transfer](https://arxiv.org/abs/2604.12281) (2026-04 (v2 2026-09))
*paper · evidence: read · relevance 4/5*

- **What:** Training-free diffusion style transfer that gives each user mask region a different reference style without compositing afterwards. It tackles style leaking between regions through attention. Reports the best ArtFID, FID and R-FID for 2 to 5 styles. Images only; no code linked.
- **Relevance:** Concept B: the 2026 state of the art for one image with several painted styles, the still-image version of our multi-world Paint.
- **How we differ:** Images only, and slow. We composite separately generated worlds per pixel at camera rate, so seams between worlds are hard or blended. MAST makes regions coherent inside a single generation.
- **What to take:** Cite it. Its 'style leakage' problem is the opposite of ours: our seams can be inconsistent because each world is generated separately.

### [LTX-2.3 Clean Plate IC-LoRA (Lightricks; ComfyUI)](https://comfyui-wiki.com/en/news/2026-07-19-ltx-2-3-clean-plate-ic-lora) (2026-07)
*model · evidence: snippet · relevance 4/5*

- **What:** A video-to-video LoRA that removes people, vehicles and cast shadows and rebuilds the empty background without a mask. Users report ghosting or smears, fixed by describing the empty scene in more detail. Also available as a hosted workflow on floyo.ai.
- **Relevance:** Concept A: a drop-in, stronger replacement for our temporal median when people linger or shadows stay in the plate.
- **How we differ:** A heavy video model (GPU). The median is free and exact when people keep moving.
- **What to take:** Offer it as a Colab option for clips where the median fails, and compare with the median in the report.

### [ComfyUI hub: 'Minimax H3 Video Restyling' and 'Change a video's background' templates](https://comfy.org/hub/workflows/minimax-h3-video-restyling-58a3f7167dba/) (2026)
*product · evidence: snippet · relevance 4/5*

- **What:** Official ComfyUI templates. One restyles a video's background and lighting from a guide image with the open-weights MiniMax H3 model. The other (Bria nodes) replaces a video's background while the prompt tells it to keep the subject, pose and timing.
- **Relevance:** Concept A: shows that 'restyle the background, keep the person' is now a one-click template.
- **How we differ:** Re-generates every frame with a video model and the whole background. No aligned restyle of the plate, no zones.
- **What to take:** Shows we must not pitch 'AI background, real people' as the novelty. Pitch the zones.

### [Sportvision '1st & Ten' virtual first-down line](https://entertainment.howstuffworks.com/first-down-line.htm) (1998-09 (first on ESPN))
*product · evidence: snippet · relevance 4/5*

- **What:** Laser-surveyed 3D field model, camera pan, tilt and zoom sensors, and a per-frame colour key that paints the line only on turf pixels and never over players, referees or the ball. Program video is delayed a few frames. The line is not shown when mud makes players and turf look alike.
- **Relevance:** Concept C: the classic precedent for drawing on the world under the real people with a per-pixel 'is this ground or a person?' test, which is exactly our w-mask times person-mask logic.
- **How we differ:** Graphics only. Nothing is restyled and people never change. It has the same failure mode as our background difference (when people and ground look alike).
- **What to take:** A great one-line analogy for the 2-minute talk: 'like the yellow first-down line, the world is painted under the players, never on them'.

### [Krita AI Diffusion (Acly) Regions and Live Painting](https://github.com/Acly/krita-ai-diffusion) (2026 (active))
*repo · evidence: read · relevance 4/5*

- **What:** An open-source Krita plugin: 'Regions: assign individual text descriptions to image areas defined by layers', plus 'Live Painting' where the AI interprets the canvas in real time; the gallery shows 'live painting with regions'. Images only.
- **Relevance:** Concept B: the most polished UX for 'paint where each prompt applies', with layers as regions.
- **How we differ:** A still canvas, and the AI redraws painted areas. We paint where already-generated worlds show over live video.
- **What to take:** Copy the UX: one layer per world, live preview while painting. Could generate a single multi-region world image so seams are coherent.

### [sd-webui-regional-prompter and ComfyUI mask regional conditioning (Inspire 'Regional Prompt By Color Mask', RES4LYF, Steaked 'Regional Prompts (Latent Img2Img)')](https://github.com/hako-mikan/sd-webui-regional-prompter) (2023-2026)
*repo · evidence: snippet · relevance 4/5*

- **What:** Assign different prompts to hand-drawn masks or a colour-coded mask image, including an img2img variant that starts from a real photo.
- **Relevance:** Concept B: ready-made code to render all painted worlds in one SD 1.5 pass from our paint masks.
- **How we differ:** Generation-time regions in a still. We switch per pixel at run time.
- **What to take:** An optional 'coherent paint' mode: export the paint masks as a colour mask, then run one regional img2img+ControlNet pass on the plate.

### [VideoBackgroundReplacer Hugging Face Space (MogensR): SAM2 plus MatAnyone](https://huggingface.co/spaces/MogensR/VideoBackgroundReplacer) (2025-2026)
*demo · evidence: snippet · relevance 4/5*

- **What:** An open Space for video background replacement with SAM2 segmentation, optional MatAnyone matting, hair and edge modules, temporal smoothing and a CPU fallback.
- **Relevance:** Concept A tooling: better person mattes than our background difference.
- **How we differ:** Swaps in a given background; no restyle or zones.
- **What to take:** Run MatAnyone (or SAM2) offline on Colab for uploaded clips to fix fringes, trails and shadows in our masks.

### [Virtual perimeter advertising (Supponor / TGI Sport, AIM Sport)](https://heise.de/-9794857) (2018-2025 (AIM did all UEFA Euro 2024 matches))
*product · evidence: snippet · relevance 3/5*

- **What:** Replaces the stadium's ad boards in the broadcast feed with region-specific ads, keyed by chroma (magenta boards) or infrared-emitting boards plus AI keying, with players occluding the boards correctly.
- **Relevance:** Concept C: replacing part of the world behind real people in live video, region by region.
- **How we differ:** Only flat board surfaces and prepared ads. No generated restyle of the scene, and people are not changed.
- **What to take:** A second broadcast analogy, and a precedent for different viewers seeing different worlds.

### [NYU ITP Winter Show 2015: Interactive Sound Walk (Shangbo Chen, Yun Li)](https://itp.nyu.edu/shows/winter2015/interactive-sound-walk/) (2015-12)
*artwork · evidence: snippet · relevance 3/5*

- **What:** A participant walks on a 5x5 grid of projected floor tiles, each showing a different environment that shifts as they move; tracked with a Kinect and Processing.
- **Relevance:** Concept C: the closest zone-triggered installation found. Regions of the floor are different worlds and your position picks one.
- **How we differ:** The worlds are projected tiles, not a restyle of the actual room, and the walker's appearance does not change.
- **What to take:** Demo idea: a 'checkerboard of worlds' painted preset (Wilkes once wanted to 'checkerboard time').

### [RoomAlive (Microsoft Research)](https://core.ac.uk/download/301374182.pdf) (2014 (memory; the snippet only cited it))
*paper · evidence: snippet · relevance 3/5*

- **What:** Captures a room's geometry with depth cameras and projection-maps new looks onto the physical room (e.g. Tron-themed, swampy river).
- **Relevance:** Concept D: 'the actual room restyled' with visitors inside it, done with projectors instead of a screen.
- **How we differ:** Projected, so it lights the people too. No generative restyle and no zones.
- **What to take:** A related-work line: physical restyling of the room versus our screen-based version.

### [SIGGRAPH 2026 Real-Time Live! recap](https://blog.siggraph.org/2026/07/watch-it-work-real-time-live-2026-brings-emerging-technology-to-the-stage-in-la.html/) (2026-07)
*post · evidence: snippet · relevance 3/5*

- **What:** The search snippet says one demo was a real-time camera system that changes avatars, backgrounds and visual effects live from text prompts. I could not open the page or get the title.
- **Relevance:** Concept D: possibly the closest 2026 live demo, but likely per-frame generation rather than an aligned restyle of the room.
- **How we differ:** Unknown; probably restyles per frame on a GPU, with no spatial zones.
- **What to take:** A human should check the title and the recording before the talk.

### [Atomic Digital AI mirror (Snap Camera Kit plus generative AI), PSG activation](https://atomicdigital.design/en/mirror) (2025)
*product · evidence: snippet · relevance 3/5*

- **What:** A branded mirror kiosk using AR, generative AI and Snap Camera Kit for 'dynamic environment alterations'. The PSG activation reports 6,000 sessions and a 50-s average play time.
- **Relevance:** Concept D: the commercial kiosk class. Visitors see themselves with the environment altered.
- **How we differ:** It probably swaps in a themed scene or AR overlay, not a restyled copy of the actual room, and has no crossing zones (not verified).
- **What to take:** Session metrics as a benchmark if we run the kiosk at the course demo.

### [Morphic 'AI portal transition' / portal effect videos](https://morphic.com/resources/vfx/portal-transition-effect) (2025-2026)
*product · evidence: snippet · relevance 3/5*

- **What:** Template: 'a figure walks into a glowing ring and the world behind them changes'.
- **Relevance:** Concept F (and C): the closest consumer version of 'person steps through into another world'.
- **How we differ:** An image-to-video or video model regenerates the whole shot, the person included. The new world is not an aligned restyle of the same place, and there is no persistent boundary.
- **What to take:** Shows the public already knows the 'step into another world' idea. Our version keeps the real place and the real person.

### [Magicshot 'Portal Step' and Magic Hour 'Portal Walk' templates](https://magicshot.ai/video-effects/portal-step) (2025-2026)
*product · evidence: snippet · relevance 3/5*

- **What:** From a clip of someone walking, a lit portal tears open and the next step carries them to somewhere else. The page notes the cut 'reads like a scene change' because it lands on real footage.
- **Relevance:** Concept F: a real-to-AI transition on real footage, triggered by walking.
- **How we differ:** A transition in time (a cut), not a spatial region in one frame. The whole frame is generated afterwards.

### [OpenArt AI Video Inpainting (Beeble SwitchX)](https://openart.ai/features/ai-video-inpainting/) (2026)
*product · evidence: snippet · relevance 3/5*

- **What:** Brush over what should stay (face, prop, performer) on the first frame, prompt the rest, and the tool tracks the region and regenerates the rest of every frame.
- **Relevance:** Concept B: brush-to-keep plus AI restyle of the rest is now a consumer feature.
- **How we differ:** Brushes protect the person rather than assigning worlds to places. One style per pass, re-generated per frame.
- **What to take:** A UX pattern: first-frame brush plus tracking, if we ever support moving objects.

### [UniVST: Training-free Localized Video Style Transfer (TPAMI 2025)](https://arxiv.org/abs/2410.20084) (2024-10 (v5 2025-11))
*paper · evidence: read · relevance 3/5*

- **What:** Diffusion stylisation of the main masked object in a video. Mask propagation by point matching on DDIM-inversion features, AdaIN in latent and attention space, and flow-based sliding-window smoothing. Code at github.com/QuanjianSong/UniVST.
- **Relevance:** Concept B: localized style for video with diffusion. It styles the object, the inverse of our 'keep the person' design.
- **How we differ:** Styles the moving foreground; heavy GPU inversion. We style the static background once.
- **What to take:** Its mask propagation idea could help if the camera moves later (Ray-Ban roadmap).

### [StreamDiffusionTD in TouchDesigner with person masks (Derivative tutorials)](https://derivative.ca/community-post/using-streamdiffusion-touchdesigner/71576) (2024-2026)
*tutorial · evidence: snippet · relevance 3/5*

- **What:** The usual installation stack: StreamDiffusion (DotSimulate TOX) plus MediaPipe or Apple Vision person masks; masks are combined with multiplyTOP and compositeTOP. I found no documented recipe for 'diffuse only the background, keep the person real'.
- **Relevance:** Concepts C/D: the toolset an installation artist would use to make our kiosk. It is a plausible rival build, but none was found.
- **How we differ:** Per-frame diffusion on a GPU, so the world flickers. Ours is generated once.

### [Groove Jones: 'Not all AI mirrors are the same' / FitCheck Magic Mirror](https://www.groovejones.com/not-all-ai-mirrors-are-the-same) (2025)
*post · evidence: snippet · relevance 2/5*

- **What:** An agency explainer that sorts event AI mirrors into kinds; some 'behave like a live mirror, changing a participant's appearance as they move'.
- **Relevance:** Concept D: confirms that the market changes the person, the inverse of ours.
- **How we differ:** They change the visitor; we keep the visitor and change the room.
- **What to take:** Positioning: 'mirrors restyle you; we restyle the room and keep you'.

### [Kapwing guide: 'Falling through Instagram' trend](https://www.kapwing.com/resources/how-to-do-the-falling-through-instagram-trend/) (2025)
*tutorial · evidence: snippet · relevance 2/5*

- **What:** Start in the real world, fall through the screen, then drop through a series of posts, each turning you into a different AI style. Made by generating the AI worlds after the real opening segment.
- **Relevance:** Concept F: a viral 'real, then many AI worlds' format.
- **How we differ:** Sequential, and it restyles the person. Ours is simultaneous worlds in one frame with the person real.
- **What to take:** A demo-video structure: a real opening, then cascade through the worlds.

### [Dreamina (CapCut) 'How to mask part of a video for AI editing' (Seedance 2.5)](https://dreamina.capcut.com/ai-video/how-to-mask-part-of-a-video-for-ai-editing) (2026)
*tutorial · evidence: snippet · relevance 2/5*

- **What:** A masking workflow for AI video edits: keep the mask tight, shrink it if too much changed, grow it if seams remain. Vague prompts restyle the whole scene.
- **Relevance:** Concept B/F: a CapCut-family masked regional AI edit.
- **How we differ:** One edit per pass, made by the generator; no zones that people trigger.

### [Bharat-style per-frame student baselines: 'Paint your Zoom Background' (UW CS639) and Stanford CS231N background-inpainting report](https://cs231n.stanford.edu/papers/text_file_840579931-CS231N_Final_Report.pdf) (unknown (CS231N report, likely 2024-2025))
*paper · evidence: snippet · relevance 2/5*

- **What:** The snippet describes background inpainting that produces a clean, temporally consistent background and notes that static backgrounds are a known problem for video diffusion. I could not open it.
- **Relevance:** Concept E: the nearest student work; per-frame or video-diffusion pipelines.
- **How we differ:** No once-per-world restyle and no zones (as far as visible).
- **What to take:** A human should open the PDF and cite it if it is close.

### [US patent 12205254 'AI-driven video stylization with text description tuning' and US 12333637 'AI-driven foreground stylization using diffusion and object detection'](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12205254) (2025 (grant year uncertain))
*other · evidence: snippet · relevance 2/5*

- **What:** Snippets: a latent diffusion model applies stylisation only to the masked part of a frame, leaving the rest unchanged. The second patent stylises the main object and keeps the background.
- **Relevance:** Concept A/B: patents on masked diffusion stylisation of video.
- **How we differ:** Generic masked stylisation per frame; no static plate and no zones that people trigger.
- **What to take:** Mention it only if asked; this is not legal advice.

## Ideas to borrow

- **Use the first-down line as the one-sentence explanation in the 2-minute talk: the worlds are painted under the people, never on them, with the same per-pixel 'ground or person' decision, and the same failure when people look like the ground.** Source: Sportvision 1st & Ten, https://entertainment.howstuffworks.com/first-down-line.htm. Everyone has seen it, it is honest about the precedent, and it explains the w-mask times person-mask composite in five seconds. *Effort: hours; slide only*
- **'Coherent paint' mode: turn the painted world masks into one colour-coded mask and run a single regional img2img+ControlNet pass on the plate (Regional Prompter or ComfyUI mask conditioning), so the borders between worlds are generated together rather than cut.** Source: hako-mikan/sd-webui-regional-prompter https://github.com/hako-mikan/sd-webui-regional-prompter; MAST https://arxiv.org/abs/2604.12281. Fixes hard seams between separately generated worlds and lets us compare 'run-time switch' against 'generation-time regions' as an ablation in the report. *Effort: days; works on CPU with SD 1.5 at a few minutes per image*
- **Replace or back up the temporal median with the LTX-2.3 Clean Plate IC-LoRA when people linger or cast shadows that stay in the plate; show a side-by-side figure of the two plates.** Source: LTX Clean Plate IC-LoRA, https://comfyui-wiki.com/en/news/2026-07-19-ltx-2-3-clean-plate-ic-lora. Fixes a known weak point (dirty plates) and is a clear state-of-the-art comparison for the report. *Effort: a day; free Colab GPU, ComfyUI*
- **Offline person mattes for uploaded clips with SAM2 plus MatAnyone, used instead of colour difference.** Source: MogensR VideoBackgroundReplacer Space, https://huggingface.co/spaces/MogensR/VideoBackgroundReplacer. Our masks are the roughest part (fringes, trails, shadows). The Space shows the stack and has a CPU fallback. *Effort: days; Colab GPU recommended*
- **A painting UX like Krita AI Diffusion's Regions: one layer per world with a live preview while painting, plus per-layer opacity or feather.** Source: Acly/krita-ai-diffusion, https://github.com/Acly/krita-ai-diffusion. A mature, open UX for exactly our painted-regions interaction; easy to borrow. *Effort: hours to days; front end only*
- **A 'checkerboard of worlds' preset: a grid of painted tiles, each a different world, so a walker hops between worlds tile by tile.** Source: NYU ITP Interactive Sound Walk (2015), https://itp.nyu.edu/shows/winter2015/interactive-sound-walk/; Stephen Wilkes's wish to 'checkerboard time'. A striking demo shot that shows the crossing rule many times in one clip, with clear precedents to credit. *Effort: hours*
- **A demo video shaped like the 'falling through' and portal trends: open on the real Sather Gate shot, then a person walks through painted zones and each step changes world. Point out on screen that the place and the person stay real.** Source: Kapwing falling-through guide https://www.kapwing.com/resources/how-to-do-the-falling-through-instagram-trend/; Morphic portal https://morphic.com/resources/vfx/portal-transition-effect. The audience already knows the format, so the difference (real person, real place, live) shows up at once. *Effort: days; filming plus export*
- **Name AnyPortal (with IC-Light) as the relighting upgrade in Future Work, and say plainly that we only colour-match.** Source: AnyPortal ICCV 2025, https://arxiv.org/abs/2509.07472. Shows the team knows the current best method for the people-in-new-background problem without overclaiming. *Effort: hours; writing*
- **Cite Xia et al. 2020 as the ancestor of the Paint tool and borrow its 'styles transition over time' framing for Morph inside painted regions (a region grows in while others hold).** Source: https://arxiv.org/abs/2010.10056. It is the closest work to B; citing it heads off a 'this exists' objection. *Effort: hours*

## Not reached or not verified

- blog.siggraph.org was blocked: the SIGGRAPH 2026 Real-Time Live demo that changes backgrounds live from text prompts needs its title and a check of the video. Also check the SIGGRAPH 2024-2026 Emerging Technologies and Art Gallery listings by hand.
- Ars Electronica 2024-2026: only JKU and festival snippets (Digital Shadows, Egovatar, Spot On); none fits. Search ars.electronica.art/archive for 'diffusion', 'mirror' and 'clean plate'.
- CVPR AI Art Gallery 2024-2026 and NeurIPS Creative AI track: not searched individually (ran out of budget). Check thecvf-art.com and the NeurIPS creative AI gallery.
- Course galleries (concept E): no Berkeley CS180/CS194-26 final-project gallery surfaced; searches returned only Project 5 pages. CMU 16-726, CS348K, MIT 6.8300, Brown 1290/1430, UIUC CS445 and Cornell CS5670 galleries were not found. Search each course site for 'final project' plus 'median background' or 'stylize background'.
- contra.com 'Dual World AI Transformation' (Aya Ahmed) was blocked; the title suggests half-real, half-AI in one frame. Check it by hand.
- cs231n.stanford.edu was blocked: open the CS231N background-inpainting report and read its pipeline.
- Inside the TikTok, Instagram and CapCut apps: search 'half AI', 'AI world split', 'walk into anime world', 'real vs AI line', 'portal step' and 'AI background only'. Also search Effect House for effects that segment the person and run an AI style on the background. Web search cannot see effect galleries.
- Reddit r/StableDiffusion, r/comfyui and r/TouchDesigner, and X: search 'clean plate restyle', 'background only StreamDiffusion' and 'masked worlds'. Not searched.
- Video-analytics 'line crossing' (Hikvision and others) and virtual-production set extension are from memory and were not fetched; they are only analogies for the idea, so low risk.
- FXjutsu and Teams were not re-checked this round; their evidence levels come from novelty_audit.md.

## Notes

## Verdicts by concept

**A. Fixed camera, clean plate, plate restyled once, people composited back: FOUND (as an idea and as products). Our exact chain (temporal median, one SD 1.5 + ControlNet image per world, per-pixel composite in WebGL) was NOT FOUND as a public repo, but it is easy to assemble.**
- Already known: Teams Decorate (2023-24) and FXjutsu Toon World (2026).
- New this round:
  - ComfyUI official templates: MiniMax H3 background restyle from a guide image, and Bria 'change a video's background' with a 'keep subject, pose, timing' prompt ([comfy.org hub](https://comfy.org/hub/workflows/minimax-h3-video-restyling-58a3f7167dba/), [change-video-background](https://comfy.org/hub/workflows/change-video-background/)) [snippet].
  - LTX-2.3 Clean Plate IC-LoRA, July 2026 ([comfyui-wiki](https://comfyui-wiki.com/en/news/2026-07-19-ltx-2-3-clean-plate-ic-lora); hosted on [floyo](https://floyo.ai/workflows/ltx-2-3-clean-plate-video-object-rem-eghzhqjdqljh)) [snippet].
  - AnyPortal, ICCV 2025, which claims precise foreground preservation ([arXiv 2509.07472](https://arxiv.org/abs/2509.07472)) [fetched].
  - FRESCO's 'background smoothing' for static backgrounds and StableVideo's background atlas ([FRESCO](https://github.com/zhangyuqiang/fresco)) [snippet].
- Queries tried: ComfyUI restyle background keep person clean plate 2026; GitHub "clean plate" stable diffusion restyle composite static camera; HF Space video background restyle keep person.
- Left for us: the plate is the free temporal median, and each world is one image (so it cannot flicker), generated on a CPU. These are the substrate for the zones, not the claim.

**B. Paint or mask regions; each region a different AI style or world; people kept: PARTLY.**
- Prior work by medium:
  - Video, non-diffusion: Xia et al. 2020, user scribbles, several styles on several objects, real time ([arXiv 2010.10056](https://arxiv.org/abs/2010.10056)) [fetched].
  - Video, diffusion, one object: UniVST (TPAMI 2025) ([arXiv 2410.20084](https://arxiv.org/abs/2410.20084)) [fetched].
  - Images, several regions: MAST (April 2026) ([arXiv 2604.12281](https://arxiv.org/abs/2604.12281)) [fetched]; Regional Prompter and ComfyUI mask conditioning [snippet]; Krita AI Diffusion 'Regions' plus 'Live painting with regions' ([GitHub](https://github.com/Acly/krita-ai-diffusion)) [fetched].
  - Consumer video, brush to protect a region and restyle the rest: OpenArt (Beeble SwitchX), Dreamina/Seedance 2.5 [snippet].
- NOT FOUND: painted regions of a fixed scene, each showing a different pre-generated, pixel-aligned world, live, with people kept real and switching world as a whole by the region at their feet.
- Queries tried: regional style video mask paint; masked region-wise video stylization multiple styles; multi-region prompt img2img paint masks video ComfyUI; brush mask restyle part of video 2026.

**C. Zone- or line-triggered change; broadcast graphics under people: PARTLY (non-generative ancestors are strong).**
- First-down line (ESPN, 27 Sep 1998). It keys graphics onto turf pixels only and is skipped when mud makes players look like turf ([HowStuffWorks](https://entertainment.howstuffworks.com/first-down-line.htm)) [snippet]. This is the same per-pixel test as ours, with the same failure mode.
- Virtual perimeter ads (Supponor/TGI with IR boards plus AI keying; AIM Sport for all Euro 2024 matches) ([heise](https://heise.de/-9794857)) [snippet].
- ITP 2015: a 5x5 grid of floor tiles, each a different environment, Kinect-tracked ([ITP](https://itp.nyu.edu/shows/winter2015/interactive-sound-walk/)) [snippet].
- No installation found where entering a zone restyles the person. Video-analytics 'line crossing' and weather-map chroma key are from memory.
- Queries tried: Kinect floor zone triggered style; TouchDesigner StreamDiffusion background only person mask; Sportvision keying occlusion; virtual advertising occlusion keying.

**D. Kiosks and installations 2024-2026 showing visitors, unaltered, inside an AI-restyled copy of the real room: NOT FOUND (weak search).**
- SIGGRAPH 2026 Real-Time Live had a 'real-time camera system that responds to text prompts' to change avatars and backgrounds [snippet, page blocked].
- The 2026 Art Gallery had 'Diffusion TV' [snippet].
- Ars Electronica 2025 had Digital Shadows and Egovatar, which make AI portraits of the visitor [snippet].
- Brand AI mirrors (Atomic Digital for PSG in 2025: 6,000 sessions, 50-s average; Groove Jones) change the visitor or the environment, mostly per frame or as AR [snippet].
- RoomAlive (2014) restyles the actual room with projectors.
- Queries tried: SIGGRAPH 2026 RTL generative mirror room; Ars Electronica 2025 AI room visitors; brand activation AI mirror restyles surroundings.

**E. Student projects: NOT FOUND.**
- The Berkeley search returned only Project 5 (DeepFloyd) pages.
- Earlier neighbours: UW CS639 'Paint your Zoom Background' and the AI 535 report (from the earlier audit), plus a Stanford CS231N background-inpainting report [snippet, blocked].
- Note: the team's own repo (garysun1/CS-180-Final-Project) may show up in searches; it is not prior art.

**F. TikTok, CapCut and Instagram templates that mix real and AI in one frame: PARTLY.**
- Portal templates: Morphic ('walks into a glowing ring and the world behind them changes'), Magicshot 'Portal Step', Magic Hour 'Portal Walk' [snippet].
- The Instagram 'falling through' trend ([Kapwing](https://www.kapwing.com/resources/how-to-do-the-falling-through-instagram-trend/)) [snippet].
- A Media.io-listed CapCut template that 'keeps the person recognizable while transforming the background' [snippet].
- All of them regenerate the whole frame and usually the person. They are transitions in time, not lasting regions in space.
- Not checked inside the apps.

## What Cross the Line still adds (as of 27 Nov 2026, hedged as 'we did not find')
1. **Lasting spatial rules over one pixel-aligned pair.** A line, a ring, a depth threshold, or hand-painted masks with several worlds at once choose per pixel between the real frame and a restyled copy of the same place. Rivals regenerate a whole frame or change the person.
2. **People switch as a whole by the region under their feet.** This combines the first-down-line keying logic with Hoiem-style ground contact. I found it nowhere, generative or not.
3. **Cheap and live.** One generation per world on a CPU, then compositing at camera rate in a browser. AnyPortal, LTX, MiniMax and Aleph need a GPU and minutes per clip.

## Claims to avoid after this round
- 'Paint different AI styles onto regions' as new: Xia 2020, MAST 2026 and Krita Regions exist.
- 'AI background with real people' as new: Teams, ComfyUI templates, AnyPortal and FXjutsu exist.
- 'Step into another AI world' as new: Morphic and Magicshot portal templates are mainstream.

## Safe phrasing for the Paint tool
"Painting regions with different styles exists for still images (MAST, Krita AI Diffusion, Regional Prompter) and for per-frame video stylisation (Xia et al. 2020). We paint where pre-generated, aligned worlds show over a live fixed-camera feed. People stay real and take on the world of whatever region they step onto, like the first-down line drawn under the players."
