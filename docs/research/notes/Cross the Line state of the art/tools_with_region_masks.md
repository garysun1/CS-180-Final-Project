# Products with region masks

> Research sweep of 27 November 2026. Evidence marks: **read** (the page was opened), **snippet** (search-result text only), **memory** (unverified). Social and product sites were blocked in the session, so product facts are mostly snippets.

## Summary

In the shipping tools found, selecting a region of a video is now cheap: text or click segmentation (SAM 3, the SAM 3 plus Wan VACE "Change Any Objects" workflow, After Effects Object Matte, Resolve Magic Mask 2), a drawn box (Google Flow Insert/Remove) or a brush and mask (Pika Modify Region/Pikaswaps, Kling O1 multi-elements, Higgsfield draw-to-edit). None of the generative editors keeps the real person's pixels by construction. Runway Aleph 2.0 (21 May 2026, clips up to 30 s), Luma Ray3 Modify (10-18 s), Kling O1 (3-10 s, about $0.168/s on fal) and Lucy Edit (open 5B, 832x480, 81 frames) all re-render the whole clip, and they ask for "keep the person identical" in the prompt or through an adherence setting. I found no shipping video tool that gives different painted regions different styles in one pass. The nearest are research code (NVIDIA Cosmos Transfer1 regional prompting) and the image-only SD "Regional Prompter". The closest overall is still Microsoft Teams Premium "Decorate your background": it snapshots your real room, restyles it once in the cloud while keeping its layout, and puts the live person on top. But it offers one theme for the whole background, with no regions, no crossings and no several worlds at once. Beeble SwitchX (Feb 2026) is the strongest "keep the subject, change the world" product: it replaces the background with new lighting and shadows, at 2K or 1080p (sources conflict), in minutes in the cloud. It relights the person, which we do not. The best UX precedents for "paint where each world shows on tripod footage" are old: Microsoft Research Cliplets (2012) used layered still/loop/play regions revealed with a brush, plus feathering and Laplacian blending. Snap's ground segmentation (the 2020 "Floor is Lava" lenses) is the precedent for an automatic ground mask as the place where a world appears. Our honest edge is several worlds placed by painted masks in one frame, live at camera rate with no GPU, camera pixels for people, no clip-length limit, and a background that cannot flicker. Our weak spots are rough person masks, low-fidelity SD 1.5 worlds, and people who are only colour-tinted.

## Findings

### [Microsoft Teams Premium 'Decorate your background'](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705) (2024-01 (GA in Premium; announced Ignite 2023))
*product · evidence: snippet · relevance 5/5*

- **What:** Takes a snapshot of your webcam view and sends it to a cloud service. The service generates a new image that keeps the room's layout, colours and angles, in a theme (Clean up, Fancy, Greenhouse, Celebration). You pick from the options or press 'Generate more', and the live segmented person is shown in front of the image. Needs a Teams Premium licence.
- **Relevance:** Same architecture as our C1/C4: generate your own room once, then composite the live person. The closest shipping product.
- **How we differ:** Teams: one theme for the whole background; no regions, depth, crossings or morph; you cannot see yourself step between worlds; enterprise licence; cloud generation. Teams does better: a polished clean-up theme that fills the hole where you sat, and several candidates per theme. We do: painted regions with several worlds at once, real people tinted to each world, crossings, a browser tool, video files as well as the webcam.
- **What to take:** Several candidates per world plus 'Generate more'. The theme names make a nice preset menu. Our 'Clean up' equivalent would be plate repair.

### [Meta SAM 3 / Segment Anything Playground (and SAM 3.1)](https://ai.meta.com/sam3/) (2025-11 (SAM 3.1 reportedly 2026-03))
*model · evidence: snippet · relevance 5/5*

