# State of the art, and what we added

*Sweep of 27 November 2026: 142 findings across social posts, shipping tools, repos, papers and smart glasses; the 28 most important were re-checked. **read** = the source was opened; **snippet** = search-result text only (social and product sites were blocked). Detail: [research notes](research/notes/Cross%20the%20Line%20state%20of%20the%20art/).*

## What we added

1. **A mask per world.** You paint where each pre-drawn world shows; everywhere else is the camera's own pixels.
2. **People cross as a whole.** A person is whatever differs from the empty scene. We read the mask under their feet and show the whole person in that world, tinted to its light.
3. **One blend per pixel.** Each world is a single image, so every frame is one blend per pixel: it runs live in a browser, on a laptop, at any clip length.

Like the yellow first-down line in football broadcasts ([1998](https://entertainment.howstuffworks.com/first-down-line.htm), snippet), the world is painted under the people, never on them.

## What we build on

| Piece | Built on |
|---|---|
| The empty scene | The per-pixel median, a classic background model |
| The worlds | Stable Diffusion 1.5, ControlNet, LCM; Depth Anything V2 |
| Real people over a restyled scene | Teams "Decorate your background" (2024); FXjutsu "Toon World" (2026) |
| Painting regions | Interactive Digital Photomontage (2004); Cliplets (2012); LociArt (2026) |

## What exists

| Approach | Best examples | They do better | Only ours |
|---|---|---|---|
| Whole-clip video-to-video | Runway Aleph 2.0, Luma Modify, Meta Restyle | Fidelity, moving camera, moving worlds | The camera's own pixels for people, any length, no GPU |
| Masked multi-region video editing | LociArt, EditCtrl, Wan VACE + SAM 3 | Click or text selection, motion inside regions | Regions that people cross as a whole |
| Layered editing that keeps the source | Vera, PAI-Studio, AnyPortal, FXjutsu | Learned mattes, relit people | Median plate, one still per world, real time |
| Generate once, composite live | Teams Decorate, Zoom, Meet | Polish, robust person masks | The room and its twin in one frame |
| Live per-frame restyle | Decart Mirage and Lucy, StreamDiffusionV2 | Any motion, any prompt | No GPU per frame, a stable world, untouched people |
| Painted regions in stills and tripod video | MAST, Krita AI Diffusion "Regions"; Cliplets, Photomontage | Seams drawn by the model or by graph cuts | Generated worlds over video; people choose by their feet |
| Mattes and relighting | SAM 3.1, MatAnyone 2, HarmoVid, Beeble SwitchX | Hair-level mattes, true relighting | Shadows carried over, live on a CPU |

## The ten closest

| What | Year | Evidence | How we differ |
|---|---|---|---|
| [Teams "Decorate your background"](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705): a themed version of your real room, you live in front | 2024 | snippet | One theme everywhere; nothing to cross |
| [FXjutsu "Toon World"](https://github.com/audriu/fxjutsu): clean plate, restyle it, real people on top | 2026 | read | A video model on a 24 GB GPU; 5-s clips; not live |
| [LociArt](https://arxiv.org/abs/2610.36456): a different style per masked video region | Oct 2026 | read | Redraws every pixel; masks ignore people |
| [EditCtrl](https://arxiv.org/abs/2602.15031): mask-local, multi-region video editing | 2026 | read (abstract) | Generates every frame on a GPU |
| [Vera](https://arxiv.org/abs/2606.23610): a generated layer plus alpha over the source | 2026 | read | Kept pixels reach 35 dB at 8 min per clip; ours are exact, live |
| [PAI-Studio](https://arxiv.org/abs/2606.01399): background replacement guided by clean plates | 2026 | read (abstract) | Regenerates and relights the people |
| [AnyPortal](https://arxiv.org/abs/2509.07472): background replacement, foreground kept | 2025 | read | A new place, not the same room; no regions |
| [Higgsfield "walking location swap"](https://higgsfield.ai/academy/courses/ai-vfx-real-footage/swap-the-world-the-walking-location-swap): person kept, world swapped | 2026 | snippet | The swap fires at a moment in time; ours in space, in one take |
| [Runway "World jumping"](https://academy.runwayml.com/gen1/gen1-world-jumping), after Martin Haerlin's viral post | 2023 | snippet | Cuts in time; the person is restyled too |
| [Xia et al.](https://arxiv.org/abs/2010.10056): scribbled video regions, several styles, real time | 2020 | read | Stylises the people; no empty scene, no crossing |

## Say, and don't say

- Say **"we did not find"**, never "first".
- Say **"we build on"** for real people over an AI scene, and for painting styles onto regions.
- Say **"each world is one image, so it cannot flicker"**. Claim flicker only against per-frame and live tools: offline video models score about 0.97–0.98 on the usual consistency metrics.
- Say **"the camera's own pixels"** and **"tinted"** for people, never "relit".
- Don't put product numbers (clip limits, prices) on a slide until someone has opened the page.

## Still to check by hand

- Open the Teams, Higgsfield and Runway pages. The Higgsfield course reportedly says locked-off shots are the weak case for video models, which is worth quoting if true.
- Search inside TikTok, Instagram and CapCut for "split reality" and "real vs AI line"; find Martin Haerlin's original post.
- SIGGRAPH 2026 Real-Time Live (a live, text-prompted background demo), Ars Electronica, and past CS180 project galleries.
