# Let your audience step across the line

The single best upgrade for Cross the Line is to turn the project's own thesis into a live, laptop-only portal. Capture the empty poster-session booth, restyle that one plate ahead of time, then composite visitors live with an in-browser person segmenter and a WebGL2 shader, so anyone who steps over a taped floor line walks into 1925 or a Van Gogh night at full resolution with no flicker. Every part of that stack is mature and free: MediaPipe's 0.25 MB Selfie Segmenter, WebGL2 in every browser, and `requestVideoFrameCallback` in all engines. The AI "magic mirrors" it competes with restyle every frame with diffusion (a common toolchain runs SD-Turbo at 512×512) and flicker, which gives the team a ready-made live foil. The research found no open-source browser demo that puts a diffusion-restyled plate behind a live segmented person, so the kiosk is plausibly novel as well as engaging, though absence of evidence is not proof. Around that centerpiece, the most wow per hour comes from cheap moves that reuse existing assets:

- a baked-mask WebGL player on the website;
- a synchronized grid comparing against flickering baselines, with one stability number;
- per-world "people rules" borrowed from *Across the Spider-Verse*;
- a real 1910s Sather Gate archive photo used as a world, aligned by homography;
- a "step into the painting" 2.5D shot.

The presentation research agrees on the playbook. Make video the backbone of the short talk. Run the live kiosk at the poster session on a rehearsed "golden path," with a one-key fallback to a recorded run. Have a teammate keep crossing the line to draw a crowd. Post a sign that the camera is live and nothing is saved. Effort and frame-rate estimates below are the research team's inferences unless a source is cited. Several vendor figures (StreamDiffusionV2 speed, Runway and Nano Banana Pro pricing, FLUX.2 Klein VRAM, the SHARP license) come from secondary or search-snippet-only sources and need checking before they go on a slide.

## Twelve ideas ranked by engagement per day of work

The ranking weighs three things. Does the viewer's own body or hand drive the effect, and does it reinforce the "restyle once, cannot flicker" claim? Can two or three students build it in two to three weeks? How likely is it to fail in front of an audience? Build order differs from rank: idea #2 should be built first, because its shader is the kiosk's engine and it is the safest thing to show at a check-in.

| # | Idea | Why it engages | Effort (team-days, inferred) | Compute | Main risk |
|---|---|---|---|---|---|
| 1 | **Live "restyle-once" portal kiosk.** Empty-booth plate → pre-restyled worlds → MediaPipe person mask → WebGL2 composite at a taped floor line, with world-picker hotkeys | The visitor's own body triggers the swap. Full resolution and flicker-free, unlike per-frame AI mirrors. Draws a crowd | 5–7 (after #2) | Laptop + USB webcam, offline, no GPU server | Auto-exposure drift, soft mask edges, venue lighting |
| 2 | **WebGL2 web player** with offline masks baked into the video; line, depth and portal controls on drag; world picker | Anyone who scans the QR code drives the real result on their phone. It teaches the method | 2–4 | None (static site) | iOS autoplay and encoding quirks |
| 3 | **Synchronized baseline grid** (per-frame image edit, open video editor, Runway Aleph, ours) with one stability number and seam crops | Shows the thesis in three seconds. Provides the quantitative result the grade depends on | 3–5 | GPU hours plus about $3 per 10 s Aleph clip (secondary price) | GPU access; over-claiming the metric |
| 4 | **Per-world "people rules"** plus a Spider-Verse glitch on the person layer, with the cheap ones ported to the kiosk shader | The person visibly transforms at the line ("the content is you") | 2–4 | CPU (NumPy/OpenCV) plus shader | Effects pile up and bury the seam story |
| 5 | **Film-borrowed trailer beats:** verse-jump montage, expanding split, endless push-in, reach-across hand, cinemagraph freeze, multiverse crowd | Cheap, shareable shots, because all plates share geometry | 0.5–1 each | CPU | Time sink; cap at two or three |
| 6 | **Real 1910s Sather Gate archive world**, rephotographed from a matched vantage; "which is real?" vote against the AI 1920s | Local history and real time travel, with a game built in | 2–3 plus the shoot | None | Vantage can't be reproduced; rights and dates need checking |
| 7 | **"Step into the painting" 2.5D:** SHARP splat or depth-layer parallax of the restyled plates; head-coupled parallax at the kiosk | The camera seems to move inside a still world | 2–5 | One GPU pass per plate | Tearing on large moves; SHARP license unconfirmed |
| 8 | **Sound that follows the line:** crossfade room tone into a world pad as people cross; a whoosh on every crossing | A second sense; the aisle hears crossings before seeing them | 1–2 | None | Browser audio unlock; booth noise |
| 9 | **Live per-frame diffusion foil pane** (StreamDiffusion + SD-Turbo) beside the kiosk | The thesis as a live A/B experiment | 2–4 | RTX 4090-class GPU on site | Highest hardware and setup risk |
| 10 | **Relight walkers** into night or Van Gogh with IC-Light on keyframes plus a per-person color transform | Fixes the "sunlit person in a night world" failure | 3–5 | GPU, seconds per frame (inferred) | Flicker, identity drift |
| 11 | **Mobile "portal you hold up" page** via QR code | Visitors take the effect home | 2–3 after #1 | Phone | Device variety; iOS permission prompts |
| 12 | **Opt-in "save my crossing" clip** plus a "blur me" toggle | A shareable keepsake that respects privacy | 1–2 | Needs storage | Data handling; breaks the no-backend design |