- **What:** Text, exemplar and positive/negative click segmentation, with tracking in video. The Playground lets you upload video, prompt or click, and track. Meta said Edits would get per-object effects: pixelate, spotlight, motion trails, magnify. Picsart reports SAM 3.1 doubled video tracking speed (unverified).
- **Relevance:** Click or text to select is the main 2026 masking UX. It applies directly to our brush: segment 'ground', 'sky' or 'building' on the plate once.
- **How we differ:** It segments and applies effects but does not generate worlds or keep a background plate. We would use it, not compete with it.
- **What to take:** Snap-to-segment painting. Run SAM 3 once on the plate (Colab), ship the masks with the world PNGs, and let the brush fill a segment with one click.

### [Runway Aleph 2.0 + Edit Studio](https://runway.com/news/introducing-aleph-2-and-edit-studio) (2026-05-21 (third-party listings say 2026-06-02 or 2026-07-29))
*product · evidence: snippet · relevance 4/5*

- **What:** Prompt-based or reference-frame editing of existing footage. You edit one frame and the model carries the change across the clip, including across cuts. Clips up to 30 s. Runway help says objects are detected without masks or manual tracking. The older Inpainting tool was reportedly retired on 30 Jul 2026.
- **Relevance:** C1 per-clip regeneration family. The 'weather, season, time of day' edits are exactly our world list.
- **How we differ:** It regenerates the whole clip, people included. There are no persistent painted regions, nothing live, a 30 s cap and a per-second credit cost. It does better: much higher fidelity, a moving camera, and relighting implied by the regeneration. We do: exact camera pixels for people, unlimited length, live use, several worlds at once, and no flicker by construction.
- **What to take:** The 'edit one frame, propagate' mental model. Our plate is that one frame, so we can present Paint the same way in the pitch.

### [Beeble SwitchX / SwitchLight 3.0](https://digitalproduction.com/2026/02/27/beeble-switchx-focuses-on-easy-background-swaps/) (SwitchLight 3.0 2025-11; SwitchX 2026-02)
*product · evidence: snippet · relevance 4/5*

- **What:** SwitchX replaces the background of a clip, with updated lighting, shadows and camera perspective, in a few minutes. Beeble claims 2K; an Aug 2026 third-party guide says 1080p and cloud only. It aims to keep identity and lip sync. SwitchLight turns footage into PBR passes for relighting with HDRIs, in the browser or locally in 4K in Beeble Studio.
- **Relevance:** 'Keep the subject, change the world', with relighting, which is our known weak point (we only tint).
- **How we differ:** SwitchX: one background for the whole clip, cloud, offline, a GPU service; the person is re-lit, so not exactly the camera pixels. We do: regions, live use, several worlds, crossings, free.
- **What to take:** A relighting pass for people (normals plus a lighting estimate per world) as a stretch goal; show 'tint versus relight' honestly in the report.

### [Wan 2.1 VACE + SAM3 ComfyUI workflows ('Change Any Objects', VACE Inpainting)](https://comfy.org/hub/workflows/change-any-objects-cf84f066d9dd/) (2025-2026)
*repo · evidence: snippet · relevance 4/5*

- **What:** Open-weights video inpainting and regional editing. A text prompt gives a SAM3 mask, then Wan VACE regenerates the masked region, guided by a prompt or a reference image. The ComfyUI docs list background replacement that 'preserves subjects while changing environmental backgrounds'. 14B (~32 GB) or 1.3B (~7 GB) models.
- **Relevance:** The open-source front end for 'select a region and restyle it' on video. The thing we could build on for high-fidelity per-region world video.
- **How we differ:** It needs a 24 GB+ GPU, runs offline, handles short clips (~81 frames typical), one region and prompt per pass, and re-renders the boundary area. We are live, run on a CPU and keep exact pixels.
- **What to take:** Run VACE on the plate region with our painted mask to make a moving world (falling snow, water) on Colab. Use SAM3 text prompts to start the brush.

### [Pika Modify Region (Pikaswaps API)](https://dev.pika.art/docs/api-reference/generate-pikaswaps) (2025)
*product · evidence: snippet · relevance 4/5*

