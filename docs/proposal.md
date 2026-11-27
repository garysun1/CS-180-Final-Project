# Project Proposal (updated 27 November, for check-in 2)

## Abstract

**Film from a tripod, paint AI worlds onto the scene, and watch real people walk from one into the next. Each world is drawn once, so it cannot flicker.**

We film a place from a tripod and redraw the empty scene once per "world": winter, night, the 1920s, a Van Gogh painting. You paint where each world shows, or use a line or a ring on the ground. The real people are cut out and put back, and each person takes the world under their feet, so anyone who walks across steps into another world. It runs in a browser, on recorded clips and on a live camera.

## How it is done today, and why it falls short

Restyling one photo is routine: pix2pix [1], CycleGAN [2], ControlNet [3]. For video, we surveyed papers, products, repos and social posts on 27 November ([state of the art](state-of-the-art.md)). Most pieces of our idea exist:

- **Real people in an AI world is a known genre.** Creators have filmed it since Runway's 2023 "World jumping" tutorial [28]. Video-to-video models (Runway Aleph 2.0, Luma, Wan VACE [7–9], VISTA [10], FreeViS [11]) and background replacement that keeps the foreground (AnyPortal [29], PAI-Studio [30], Vera [31]) all regenerate every frame on a GPU, in clips of seconds, with people redrawn or relit.
- **Painting regions with different styles exists.** For stills: Interactive Digital Photomontage [32] and MAST [33]. For tripod video before AI: Cliplets [34]. For AI video: Xia et al. [35], LociArt [36] and EditCtrl [37]. Their regions are fixed pixel areas, and people are restyled like everything else.
- **Per-frame and live tools** (Rerender-A-Video, TokenFlow, FRESCO [4–6]; StreamDiffusion, StreamDiffusionV2, Decart [12–14]) flicker or drift, and change faces. Offline video models no longer flicker much by the usual metrics [31, 36], so we do not claim that against them.
- **Layered video editing** (Layered Neural Atlases, CoDeF, Omnimatte [15–17]) edits one shared canvas, learned per video. The idea goes back to Wang and Adelson's layers [38].
- **Restyle once, real people on top:** Teams' "Decorate your background" [18] and FXjutsu's "Toon World" [39] work in the same order as we do, with one theme for the whole background and nothing to cross.

## What is new, and why we think it works

A tripod turns the shared canvas into one image, the per-pixel median [19]. We redraw it once per world with Stable Diffusion 1.5, ControlNet (edges, and depth from Depth Anything V2 [40]) and LCM [41], in 80–149 s per world on four CPU cores. On top of that we add three things:

1. **A mask per world.** You paint where each pre-drawn world shows; everywhere else is the camera's own pixels.
2. **People cross as a whole.** A person is whatever differs from the empty scene. We read the mask under their feet [21] and show the whole person in that world, tinted to its light, with their shadow carried over [20].
3. **One blend per pixel.** Each world is a single image, so every frame is one blend per pixel: it runs live in a browser, on a laptop, at any clip length.

Like the yellow first-down line in football broadcasts [42], the world is painted under the people, never on them. We looked for the crossing itself, people changing world as a whole by where they stand, and did not find it. Its nearest relatives are photographers who blend day and night across one fixed view by hand [22], and AR portals that open onto authored 3D rooms [23].

Two more features exist in early form and come later: splitting by depth, and a morph in which a world grows in through the model's own lower-strength images [25–27].

## What we tried, and what it says

