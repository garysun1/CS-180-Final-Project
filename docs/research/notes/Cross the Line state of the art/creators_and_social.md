# Creators and social posts

> Research sweep of 27 November 2026. Evidence marks: **read** (the page was opened), **snippet** (search-result text only), **memory** (unverified). Social and product sites were blocked in the session, so product facts are mostly snippets.

## Summary

Most of the useful social-media evidence came from search snippets only. In this session reddit.com is refused by the search tool, and the fetch tool cannot resolve youtube/x/tiktok/instagram, runwayml, lumalabs, higgsfield, capcut, contra or most blogs. Only one page was actually fetched: the HunyuanLoom GitHub repo. The closest creator precedent is a known format, not a novelty. Runway Academy's Gen-1 "World jumping" lesson says it was "inspired by Martin Haerlin's viral Twitter post": you film yourself walking through a space and the world transforms at chosen moments. In 2026 the Higgsfield Academy course "Add AI VFX to Real Footage" teaches "Swap the world: the walking location swap" with Seedance 2.0: the subject stays as shot, the surroundings change, and a contact shadow is added. So "a real person walks and the world changes" is an established, taught genre. What these clips do not show is a spatial rule inside one shot (a line, ring or painted region) where the real side stays untouched and a person changes world when they step across. I found no TikTok, CapCut or Instagram effect that does this. The nearest are CapCut "split reality, half real half animated" edits and "the cut breaks on the sky" transitions, which are made by hand in the editor. Commercial video-to-video tools all regenerate the whole clip, with clip and cost limits: Luma Modify Video (June 2025, up to 10 s), Runway Aleph (July 2025) and Aleph 2.0 (May 2026), Higgsfield Genjutsu (2026, up to 30 s, about $0.68/s at 720p), and Decart Mirage/Lucy (live, 768x432). Users complain about flicker, identity drift, short clips and credits burning fast. These are exactly the axes where "one image per world, real people untouched" is a clear contrast. For the paint tool, the most useful things to build on are ComfyUI regional prompting by colour mask (Inspire pack, regional IPAdapter) and HunyuanLoom's experimental regional prompting over video. For the demo, the takeaways are Karen X. Cheng's "show the process" growth lesson, the walk-and-jump structure of World jumping, and a split-frame opening.

## Findings

### [Runway Academy: Gen-1 'World jumping' (inspired by Martin Haerlin's viral Twitter post)](https://academy.runwayml.com/gen1/gen1-world-jumping) (2023)
*tutorial · evidence: snippet · relevance 5/5*