- **What:** Video-to-video inpainting. You mark the region with a brush or a mask image (white = change, black = keep), or with a text description of the region, and optionally give a replacement image. Input video at least 5 s per RunComfy.
- **Relevance:** The cleanest 'brush a region of a video and prompt it' product UX.
- **How we differ:** One region per generation. It regenerates the region per frame and runs offline on credits. No several worlds, no live use.
- **What to take:** The mask convention (white = world) and the 'describe or brush' dual input; export our painted masks as PNG in this format for interop.

### [Decart Lucy Edit Dev (open weights)](https://huggingface.co/decart-ai/Lucy-Edit-Dev) (2025-09-18 (1.1-Dev 2025-11; Lucy Edit 2 hosted 2026))
*model · evidence: read · relevance 4/5*

- **What:** 5B text-guided video editor on Wan2.2 5B. No masks needed. Strongest at clothing; scene transforms such as beach to snowy tundra 'can alter subject identity'. Example 832x480, 81 frames, 24 fps. Non-commercial licence; 16-24 GB VRAM.
- **Relevance:** Open baseline for 'restyle the whole clip by prompt'. Useful as a comparison figure: same prompt, Lucy versus ours.
- **How we differ:** It regenerates the person (the card admits identity drift on scene changes); short; GPU. We keep the person.
- **What to take:** Run one Colab comparison: the 'winter' prompt through Lucy Edit on our clip, next to our composite. Measure identity drift and flicker.

### [Microsoft Research Cliplets](https://hhoppe.com/cliplets.pdf) (2012)
*paper · evidence: snippet · relevance 4/5*

- **What:** A Windows app for tripod and handheld video. You stack layers (still, loop, mirror, play) and paint with a brush where each layer shows. Alignment, loop optimisation, feathering, matting and Laplacian blending hide the seams. Exports GIF/MP4/WMV.
- **Relevance:** The UX ancestor of our Paint tool: brush-defined regions on fixed-camera video, a layer stack, seam blending.
- **How we differ:** Time layers of the same footage instead of AI worlds; no people tracking.
- **What to take:** A layer panel (one row per world: visibility, opacity, feather) and the Laplacian blend at painted borders; cite it as UX prior work.

### [Kling O1 / Omni video edit and multi-elements](https://kling.ai/document-api/api/video/multi-elements.md) (2025-12 (Kling 3.0 Omni Edit in 2026 via Higgsfield and Firefly))
*product · evidence: snippet · relevance 3/5*

- **What:** Natural-language video edits: swap, add, remove, restyle. The official multi-elements API needs elements marked first (init and add selection calls return per-frame RLE/PNG masks); marketing calls it mask-free. 3-10 s clips, up to 4 element/style references, ~$0.168/s on fal.
- **Relevance:** Regional replace or restyle with several elements in one job, the nearest commercial thing to 'several regions'.
- **How we differ:** Short clips, the whole clip regenerated, cloud credits. We: unlimited length, live, exact pixels.
- **What to take:** Click-to-select with incremental add-selection (a positive/negative click list) as the API model for our Paint tool.

### [Luma Ray3 Modify (Dream Machine Modify Video)](https://www.businesswire.com/news/home/20251218399664/en/Luma-AI-Announces-Ray3-Modify-a-New-Model-for-Hybrid-AI-Workflows-for-Acting-Performances-Now-Available-in-Dream-Machine) (2025-12-18)
*product · evidence: snippet · relevance 3/5*

- **What:** Video-to-video that keeps an actor's motion, timing and delivery while background, lighting or wardrobe change. The lowest strength, 'Adhere', is recommended for background swaps; help suggests prompting 'keep the person identical'. 10 s per help (another source says 18 s). Krea's video restyle runs on Luma Modify.
- **Relevance:** Commercial 'keep the subject, change the world' by regeneration.
- **How we differ:** It keeps the subject statistically, not by construction; whole-frame; short; offline. We keep pixels exactly.
- **What to take:** Three strength levels map onto our SDEdit morph ladder; offer 'Adhere / Flex / Reimagine' labels for world strength.

