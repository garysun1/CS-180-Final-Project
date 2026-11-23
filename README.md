# Project Proposal (check-in 1)

## Abstract

Film a place from a tripod. We redraw the empty place once with AI as winter, night, the 1920s or a Van Gogh painting. Then anyone who walks across a line in the frame steps from the real world into that one, and back. The line can also be a distance ("everything farther than here"), a ring on the ground, or a wave that sweeps in from the horizon. On the real side, every pixel is the camera's own. On the other side is a generated twin of the same place, aligned to the pixel. A short web demo and a live-camera kiosk let people do the crossing themselves.

## How it is done today, and why it falls short

Restyling one photo is routine: pix2pix [1], CycleGAN's summer-to-winter Yosemite [2], and diffusion guided by an image's edges and depth (ControlNet [3]). Video is harder, and today's approaches all regenerate the scene over time:

- **Per-frame editors** (Rerender-A-Video, TokenFlow, FRESCO [4–6]) diffuse every frame and hold the frames together by correspondence. They flicker wherever that fails, and run at roughly 0.1–1 fps on an A100.
- **Video-to-video models** (Runway Aleph 2.0, Luma Ray3.2, Wan VACE [7–9], VISTA [10], FreeViS [11]) regenerate every pixel, people included. They cap clips at about 5–30 s.
- **Real-time generative video** (StreamDiffusion, StreamDiffusionV2, Decart MirageLSD [12–14]) re-renders each webcam frame on high-end GPUs, from one RTX 4090 up to four H100s. Frame-by-frame generation "introduces flicker and drift" [13], and it changes the person's face too.
- **Layered video editing** (Layered Neural Atlases, CoDeF, Omnimatte [15–17]) edits one shared canvas and maps it back to every frame. It needs per-video optimisation, from minutes to about ten hours.
- **Meeting apps** come closest in spirit. Teams' "Decorate your background", Zoom and Meet [18] generate a background once and paste the live person on top. But that background replaces the room; it never shares the frame with it.

## What is new, and why we think it works

**A tripod turns video editing into image editing.** With a fixed camera, the layered-editing canvas needs no learning: every frame maps to it by the identity, so the canvas *is* the clean plate. A per-pixel median over the clip recovers it in closed form [19]. We restyle that one image with Stable Diffusion 1.5, ControlNet (depth and edges) and LCM, in 80–149 s per world on four CPU cores. The world is a single image, so it cannot flicker, and it works at any clip length or resolution. Like VFX clean-plate compositing, people are cut out (pixels that differ from the plate) and put back. They are colour-matched to each world, and their shadows carry over as the frame-to-plate brightness ratio, a simple form of shadow compositing [20].

**What this exactness buys is the crossing.** A rule picks, for every pixel, the real frame or its generated twin:
- a line;
- depth, from Depth Anything V2 on the plate, with each person taking the depth of the ground at their feet [21], so they change as one piece while walking away;
- a portal ring;
- a horizon wave.

People take on the world of wherever they stand. Photographers split one fixed view into day and night by hand (Stephen Wilkes's *Day to Night* takes months per still) [22], and AR portals open onto authored 3D rooms [23]. We did not find a tool, paper or artwork that splits a live or filmed frame between reality and a generated version of the same scene, with people walking through the seam.

**The seam measures itself.** One side is untouched, so any geometry the generator moves shows up as a step at the line, measured in pixels. That is more direct than feature-similarity scores, which are unreliable under big colour changes like night [24].

**The world grows instead of cutting.** img2img at lower strength [25] gives the model's own unfinished versions of a world. We play them in order, from the plate to the filter image the generation started from, to partial results, to the final world. Neighbouring versions are joined with a two-band blend run over time (Brown–Lowe [26]; the 2-level pyramid from the mosaics project): colour crossfades while fine detail switches pixel by pixel. That avoids the double-exposure look of a plain crossfade [27]. It is Project 5's "series of edits at increasing noise levels", played as a movie.

## What we tried, and what it says

- **Footage:** a public stand-in tripod clip (OpenCV's 768×576 plaza clip) plus two street clips.
- **Generation:** we planned to compare FLUX.2, Qwen-Image-Edit and SDXL on a GPU. We shipped with SD 1.5 on a CPU, because a world is generated only once per video and seconds of latency do not matter. ControlNet held the geometry well enough that all 7 generated worlds needed no re-alignment.
- **Alignment:** with a deliberately injected drift (a 3–4 px seam jump), homography plus a local warp brings the seam back to 0.13–0.53 px on 7 of 9 filtered styles. Two sparse styles fall back to 1.2–2.3 px.
- **People:** composited back onto the unedited plate, they match the original footage at 35 dB PSNR.
- **Depth:** person height tracks the depth at their feet with r = 0.80 over 4,154 detections. The depth rule, a stretch goal in our first proposal, now works.
- **Demos built:**
  - a web demo running the compositor in WebGL;
  - a laptop kiosk that captures the empty room, generates a world in seconds, then composites the live camera at camera rate;
  - a trailer and a 16-s one-take loop.

## Next steps and how we will measure success

1. Film Sather Gate and the Campanile with locked exposure.
2. Run the minimal experiment we owe: per-frame Stable Diffusion on 2 s of the same clip. Measure its frame-to-frame flicker on static background pixels next to ours. We have argued, but not yet shown, that one image beats per-frame generation.
3. Try a GPU editor on the real footage; the pipeline accepts any generated image.

**Success means:**
- seam drift under 2 px on our own footage;
- the per-frame baseline visibly and measurably flickers where ours does not;
- people who try the kiosk cross the line on purpose.

**The known limits:** a moving camera, swaying trees or water, and anyone who stands still for most of the clip (they get baked into the plate).

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