A plausible three-week schedule follows. It assumes check-ins fall in late November and the final presentation and poster session in the second week of December; the exact dates were not in the research notes. Thanksgiving falls on Thursday, November 26, 2026, which compresses week two.

| Window | Build | Show |
|---|---|---|
| Nov 19–25 | Film Sather Gate (tripod clip, archive-matched vantage, optional 20–30 s handheld orbit for a splat). Build the #2 shader with baked masks. Start the editor tournament (#3) | Check-in: the web player running on real footage, plus the seam chart across editors |
| Nov 26–Dec 2 | Kiosk (#1), people rules (#4), baseline grid runs (#3), audio (#8) | A recorded kiosk run through the same code, which doubles as the fallback |
| Dec 3–final | #6 or #7 if ahead; trailer v2 and a 2–3 min main video; poster; rehearse the golden path five times; signage | Talk led by video; live kiosk at the poster session |

## A restyle-once webcam portal runs on one laptop

The kiosk is feasible because the project's central trick moves the expensive step offline. Restyling a plate takes seconds to minutes on a GPU, but it happens once. The live loop only needs a person mask and a blend of three or four textures, which is a trivial fragment shader on any GPU from the last decade (inference). Write that shader for **WebGL2, not WebGPU**. WebGPU now ships by default in desktop Chrome (since 113), Safari 26 and Firefox on Windows (141) and Apple Silicon Macs. It is still off by default in Firefox on Linux, Intel Macs and Android, and in Chrome on many Linux GPUs ([gpuweb implementation status](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status)). WebGL2 runs everywhere, and Google Meet's production background effects use it for mask refinement and compositing ([Google Research](https://research.google/blog/background-features-in-google-meet-powered-by-web-ml/), via search snippet). Drive frame updates with `requestVideoFrameCallback`, which now ships in **all engines: Chrome 83, Safari 15.4 and Firefox 132** ([web-features explorer](https://web-platform-dx.github.io/web-features-explorer/features/request-video-frame-callback)).

For the website player, bake the offline masks into the same video file, with color in the top half and mask in the bottom half. One `<video>` element then keeps color and mask frame-locked, with no ML in the browser and no browser-specific alpha-video codecs (inference). Swap the video texture for a webcam texture and the same shader becomes the kiosk. Several of the prototype's NumPy styles (night, century, comic halftone) can be ported to GLSL as model-free emergency worlds. three.js (`three@0.187.0`, MIT) is the natural host if splats come later ([npm](https://www.npmjs.com/package/three)).

For live segmentation, **MediaPipe Tasks Vision's Image Segmenter with the Selfie Segmenter model** is the default. The package is Apache-2.0 at version 1.2.3, published November 11, 2026 ([npm](https://www.npmjs.com/package/@mediapipe/tasks-vision)). The model file is **249,537 bytes** ([model URL](https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite)), and a 144×256 landscape variant exists for webcam-shaped input ([MediaPipe guide](https://ai.google.dev/edge/mediapipe/solutions/vision/image_segmenter), via search snippet). Speed evidence is indirect. Google's table puts the model at about 33–35 ms on a Pixel 6, but those are native numbers and the snippet's column labels were ambiguous. Meet's 2020 web stack ran a 256×144 model at **120 fps inference and 70 fps end to end on a 2018 MacBook Pro** ([Google Research](https://research.google/blog/background-features-in-google-meet-powered-by-web-ml/)). The team should therefore expect 30 fps or more on a recent laptop (inference) and confirm it by logging `performance.now()` around each segmentation call.

One vendor blog says MediaPipe's in-browser GPU delegate runs on WebGL2 rather than WebGPU ([Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/mediapipe-selfie-segmentation-webgpu-background-blur)). Treat that as unverified. If hair edges look poor against a stylized plate, MODNet through transformers.js gives softer mattes. It weighs **6.6 MB quantized to 25.9 MB fp32** ([Hugging Face](https://huggingface.co/Xenova/modnet)), and Xenova's live WebGPU demo runs it at 256 px ([HF Space](https://huggingface.co/spaces/Xenova/webgpu-video-background-removal)). Feature-detect `navigator.gpu` and fall back to MediaPipe when it is missing. Skip BodyPix (deprecated) and RMBG (44–176 MB under BRIA's license; [Hugging Face](https://huggingface.co/briaai/RMBG-1.4)).

The camera's own automatic adjustments are the main live risk. `getUserMedia` works only in a secure context. Chrome treats `http://localhost` as secure ([discuss-webrtc](https://groups.google.com/g/discuss-webrtc/c/QUdwwa-83K8)), but `file://` is unreliable ([WebKit bug 173457](https://bugs.webkit.org/show_bug.cgi?id=173457)). Serve the kiosk from localhost with every model bundled, which also removes Wi-Fi from the failure list.

Locking exposure and white balance through `applyConstraints` worked, as of 2022, only in Chrome on Windows, Linux and Android, "depending on OS, browser, camera and driver" ([webrtcHacks](https://webrtchacks.com/?p=3807)). A pure "clean plate minus frame" difference will therefore drift as the webcam re-exposes. The robust recipe, all inference:

- Ask everyone to step out of frame for about two seconds and take the median of about 30 frames as the plate.
- Compute the foreground as `fg = max(segMask, smoothstep(t0, t1, length(cam - plate)))`, so the segmenter does most of the work and the difference term only patches holes.
- Match the live frame's global brightness to the plate.
- Smooth the mask over time with an exponential moving average.
- Optionally reuse the offline pipeline's shadow ratio (`cam / plate`, clamped) in a band below each person's feet, so shadows carry into the new world.

The restyled worlds need the booth plate before doors open. If the room is accessible in advance, photograph it from a taped tripod mark and restyle offline. If not, run one edit on site and then go offline. That means FLUX.2 Klein 4B on a GPU laptop, or a single Nano Banana call at about **$0.039 per image** ([Google Developers Blog](https://developers.googleblog.com/en/introducing-gemini-2-5-flash-image/)). Always carry the shader-only worlds as insurance (inference).

Interaction design should make the rule readable from the aisle. Tape the line on the floor where it matches the in-frame line. Let each visitor pick a world from hotkey cards. Offer depth mode as a second rule.

For depth, the cheapest live version uses MediaPipe pose or face landmarks (apparent shoulder width) as a per-person depth proxy and switches that person's whole mask between worlds. This is a design suggestion that nobody has benchmarked. Depth Anything V2 Small on WebGPU works but costs more. It weighs 19–99 MB depending on precision, and only the Small model is Apache-2.0; Base and Large are CC-BY-NC ([Hugging Face](https://huggingface.co/onnx-community/depth-anything-v2-small)). One write-up reports **8–24 fps** depending on input size, and its faster modes interpolate between depth samples ([DEV Community](https://dev.to/martindelophy/video-depth-estimation-in-the-browser-building-with-webgpu-and-depth-anything-v2-4o0m)). One open-source "volumetric mirror" author expects about 18 fps with WebGPU and about 1 fps without it, an expectation rather than a benchmark ([Depth Twin](https://github.com/allansli/depth-twin/pull/1)). Per-frame depth also flickers, so it belongs in the stretch tier.

For phones, a plain HTTPS mobile page using the same shader beats AR frameworks. iOS Safari has no WebXR through 27.2 ([caniuse](https://github.com/Fyrd/caniuse/blob/main/features-json/webxr.json)). 8th Wall's hosted platform stopped logins on **February 28, 2026**, and existing hosted projects go dark in February 2027 ([8th Wall FAQ](https://www.8thwall.com/docs/migration/faq/)). Snap Camera Kit is proprietary and needs a developer token ([npm](https://www.npmjs.com/package/@snap/camera-kit)).

The pitch at the booth writes itself. AI-era mirrors such as *STOCHASTIC MAN* (2024, three CRTs, each showing the viewer in a different painting style; [artist site](https://stochastic-man.cargo.site)) and *Mirror 3* at Burning Man 2025 ([gallery](https://gallery.burningman.org/asset/a24b9542-106f-4c3e-8cf8-00dc79734b66?i=1174&q=1)) run per-frame diffusion. A common toolchain for such mirrors, StreamDiffusion inside TouchDesigner, reports **55–60 fps with SD-Turbo at 512×512 on an RTX 4090** ([TouchDiffusion](https://github.com/olegchomp/TouchDiffusion)). Cross the Line delivers its world at full resolution, and the world is pixel-stable because it was generated once.

Two forkable starting points exist: Xenova's real-time WebGPU depth and background-removal Spaces, and the [Volcomix virtual-background](https://github.com/Volcomix/virtual-background) WebGL2 pipeline. No existing open demo was found that wires a generated plate behind a live segmented person, so the team would be first in that niche, at least among public repos.

## Per-frame diffusion's flicker becomes your best live foil

The project's claim is comparative: one still cannot flicker, and per-frame restyling does. The most persuasive demo puts both on screen at once. StreamDiffusion v1 runs SD-Turbo img2img at **93.90 fps on an RTX 4090** (with a Core i9-13900K) ([GitHub](https://github.com/cumulo-autumn/StreamDiffusion)). Its "Stochastic Similarity Filter" cuts GPU load but does not enforce temporal consistency, so a webcam pane through it flickers visibly. Next to the kiosk pane, visitors would see their reflection boil on one side and stay rock-steady on the other (inference). Fixed seeds, img2img strength around 0.3–0.5, a ControlNet and an exponential moving average over output frames reduce that flicker but do not remove it (inference).

Avoid the heavier real-time video models. StreamDiffusionV2 is temporally coherent, but its only published speeds, **58–65 fps, are on four H100s**, with no single-GPU figure ([arXiv 2511.07399](https://arxiv.org/html/2511.07399v1)). Krea Realtime 14B reaches 11 fps on one B200 ([Krea](https://www.krea.ai/blog/krea-realtime-14b)). If the team uses ComfyStream instead, its first TensorRT engine build takes 2–10 minutes, so build it before doors open ([Livepeer docs](https://docs.livepeer.org/v2/developers/build/ai-and-agents/realtime-ai/comfystream/overview)). Without a 4090 the foil pane should be pre-recorded through the same webcam and labeled as such. A Colab T4 would likely manage only single-digit to low-teens fps (inference).

The offline version of this argument is the evaluation centerpiece and costs little. Take one 5–10 s Sather Gate clip and one prompt ("winter night") and run four methods side by side, each with the same people pasted back:

1. Per-frame image editing (FLUX.2 Klein or SD-Turbo), for maximum flicker.
2. An open video editor. Wan 2.1 VACE 1.3B runs 10 s of 480p in **under 12 GB of VRAM via Wan2GP on a 4090** ([Wan2GP](https://github.com/LifeDepot/Wan2GP)). Lucy Edit Dev is an open-weight Wan2.2 5B editor that works best up to about 81 frames at 480p or 720p ([Hugging Face](https://huggingface.co/decart-ai/Lucy-Edit-Dev)).
3. Runway Aleph 2.0, at about **$0.28 per second up to 30 s at 1080p**. That price comes from secondary pricing guides and needs checking against Runway's own page ([Dupple](https://dupple.com/learn/runway-pricing)).
4. The project's composite.

The contrast is strong and specific. Open video editors top out around 480–720p and roughly 81 frames per pass, while the one-still method works at 4K for any clip length (inference from the stated limits). Older zero-shot methods such as TokenFlow ([arXiv 2307.10373](https://arxiv.org/abs/2307.10373)) and Rerender-A-Video ([arXiv 2306.07954](https://arxiv.org/abs/2306.07954)) can stand in if GPU time runs short.

Report stability with a number people can trust, and say plainly why yours is near zero. The standard temporal metric is Lai et al.'s **warping error**: warp frame t+1 onto frame t with optical flow and average the squared difference over non-occluded pixels. Pair it with a perceptual distance, because a blurry video also scores well on warping error ([arXiv 1808.00449](https://arxiv.org/pdf/1808.00449)). It also inherits optical-flow errors ([BlazeBVD, arXiv 2403.06243](https://arxiv.org/pdf/2403.06243)).

A cheaper, more legible number exists for this project. The median-background step already tells you which pixels should be static, so compute the frame-to-frame standard deviation on those pixels for each method (inference). Frame the result honestly: "near zero by construction; the trade-off is no camera motion and no scene-reactive lighting."

Turn the metric into pictures for the poster:

- A zoomed crop of a building edge crossing the line, before and after alignment, with the pixel jump annotated.
- An x–t slice: one pixel row stacked over time. The baseline shows streaky noise and the method shows clean vertical stripes. This is standard video practice, but no source was retrieved.
- The identity check: people composited onto the unedited plate should reproduce the input.
- An informal two-alternative forced-choice poll of about 10 classmates, reported with its n.
- A failure gallery of three to five GIFs with one-line causes, such as stationary people absorbed into the median, shadows crossing the line, or editors inventing geometry.

The editor choice can itself become a measurable mini-result, because no rigorous benchmark of geometry preservation across image editors turned up. Two open candidates lead. **Qwen-Image-Edit-2511** (Apache-2.0, December 2025) explicitly targets consistency and "mitigat[ing] image drift" ([Hugging Face](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)), but at 20B parameters it needs quantization and offloading on consumer GPUs ([ComfyDeploy](https://studio.comfydeploy.com/news/flux-kontext-dev)). **FLUX.2 Klein** was released January 15, 2026. Its **4B model is Apache-2.0 and its 9B model uses the FLUX Non-Commercial License** ([VentureBeat](https://venturebeat.com/technology/black-forest-labs-launches-open-source-flux-2-klein-to-generate-ai-images-in)). The proposal's planned 9B is therefore fine for coursework but not for reuse. Black Forest Labs' own pages give conflicting 4B VRAM figures, about 8 GB versus about 13 GB.

One informal comparison found FLUX.1 Kontext "only change[s] what you tell it to" while Qwen "takes a much freer approach" ([Diffusion Doodles](https://diffusiondoodles.substack.com/p/qwen-image-edit-vs-flux1-kontext)). That test used the original Qwen-Image-Edit, not 2511. Adding Nano Banana Pro as the closed comparator costs about $0.134 per image (a third-party figure; [YingTu](https://yingtu.ai/blog/nano-banana-pro-api-pricing-per-image)). At that price, ten worlds times five tries comes to roughly $7, so the whole tournament costs less than a lunch (inference).

## Borrowed rules from art, film and the archive give each world a story

### Installations teach one frame, one rule, one body

The most memorable precedents each pair a physical frame with a single rule that the visitor's body triggers:

- *Rain Room* switches off the water in roughly a six-foot radius around each visitor ([My Modern Met](https://mymodernmet.com/random-international-rain-room)).
- *Text Rain* (1999) lets letters "land" on anything darker than a threshold ([Camille Utterback](https://camilleutterback.com/projects/text-rain/)).
- Daniel Rozin's mechanical mirrors embody his line "the contents of the piece is you" ([Dezeen](https://www.dezeen.com/2014/02/21/mechanical-mirrors-by-daniel-rozin-replicate-images-using-everyday-objects/)).
- *The Portal*'s round concrete doors have linked Vilnius and Lublin live since May 2021, and New York and Dublin since 2024 ([Wikipedia](https://www.wikipedia.org/wiki/Portal_(sculptures))).

Each lesson maps directly onto the kiosk (inference). A cardboard ring or bright floor tape borrows the Portal's doorway framing. Depth mode is Text Rain's rule restated ("anything nearer than d stays real"), so show the depth map as a small live inset to make it legible. Rozin argues for keeping the world still and transforming only the visitor. Lozano-Hemmer's *Redundant Assembly*, which merges several visitors' faces into one portrait ([arXiv 2004.09685](https://arxiv.org/pdf/2004.09685)), suggests giving each passer-by in the tripod footage a different world, turning the crowd into a multiverse.

### Across the Spider-Verse already wrote the per-world rulebook

The trailer's glitch climax can go further, because the Spider-Verse look is a short list of rule-based print tricks:

- chromatic aberration that mimics press misregistration;
- halftone dots in highlights and hatching in shadows;
- switching between animating "on ones" and "on twos";
- design-driven, rather than simulated, glitch fractures that hit buildings and cars as well as characters.

These points come from search summaries of fxphd and SideFX coverage; the full articles could not be fetched ([fxphd](https://www.fxphd.com/fxblog/spider-verse-at-siggraph/); [SideFX](https://www.sidefx.com/community/spider-man-into-the-spider-verse/)). The sequel gave each universe its own art style, and producers announced six distinct styles ([AWN](https://www.awn.com/news/spider-man-across-spider-verse-feature-six-different-art-styles)). That is exactly the project's "match people to the world" option, and the prototype already has a `matched` person style and a halftone comic style to build on.

Concrete per-world people rules follow (inference). They take two to four days in NumPy, and the cheap ones port to the kiosk shader:

| World | Rule for people |
|---|---|
| 1920s | Sepia, grain, an 18 fps step and gate weave |
| Van Gogh | On twos, plus brush texture |
| Night | Darker, with a neon rim |
| Cyberpunk | Chromatic aberration and scanlines |
| Winter | Desaturated, with breath or snow particles |

Spread the glitch to the buildings next to the person, as the film did.

Film supplies a handful of cheap transitions for the trailer and the main video (all inference about how to borrow them):

- **The *Everything Everywhere All at Once* verse-jump:** the same footstep in six worlds, cut on six consecutive beats. That film's core effects team of about five people delivered close to 500 shots ([Slashfilm](https://www.slashfilm.com/825916/watch-how-vfx-brings-the-multiverse-of-everything-everywhere-all-at-once-to-life)), a useful line about constraints beating budget.
- **The *(500) Days of Summer* split:** the "reality" half slowly takes over the frame ([Lipstick Letters](https://lipstickletters.substack.com/p/truth-and-perspective-in-500-days)). Here the line becomes a beat-synced wipe.
- **The *Take On Me* reach-across** ([Wikipedia](https://en.wikipedia.org/wiki/Take_On_Me)): a hand extends over the line and turns to pencil sketch while the body stays real. This works because the line test is per pixel.
- **The endless push-in:** Paul Trillo's continuous push through eras in the Sora video for "The Hardest Part" drew on about 700 generated clips ([fxguide](https://www.fxguide.com/?p=419437)). A crop-zoom in which each step crosses into a new world gives a similar feel.
- **The cinemagraph freeze:** one passer-by keeps walking while the world and everyone else stop ([Wikipedia](https://en.wikipedia.org/wiki/Cinemagraph)). It reads instantly as time travel.

### A real 1910s Sather Gate beats an imagined 1920s one

The strongest local hook is real history. A 1915 Sather Gate view appears in the Online Archive of California ([OAC](https://oac.cdlib.org/findaid/ark:/13030/kt429003bb/dsc/)). The Berkeley Historical Society holds c.1909–1910 photographs, including a view through the gate south toward Telegraph ([CatalogIt](https://hub.catalogit.app/berkeley-historical-society-museum/folder/entry/university-of-california-28)). Berkeley Lab's "Then & Now" already pairs a 1943 Campanile view with 2018 from the same vantage ([Berkeley Lab](https://history.lbl.gov/then-and-now/)).

The canonical CS citation is Bae, Agarwala and Durand's *Computational Rephotography* (ACM TOG 2010). Their pilot studies found that untrained users could not reproduce a historic viewpoint even with simple visual aids, which is why they built a guided pose-estimation tool ([paper](https://people.csail.mit.edu/soonmin/rephoto/rephoto.pdf)). A light version is easy: show a translucent onion-skin of the archive photo on the camera monitor while framing the tripod, then align with the homography step the pipeline already has (inference). Crossing the line then leads into the actual past. Showing the real archive world next to the AI "1920s" world and asking visitors which is real turns it into a game. Consumer then-and-now apps were "a bit hit and miss" on alignment ([Geography Realm on WhatWasThere](https://www.geographyrealm.com/whatwasthere-augmented-reality/)), which makes a good foil for the project's under-2-pixel seam target.

Two checks are mandatory before anything is printed. Rights: pre-1929 publication is likely US public domain, but each item needs checking. Dates: sources disagree on whether the gate was completed in 1910 or 1913 ([Calisphere](https://calisphere.org/item/5284aa6e7f33a9fc3bd43f3f2327240c)).

### Relighting, splats and sound finish the crossing

**Relighting** fixes the most visible failure, a sunlit person standing in a night world. IC-Light's `fbc` model conditions on text, the cut-out foreground and the background, which here is the restyled world ([GitHub](https://github.com/lllyasviel/IC-Light)). It is SD1.5-based and runs per frame, so it will flicker and drift in identity. The pragmatic route is to relight a few keyframes per person and fit a smooth per-person color and gain transform applied to every frame (inference). TC-Light inflates IC-Light into a video model and optimizes warping error ([arXiv 2506.18904](https://arxiv.org/html/2506.18904v1)). LBM relights in one step but is CC BY-NC ([Hugging Face](https://huggingface.co/jasperai/LBM_relighting)). Classical Reinhard color transfer is the baseline a computational photography course will want to see (inference). Note that IC-Light's bundled BRIA matting is non-commercial; the repo itself recommends BiRefNet instead.

**The "step into the painting" shot.** Apple's **SHARP** (December 2025) turns one image into a metric 3D Gaussian splat in **under a second on an A100** and renders at more than 100 fps for nearby views ([arXiv 2512.10685](https://arxiv.org/html/2512.10685v1)). Running it on each restyled plate gives a two-to-three-second dolly-in at the crossing moment. Keep the move small, roughly 10–20% of scene depth, or the splat tears (inference). Its license is unconfirmed; one site says MIT. Spark 2.4 (MIT, from World Labs) renders splats inside three.js on WebGL2, including on phones, and composites them with ordinary meshes ([npm](https://www.npmjs.com/package/@sparkjsdev/spark)). That makes a web viewer with a masked person billboard plausible, though no example was found.

Depth Anything 3 (November 2025; smaller models Apache-2.0, Giant CC BY-NC) supports the more classical route ([Hugging Face](https://huggingface.co/depth-anything/da3-giant)): split the plate into three to five depth layers, inpaint the gaps and pan, a "3D Ken Burns" effect that fits the course well. For the kiosk, head-coupled "window" parallax driven by MediaPipe face landmarks already exists as open code ([IvRogoz/Portal](https://github.com/IvRogoz/Portal)). It works for one viewer at a time ([trompeloeil](https://github.com/vivien000/trompeloeil)). A tripod clip has no camera parallax, so a true splat of the real gate needs an extra handheld orbit (inference).

**Sound.** Web Audio needs one user gesture to start, and iOS is strict about it ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices); [WebKit bug 180522](https://bugs.webkit.org/show_bug.cgi?id=180522)). A single "Tap to enter" screen should therefore start both the camera and Tone.js (MIT; [npm](https://www.npmjs.com/package/tone)). From there, map the fraction of mask pixels past the line to a crossfade between room tone and a world pad, and trigger a whoosh when a person's centroid crosses (inference, one to two days).

The trailer's synthesized soundtrack sidesteps music licensing. For generated additions, the licenses differ:

- **ACE-Step** v1 is Apache-2.0, and 1.5 is reportedly MIT ([project page](https://ace-step.github.io/ace-step-v1.5.github.io)).
- **Stable Audio Open** allows use by anyone under $1M in annual revenue, which suits crossing sound effects ([Hugging Face](https://huggingface.co/stabilityai/stable-audio-open-1.0)).
- **MusicGen**'s weights are CC-BY-NC (one table conflicts), so keep them out of any monetized upload ([MusicGen wiki](https://spokes-wiki.pages.dev/speech-audio-wiki/musicgen)).

## Rehearse a golden path, then seed the honeypot

### Lead the talk with video and save the live run for the poster

Practitioners who present for a living rarely bet a short slot on a live demo. Y Combinator's own guide says "demos seldom work in modern demo day presentations" ([YC](https://www.ycombinator.com/blog/guide-to-demo-day-pitches/)). Justin Kan's advice is blunter: "Don't do a demo. Demos break… show a video" ([Justin Kan](https://justinkan.com/feed/how-to-pitch-your-startup-on-stage)).

The counterexample is instructive. SIGGRAPH Real-Time Live! runs live demos successfully, but in 2023 it required tech setup the day before and a full-program rehearsal on show morning ([SIGGRAPH 2023](https://s2023.siggraph.org/program/real-time-live)). The 2007 iPhone keynote survived on a "golden path," a specific sequence of tasks in a specific order that engineers found would not crash the prototype ([MacRumors, summarizing Vogelstein](https://www.macrumors.com/2013/10/04/former-apple-engineer-gives-behind-the-scenes-look-at-the-original-iphone-introduction/)).

The resolution for this team (inference) is to make the trailer and main video the backbone of the talk. At most, end with a 30-second live crossing on a scripted path: a teammate walks across in real mode, then the worlds switch to Night, 1920s and Painting. Hold a one-key fallback ladder ready:

1. The live webcam.
2. The same app replaying a recorded webcam clip through identical code, labeled "recorded run, same pipeline."
3. The trailer MP4 stored locally.
4. Stills.

Keep the backup in "exactly the same state" as the primary, as Microsoft's event-demo team advises ([Microsoft](https://learn.microsoft.com/en-my/archive/blogs/cjohnson/how-we-demo)), and never debug on stage.

Set latency targets from Nielsen's limits ([NN/g](https://www.nngroup.com/articles/website-response-times/)). Around **0.1 s** feels like direct manipulation, so the crossing "pop" must land within it. About **1 s** is acceptable for a world switch. Anything near **10 s**, such as generating a new world from a typed prompt, must leave the live path. The pre-flight checklist:

- Rehearse with Wi-Fi off.
- Keep the laptop on wall power with notifications disabled.
- Lock camera settings.
- Bring a spare webcam and display adapter.
- Tape the tripod position and the line.

The talk can also claim a lineage. GauGAN, co-created by Berkeley PhD student Taesung Park, won **Best in Show and Audience Choice at SIGGRAPH 2019 Real-Time Live** by letting the audience drive the input ([Berkeley EECS](https://eecs.berkeley.edu/news/gaugan-ai-art-tool-wins-two-major-awards-siggraph-2019-real-time-live-competition/)). Berkeley's *Everybody Dance Now* spread within days on a side-by-side video anyone could read ([project page](https://carolineec.github.io/everybody_dance_now/)). Its source → intermediate → output layout is the template for a "peel-away layers" making-of: original, clean plate, restyle, masks, composite.

### Crowds gather around someone already crossing

Public-display research explains how a booth fills or stays empty:

- **The honeypot effect:** people interacting with a display attract others, and without a current user it does not happen ([Frontiers in VR 2025](https://public-pages-files-2025.frontiersin.org/journals/virtual-reality/articles/10.3389/frvir.2025.1714725/epub)).
- **The landing effect:** in a study of 502 sessions, passers-by often noticed interactivity late and had to walk back ([Dürr, LMU](https://www.mmi.ifi.lmu.de/lehre/ss15/ps/papers/Duerr-NoticingInteractivity.pdf)).
- **Crowds push users back:** larger and closer audiences push the active user farther from the display and shorten interaction ([Gentile et al., PerDis 2017](https://www.medien.ifi.lmu.de/pubdb/publications/pub/gentile2017perdis/gentile2017perdis.pdf)).
- **Display shape:** flat display layouts triggered the strongest honeypot effect ([chained displays study](https://typeset.io/pdf/chained-displays-configurations-of-public-displays-can-be-3qr69ccilw.pdf)).

The booth design follows (inference):

- Put a flat screen facing the aisle, with the tripod camera visibly beside it.
- Put a sign readable at about 3 m ("Cross the line → step into 1925").
- Have a teammate cross back and forth whenever the booth is idle.
- Ask spectators to stand to the side so the walker has room.
- Let each visitor pick their world. One crossing takes about 3–5 s, so the queue moves.

Privacy should be visible, default-off and easy. Posted signs do get read: in museum research, **75% of visitors leaving a recording area had read and understood the signs** ([InformalScience](https://www.informalscience.org/gaining-visitor-consent-research-iii-trilingual-posted-sign-method)). Edinburgh's Inspace states on site that its cameras capture a live feed and nothing is recorded or stored ([Inspace](https://inspace.ed.ac.uk/?p=4388)). *Wave at First Sight* auto-blurs detected people ([Images Out of Control](https://images-out-of-control.kleio.com/4_2024/22_wave-at-first-sight)). Immersive-art practitioners stress opt-in consent ([arXiv 2407.05450](https://ar5iv.labs.arxiv.org/html/2407.05450)).

Suggested sign text: "Live camera. Nothing is saved unless you press SAVE. Saved clips are deleted after today. Want to be blurred? Ask us." Back the last line with a "blur me" toggle driven by the same person mask. Note that any "save my crossing" QR link needs storage, which breaks the no-backend design and adds data-handling duty. The lowest-risk default is to let visitors film the screen with their own phones (inference).

For the course video, get a verbal or written OK from identifiable people, and blur or keep small any incidental Sather Gate passers-by. No UC Berkeley policy on filming the public for coursework was retrieved, so ask course staff.

### Make the website and video each teach one idea

Start the website from the Nerfies-lineage Academic Project Page Template, which deploys straight to GitHub Pages ([GitHub](https://github.com/eliahuhorwitz/Academic-project-page-template)). Treat each widget as a Bret Victor-style explorable that guides attention to one phenomenon rather than a free-floating toy ([Victor](https://worrydream.com/ExplorableExplanations/)). In practice, the drag-the-line player should open on a frame with someone mid-crossing, under a caption such as "drag the line through the Campanile — edges should not jump." Build the slider on a native `<input type="range">`, which gets touch, arrow keys and screen-reader support for free ([img-comparison-slider](https://cdn.jsdelivr.net/npm/img-comparison-slider@8.0.7/README.md)).

The page order follows from that (inference):

1. Hook and autoplaying muted trailer.
2. The interactive player.
3. The world gallery.
4. The pipeline figure.
5. The baseline grid.
6. Depth mode.
7. The failure gallery.
8. Credits.

Test it on a phone over cellular, because poster visitors arrive by QR code. Use `muted playsinline` so autoplay works on iOS.

For video, keep the existing 55 s trailer as the hook. Cut a 20–30 s fast-forward for the poster loop, with burned-in labels such as "per-frame baseline," "ours" and "real ↔ restyled" so it works muted. Add a 2–3 minute main video in this order:

1. Cold open on a crossing.
2. A 3-second flicker split-screen.
3. One animated method diagram.
4. A results montage cut on crossings.
5. Evaluation and failures.
6. A "how it's made" outro.

This mirrors SIGGRAPH's Thesis Fast Forward cap of **3 minutes at 1080p and 30 fps** ([SIGGRAPH](https://research.siggraph.org/programs/thesisff-2026/)). It also respects hackathon guidance that judges may not watch past 2 minutes ([HackHCC](https://hackhcc.gitbook.io/hackhcc-docs/other-resources/submission-and-judging-guide)). The structure itself is synthesized, not sourced.

## Conclusion

The research shows that the project's limitation is also its demo advantage. A fixed camera rules out camera moves and scene-reactive light, but it pushes every expensive generative step offline. What remains live is segmentation and compositing, which is cheaper and steadier than what the state-of-the-art AI mirrors attempt. That makes Cross the Line more demo-able than flashier real-time diffusion work, and it means the interactive kiosk and the quantitative evaluation are the same argument told twice. The flicker foil both draws a crowd and proves the claim. The editor tournament both picks the model and fills the gap left by the missing geometry-preservation benchmark.

The things to cut are just as clear: WebXR and 8th Wall, live StreamDiffusionV2 or Genie-class world models, live Depth Anything as the primary depth path, and anything that needs Wi-Fi on demo day. The open uncertainties are empirical and cheap to resolve in the first week: segmentation fps on the team's actual laptop and webcam, the poster room's lighting, whether an archive photo's vantage can be matched at Sather Gate, and the licenses (SHARP, any Depth Anything 3 checkpoint above Small, each archive photo) that must be confirmed before anything is published.