### [Google Flow (Veo 3.1) Insert / Remove](https://blog.google/technology/ai/veo-updates-flow/) (2025-10 (Insert); Remove experimental, rolled out 2026)
*product · evidence: snippet · relevance 3/5*

- **What:** Insert: describe an object, optionally drag a box to place it, and Flow matches lighting and shadows. Remove: drag a box around an object and Flow rebuilds the background. Works best on objects that are stationary or barely moving; not for extended clips.
- **Relevance:** Box-drag region UX; Remove amounts to a clean-plate generator.
- **How we differ:** Short generated clips, cloud. No persistent regions, no live use.
- **What to take:** A drag-a-box 'place object in this world' tool; also box-remove to repair a plate where someone never moved.

### [After Effects Object Matte (replaced Roto Brush in 26.2) + Content-Aware Fill](https://helpx.adobe.com/after-effects/using/object-matte.html) (2026 (AE 26.2))
*product · evidence: snippet · relevance 3/5*

- **What:** Object Matte is an AI selection that propagates through the clip, faster and more accurately than Roto Brush; the classic brush is now 'Quick Selection'; Refine Edge handles hair. The Content-Aware Fill panel removes objects across video, which makes a clean plate.
- **Relevance:** The pro reference for brush plus propagation and for clean plates.
- **How we differ:** Pro desktop; no generative worlds by region. Content-Aware Fill is the gold standard for the plate step we do with a median.
- **What to take:** A 'Quick Selection' plus 'Refine Edge' pair: a coarse brush, then edge-aware snapping (a guided filter on plate colours) to fix our hand-painted mask edges.

### [Snap Lens Studio Ground Segmentation ('Floor is Lava' lenses)](https://developers.snap.com/lens-studio/features/snap-ml/snap-ml-templates/other-ml-templates/ground-segmentation) (2020 lenses; template current)
*product · evidence: snippet · relevance 3/5*

- **What:** An ML ground mask (white = ground) in screen space limits where effects render; the 2020 lava and water lenses opened the ground to magma. Sky segmentation is a separate feature using the gyroscope.
- **Relevance:** Precedent for 'a world appears only on the ground' and automatic sky/ground regions; matches our ring-on-ground rule.
- **How we differ:** Live but one fixed effect, not a restyle of your own scene; no people crossings.
- **What to take:** Automatic 'Ground' and 'Sky' brush presets (from segmentation or depth) as one-click regions.

### [NVIDIA Cosmos Transfer1 regional prompting utils](https://huggingface.co/spaces/NTUST-DDRC/cosmos_transfer1_av/blob/main/cosmos_transfer1/utils/regional_prompting_utils.py) (2025)
*repo · evidence: snippet · relevance 3/5*

- **What:** Builds per-region masks from boxes or segmentation maps, each paired with its own prompt, plus a global prompt, for a video DiT.
- **Relevance:** The only code found for 'several regions, different prompts, one video generation'.
- **How we differ:** Research code, big GPU, regenerates everything.
- **What to take:** Prior art for 'several worlds at once'; the idea of generating several worlds in one pass so painted borders are coherent.

### [Regional Prompter (SD WebUI extension) / Training-free Regional Prompting for FLUX](https://arxiv.org/html/2411.02395v1) (2023-2024)
*repo · evidence: snippet · relevance 3/5*

- **What:** Hand-drawn or uploaded masks, each with its own prompt, inside one SD/FLUX image generation; attention masking, no retraining.
- **Relevance:** Image-side tool to generate one plate image with several worlds whose borders follow our painted masks.
- **How we differ:** Images only; we composite separate worlds instead.
- **What to take:** An optional 'blend-aware border' generation: one SD 1.5 Regional Prompter pass using our painted masks, for seam regions.

### [Zoom / Google Meet generated backgrounds](https://support.google.com/meet/answer/13784433?hl=en) (2024-2025)
*product · evidence: snippet · relevance 3/5*