- **Footage:** a public stand-in tripod clip (OpenCV's 768×576 plaza clip) plus two street clips.
- **Generation:** we planned to compare FLUX.2, Qwen-Image-Edit and SDXL on a GPU. We shipped with SD 1.5 on a CPU, because a world is generated only once per video and seconds of latency do not matter. ControlNet held the geometry well enough that all 7 generated worlds needed no re-alignment.
- **Alignment:** with a deliberately injected drift (a 3–4 px seam jump), homography plus a local warp brings the seam back to 0.13–0.53 px on 7 of 9 filtered styles. Two sparse styles fall back to 1.2–2.3 px. Measuring the jump at the seam in pixels is more direct than feature-similarity scores, which are unreliable under large colour changes [24].
- **People:** composited back onto the unedited plate, they match the original footage at 35 dB PSNR.
- **Depth:** person height tracks the depth at their feet with r = 0.80 over 4,154 detections.
- **Paint (new):** several worlds painted at once in the browser, with an eraser and undo. Outside the paint, the output equals the camera frame exactly, and a walker stepping onto paint is detected as a crossing.
- **Survey (new):** it changed our claims. "An AI world behind real people" and "painted styles" are now credited as prior work, and we claim flicker only against per-frame and live tools.
- **Demos built:** a web demo running the compositor in WebGL, and a laptop kiosk that captures the empty room, generates a world, then composites the live camera at camera rate.

## Next steps and how we will measure success

1. Film Sather Gate and the Campanile with locked exposure.
2. Run the experiment we owe: per-frame Stable Diffusion on a few seconds of the same clip, measured the way recent papers do (frame-to-frame similarity, warp error on static pixels, PSNR on people) next to ours.
3. Export the result as a video, and record the 60–90 s demo.

**Success means:**
- the per-frame baseline measurably flickers where ours does not;
- outside the paint, our output equals the camera frame exactly (true in today's tests);
- people who try it walk across on purpose.

**The known limits:** a moving camera, swaying trees or water, and anyone who stands still for most of the clip (they get baked into the empty scene). People are tinted, not relit.

## Data

Each 1–3 min fixed-camera clip separates into the still scene and the people moving through it. Exposure, focus and white balance stay locked, so the camera adds no change of its own. Until our shoot, we use public stand-in clips.

## References

1. Isola et al., pix2pix, CVPR 2017. https://arxiv.org/abs/1611.07004
2. Zhu et al., CycleGAN, ICCV 2017. https://arxiv.org/abs/1703.10593
3. Zhang et al., ControlNet, ICCV 2023. https://arxiv.org/abs/2302.05543
4. Yang et al., Rerender-A-Video, SIGGRAPH Asia 2023. https://arxiv.org/abs/2306.07954
5. Geyer et al., TokenFlow, ICLR 2024. https://arxiv.org/abs/2307.10373
6. Yang et al., FRESCO, CVPR 2024. https://arxiv.org/abs/2403.12962
7. Runway, Aleph 2.0 (May 2026). https://runway.com/news/introducing-aleph-2-and-edit-studio
8. Luma, Ray3.2 video-to-video. https://lumalabs.ai/learning-center/articles/ray-3-2-video-to-video
9. Jiang et al., VACE, ICCV 2025. https://github.com/ali-vilab/VACE
10. Song et al., VISTA: Triplet-Supervised Video Style Transfer, arXiv 2605.17312 (2026). https://arxiv.org/abs/2605.17312
11. Xu et al., FreeViS, ICLR 2026. https://arxiv.org/abs/2510.01686
12. Kodaira et al., StreamDiffusion, ICCV 2025. https://arxiv.org/abs/2312.12491
13. StreamDiffusionV2, MLSys 2026. https://arxiv.org/abs/2511.07399
14. Decart, MirageLSD (2025). https://decart.ai/publications/mirage
15. Kasten et al., Layered Neural Atlases, SIGGRAPH Asia 2021. https://arxiv.org/abs/2109.11418
16. Ouyang et al., CoDeF, CVPR 2024. https://arxiv.org/abs/2308.07926
17. Lu et al., Omnimatte, CVPR 2021. https://arxiv.org/abs/2105.06993
18. Microsoft Teams Premium, "Decorate your background" (2024). https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705
19. Piccardi, Background subtraction techniques: a review, IEEE SMC 2004. https://zenodo.org/records/891536
20. Chuang et al., Shadow Matting and Compositing, SIGGRAPH 2003. https://grail.cs.washington.edu/projects/digital-matting/shadow-matting/
21. Hoiem, Efros, Hebert, Putting Objects in Perspective, CVPR 2006 / IJCV 2008. https://www.ri.cmu.edu/pub_files/2008/10/ijcv2008ObjectsInPerspective.pdf
22. Stephen Wilkes, *Day to Night* (NPR, 2016). https://www.npr.org/sections/alltechconsidered/2016/02/19/467338386/when-people-can-see-time-photographer-captures-day-night-in-one-image
23. Snap Lens Studio, Portal. https://developers.snap.com/lens-studio/examples/lens-examples/portal
24. ReFlex (on DINO structure distance under colour change), arXiv 2507.01496. https://arxiv.org/abs/2507.01496
25. Meng et al., SDEdit, ICLR 2022. https://arxiv.org/abs/2108.01073
26. Brown & Lowe, Recognising Panoramas, ICCV 2003. https://www.cs.ubc.ca/labs/lci/papers/docs2003/brown03.pdf
27. Wang & Golland, Interpolating between Images with Diffusion Models, 2023. https://arxiv.org/abs/2307.12560
28. Runway Academy, "World jumping" (Gen-1, 2023), after Martin Haerlin's post. https://academy.runwayml.com/gen1/gen1-world-jumping
29. Gao, Lan, Yang, AnyPortal: Zero-Shot Consistent Video Background Replacement, ICCV 2025. https://arxiv.org/abs/2509.07472
30. PAI-Studio: Cinematic Video Background Replacement with Camera-Aware Motion, arXiv 2606.01399 (2026). https://arxiv.org/abs/2606.01399
31. Vera: A Layered Diffusion Model for Content-Preserving Video Editing, arXiv 2606.23610 (2026). https://arxiv.org/abs/2606.23610
32. Agarwala et al., Interactive Digital Photomontage, SIGGRAPH 2004. https://grail.cs.washington.edu/projects/photomontage/
33. MAST: Mask-Guided Attention Control for Training-Free Regional Multi-Style Transfer, arXiv 2604.12281 (2026). https://arxiv.org/abs/2604.12281
34. Joshi et al., Cliplets: Juxtaposing Still and Dynamic Imagery, UIST 2012. https://hhoppe.com/proj/cliplets/
35. Xia et al., Real-time Localized Photorealistic Video Style Transfer, arXiv 2010.10056 (2020). https://arxiv.org/abs/2010.10056
36. LociArt: A Unified Paradigm for Free-Style Local Video Stylization, arXiv 2610.36456 (2026). https://arxiv.org/abs/2610.36456
37. Litman et al., EditCtrl: Disentangled Local and Global Control for Real-Time Generative Video Editing, arXiv 2602.15031 (2026). https://arxiv.org/abs/2602.15031
38. Wang and Adelson, Representing Moving Images with Layers, IEEE TIP 1994. https://persci.mit.edu/pub_abstracts/wang_tr279_abs.html
39. FXjutsu, "Toon World" preset (2026). https://github.com/audriu/fxjutsu
40. Yang et al., Depth Anything V2, NeurIPS 2024. https://arxiv.org/abs/2406.09414
41. Luo et al., LCM-LoRA, 2023. https://arxiv.org/abs/2311.05556
42. Sportvision, the "1st & Ten" virtual first-down line (1998). https://entertainment.howstuffworks.com/first-down-line.htm
