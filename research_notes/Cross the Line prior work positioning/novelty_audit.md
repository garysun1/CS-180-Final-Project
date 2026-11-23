# Novelty audit: "Cross the Line" (CS180/280A Fall 2026 final project)

Method: about 33 tool calls (searches and fetches) on 23 Nov 2026. Each item is marked by how well it was checked:
- **[fetched]**: I read the page itself.
- **[snippet]**: I saw only the search-result text, often because the host is blocked in this session.
- **Gaps**: anything taken from background knowledge only. Those items are in the Gaps sections.

These hosts could not be fetched from this session: techcommunity.microsoft.com, digitaltrends.wp.txstate.edu, ltx.io and zhang-yw.github.io. The GitHub API was also not enabled for audriu/fxjutsu.

**Self-hit warning.** A search for "Berkeley CS180 final project stable diffusion video background restyle seasons" returns the team's own repo, `garysun1/CS-180-Final-Project` (it is this checkout's `origin`), as the top result. It is not prior art. Its README still describes the old plan:
- it compares FLUX.2 Klein 9B, Qwen-Image-Edit-2511 and SDXL+ControlNet;
- it sets a goal of "<2 px edge jump";
- it lists depth splitting only as a stretch goal.

That no longer matches the shipped SD 1.5 + ControlNet depth/canny + LCM pipeline. The rubric checks that "details of your project are consistent with the story", so this should be fixed. — [garysun1/CS-180-Final-Project](https://github.com/garysun1/CS-180-Final-Project) [fetched]

---

## C1. Restyle a static-camera video by editing one clean background image once, then compositing the real people back

### Takeaway
**Verdict: KNOWN as an idea; the team's own version is ordinary execution.**
- Microsoft Teams Premium ships the same pipeline for webcams: snapshot the room, remove the person, fill the hole, restyle it once with image-to-image, then show the live person in front.
- An open-source ComfyUI/LTX preset ("Toon World") uses the same order for video: clean plate, restyle the empty plate, put the real people back on top.
- The academic ancestor "edit once, propagate to every frame" is Layered Neural Atlases (2021).
- What is ours is the substrate choice: a tripod plus a temporal median makes the plate one image, so it cannot flicker. We use that plate as the base for the crossing effects in C2 and C3.

### Cited Findings
- **Microsoft Teams "Decorate your background"** (announced at Ignite 2023, generally available to Teams Premium in 2024, later extended to GCC/GCC High):
  - Microsoft says it "uses AI-powered image to image processing to take a snapshot of your video feed and generate a new image that is based on the foundational elements of your physical room."
  - A May 2024 explainer says the service "removes the user from the screenshot, fills the user-shaped hole in the background, and then passes this image to the generative AI image service, along with text instructions for the selected style."
  - The styles include Clean up, Fancy, Greenhouse and Celebration.
  - Sources: [Microsoft Tech Community](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705) [snippet]; [TxState Digital Trends, 7 May 2024](https://digitaltrends.wp.txstate.edu/?p=2983) [snippet]; [Windows Report](https://windowsreport.com/microsoft-teams-can-now-tidy-up-your-webcam-background-with-ai/) [snippet]; [M365 roadmap RM419811](https://mc.merill.net/message/RM419811) [snippet]
- **FXjutsu** (GitHub, 2026, LTX-2.5 + Lightricks IC-LoRAs on ComfyUI):
  - The "Toon World" preset is "Alpha-Gen + Clean-Plate + Union Control": "the world becomes anime, people stay real."
  - Its README says: "Restyling the empty plate is what keeps a cartoon copy of the subject from peeking out around the real one."
  - The "Golden Statue / Hologram" presets restyle only the people over the original footage.
  - It renders offline: about 2–3 min per 5-s clip on an RTX 4090. It uses a video model over the whole clip, not one still image. The boundary is a person matte ("grown 2 px and feathered"); there is no line or depth split.
  - Source: [github.com/audriu/fxjutsu](https://github.com/audriu/fxjutsu) [fetched; exact creation date not visible]
- **LTX-2.3/2.5 "Clean Plate" IC-LoRA** removes people, vehicles and their cast shadows from video and reconstructs the empty background. Static cameras are supported. — [LTX blog](https://ltx.io/blog/remove-people-and-shadows-from-video) [snippet]; [SD_Tutorial on X](https://x.com/SD_Tutorial/status/2098687407478677798) [snippet]
- **Runway Aleph** (July 2025; Aleph 2.0 now) edits existing footage by prompt:
  - "Describe the weather, season, or time of day you want, and Aleph 2.0 updates the atmosphere across your clip".
  - It "substitutes [the setting] while preserving your subject and foreground elements".
  - A third-party guide warns that it can restyle wardrobe too much during a season change. It defaults to the first 5 s, and a render takes about 2–4 min per pass.
  - Sources: [Runway Aleph 2.0 guide](https://help.runwayml.com/hc/en-us/articles/52150503729171-Aleph-2-0-Prompting-Guide) [snippet]; [PetaPixel, 29 Jul 2025](https://petapixel.com/2025/07/29/runways-new-model-can-transform-existing-video-footage-using-just-a-prompt) [snippet]; [Martini guide](https://martini.art/en/how-to/edit-existing-video/runway-aleph) [snippet]; [Runway "Change Time of Day" app](https://runwayml.com/apps/change-time-of-day) [snippet]
- **Layered Neural Atlases** (Kasten, Ofri, Wang, Dekel; SIGGRAPH Asia 2021) map a video onto 2D atlases. Edits to one atlas "are automatically and consistently mapped back to the original video frames", which preserves occlusions, shadows and reflections. The applications include video style transfer. — [SIGGRAPH History Archive](https://history.siggraph.org/?p=214129) [snippet]; [Neural Atlas Graphs, 2025, describing LNA](https://arxiv.org/pdf/2509.16336) [snippet]
- **Omnimatte** (CVPR 2021) splits a video into a static background layer plus RGBA layers, one per subject. Each subject's layer carries its shadows and reflections, so it can be edited in standard tools. A new network is trained for each video. — [CVPR 2021 paper](https://openaccess.thecvf.com/content/CVPR2021/papers/Lu_Omnimatte_Associating_Objects_and_Their_Effects_in_Video_CVPR_2021_paper.pdf); [Google Research blog](https://www.research.google/blog/introducing-omnimattes-a-new-approach-to-matte-generation-using-layered-neural-rendering/) [snippet]
- **Generative Omnimatte** (2024) notes that inpainting models "preserve the removed objects' shadows and reflections outside the mask". It trains a video diffusion model to remove those effects. — [arXiv 2411.16683](https://arxiv.org/abs/2411.16683) [snippet]
- **Student projects with the same idea, done per frame:**
  - "Paint your Zoom Background: Portrait Segmentation for Video Stylization" (UW–Madison CS639) stylizes the video background while keeping the portrait. It masks each frame and combines the mask with the stylized frame. — [zhang-yw.github.io/CS639](https://zhang-yw.github.io/CS639) [snippet; year unknown]
  - An "AI 535" course report combines video object segmentation with Fast Neural Style Transfer to stylize only the background. — [AI 535 report](https://kuanchia-chen.github.io/documents/AI_535_Deep_Learning_Final_Report_Group_19.pdf) [snippet]
- **The temporal median plate is classic.** Background initialization from static-camera video is a standard topic in background subtraction. — [Background Subtraction review, arXiv 1901.03577](https://arxiv.org/pdf/1901.03577) [snippet]

### Inferences
- A GSI or hiring manager may know Teams' Decorate, Runway Aleph or atlas methods. Claiming C1 as new would hurt credibility.
- C1 is still very useful as the "how is it done today" Heilmeier answer. There are three families today:
  1. per-clip regeneration (Aleph, FXjutsu, LTX): minutes per clip, a GPU, and the whole frame resynthesized;
  2. per-video optimization (atlases, Omnimatte);
  3. a single snapshot restyled and shown as a full background (Teams).
- Our deliberate simplification (tripod, median, one SD 1.5 image on CPU) is what makes the crossing effects possible. The tripod constraint is the insight, not a weakness.

### Gaps
- I could not open Microsoft's primary pages. Two things remain unconfirmed: whether Teams renders the person live over the decorated still (implied by "background effect" but not quoted), and whether the generation runs in the cloud or on device. Sources differ: one snippet says images are not stored in the cloud and replacement "happens on the user's machine".
- FXjutsu's creation date and commit history were not checked (GitHub API blocked).
- Unverified leads from background knowledge, worth checking before citing:
  - EbSynth / "Stylizing Video by Example" (Jamriška et al. 2019): paint one keyframe and propagate it;
  - Rerender-A-Video (2023), CoDeF (2023), Text2LIVE (2022) and StableVideo (2023): canonical or atlas-image editing;
  - Zoom and Google Meet "generate a background" (text-to-image, not of your own room);
  - classic VFX matte painting and set extension over a locked-off clean plate.

---

## C2. A spatial boundary (line, depth or portal) splits one frame into the real scene and a pixel-aligned generated version of the same scene; people change world as they cross

### Takeaway
**Verdict: PARTLY KNOWN. The "crossing" experience is the strongest candidate for genuine novelty, but it is not certain.**
- The same idea exists in non-generative forms:
  - Stephen Wilkes' "Day to Night" photographs split one fixed-camera scene into day and night regions;
  - DuctTake composites several takes of one scene along seams;
  - AR "portals" open into another world;
  - before/after sliders are common.
- I found no work, product, filter or installation where a line, depth threshold or portal inside one filmed or live frame keeps the real side untouched and shows a generated restyle of the same scene on the other side, with people switching world as they cross.
- That is an absence of evidence. TikTok, CapCut and Instagram effects are poorly indexed.

### Cited Findings
- **Stephen Wilkes, "Day to Night"** (c. 2009 onward):
  - Each image is a composite of about 1,500 frames from a fixed position over 16–30 hours.
  - Wilkes "decide[s] where day begins and night ends", and once wanted to "checkerboard time".
  - Sources: [Smithsonian](https://www.smithsonianmag.com/travel/how-photographer-stephen-wilkes-captures-full-day-single-image-180972935/) [snippet]; [NPR, Feb 2016](https://www.npr.org/sections/alltechconsidered/2016/02/19/467338386/when-people-can-see-time-photographer-captures-day-night-in-one-image) [snippet]; [designboom 2015](https://www.designboom.com/art/stephen-wilkess-day-to-night-bryce-wolkowitz-gallery-11-09-2015/) [snippet]
- **DuctTake** (Disney Research / ETH; Eurographics 2012, CGF 2013; arXiv 2021) composites multiple takes of the same scene along spatiotemporal seams found by 3D graph cuts. It expects similar content and camera location, and notes that differences along the seam cause colour bleeding. — [arXiv 2101.04772](https://arxiv.org/abs/2101.04772) [snippet]; [Disney Research](https://studios.disneyresearch.com/2013/05/06/ducttake-seam-based-video-compositing/) [snippet]
- **Snap Lens Studio's Portal asset** lets users "enter a portal or doorway into another world" using surface tracking and occlusion. The other world is a separate 3D scene, not the same scene restyled. — [Snap developer docs](https://developers.snap.com/lens-studio/examples/lens-examples/portal) [snippet]
- **Shopify "Reverse AR"** segments furniture and people from the camera feed and composites them into a virtual room. — [Shopify spatial-commerce projects](https://shopify.github.io/spatial-commerce-projects/Reverse-AR) [snippet]
- **Physical "Portals"** (Amar Bakshi, 2014–; 40+ cities) and **"Portal" sculptures** (NYC–Dublin 2024; Manila Jan 2026) are live video links between cities, with no generation. — [Wikipedia: Portals initiative](https://en.wikipedia.org/wiki/Portals_(initiative)); [Wikipedia: Portal sculptures](https://en.wikipedia.org/wiki/Portal_(sculptures)) [snippet]
- **Social filters:** searches for a line-crossing AI effect found TikTok's AI Manga and anime filters, which restyle the whole frame or the person, and CapCut split-screen templates. None splits the scene with a line that people cross. — [ComicBook.com on TikTok AI Manga](https://comicbook.com/anime/news/tiktok-anime-filter/) [snippet]; [TikTok #splitscreen](https://www.tiktok.com/tag/splitscreen?lang=en) [snippet]
- **Still-image comparison sliders** for style transfer exist (for example a Hugging Face Space using an ImageSlider). They are not live video and not person-aware. — [HF salient-style-transfer app.py](https://huggingface.co/spaces/jamino30/salient-style-transfer/blob/main/app.py) [snippet]
- **Whole-frame composites from C1** (Teams Decorate, FXjutsu Toon World) put real people into a generated version of the same scene, but with no spatial real/generated boundary. — [FXjutsu](https://github.com/audriu/fxjutsu) [fetched]
- An extended search for an installation that "captures the empty room, generates an alternate version, and composites visitors live" found none. The nearest results were Daniel Rozin's camera mirrors and Refik Anadol's rooms, neither of which is a generative restyle of the same room. — [search result: Refik Anadol](https://en.wikipedia.org/wiki/Refik_Anadol)
- The course FAQ says novelty can be creative rather than technical: "A project that is technically simple, but incredibly creative or artistic also works." — Course instructions PDF (local upload, p. 3)

### Inferences
- The defensible new thing is the interaction grammar. A spatial rule chooses real or generated per pixel in an aligned pair (real frame, restyled plate), and people inherit the world of the region they stand in. That is what makes "crossing" a visible event.
- The ingredients are known: aligned pairs, seams, masks and portals. The combination, and the live kiosk version of it, had no precedent in this search.
- Wilkes and DuctTake are the best related-work pairing: same camera, same scene, different "versions", joined spatially. Ours swaps time-of-day or takes for generated worlds and adds moving people who switch.

### Gaps
- Instagram, TikTok and CapCut effect galleries, YouTube Shorts and Reddit (r/StableDiffusion, r/vfx) were not searched directly. Some creator has probably made a hand-masked "walk from real into AI" edit; one search summary even said it "is probably a practical edit" in an editor. Hedge with "we did not find" rather than "first".
- SIGGRAPH Real-Time Live, CVPR CVEU/AI4CC workshops and Ars Electronica 2023–26 archives were not searched individually.
- Unverified leads (background knowledge): Cliplets (Joshi et al., UIST 2012), which mixes still and live regions of a tripod video with masks; cinemagraph tools; time-slice video by Dan Marker-Moore and others; *Pleasantville* (1998) colour/greyscale mixing, a pop-culture touchstone.

---

## C3. Depth split (near is real, far is generated), where each person takes the depth at their feet and so changes gradually while walking away

### Takeaway
**Verdict: PARTLY KNOWN in ingredients; the specific rule has no precedent found.**
- Depth-based compositing is standard.
- Using a person's ground-contact point to place them in depth is classic single-view geometry (Photo Clip Art, Putting Objects in Perspective).
- I found no prior use of foot-point depth to switch people between a real and a generated world, though it is an easy extension.

### Cited Findings
- **Photo Clip Art** (Lalonde, Hoiem, Efros, Rother, Winn, Criminisi; SIGGRAPH 2007) annotates library objects with whether they are on the ground plane, and assumes "all of our objects are assumed to reside on the ground plane". — [SIGGRAPH 2007 PDF](https://hci.iwr.uni-heidelberg.de/vislearn/HTML/publications/papers/2007/criminisi_siggraph_07.pdf) [snippet]
- **Putting Objects in Perspective** (Hoiem, Efros, Hebert; CVPR 2006, IJCV 2008) models object scale and position, including pedestrians, from scene geometry and viewpoint. — [IJCV 2008 PDF](https://www.ri.cmu.edu/pub_files/2008/10/ijcv2008ObjectsInPerspective.pdf) [snippet]. Efros, a co-author, is CS180 faculty, so this is a natural citation for the course.
- A GitHub repo named "depth-aware-style-transfer" exists; its content was not checked. — [Aayushchou/depth-aware-style-transfer](https://www.github.com/Aayushchou/depth-aware-style-transfer) [snippet title only]
- **Differential Diffusion** ("Giving Each Pixel Its Strength", 2023) lets each pixel take its own edit strength. A depth map used as the change map would give a graded real-to-generated image in one generation, but only for a still image. — [HF papers 2306.00950](https://huggingface.co/papers/2306.00950.md) [snippet]

### Inferences
- Treating each person as a standing billboard at their foot depth avoids an artefact: per-pixel depth would split one body into half real and half generated.
- The horizon wave that sweeps in a new world is a depth-ordered wipe, the same mechanism over time.
- Present this as "a simple, explainable rule borrowed from single-view geometry", and cite Hoiem/Lalonde.

### Gaps
- No search covered depth-based wipes or transitions in VFX or motion graphics. They are common in practice (Z-depth compositing, depth fog), but I have no citation.
- Not checked: whether any AR depth-occlusion effect (iOS people occlusion, Snap ground segmentation) applies a style by distance.
- Unverified lead: "Tour into the Picture" (Horry et al. 1997), which places foreground billboards on a ground plane.

---

## C4. Real-time kiosk: generate each world once, then composite at camera rate on modest hardware (versus per-frame real-time diffusion)

### Takeaway
**Verdict: PARTLY KNOWN.**
- The architecture (snapshot the empty room, generate once on a server, composite the live person locally) matches Teams' "Decorate your background", which shipped in 2023–24.
- The contrast with per-frame diffusion mirrors (StreamDiffusion in TouchDesigner, MirageLSD) is real and worth teaching. Those systems re-render every frame on a strong GPU. The kiosk spends about one generation per world, keeps real pixels exact, and runs on a laptop.
- What is ours: the spatial crossing rules, the portal and flood interactions, and the per-world recolouring running in WebGL.

### Cited Findings
- **Teams Decorate** takes "a snapshot of your video feed" and generates "a new image ... based on the foundational elements of your physical room". — [Microsoft Tech Community](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705) [snippet]
- **StreamDiffusion** (2023) is an open-source "pipeline-level solution for real-time interactive generation". It includes a real-time webcam img2img demo in the browser. — [GitHub cumulo-autumn/StreamDiffusion](https://github.com/cumulo-autumn/StreamDiffusion) [snippet]
- **TouchDiffusion** (StreamDiffusion in TouchDesigner) reports, at 512×512 with sd-turbo: 16 FPS on an RTX 3060, 24 FPS on a 4070 Laptop, and 55–60 FPS on a 4090. — [GitHub olegchomp/TouchDiffusion](https://github.com/olegchomp/TouchDiffusion) [snippet]
- Derivative hosts a tutorial for a "magic mirror" built with StreamDiffusion in TouchDesigner, where a viewer's movements become AI-generated visuals in real time. — [Derivative tutorial](https://derivative.ca/community-post/tutorial/magic-mirror-effect-working-streamdiffusion-touchdesigner/71161) [snippet]
- **Decart MirageLSD** (July 2025) does "live-stream diffusion" on camera, video-call and game feeds:
  - Decart claims under 40 ms per frame and 24 FPS;
  - The Decoder reports 20 FPS at 768×432;
  - PetaPixel headlined it "the World's First AI Video That Can Transform Live Footage in Real Time".
  - Sources: [The Decoder](https://the-decoder.com/decart-launches-miragelsd-an-ai-model-that-transforms-live-video-feeds-in-real-time) [snippet]; [PetaPixel, 18 Jul 2025](https://petapixel.com/2025/07/18/mirage-is-the-worlds-first-ai-video-that-can-transform-live-footage-in-real-time) [snippet]
- **Overworld Waypoint-1** is a real-time interactive video diffusion model. — [HF blog](https://huggingface.co/blog/waypoint-1) [snippet]
- **Earlier per-frame style mirrors:** neural-style-mirror (Johnson et al. feed-forward style transfer on a webcam) and Gene Kogan's CubistMirror. — [neural-style-mirror](https://github.com/brandonherzog/neural-style-mirror) [snippet]; [CubistMirror](https://www.github.com/genekogan/CubistMirror) [snippet]

### Inferences
- The honest Heilmeier contrast: per-frame systems give a world that reacts every frame, but they cost a GPU per screen, flicker or drift, and alter the real people. "Generate once" gives exact real pixels, a stable world and laptop hardware. The cost is that the world is static and cannot react except through compositing.
- This is a design choice the team can defend. It is not an invention. Cite Teams Decorate as the same "generate once from a snapshot" idea applied to video calls.

### Gaps
- StreamDiffusion's headline throughput (about 91 FPS on an RTX 4090 in the paper, arXiv 2312.12491) is from background knowledge and was not verified here.
- Not checked: Zoom, Google Meet or Apple generative backgrounds; AI photo-booth kiosks (they restyle the person once per guest, which is the inverse of ours).

---

## C5. The boundary as a quantitative alignment test (seam drift in px) for generative edits

### Takeaway
**Verdict: PARTLY KNOWN; minor contribution.**
- Measuring structure preservation of generative edits is an established practice. The standard metric is DINO self-similarity "structure distance" (Tumanyan et al. 2022, used on PIE-Bench). Seam visibility is the central quality criterion in stitching and DuctTake.
- I found no metric that measures drift across a real|generated boundary in pixels. It is a natural, interpretable registration-error measurement, so present it as a sanity test, not a new metric.

### Cited Findings
- **DINO self-similarity structure distance** builds self-similarity matrices from DINO ViT features of the source and edited image and reports their difference; lower is better. It is standard in editing papers. — [Direct Inversion, arXiv 2310.01506](https://arxiv.org/pdf/2310.01506) [snippet]; [arXiv 2608.03059](https://arxiv.org/pdf/2608.03059) [snippet]
- It "can be unreliable when there are large semantic changes, such as big shifts in color distribution". That is exactly our case (night, underwater), and it motivates a geometric pixel measure instead. — [ReFlex, arXiv 2507.01496](https://arxiv.org/pdf/2507.01496) [snippet]
- GEditBench v2 uses a DINOv3 version computed only on the edited region. — [arXiv 2603.28547](https://arxiv.org/pdf/2603.28547) [snippet]
- DuctTake: "differences on the seams cause color bleeding", so seam quality is its central criterion. — [arXiv 2101.04772](https://arxiv.org/abs/2101.04772) [snippet]
- The team's own README already promises "measure seam drift ... under 2 pixels". — [garysun1/CS-180-Final-Project](https://github.com/garysun1/CS-180-Final-Project) [fetched]

### Inferences
- Strongest framing: "the line is self-checking". Any geometric drift from the img2img step shows up as a visible step at the seam, and we report it in pixels after homography re-alignment. That is easy to explain and fits CS180, but cite the DINO structure distance as the standard alternative and explain why it fits less well here.

### Gaps
- No search on edge- or Canny-based structure metrics (for example edge F-score) or on ControlNet-condition consistency metrics. These may be close neighbours.

---

## C6. "Grow" morph: walk the model's own partial-generation ladder with a two-band blend (exact endpoints, no double exposure)

### Takeaway
**Verdict: PARTLY KNOWN ingredients; the combination had no direct precedent found.**
- SDEdit's strength trade-off is the reason a strength ladder exists. The A1111 "Loopback Wave" script already animates denoising strength into videos.
- Two-band blending is Brown & Lowe's panorama method (low frequencies blended smoothly, high frequencies with a binary winner-take-all alpha), a simplification of Burt & Adelson. It is CS180 lecture content.
- Diffusion morphing (DiffMorpher, CVPR 2024) names "ghosting artifacts" as the failure of pixel-blend morphs.
- Ours applies the two-band rule in time, between strength rungs of one generation anchored to the plate. That is a tidy, explainable contribution, not a new algorithm.

### Cited Findings
- **SDEdit strength:** higher strength adds more noise and runs more denoising iterations. The "strength" knob comes from SDEdit's realism-versus-faithfulness trade-off. — [Diffusers img2img docs](https://huggingface.co/docs/diffusers/main/en/api/pipelines/stable_diffusion/img2img.md) [snippet]; [Differential Diffusion](https://huggingface.co/papers/2306.00950.md) [snippet]
- **Loopback Wave script** "modulates the denoising strength in a sinusoidal fashion, then produces a video". It has base and maximum strength settings. It is loopback (output fed back as input), not a ladder anchored to one source. — [rentry.co/sd-loopback-wave](https://rentry.co/sd-loopback-wave) [snippet]
- **Two-band blending** (Brown & Lowe, ICCV 2003 / IJCV 2007) splits images into a low-frequency layer blended smoothly over a wide transition and a high-frequency layer composited with a binary alpha. It is a simplification of Burt & Adelson. — [Durand comp-photo book, blending](https://people.csail.mit.edu/fredo/comp-photo-book/10-multiple-exposure-imaging-07-blending.html) [snippet]; [CS180 Fa25 Pyramids & Blending slides](https://cal-cs180.github.io/fa25/Lectures/PyramidsBlending.pdf) [snippet]
- **DiffMorpher** (Zhang et al., CVPR 2024) says earlier methods "fall short of creating new content beyond the given inputs, thus leading to unsatisfactory results like ghosting artifacts". It interpolates LoRAs and latents (slerp) instead. — [arXiv 2312.07409](https://arxiv.org/pdf/2312.07409) [snippet]; [CVPR 2024 open access](https://openaccess.thecvf.com/content/CVPR2024/papers/Zhang_DiffMorpher_Unleashing_the_Capability_of_Diffusion_Models_for_Image_Morphing_CVPR_2024_paper.pdf) [snippet]

### Inferences
- Exact endpoints are true by construction: the first rung is the plate and the last is the final world. Say so plainly rather than as a feature.
- "No ghosting" overclaims. The low band is still a crossfade, so colour blends. The per-pixel high-frequency switch can look like a dissolve or sparkle. Say: "avoids the double-exposure look of a plain crossfade because fine detail is never shown from two rungs at once."
- Why it works, to teach: the rungs share layout because each is the same generation stopped at a lower strength, so a cheap blend between neighbouring rungs looks like growth, not a cross-dissolve.
- Good link for the course: the method reuses Project 2 blending (Brown–Lowe/Burt–Adelson) along the time axis.

### Gaps
- Not searched: whether "strength sweep" morph videos from one source image are common on YouTube or Reddit (very likely), or whether anyone has blended between rungs with two bands.
- Unverified lead: "random dissolve / dither dissolve" transitions in classic video editing as precedent for the per-pixel threshold switch.

---

## C7. People recoloured to each world's light, with shadows transferred as the frame/plate ratio

### Takeaway
**Verdict: KNOWN technique, a lightweight application.**
- Ratio-based shadow transfer is the core of Chuang et al.'s "Shadow Matting and Compositing" (SIGGRAPH 2003): extract a shadow matte from lit and shadowed versions of a scene and composite it onto a new background.
- Recolouring a foreground to match a new background is image harmonization and colour transfer.
- The course PDF itself lists IC-Light and ZeroComp as heavier neighbours. Present ours as the simple, real-time-friendly version.

### Cited Findings
- **Chuang, Goldman, Curless, Salesin, Szeliski, "Shadow Matting and Compositing"** (ACM TOG / SIGGRAPH 2003, 22(3):494–500): I = βL + (1−β)S, where β is the shadow matte. They recover lit and shadow images by max/min compositing and composite the shadow into new scenes. — [UW GRAIL project page](https://grail.cs.washington.edu/projects/digital-matting/shadow-matting/) [snippet]; [SIGGRAPH history](https://history.siggraph.org/?p=115892) [snippet]
- **Omnimatte** associates shadows and reflections with each person's layer. — [CVPR 2021](https://openaccess.thecvf.com/content/CVPR2021/papers/Lu_Omnimatte_Associating_Objects_and_Their_Effects_in_Video_CVPR_2021_paper.pdf) [snippet]
- **LTX Clean Plate** removes people together with their cast shadows. — [LTX blog](https://ltx.io/blog/remove-people-and-shadows-from-video) [snippet]
- The course PDF lists IC-Light (relighting) and ZeroComp (zero-shot object compositing) under "Do something cool with diffusion". Staff know these as the high-end alternatives. — Course instructions PDF (local upload, p. 5)

### Inferences
- With a tripod plate, frame/plate is a per-pixel illumination ratio: below 1 means shadow. Multiplying the generated plate by that ratio is a Chuang-style shadow composite with the plate as the lit image. Cite Chuang.
- The recolouring is a global or statistical colour match to the world's palette. Call it "colour matching / harmonization", not "relighting".

### Gaps
- Unverified leads: Reinhard et al. 2001 "Color Transfer between Images"; quotient or ratio images (Shashua & Riklin-Raviv 2001; Liu, Shan, Zhang 2001); deep harmonization (Tsai 2017, DoveNet 2020). All are background knowledge only.

---

## Ranked list of the 10 closest neighbours

### Takeaway
The closest overall neighbours are Teams' "Decorate your background" (C1 + C4 architecture), FXjutsu's "Toon World" (C1 pipeline order) and Runway Aleph (the commercial "how is it done today"). None has the crossing boundary.

### Cited Findings
1. **Microsoft Teams Premium "Decorate your background"** (Ignite Nov 2023; generally available 2024). Snapshot the room, remove the user, inpaint, restyle once with img2img, show the live person in front.
   - Same idea as C1 and C4, for webcams.
   - No spatial split, crossing, depth rule or shadow handling (as far as found).
   - [Tech Community](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705) [snippet]
2. **FXjutsu "Toon World" / "Golden Statue"** (GitHub, 2026). Clean plate, then restyle the empty plate, then real people back on top, with an explicit rationale.
   - Same order as C1.
   - Offline video model, about 1–3 min per clip, matte boundary only, no line, depth or live mode.
   - [github.com/audriu/fxjutsu](https://github.com/audriu/fxjutsu) [fetched]
3. **Runway Aleph / Aleph 2.0** (July 2025). Prompt "change the season / time of day" on existing video while preserving the subject.
   - Same goal as our "worlds"; regenerates the whole clip.
   - Real pixels are not preserved; 5-s default; minutes per pass.
   - [Runway guide](https://help.runwayml.com/hc/en-us/articles/52150503729171-Aleph-2-0-Prompting-Guide) [snippet]
4. **Stephen Wilkes, "Day to Night"** (c. 2009–). One fixed-camera scene split spatially into two "times", with the artist choosing the boundary.
   - Closest aesthetic precedent for C2.
   - Stills, real photographs, no crossing people.
   - [Smithsonian](https://www.smithsonianmag.com/travel/how-photographer-stephen-wilkes-captures-full-day-single-image-180972935/) [snippet]
5. **Layered Neural Atlases** (SIGGRAPH Asia 2021). Edit one atlas, propagate to every frame, preserving shadows.
   - Academic ancestor of C1.
   - Needs per-video optimization; our tripod plate is the trivial atlas.
   - [SIGGRAPH archive](https://history.siggraph.org/?p=214129) [snippet]
6. **Omnimatte** (CVPR 2021) and **Generative Omnimatte** (2024). Background plus person layers that include shadows.
   - Ancestor of C1 and C7.
   - Per-video training or a heavy video model.
   - [CVPR paper](https://openaccess.thecvf.com/content/CVPR2021/papers/Lu_Omnimatte_Associating_Objects_and_Their_Effects_in_Video_CVPR_2021_paper.pdf); [arXiv 2411.16683](https://arxiv.org/abs/2411.16683) [snippet]
7. **StreamDiffusion "magic mirrors" (TouchDesigner) and Decart MirageLSD** (2023–2025). Per-frame real-time diffusion of a camera feed.
   - The C4 contrast class: GPU per frame, the real person is altered.
   - [TouchDiffusion](https://github.com/olegchomp/TouchDiffusion); [The Decoder](https://the-decoder.com/decart-launches-miragelsd-an-ai-model-that-transforms-live-video-feeds-in-real-time) [snippet]
8. **DuctTake** (EG 2012 / CGF 2013). Seam compositing of multiple takes of the same scene.
   - Neighbour for C2 (two versions of one scene joined spatially) and C5 (seam quality).
   - [arXiv 2101.04772](https://arxiv.org/abs/2101.04772) [snippet]
9. **Chuang et al., Shadow Matting and Compositing** (SIGGRAPH 2003). Shadow matte transferred to a new background.
   - Direct precedent for C7's ratio shadows.
   - [UW GRAIL](https://grail.cs.washington.edu/projects/digital-matting/shadow-matting/) [snippet]
10. **SDEdit strength plus the "Loopback Wave" strength animation, plus Brown & Lowe two-band blending.**
    - Together these cover C6's ingredients; DiffMorpher is the "ghosting" foil.
    - [Loopback Wave](https://rentry.co/sd-loopback-wave); [Durand book](https://people.csail.mit.edu/fredo/comp-photo-book/10-multiple-exposure-imaging-07-blending.html); [DiffMorpher](https://arxiv.org/pdf/2312.07409) [snippet]

Honourable mentions:
- Snap Lens Studio Portal ([docs](https://developers.snap.com/lens-studio/examples/lens-examples/portal)) and Shopify Reverse AR ([page](https://shopify.github.io/spatial-commerce-projects/Reverse-AR)) for C2/C4.
- Photo Clip Art and Hoiem et al. for C3 ([PDF](https://hci.iwr.uni-heidelberg.de/vislearn/HTML/publications/papers/2007/criminisi_siggraph_07.pdf)).
- DINO structure distance for C5 ([arXiv 2310.01506](https://arxiv.org/pdf/2310.01506)).
- LTX Clean Plate IC-LoRA for C1 ([LTX](https://ltx.io/blog/remove-people-and-shadows-from-video)).
- The per-frame student projects "Paint your Zoom Background" (CS639) and the AI 535 report for C1.
- Differential Diffusion for C3/C6.

### Inferences
- Positioning in one sentence: products and papers already restyle a whole scene behind real people (Teams, FXjutsu, Aleph, atlases). Our addition is a visible boundary that keeps one side real and lets people walk between the two versions, cheaply enough to run live.
- Mapping to the rubric's "what you started from": the team started from SD 1.5, ControlNet, LCM-LoRA, Depth Anything V2, the temporal median, homographies and two-band blending. The last three are CS180 course material. The human contribution is the crossing rules, the foot-depth rule, the ladder morph, the alignment test and the interactive/kiosk design.

### Gaps
- Ranks 1–3 rest partly on snippets because hosts were blocked. Teams' live-compositing behaviour is inferred, not quoted.

---

## Safe phrasings and phrasings to avoid

### Takeaway
Claim the experience and the cheap, exact design. Credit the components (restyle-once compositing, depth compositing, ratio shadows, two-band blending, strength ladders) to their owners. Hedge every novelty statement as "we did not find", never "first".

### Cited Findings
- Rubric: "championed what is excellent ... but didn't oversell", and "speak authoritatively and fluently about the relevant prior work ... what you started from and what your human contribution was". — Course instructions PDF (local upload, p. 2)
- FAQ: technically simple but creative or artistic projects qualify. — Course instructions PDF (p. 3)
- Prior art that rules out "first" claims: Teams Decorate ([snippet](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/decorate-your-background-in-microsoft-teams-premium-now/ba-p/4042705)), FXjutsu ([fetched](https://github.com/audriu/fxjutsu)), Runway Aleph ([snippet](https://help.runwayml.com/hc/en-us/articles/52150503729171-Aleph-2-0-Prompting-Guide)), MirageLSD ([snippet](https://petapixel.com/2025/07/18/mirage-is-the-worlds-first-ai-video-that-can-transform-live-footage-in-real-time)).

### Inferences — recommended safe phrasings

| Claim | Safe phrasing |
|---|---|
| C1 | "Like Microsoft Teams' 'Decorate your background' and layered-video methods (Neural Atlases, Omnimatte), we restyle the scene once instead of every frame. With a tripod, the 'atlas' is just the per-pixel median, a single clean plate, so the generated world is one image and cannot flicker." |
| C2 | "Our twist is a visible boundary. A spatial rule (a line, a depth threshold or a portal) decides per pixel whether you see the real frame or the restyled plate, and people switch worlds as they cross it. Photographers like Stephen Wilkes split one view into day and night. We do it live, with generated worlds and moving people. We did not find an existing tool or artwork that does this crossing effect." |
| C3 | "In depth mode, each person is treated as standing at the depth of their feet, the ground-contact cue from single-view geometry (Hoiem et al.; Photo Clip Art), so a whole person fades into the world as they walk away instead of being sliced in half." |
| C4 | "The kiosk generates each world once (seconds on a server), then composites at camera rate on a laptop, the same 'generate once' idea Teams uses for meeting backgrounds. Real-time diffusion mirrors (StreamDiffusion, MirageLSD) instead re-render every frame on a high-end GPU and change the people too. We trade a static world for exact real pixels, stability and cheap hardware." |
| C5 | "Because one side of the line is untouched, the line doubles as an alignment test: any shift the generator introduces shows up as a step at the seam, which we measure in pixels after homography re-alignment. We prefer it to DINO structure distance, which is known to be unreliable under large colour changes like night or underwater." |
| C6 | "'Grow' walks the model's own partial generations (SDEdit's strength ladder, from plate to final world) and blends neighbouring rungs with Brown & Lowe's two-band rule run over time: smooth crossfade for colour, a per-pixel switch for fine detail. Endpoints are exact by construction, and it avoids the double-exposure look of a plain crossfade." |
| C7 | "People are colour-matched to each world's palette. Shadows carry over as the frame/plate brightness ratio, a simple version of Chuang et al.'s shadow compositing (SIGGRAPH 2003); IC-Light or ZeroComp would be the heavier, learned alternatives." |
| Guarantees | "The background cannot flicker because it is a single image; pixels on the real side come straight from the camera, unmodified (before video compression)." |
| Scope | "Works for a locked-off camera and a mostly static scene. Moving foliage, water, lighting changes and people who stand still for a long time break the plate or the person mask." |

### Inferences — phrasings to avoid
- "First / novel method for video restyling", "nobody has done this", or "a new way to edit video with AI". Teams, FXjutsu, Aleph and atlases contradict it.
- "Real-time diffusion" or "real-time generative video". The generation is not real-time; only the compositing is. MirageLSD and StreamDiffusion own that phrase.
- "First real-time AI portal / mirror installation". Diffusion mirrors exist, and our searches of TikTok, Instagram and festivals were incomplete.
- "Bit-exact" in any statement about the delivered MP4 or WebGL output. Compression breaks it, and recoloured people are not exact. Limit it to "untouched source pixels in our pipeline".
- "Flicker-free video editing" with no qualifier. The person matte and recolour can still shimmer.
- "Relighting" or "physically correct shadows". It is a colour match plus a ratio multiply.
- "Zero ghosting" or "a new morphing algorithm". DiffMorpher-style methods exist, and the low band still crossfades.
- "A new metric for generative editing" for seam drift. Call it an alignment test or sanity check.
- Presenting the Spider-Verse glitch, flood or horizon wave as technical contributions. They are design flourishes; credit them as such.
- Repeating the old README's claims (FLUX.2, Qwen-Image-Edit or SDXL compared; depth as a "stretch goal") after the pipeline has changed. Update the README so the story stays consistent.

### Gaps
- The safe phrasings assume no closer precedent exists in unsearched places: TikTok/CapCut effect templates, Instagram Reels, SIGGRAPH Real-Time Live 2023–26 recordings, Ars Electronica archives, and earlier CS180/CS194-26 project galleries searched by keyword such as "median". A short manual check of TikTok and Instagram for "walk into AI world line" before the presentation would lower the remaining risk.