- **What:** A prompt generates a background once, and the segmented live person is composited over it each frame. Paid tiers.
- **Relevance:** 'Generate once, composite forever', but the background is not your own room.
- **How we differ:** No alignment to your scene, so there is nothing to cross into.

### [DaVinci Resolve 20 Magic Mask 2](https://mixinglight.com/color-grading-tutorials/ai-magic-mask-2-davinci-resolve) (2025)
*product · evidence: snippet · relevance 2/5*

- **What:** Click or stroke object masks that track through the shot; colourists test it against Power Windows. Tips cover rendering the matte to a file so it never needs retracking. Studio also has sky masking and an 'Artificial Sky'.
- **Relevance:** Click-to-segment masks used to drive regional grades: a grade per region is analogous to a world per region.
- **How we differ:** Grades rather than generated worlds; offline.
- **What to take:** Save masks as files (luma mattes) so a painted layout can be reloaded or shared.

### [Higgsfield video editor (Kling 3.0 Omni Edit, draw-to-edit)](https://higgsfield.ai/blog/edit-ai-video-without-regenerating) (2026)
*product · evidence: snippet · relevance 2/5*

- **What:** An aggregator: you mark a region of the frame and describe the change; text-based removal and restyle; Kling 3.0 Omni Edit and FLUX 3 Video Edit models.
- **Relevance:** Shows 'draw region and prompt' is a mainstream 2026 UX.
- **How we differ:** Regenerates; credits; short clips.

### [Krea video-to-video restyle](https://www.krea.ai/apps/video-to-video) (2025-04 launch; page 2026)
*product · evidence: snippet · relevance 2/5*

- **What:** Restyles an uploaded clip from a prompt with three strength levels, powered by Luma Modify; paid plans only. The page says Runway Aleph was shut down on 30 Jul 2026 (vendor claim, unverified).
- **Relevance:** Whole-clip restyle; no regions.
- **How we differ:** Whole frame regenerated.

### [Adobe Firefly Video Editor](https://blog.adobe.com/en/publish/2026/04/15/adobe-extends-leadership-video-unleashing-new-ai-powered-creation-firefly-reinventing-color-editors-in-premiere) (beta 2025-12; Kling 3.0/Omni added 2026-04)
*product · evidence: snippet · relevance 2/5*

- **What:** A browser editor with prompt-based edits, upscaling and partner models (FLUX.2, Kling 3.0 Omni). I found no confirmed Generative-Fill-style 'mask a video region and prompt' tool.
- **Relevance:** Photoshop Generative Fill is the UX reference, but Firefly video has not shipped an exact video equivalent that I could find.
- **How we differ:** Whole-clip edits.

### [Autodesk Flow Studio (formerly Wonder Studio)](https://www.autodesk.com/products/flow-studio/overview) (2025-2026)
*product · evidence: snippet · relevance 2/5*

- **What:** Cloud tool that turns live action into editable CG. Exports camera track, alpha masks, mocap and 'clean plate', and Camera Track and Clean Plate can be used as standalone tools.
- **Relevance:** Commercial clean-plate export, the pro version of our median plate, and it works with a moving camera.
- **How we differ:** It replaces actors with CG characters; offline cloud processing.
- **What to take:** A 'Clean plate only' export as an honest feature and a comparison point.

## Ideas to borrow