- **What:** An official Runway tutorial for Gen-1 video-to-video. You record yourself walking through a space and capture a transformation at chosen moments. The page credits Martin Haerlin's viral Twitter post as the inspiration.
- **Relevance:** The closest 'person walks, the world changes' precedent, and a format audiences already know. Gen-1 restyles the whole frame in segments, so the person is restyled too. There is no spatial line, and the real side is not kept.
- **How we differ:** Theirs: whole-frame restyle per segment, a moving camera, cuts in time. Ours: a fixed camera, one plate image per world, real pixels on the real side, and the change triggered in space (where a person's feet are) rather than at a time cut.
- **What to take:** Name the lineage in related work ('world jumping'). Our demo can be the spatial version: one take, several worlds visible at once, people jumping as they cross.

### [Higgsfield Academy course 'Add AI VFX to Real Footage': 'Swap the world: the walking location swap' and 'World swap while driving'](https://higgsfield.ai/academy/courses/ai-vfx-real-footage/swap-the-world-the-walking-location-swap) (2026)
*tutorial · evidence: snippet · relevance 5/5*

- **What:** An 11-lesson course taught by Rus Syzdykov, using Seedance 2.0 at 4K. In the walking lesson the subject stays as shot and the surroundings change. Timing and performance are kept, and a contact shadow is added so the person does not look pasted in. The driving lesson reuses one locked drive across several worlds.
- **Relevance:** The current commercial state of the art for 'real person kept, world restyled', taught as a creator skill in 2026. It is very close to our C1 claim.
- **How we differ:** Theirs: a cloud video model over the whole clip, a moving camera, paid credits, the whole frame swapped. Ours: a tripod only, browser compositing, worlds that cannot flicker, partial and painted regions, crossing events, a live kiosk.
- **What to take:** Their emphasis on a contact shadow confirms that our carried-over shadow ratio is worth showing in the Layers view. 'Reuse one locked drive across many worlds' is our one-plate, many-worlds idea, so cite it.

### [FXjutsu 'Toon World' preset (LTX + IC-LoRAs on ComfyUI)](https://github.com/audriu/fxjutsu) (2026)
*repo · evidence: snippet · relevance 5/5*

- **What:** Alpha-Gen + Clean-Plate + Union Control: 'the world becomes anime, people stay real'. It restyles the empty plate so a cartoon copy does not peek out around the person. About 2-3 min per 5-s clip on an RTX 4090.
- **Relevance:** The closest open-source match to our substrate idea (restyle the plate, keep people). Found and fetched in earlier research; not re-fetched here.
- **How we differ:** It uses a video model over the clip with a GPU, and the matte is the person. It has no boundary, crossing or painted regions.
- **What to take:** Cite it as a direct neighbour. Its README sentence about restyling the plate supports our design choice.

### [Luma 'Modify Video' (Dream Machine, Ray2; later Ray3 Modify)](https://lumalabs.ai/news/introducing-modify-video) (2025-06-02)
*product · evidence: snippet · relevance 4/5*

- **What:** Transforms footage into 'completely different worlds, styles' while keeping 'the original motion and performance perfectly intact'. It reads pose, face, lip sync and scene structure. Clips up to 10 s, with strength presets. Ray3 Modify added character references. By 2026 the app calls it 'Video To Video'.
- **Relevance:** A direct competitor for the restyle-footage idea. The launch messaging is about keeping the performance, which is our 'real people stay real' pitch, achieved by regeneration.
- **How we differ:** Luma regenerates the person, keeping the performance but not the pixels. Clips are capped at 10 s and there is no spatial split.
- **What to take:** Contrast in the pitch: they keep the performance, we keep the actual pixels.

### [Runway Aleph (July 2025) and Aleph 2.0 / Edit Studio (May 2026)](https://runwayml.com/news/introducing-aleph-2-and-edit-studio) (2025-07-25 / 2026-05)
*product · evidence: snippet · relevance 4/5*

- **What:** Prompt-based editing of existing footage, including time-of-day and weather changes. Aleph 2.0's claim is that it 'only changes what you asked for and keeps everything else'. Users ask about clip-length limits (an Adobe community post asks whether 6 s is possible). A review site reports a $15/mo plan yields about 50 s of video.
- **Relevance:** The strongest whole-clip baseline for 'change the season of my real clip'.
- **How we differ:** It still regenerates the frame and runs as a cloud service with short clips. There is no line, ring or paint rule.
- **What to take:** Use as the baseline in the report. If credits allow, run one of our clips through Aleph and show it side by side, comparing flicker and face changes.

### [Contra tutorial: CapCut AI effects 'split reality: half real, half animated'](https://contra.com/community/324kP95G-transform-videos-with-cap-cut-ai-effects) (unknown (2025-2026))
*tutorial · evidence: snippet · relevance 4/5*

- **What:** Apply CapCut AI effects to real footage and composite half the frame as real and half as AI-animated: 'You end up with this split reality look. Half real, half animated.'
- **Relevance:** The closest consumer 'real/AI split in one frame' look we found, built by hand in CapCut. A static split with no crossing logic.
- **How we differ:** Manual and per video, and the AI half is usually a per-frame filter, so it flickers. People do not switch sides as a whole.
- **What to take:** This look already reads as 'cool' to TikTok audiences. Use it as our first-2-seconds frame, then break it with a crossing.

### [ComfyUI official 'Video Restyle' template (Wan 2.1 VACE + Canny + DepthAnything V2)](https://comfy.org/hub/workflows/video-restyle-5931e9bdf9db/) (2025-2026)
*repo · evidence: snippet · relevance 4/5*

- **What:** Restyles a video from a reference image using WanVideoVACEEncode with canny-edge and Depth Anything V2 control.
- **Relevance:** The same control stack we use (Depth Anything V2 plus canny), applied to every frame with a video model. It is the natural 'start where others left off' path to higher-fidelity worlds.
- **How we differ:** Video model per frame (GPU, possible flicker) against our single image per world.
- **What to take:** On Colab, run this template on our plate as a still (or a 1-frame video) to get better worlds than SD 1.5. It also makes a flicker baseline: restyle the whole clip with it and show the difference.

### [ComfyUI-HunyuanLoom (FlowEdit + experimental regional prompting over video)](https://github.com/logtd/ComfyUI-HunyuanLoom) (2025 (no date shown; 494 stars, 29 commits))
*repo · evidence: read · relevance 4/5*

- **What:** Nodes for HunyuanVideo: FlowEdit editing of existing video, and experimental regional prompting 'to prompt specific areas of a video over time'. The examples split the frame into left/right regions and first/second halves of the clip.
- **Relevance:** The nearest generative-model precedent for our paint tool (different prompts in different regions of one video). Its regions are coarse and the whole clip is regenerated.
- **How we differ:** Its regions are fixed rectangles or time halves, and people get regenerated. Ours are brush-painted, composited per pixel over real footage, with people switching as a whole.
- **What to take:** Cite it as the 'regional prompting in video' precedent. Its left/right example is a good visual comparison against our painted masks.

### [ComfyUI Inspire pack 'RegionalPromptColorMask' / regional IPAdapter by colour mask](https://www.runcomfy.com/comfyui-nodes/ComfyUI-Inspire-Pack/RegionalPromptColorMask-__Inspire) (2024-2026)
*repo · evidence: snippet · relevance 4/5*

- **What:** Each region of a colour-block mask image gets its own prompt (or IPAdapter style reference) within one diffusion pass. Variants such as 'Regional IPAdapter RGB - combine styles and characters' exist on Civitai/comfy.icu.
- **Relevance:** A direct building block for the paint tool: our painted multi-world mask is already a colour-block mask.
- **How we differ:** Image-only. It produces one image with several styles, not a person-aware composite.
- **What to take:** Export the painted canvas as a colour mask, then make one regional SD/SDXL pass over the plate. The result is a single coherent patchwork world with soft, model-consistent seams, as an alternative to blending separate worlds.

### [Higgsfield Genjutsu (video-to-video restyle / motion transfer / object swap)](https://www.media.io/video-effects/higgsfield-ai-genjutsu-tutorial.html) (2026 (one aggregator says September 2026; not confirmed))
*product · evidence: snippet · relevance 3/5*

- **What:** Upload footage and restyle it in one click while keeping motion, camera and lip sync. Documented for source clips up to 30 s. One aggregator lists about $0.681 per second at 720p. Reactions were mixed: praise for motion transfer, some 'scam' complaints about cost and access.
- **Relevance:** The latest whole-clip restyler aimed at creators. Useful for a cost and length comparison.
- **How we differ:** It regenerates every pixel, people included, and charges per second. Ours draws each world once on the CPU and keeps people real.
- **What to take:** One line on a comparison slide: cost per second against our 'one image per world, any length'.

### [CapCut guide: 'Turn an Everyday Clip Into a Fantasy Scene: The Cut Breaks on the Sky'](https://www.capcut.com/create/everyday-clip-to-fantasy-scene-ai-transition) (2026)
*tutorial · evidence: snippet · relevance 3/5*

- **What:** A real clip cuts to an AI clip of the same subject in the same pose and camera position, timed to a break on the sky line.
- **Relevance:** Real-to-AI transitions of the same place are a common template. Here the boundary is a cut in time, not a region in space.
- **How we differ:** A cut in time against our spatial split, and the person is regenerated in the AI clip.
- **What to take:** The idea of hiding the seam on a natural edge (the sky line) suggests snapping painted strokes or the line rule to edges or depth.

### [Kapwing December 2025 AI trends: the 'outfit transition' trend (Higgsfield)](https://www.kapwing.com/resources/december-2025-ai-trends-for-creators-brands/) (2025-12)
*post · evidence: snippet · relevance 3/5*

- **What:** Creators shoot each outfit in the exact same spot with consistent framing and lighting, then let Higgsfield generate the transition so the clothes shift while the background stays locked.
- **Relevance:** The mirror image of our idea: a locked background with the person changing. It shows that the fixed-camera, same-spot format spreads on TikTok.
- **How we differ:** Inverted: they change the person and keep the place. We change the place and keep the person.
- **What to take:** Tagline idea: 'The world changes. You don't.' It plays off a format the audience already knows.

### [Minimax H3 Video Restyling (Comfy hub workflow)](https://comfy.org/hub/workflows/minimax-h3-video-restyling-58a3f7167dba/) (2026)
*repo · evidence: snippet · relevance 3/5*

- **What:** Restyles a video's background and lighting from a guide key-art image using open-weights Minimax H3. It can swap the person too. Its prompt guidance keeps the camera and motion fixed.
- **Relevance:** Another 2026 open workflow for background restyling with a fixed camera.
- **How we differ:** Regenerates the whole frame.
- **What to take:** A possible higher-quality plate restyler on a Colab GPU.

### [RunComfy 'ComfyUI Vid2Vid Part 1: composition and masking'](https://www.runcomfy.com/tr/comfyui-workflows/comfyui-vid2vid-part1-composition-and-masking) (2024)
*tutorial · evidence: snippet · relevance 3/5*

- **What:** Automated subject masking, mask refinement, and compositing of the animated subject over a separately processed background.
- **Relevance:** The community 'restyle background, keep or composite the subject' workflow. It shows that the mask-and-composite approach is standard practice.
- **How we differ:** Offline and per frame, with no fixed-plate guarantee.

### [Corridor Crew 'Anime Rock, Paper, Scissors'](https://knowyourmeme.com/memes/corridor-digital-rock-paper-scissors-ai-anime-controversy) (2023-02)
*post · evidence: snippet · relevance 3/5*

- **What:** Green-screen actors were restyled with Stable Diffusion + DreamBooth, deflickered in DaVinci Resolve, over Unreal Engine backgrounds. Over 2.2 million views in 8 days. The backlash cited faces that don't read emotion and mouths 'open eerily too wide'.
- **Relevance:** The inverse of our split (people restyled, backgrounds built separately). The audience reaction confirms that restyling faces is what people dislike.
- **How we differ:** They regenerate people. We deliberately do not.
- **What to take:** Pitch evidence: the most-watched AI restyle short drew criticism for exactly the face artefacts we avoid.

### [Decart Mirage / MirageLSD, now Lucy 2.0](https://petapixel.com/2025/07/18/mirage-is-the-worlds-first-ai-video-that-can-transform-live-footage-in-real-time) (2025-07)
*product · evidence: snippet · relevance 3/5*

- **What:** Live video-to-video restyling at 20 fps and 768x432, with a claimed latency under 40 ms. Preset themes such as Comic Book, K-POP and Steampunk can restyle YouTube clips or a webcam. Decart now lists Lucy 2.0 real-time editing with API access.
- **Relevance:** The live counterpart to our kiosk. It restyles everything, people included.
- **How we differ:** Needs a GPU in the cloud, whole-frame and low resolution. Ours runs locally at camera rate because the world is a precomputed image. I could not find anything on 'Delulu'.
- **What to take:** Kiosk framing: 'live like Mirage, but your face is still yours, and the room is the same room'.

### [Karen X. Cheng on a16z: behind-the-scenes process as the growth lever](https://rosetta.to/u/a16z/ai-and-the-creator-economy-with-karen-x-cheng) (2023-2024)
*post · evidence: snippet · relevance 3/5*

- **What:** An episode summary says that sharing the behind-the-scenes process, rather than only the polished output, was the key unlock for her following. It also mentions her EbSynth-based AI video work.
- **Relevance:** Advice on demo format from the best-known creator in this niche.
- **What to take:** Make our 60-90 s demo half process: plate, then worlds, then mask, then composite, as a layer breakdown.

### [AI video flicker and identity-drift complaints (LTX blog; Hugging Face forum)](https://ltx.io/blog/temporal-consistency-in-ai-video) (2025-2026)
*post · evidence: snippet · relevance 3/5*

- **What:** LTX lists 'flickering, warble, identity drift, and motion discontinuities'. A Hugging Face forum thread reports faces drifting across clips in ComfyUI projects, blamed on how AnimateDiff and SVD generate keyframes. Guides recommend shorter clips and locked references.
- **Relevance:** Documents the pain points that our design (static plate, untouched people) removes by construction.
- **What to take:** Quote these terms on a 'problems we avoid' slide.

### [CapCut Director Mode 'fall out of a portal' tutorial (and its no-AI fixed-camera alternative)](https://www.tiktok.com/discover/how-to-use-the-portal-effect) (2025-2026)
*tutorial · evidence: snippet · relevance 2/5*

- **What:** Film yourself at one location, then 'fall out of a portal' at a second. An AI agent builds the final video from both clips. The creator notes the same look can be made without AI by filming three positions from a fixed camera and stacking the cutouts.
- **Relevance:** Portal trends on TikTok are about teleporting between different places, not restyling the same place. They confirm that a fixed camera plus cutouts is a known creator trick.
- **How we differ:** A different place, not a restyled version of the same place.

### [Krea blog: 'The Westies' (Cream Productions): real and AI material in the same shots](https://www.krea.ai/blog/spot-the-ai) (2026)
*post · evidence: snippet · relevance 2/5*

- **What:** Generated 1980s New York shots cut with live action. Krea says the AI and filmed material 'sit inside the same shots, trading places'.
- **Relevance:** Professional hybrid shots where real and generated material share a frame. A promotional source.
- **How we differ:** Offline VFX, with no interaction.

### [FilmBro 'Artistic Walk Through Worlds' (After Effects) / PremiumBeat walkthrough portal transition](https://www.filmbro.com/blogs/tutorials/artistic-walk-through-worlds-after-effects) (unknown)
*tutorial · evidence: snippet · relevance 2/5*

- **What:** After Effects tutorials, with no plugins, where a person walks through a portal or wipe and the world behind changes. They are built from masks and layer order.
- **Relevance:** The pre-AI hand-masked version of our crossing. It shows that the look was laborious and done by hand.
- **How we differ:** Manual rotoscoping for each shot. Ours is automatic from the plate difference.
- **What to take:** Our pitch: the tool automates what After Effects artists rotoscope by hand.

### [TikTok 'AI walk effect' / 'pimpwalk entrance' templates (2026)](https://miraflow.ai/blog/ai-walk-effect-runway-video-prompts-2026) (2026-10)
*post · evidence: snippet · relevance 2/5*

- **What:** One-photo templates (CyberLink, FlexClip, Media.io, Vidu; Seedance, Kling, Runway, Veo models) generate a person walking. The 'hold-the-door pimpwalk' variant was packaged as a preset by late October 2026.
- **Relevance:** The dominant 2026 consumer 'walk' and 'door' trends regenerate the person from a photo. There is no real footage and no same-place restyle.
- **How we differ:** Everything is generated. We keep the footage.
- **What to take:** An 'AI door/portal' search mostly returns these, which is evidence that our real-footage boundary effect is not a template yet.

### [Bilawal Sidhu, 'I Accidentally Started an AI Video Trend' (scribble-to-video)](https://aitoolsreview.co.uk/video/i-accidentally-started-an-ai-video-trend) (2026-06-05)
*post · evidence: snippet · relevance 2/5*

- **What:** An aggregator listing for a Sidhu YouTube video. A simple 'scribble-to-video' experiment became a stress-test trend pitting Google's model against Seedance.
- **Relevance:** Shows how a simple, repeatable demo format from a creator spreads. Not about restyling a place.
- **What to take:** A simple, copyable challenge format, for example 'paint your street into 3 worlds'.

### [TikTok 'Walking Filter' discover page (a #portal post)](https://www.tiktok.com/discover/walking-filter?lang=en) (2026-09-28)
*post · evidence: snippet · relevance 1/5*

- **What:** A discover page of AI walking-filter posts. One post jokes about walking into the filter under #portal.
- **Relevance:** A weak signal that 'walk into the AI world' is a hook people use, but with generated people.

## Ideas to borrow

- **Make the demo a one-take spatial 'world jumping' walk. A person walks along a path across a line, a ring and painted patches, jumping to a new world at each crossing, with no cuts.** Source: Runway Academy Gen-1 'World jumping' (after Martin Haerlin) https://academy.runwayml.com/gen1/gen1-world-jumping. The audience already knows this format, and our version shows its distinctive feature: several worlds visible at once in one unbroken shot, with the real side untouched. *Effort: Hours of filming plus compositing in the existing tool. Needs a tripod shoot (Sather Gate).*
- **Open on a 'split reality' first frame (half real, half winter), then a person walks across the seam inside the first 2 seconds.** Source: Contra CapCut 'half real, half animated' tutorial https://contra.com/community/324kP95G-transform-videos-with-cap-cut-ai-effects. The split-frame look already works as a hook on TikTok. Adding a crossing turns a static gimmick into an event. *Effort: Hours; existing line rule.*
- **Export the painted multi-world canvas as a colour-block mask and run one regional-prompt pass (Inspire RegionalPromptColorMask or regional IPAdapter) over the plate, producing a single patchwork world with model-coherent seams.** Source: ComfyUI Inspire pack https://www.runcomfy.com/comfyui-nodes/ComfyUI-Inspire-Pack/RegionalPromptColorMask-__Inspire. Painted regions currently blend separately generated worlds. One regional pass gives seams the model has drawn itself, which looks better and is a new 'paint, then generate' mode. *Effort: 1-2 days; Colab GPU for ComfyUI, or diffusers attention masking on CPU (slow).*
- **Upgrade world quality by running the ComfyUI Wan 2.1 VACE Video Restyle template (Depth Anything V2 + canny, the controls we already compute) on the plate on a free Colab GPU, still keeping one image per world.** Source: ComfyUI Video Restyle template https://comfy.org/hub/workflows/video-restyle-5931e9bdf9db/. It addresses the 'SD 1.5 worlds are low fidelity' weakness and starts from a shared workflow instead of from scratch. *Effort: 1 day; Colab GPU (14B is heavy, so use a 1.3B/fp8 variant).*
- **Baseline comparison: process the same tripod clip with a whole-clip restyler (Wan VACE template, or Aleph/Luma if credits allow) and show it side by side with ours, zoomed on faces and the background.** Source: Runway Aleph 2.0 https://runwayml.com/news/introducing-aleph-2-and-edit-studio ; LTX temporal consistency https://ltx.io/blog/temporal-consistency-in-ai-video. It turns the pitch claims (no flicker, real faces) into a visible result in the presentation and the report. *Effort: Hours to a day; GPU or paid credits.*
- **Add a 'contact shadow' toggle to the Layers view, showing the shadow ratio layer on and off.** Source: Higgsfield 'walking location swap' lesson https://higgsfield.ai/academy/courses/ai-vfx-real-footage/swap-the-world-the-walking-location-swap. Professional creators single out the contact shadow as what stops people looking pasted in. We already compute it, so we should show it. *Effort: Hours; compositor.js.*
- **Spend half of the 60-90 s demo on a process reel: raw clip, then the median plate building up, then the worlds drawn once, then the painted masks, then the composite.** Source: Karen X. Cheng on a16z https://rosetta.to/u/a16z/ai-and-the-creator-economy-with-karen-x-cheng. Behind-the-scenes content is what grew the best-known creator in this niche, and for a CV course it shows the computational-photography content. *Effort: Hours of screen recording.*
- **A one-slide cost and length table: Luma Modify up to 10 s; Aleph about 50 s per $15/mo (review-site figure); Genjutsu about $0.68/s, up to 30 s; Mirage at 768x432. Against ours: one image per world, any clip length, CPU.** Source: Luma https://lumalabs.ai/news/introducing-modify-video ; Genjutsu https://www.media.io/video-effects/higgsfield-ai-genjutsu-tutorial.html ; Mirage https://petapixel.com/2025/07/18/mirage-is-the-worlds-first-ai-video-that-can-transform-live-footage-in-real-time. It answers 'why not just use Runway?' in five seconds. *Effort: Hours; verify the prices by hand first.*
- **Use the tagline 'The world changes. You don't.' as the reverse of the 2025 'outfit transition' trend, where the person changes in a locked spot.** Source: Kapwing December 2025 trends https://www.kapwing.com/resources/december-2025-ai-trends-for-creators-brands/. It plays off a format the audience already recognises and states the key property in five words. *Effort: Minutes.*
- **Snap painted strokes and the line rule to strong image edges or depth discontinuities (the sky line, a doorway), so seams sit on natural boundaries.** Source: CapCut 'The Cut Breaks on the Sky' https://www.capcut.com/create/everyday-clip-to-fantasy-scene-ai-transition. Editors hide AI transitions on natural edges. Edge-aware painting (we already have canny and depth maps) would make seams read as intentional. *Effort: 1-2 days; paint.js with the existing depth and canny maps.*

## Not reached or not verified

- reddit.com is refused by the search tool in this session, so no r/StableDiffusion, r/comfyui, r/aivideo, r/vfx or r/AfterEffects threads or user quotes were collected. A human should search reddit for 'static camera restyle', 'clean plate comfyui', 'vace background only', 'aleph changed face'.
- These hosts could not be fetched (DNS blocked): youtube, x, tiktok, instagram, runwayml (academy), lumalabs, higgsfield, capcut, contra, aitoolsreview, stepintoscene. Every social item is snippet-level. View counts are missing except Corridor's (2.2M in 8 days).
- I could not find Martin Haerlin's original viral post (search on 'Haerlin' returned noise). Check x.com/martinhaerlin and Runway's 2023 Gen-1 posts by hand.
- Not found: Decart 'Delulu', a 'time warp scan + AI' crossover, Paul Trillo's or Nathan Shipley's same-place restyle walks, Jon Finger, enigmatic_e or Purz static-camera tutorials. Search their YouTube channels and X accounts directly.
- Search inside the TikTok and CapCut apps for 'AI portal', 'real vs AI', 'split reality', 'walk into another world', 'season change AI', 'AI world switch', 'half anime'. Inside Instagram search Reels for #aiportal and #multiverse. App effect galleries are not indexed by web search.
- Genjutsu's release date (September 2026?) and price come from aggregators. Aleph's '$15 = about 50 s' comes from a review site. Verify on the official pricing pages.
- SIGGRAPH 2026 Real-Time Live and Ars Electronica 2026 were not searched in this pass.

## Notes

## Method and access
I followed the researcher method with about 30 tool calls. Nearly every social and company host was unreachable for fetching, and reddit.com is refused even inside search. Evidence is therefore mostly **snippet**. The only page fetched in this pass is github.com/logtd/ComfyUI-HunyuanLoom. FXjutsu was fetched in earlier research and is cited from those notes.

## 1. Boundary or "portal" videos: what exists
- **"World jumping" is a named, taught format from 2023.** Runway Academy's Gen-1 lesson ([link](https://academy.runwayml.com/gen1/gen1-world-jumping)) is "inspired by Martin Haerlin's viral Twitter post": record yourself walking through a space and capture a transformation at chosen moments. Gen-1 restyles the whole frame, so the person is restyled too, and segments are joined in time.
- **The 2026 commercial version keeps the person.** Higgsfield's course "Add AI VFX to Real Footage" (11 lessons, Rus Syzdykov, Seedance 2.0 at 4K) opens with "Swap the world: the walking location swap". The subject stays as shot, the surroundings change, and a contact shadow is added. A later lesson reuses "the same locked drive across several different worlds" ([course](https://higgsfield.ai/academy/courses/ai-vfx-real-footage), [lesson](https://higgsfield.ai/academy/courses/ai-vfx-real-footage/swap-the-world-the-walking-location-swap)).
- **Honest positioning.** "A real person walks and the world becomes an AI version" is no longer novel as an aesthetic. What I still could not find anywhere is:
  - a **spatial** rule inside one continuous shot (a line, ring, depth or painted region) where the real side is untouched;
  - people who switch as a whole when their feet cross;
  - several worlds visible at once;
  - a flicker-free world drawn once;
  - a live kiosk version.
  The C2 verdict "partly known, crossing is the strongest novelty" still stands, but related work should now cite World jumping and Higgsfield's world swap.
- **The TikTok "portal" and "door" trends of 2025-2026 mean something else.**
  - Teleporting between different locations: CapCut Director Mode "fall out of a portal" ([TikTok discover](https://tiktok.com/discover/how-to-use-the-portal-effect)).
  - One-photo generated walks: the "AI walk effect" and the October 2026 "pimpwalk hold-the-door" template ([miraflow](https://miraflow.ai/blog/ai-walk-effect-runway-video-prompts-2026), [makeviral](https://www.makeviral.ai/templates/pimpwalk-entrance-ai-trend)).
  Both regenerate people or places entirely.
- **Hand-made split frames exist in CapCut** ("half real, half animated", [Contra](https://contra.com/community/324kP95G-transform-videos-with-cap-cut-ai-effects)). So does same-pose real-to-AI cutting timed to "the cut breaks on the sky" ([CapCut](https://www.capcut.com/create/everyday-clip-to-fantasy-scene-ai-transition)). These are the nearest consumer looks.
- **The inverse trend.** Kapwing's December 2025 roundup describes "outfit transitions": a locked spot and locked background, with the person changing via Higgsfield ([Kapwing](https://www.kapwing.com/resources/december-2025-ai-trends-for-creators-brands/)).
- **Pre-AI version.** After Effects "walk through worlds" tutorials do the crossing by hand-animated masks ([FilmBro](https://www.filmbro.com/blogs/tutorials/artistic-walk-through-worlds-after-effects), [PremiumBeat](https://www.premiumbeat.com/blog/portal-walk-through-transition-after-effects)).

## 2. Restyling the background while keeping the subject: tools and workflows
- **Whole-clip regenerators**, all of which regenerate people:
  - Luma Modify Video (2 June 2025; Ray2; up to 10 s; "keeping the original motion and performance perfectly intact"; Ray3 Modify later; renamed "Video To Video" in the app by 2026) ([Luma](https://lumalabs.ai/news/introducing-modify-video), [TechRadar](https://www.techradar.com/computing/artificial-intelligence/luma-labs-new-modify-video-tool-can-reimagine-scenes-without-reshooting)).
  - Runway Aleph (25 July 2025) and Aleph 2.0 / Edit Studio (May 2026), which claims to change "only what you asked for" ([Runway](https://runwayml.com/news/introducing-aleph-2-and-edit-studio)).
  - Higgsfield Genjutsu (2026; up to 30 s; about $0.681/s at 720p per an aggregator) ([media.io](https://www.media.io/video-effects/higgsfield-ai-genjutsu-tutorial.html)).
  - Decart Mirage/LSD (July 2025, 20 fps at 768x432, under 40 ms claimed), now Lucy 2.0 ([PetaPixel](https://petapixel.com/2025/07/18/mirage-is-the-worlds-first-ai-video-that-can-transform-live-footage-in-real-time), [Decart](https://decart.ai/mirage-lsd)).
- **Open workflows:**
  - The ComfyUI official Video Restyle template uses Wan 2.1 VACE with CannyEdgePreprocessor and DepthAnything_V2, the same controls as ours ([Comfy hub](https://comfy.org/hub/workflows/video-restyle-5931e9bdf9db/)).
  - Minimax H3 Video Restyling restyles background and lighting from key art with a fixed camera ([Comfy hub](https://comfy.org/hub/workflows/minimax-h3-video-restyling-58a3f7167dba/)).
  - RunComfy Vid2Vid Part 1 covers masking and compositing ([RunComfy](https://www.runcomfy.com/tr/comfyui-workflows/comfyui-vid2vid-part1-composition-and-masking)).
  - The Wan 2.2 Animate template uses SAM2 for subject isolation ([Comfy](https://comfy.org/workflows/video_wan2_2_14B_animate-c2c4b45b7df5/)).
  - FXjutsu Toon World restyles the clean plate so people stay real ([GitHub](https://github.com/audriu/fxjutsu)).

## 3. Painted regions with different styles (nothing was searched for this before)
- **HunyuanLoom (fetched)** offers FlowEdit for existing video plus *experimental* regional prompting "to prompt specific areas of a video over time". Its examples use left/right halves and first/second halves of the clip. The page does not mention mask-based regions. 494 stars ([GitHub](https://github.com/logtd/ComfyUI-HunyuanLoom)).
- **Image-side building blocks:**
  - The Inspire pack's RegionalPromptColorMask (a colour-block mask, one prompt per colour) ([RunComfy](https://www.runcomfy.com/comfyui-nodes/ComfyUI-Inspire-Pack/RegionalPromptColorMask-__Inspire)).
  - "Regional IPAdapter RGB - combine styles and characters" ([comfy.icu](https://comfy.icu/models/1572367/Regional-IPAdapter-RGB-combine-styles-and-characters)).
  - Attention masking that pins each IPAdapter reference to a region ([Runflow](https://www.runflow.io/blog/comfyui-attention-masking)).
  - RES4LYF ClownRegionalConditioning, with temporal variants for video ([comfy.icu](https://comfy.icu/node/ClownRegionalConditioning)).
- **No verified example of a brush-painted, per-region style patchwork over real footage with people kept real.** The nearest social analogue is a split-screen "top half photoreal, bottom half anime, same choreography" clip ([alici.ai](https://alici.ai/formulas/media/rioaigc/c757a50d-58b6-5cea-82b0-d4a390bbc8e3-chun-li-vs-mai-shiranui-ai-video)), which is fully generated.

## 4. Complaints (snippet-level; Reddit was unreachable)
- Symptom names: "flickering, warble, identity drift, and motion discontinuities" ([LTX](https://ltx.io/blog/temporal-consistency-in-ai-video)).
- Faces drift across clips in ComfyUI projects, blamed on AnimateDiff/SVD keyframing ([HF forum](https://discuss.huggingface.co/t/1st-movie-clip/175306)).
- Aleph clip length: a user asks whether 6 s is possible ([Adobe community](https://community.adobe.com/t5/adobe-firefly-bugs/runway-aleph-is-not-accesible-firefly/idi-p/15637114)).
- Credit burn: "$15/mo plan only yields ~50 seconds" (review aggregator, [Zemith](https://www.zemith.com/en/learn/runway-review.md)). Unverified.
- Genjutsu: praise for motion transfer, and "scam" complaints over cost and access ([aichief](https://aichief.com/ai-video-tools/higgsfield-genjutsu/)).
- Corridor's Anime Rock, Paper, Scissors (February 2023; over 2.2M views in 8 days): the backlash centred on faces whose emotions don't read and mouths "open eerily too wide". It was made with SD + DreamBooth + Resolve deflicker over Unreal backgrounds ([KYM](https://knowyourmeme.com/memes/corridor-digital-rock-paper-scissors-ai-anime-controversy)).

## 5. Demo formats (examples, with the counts I could find)
1. Corridor's ARPS short plus its VFX-reveal "how we made it" video: 2.2M views in 8 days ([Fox Renderfarm on the reveal](https://www.foxrenderfarm.com/news/corridor-digital-drops-vfx-reveal-of-anime-rock-paper-scissors/)).
2. Haerlin-style world jumping: a single walk with transformations at moments (no count found).
3. CapCut split-reality half/half frame as a static hook.
4. "The cut breaks on the sky": the transition is timed to a natural edge.
5. Kapwing outfit transitions: same spot, locked frame, repeated across a series.
6. Karen X. Cheng: show the process, not only the result (a16z summary).
7. Bilawal Sidhu (5 June 2026): a simple copyable experiment became a model-vs-model challenge trend ([aggregator](https://aitoolsreview.co.uk/video/i-accidentally-started-an-ai-video-trend)).

I could not get view counts for items 2-7.

## People and accounts to follow
- Martin Haerlin (world jumping).
- Rus Syzdykov (Higgsfield real-footage VFX).
- Karen X. Cheng (process-first AI video).
- Corridor Crew.
- Bilawal Sidhu.
- Paul Trillo (Runway shorts; his Gen-1 restyle use is not confirmed).
- The logtd GitHub account (HunyuanLoom).
- The audriu GitHub account (FXjutsu).
- The ComfyUI hub template authors.

enigmatic_e, Purz, Jon Finger and Nathan Shipley were not confirmed in any search result; check them by hand.