- **Snap-to-segment brush: run SAM 3 once on the clean plate (Colab, or SlimSAM/ONNX in the browser), ship a label map with the worlds, and let a click fill a whole segment (ground, wall, sky). Positive and negative clicks, then the hand brush refines.** Source: Meta SAM 3 / Segment Anything Playground, https://ai.meta.com/sam3/. The plate is a single still, so segmentation runs once and is cheap. It fixes ragged hand-painted borders and matches the 2026 click-to-select UX. *Effort: days; Colab GPU for SAM 3, or a CPU SlimSAM/MobileSAM in ONNX*
- **One-click 'Ground', 'Sky' and 'Far' presets computed from the Depth Anything map plus a ground/sky segmenter (Mask2Former ADE20K labels), so a world can be placed only on the floor (a 'floor is lava' style).** Source: Snap Lens Studio Ground Segmentation, https://developers.snap.com/lens-studio/features/snap-ml/snap-ml-templates/other-ml-templates/ground-segmentation. Our crossing rule fires on the feet, so ground regions are the natural unit; we already have depth. *Effort: hours to days; CPU*
- **A Cliplets-style layer panel: one row per world with show/hide, opacity, feather radius and order, plus a Laplacian or two-band blend at painted borders.** Source: Microsoft Research Cliplets, https://hhoppe.com/cliplets.pdf. Several worlds at once needs layer management. Cliplets is direct, citable UX prior work for painted regions on fixed-camera video. *Effort: days; WebGL2 only*
- **Edge-aware mask refinement: after painting, snap the mask to plate edges with a guided or joint-bilateral filter (Quick Selection plus Refine Edge style).** Source: After Effects Object Matte / Refine Edge, https://helpx.adobe.com/after-effects/using/object-matte.html. Painted borders that follow real edges (a doorway, a curb) look designed rather than smeared. *Effort: days; shader in the browser*
- **Export and import painted masks as white-is-world PNGs (Pika/Kling/VACE convention), and add a 'hand off to VACE' Colab notebook that turns one painted region into a moving world (falling snow, water) to put back in our compositor.** Source: Pikaswaps mask format https://dev.pika.art/docs/api-reference/generate-pikaswaps and Wan VACE Inpainting https://comfy.org/hub/workflows/wan2-1-vace-inpainting-a1bb55d904c9/. Answers the 'static image worlds look dead' critique while keeping people real, and it interoperates with the tools teams already use. *Effort: days; Colab GPU (1.3B VACE ~7 GB)*
- **Several candidates per world ('Generate more'), with the user picking one, plus a 'Clean up' theme that tidies the plate.** Source: Teams Decorate your background, https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705. SD 1.5 outputs vary; picking the best seed of 3-4 is the cheapest fidelity gain. *Effort: hours; more CPU minutes per world*
- **A head-to-head comparison figure: the same tripod clip and 'winter' prompt through Lucy Edit Dev (open) and, if anyone has credits, Aleph 2.0 or Luma Modify, next to ours. Report person identity drift (face crop SSIM or ArcFace distance) and background flicker (warp error).** Source: Lucy Edit Dev, https://huggingface.co/decart-ai/Lucy-Edit-Dev. Turns 'real people stay real, no flicker' from a claim into a measurement; strong for the report. *Effort: a day; Colab GPU 24 GB, or the hosted Lucy API*
- **Strength labels per world (Adhere / Flex / Reimagine) mapped onto our SDEdit strength ladder, chosen per region.** Source: Luma Ray3 Modify, https://lumaai-help.freshdesk.com/support/solutions/articles/151000220119-how-do-i-use-modify-video-to-transform-footage-while-preserving-motion-. Familiar UX language; we already have the ladder images for the morph. *Effort: hours*
- **Optional seam-coherent generation: one SD 1.5 Regional Prompter pass that uses the painted masks to draw all worlds in one image, so a winter-to-autumn border is drawn by the model rather than blended.** Source: Regional Prompter / Training-free Regional Prompting, https://arxiv.org/html/2411.02395v1; Cosmos Transfer1 regional_prompting_utils. Borders between worlds are the weakest visual moment of the Paint tool. *Effort: days; CPU slow, Colab better*
- **Box-remove plate repair for people who never move (the median fails there): drag a box, then inpaint the plate with LaMa or SD inpainting once.** Source: Google Flow Remove, https://blog.google/technology/ai/veo-updates-flow/; AE Content-Aware Fill. A known failure mode of median plates; one still to fix, not a video. *Effort: days; CPU LaMa is feasible*

## Not reached or not verified

- Most vendor sites were unreachable from this session (runway.com, replicate.com, fal.ai, dev.pika.art, docs.comfy.org failed DNS). Almost every product item is search-snippet evidence; only the Lucy Edit Dev Hugging Face card was fetched.
- Runway: whether Edit Studio has a brush or mask tool, the Aleph 2.0 per-second price and resolution, and whether 'Aleph shut down 30 Jul 2026' (Krea page) means Aleph v1 or the old Inpainting tool. Check help.runwayml.com by hand.
- Runway Motion Brush, Green Screen and Pika Pikadditions in 2026: not searched for lack of budget.
- Kling motion brush and multi-elements in the Kling app (not the API); Kling 3.0 Omni Edit details and price.
- LTX Studio and Freepik regional video editing: no reliable 2026 info found.
- Teams Decorate: whether the live person sits over the generated image as an ordinary virtual background, and how the hole where the person sat is filled. Microsoft's own page could not be fetched; try it in Teams Premium.
- NVIDIA Broadcast, CapCut AI backgrounds and auto cutout, Premiere object masks, Resolve Relight, TikTok Effect House, Plotaverse and Flixel Cinemagraph Pro: not verified this pass.
- Whether Meta's Edits app shipped the per-object SAM 3 effects (spotlight, motion trails); check inside the Edits app.
- Hand searches: TikTok and Instagram for 'floor is lava filter', 'AI background my room', 'half winter half summer filter'; CapCut template gallery for 'split season'; X and Reddit r/comfyui for 'VACE regional prompt' and 'multi-region video inpainting'; YouTube 'Aleph 2 edit studio mask'.

## Notes

## How each tool selects a region (late 2026)

| Tool | Selection | Different styles per region in one shot? | Real person pixels kept? | Limits / price | Fixed camera? |
|---|---|---|---|---|---|
| Teams Decorate | none (whole background behind segmented person) | no, one theme | yes (live segmentation) | Teams Premium licence | uses the webcam snapshot; effectively fixed |
| Runway Aleph 2.0 | prompt or edited reference frame; reportedly no masks | no | no, re-rendered | up to 30 s; credits | not needed |
| Luma Ray3 Modify | prompt plus strength (Adhere for background swaps) | no | no (prompt "keep identical") | 10 s (help) or 18 s | not needed |
| Pika Modify Region | brush, mask image or text region | one per job | outside the mask only | at least 5 s input; credits | not needed |
| Kling O1 / Omni | text, or marked elements (API returns per-frame masks) | up to 4 references | no | 3-10 s, ~$0.168/s on fal | not needed |
| Flow (Veo 3.1) | drag a box | no | outside the box | short clips; Remove experimental | works best on static objects |
| Wan VACE + SAM3 (ComfyUI) | text, click or mask | one per pass | outside the mask | GPU 7-32 GB, ~81 frames | not needed |
| Lucy Edit Dev | text only, no masks | no | no (card warns of identity drift) | 832x480, 81 frames, non-commercial | not needed |
| Beeble SwitchX | automatic subject | no | relit (not exact pixels) | 2K claimed, 1080p reported; cloud | not needed |
| AE Object Matte / Content-Aware Fill | click or stroke with propagation; fill makes a clean plate | n/a (masks for compositing) | yes | Creative Cloud | helps |
| Resolve Magic Mask 2 | click or stroke tracking | grades per mask | yes | Studio | helps |
| Snap ground segmentation | automatic ground or sky | one effect | yes | live on phone | no |
| Cliplets (2012) | brush per layer | yes (layers of time) | yes | free, Windows | yes, built for it |
| **Cross the Line** | brush with eraser and undo; line, ring, lens, depth rules | **yes, several worlds** | **yes, tinted** | unlimited length, CPU, live | **requires it** |

Sources: Aleph 2.0 date, 30 s limit and mask-free claim from search snippets of runway.com and Runway help ([Runway news](https://runway.com/news/introducing-aleph-2-and-edit-studio)). The release dates conflict (OpenRouter 29 Jul 2026, Runware 2 Jun 2026). Luma clip limit: 10 s in the [Luma help article](https://lumaai-help.freshdesk.com/support/solutions/articles/151000220119-how-do-i-use-modify-video-to-transform-footage-while-preserving-motion-) versus 18 s in another listing. Kling's official API needs selections before replace or remove ([Kling multi-elements doc](https://kling.ai/document-api/api/video/multi-elements.md)), contradicting "mask-free" marketing ([VEED](https://www.veed.io/learn/how-to-use-kling-o1)). Flow: "click and drag a box" for both Insert and Remove; Remove "works best on objects that are stationary or barely moving" ([Google blog](https://blog.google/technology/ai/veo-updates-flow/); [Flow help](https://support.google.com/flow/answer/16935718)). AE 26.2 replaced Roto Brush with Object Matte ([Adobe community](https://community.adobe.com/announcements-532/new-in-beta-object-matte-in-after-effects-1550754)).

## The three strongest competitors for our exact pitch

1. **Microsoft Teams Decorate your background.** Same pipeline: snapshot your real room, restyle it once while keeping layout, colours and angles, then put the live you in front. It is live and keeps real pixels. What it lacks: regions, several worlds, crossings, video files, and any visible relation between reality and the world. We should say plainly in the talk that Teams already restyles your room once and composites you live.
2. **Runway Aleph 2.0 (and Luma Ray3 Modify, which also powers Krea's restyle).** Best fidelity for "same shot, winter or night", and it works with a moving camera. But it regenerates the person, is capped at 30 s (Luma at 10-18 s), costs credits, and offers one look per clip.
3. **Open Wan VACE + SAM3 ComfyUI workflows.** These are the real "select a region, restyle it" competitor and the thing to build on. They are masked, open and free, but need a big GPU, run offline, handle short clips and one region per pass. Beeble SwitchX is a close fourth for "keep the subject, change the world" with relighting.

## Our honest edge
- **Several worlds at once in one frame, placed by painting.** I found no shipping video product that does this. The nearest are research regional-prompting code (Cosmos Transfer1) and image-only Regional Prompter; Cliplets did painted layers in 2012, but of time, not AI worlds.
- **Exact camera pixels for people, by construction.** Every generative editor re-renders people, Lucy's own card warns of identity drift, and Beeble relights.
- **No length limit and no flicker.** The world is a fixed image, against 3-30 s caps for regeneration.
- **Live at camera rate on a CPU in a browser.** Only Teams, Zoom, Meet and Snap are live, and none of them offers regions of your own room.
- **Crossings as an interaction.** No tool found ties a world change to a person's feet entering a region. Snap's lava lens uses the ground as the place an effect appears, but no crossing.

## Where they beat us
- Fidelity: SD 1.5 against Aleph, Veo or Kling.
- Moving camera: all the generative editors handle it.
- Relighting: Beeble.
- Mask quality: SAM 3, Object Matte and Magic Mask versus our colour difference.
- Clean plates when people never leave: Content-Aware Fill and Flow Remove.
- Animated worlds: our worlds are static images, which is also why they cannot flicker. VACE or Aleph give moving snow and water.

## UX patterns to copy (ranked)
1. Click to segment with positive and negative clicks, then brush refinement (SAM 3, Object Matte, Kling add-selection).
2. Automatic region presets for ground and sky (Snap).
3. Layer stack with per-layer feather and blend (Cliplets).
4. "Describe or brush" dual input for a region (Pika).
5. Several candidates and "Generate more" (Teams).
6. Strength presets (Luma Adhere / Flex / Reimagine).
7. Box drag to insert or remove (Flow).
8. Save masks as files (Resolve luma-matte tip).

## Caveats
Nearly all product facts above come from search-result snippets, because the vendor hosts were blocked in this session. Treat the numbers (clip lengths, prices, resolutions) as unverified until someone opens the pages by hand.
