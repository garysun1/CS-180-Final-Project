# Positioning research for "Cross the Line": real-time generative video, consumer AI effects, AR portals, time-blend photography, diffusion morphing, classic transitions, and CS180 course material

Research date: 2026-11-23. The two existing notes cover art installations, AI mirrors (TouchDiffusion), film precedents, rephotography (Bae et al., Historypin, WhatWasThere, Berkeley Lab Then & Now) and browser tech. This note does not repeat those.

**How each claim was checked.** Each finding is tagged:
- **[fetched]**: I read the page myself.
- **[snippet]**: the claim comes from a search-engine summary only.

**Sites I could not reach.** These hosts could not be fetched from this session (they fail DNS under the session's network policy): decart.ai, www.krea.ai, the-decoder.com, runway.com, petapixel.com, techcrunch.com, inst.eecs.berkeley.edu, people.csail.mit.edu, courses.cs.washington.edu and pages.cs.wisc.edu. They would have to be allowed in the session's network settings to fetch them. Claims from those sites are all [snippet].

**How I got the CS180 specs.** I read the course-site source in the public GitHub repos `cal-cs180/fa24`, `cal-cs180/fa25` and `cal-cs180/cal-cs180.github.io` (fa26 folder) through raw.githubusercontent.com.

## 1. Real-time generative video, 2023–2026 (Decart, StreamDiffusion v1/v2, Krea Realtime, Daydream/Livepeer, Runway, Pika)

### Takeaway
Every real-time system found regenerates the whole frame, person included, on every frame or chunk:
- **Hardware:** they need an RTX 4090 at minimum, and more often one or more H100s or a B200.
- **Speed:** roughly 11–60 fps at 360p–1080p.
- **Stability:** the vendors fight flicker and identity drift with tricks such as sink tokens, KV-cache recomputation and "history augmentation".

Cross the Line inverts this. It generates once, on a CPU, in seconds, then composites real pixels at camera rate in WebGL. So the generated region cannot flicker (it is a fixed image), and the person cannot drift in identity (they are the real pixels, recoloured).

### Cited Findings
**StreamDiffusion (v1), Kodaira et al.** (arXiv 19 Dec 2023, v2 8 Jul 2025, ICCV 2025)
- Up to 91.07 fps for image-to-image on one RTX 4090, and 59.56× the throughput of Diffusers' AutoPipeline.
- Speed comes from three techniques: Stream Batch, residual CFG (RCFG) and a stochastic similarity filter. — [arXiv 2312.12491v2](https://arxiv.org/abs/2312.12491v2); [ICCV 2025 paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Kodaira_StreamDiffusion_A_Pipeline-level_Solution_for_Real-Time_Interactive_Generation_ICCV_2025_paper.pdf) [snippet]
- Flicker, measured by the StreamDiffusionV2 authors: StreamDiffusion scores Warp Error 117.01 and Temporal CLIP 95.24, against 73.31 and 98.51 for StreamDiffusionV2. The V2 paper says frame-by-frame image generation "introduces flicker and drift". — [arXiv 2511.07399v2 HTML](https://arxiv.org/html/2511.07399v2) [fetched]
- Difference from Cross the Line: StreamDiffusion re-runs img2img on every webcam frame, so the person and background are both regenerated and flicker. Ours runs the model once per world, and only the person mask changes each frame.

**StreamDiffusionV2** (arXiv 2511.07399; v1 10 Nov 2025, v2 22 Feb 2026; MLSys 2026)
- Authors are from UT Austin, UC Berkeley, MIT, Stanford, Nunchaku AI and others.
- Throughput without TensorRT or quantization:
  - 4×H100: 58.28 fps (14B model) and 64.52 fps (1.3B model). With more denoising steps, the abstract gives 31.62 fps (14B) and 61.57 fps (1.3B).
  - Single H100, 1.3B model, 1 step: 42.26 fps at 480p and 61.57 fps at 512².
  - 4×RTX 4090: "nearly 16 FPS in 480P and 24 FPS in 512×512".
- First frame in 0.47 s at 16 fps and 0.37 s at 30 fps. Under a 1 s budget it misses 0.2% of deadlines, with 21 ms mean jitter.
- Stability tools: sink tokens ("stabilizes global style across frames"), a rolling KV cache, RoPE refresh and a motion-aware noise controller.
- The VAE takes about 30% of inference time. — [arXiv abs](https://arxiv.org/abs/2511.07399); [HTML v2](https://arxiv.org/html/2511.07399v2) [fetched]; [MLSys 2026 PDF](https://proceedings.mlsys.org/paper_files/paper/2026/file/698cfaf72a208aef2e78bcac55b74328-Paper-Conference.pdf) [snippet]
- Runway's Characters paper says the two open-source real-time systems it benchmarked, at 4 denoising passes, "miss real time or add over a second of latency (one by estimate), at a third to half of our resolution". — [arXiv 2611.05642](https://arxiv.org/abs/2611.05642) [fetched]
- Difference from Cross the Line: a video diffusion model streams every frame on 1–4 datacenter GPUs. Our per-frame cost is one fragment shader on a laptop, and the "world" is a single fixed image.

**Krea Realtime 14B** (Oct/Nov 2025)
- 11 fps text-to-video on a single NVIDIA B200, with 4 inference steps and about 1 s to the first frame.
- Distilled from Wan 2.1 14B with Self-Forcing. Apache-2.0.
- Accepts "real videos, webcam inputs, or canvas primitives" for streaming video-to-video.
- Fights drift with "KV Cache Recomputation" and "KV Cache Attention Bias".
- Recommends torch.compile, SageAttention and FP8 on H100-class GPUs. — [Hugging Face model card](https://huggingface.co/krea/krea-realtime-video) [fetched]
- Release month comes from secondary coverage only. — [CGWORLD](https://cgworld.jp/flashnews/01-202511-Krea-Realtime-14B.html) [snippet]
- The precedents note already covers Krea's 2024 SIGGRAPH Real-Time Live appearance.
- Difference from Cross the Line: webcam video-to-video on Krea regenerates the person every chunk on a B200. We keep the person's real pixels and need no GPU server.

**Daydream / Livepeer**
- 6 Nov 2025: Daydream released Scope (an open-source toolkit for real-time video and world-model workflows) and added SDXL to its StreamDiffusion fork. — [BusinessWire](https://www.businesswire.com/news/home/20251106860538/en/Daydream-Launches-Scope-and-Expands-StreamDiffusion-with-SDXL-Support-Advancing-the-Open-Source-Real-Time-AI-Video-Ecosystem) [snippet]
- Livepeer's docs say StreamDiffusion is the primary live-video model on the network and reaches "30+ fps on an RTX 4090". — [Livepeer orchestrator guide](https://docs.livepeer.org/v2/orchestrators/guides/ai-and-job-workloads/realtime-ai-setup) [snippet]
- The same docs call real-time AI "beta"; frames route through gateway → orchestrator → ai-runner (ComfyUI). — [Livepeer realtime AI overview](https://docs.livepeer.org/v2/developers/build/ai-and-agents/realtime-ai/overview) [snippet]
- ComfyStream ported Daydream's pipeline, and StreamDiffusion V2 adds video-to-video. — [ComfyStream docs](https://docs.livepeer.org/v2/developers/build/ai-and-agents/realtime-ai/ComfyStream/overview) [snippet]
- Difference from Cross the Line: Daydream depends on remote GPU nodes and regenerates every frame. Our kiosk runs offline on a laptop after one local generation.

**Decart Oasis** (31 Oct 2024, with Etched)
- A playable Minecraft-like world model: 360p at 20 fps on H100s. Etched's Sohu chip is claimed to reach up to 4K.
- Other outlets report 460p or 720p, so resolution figures conflict.
- Weaknesses: it "forget[s]" level layouts, you can play only "for minutes at a time", and it is "prone to hallucinations". — [Decart publication](https://decart.ai/publications/oasis-interactive-ai-video-game-model); [TechCrunch](https://techcrunch.com/2024/10/31/decarts-ai-simulates-a-real-time-playable-version-of-minecraft); [MIT Technology Review](https://www.technologyreview.com/2024/10/31/1106461/this-ai-generated-minecraft-may-represent-the-future-of-real-time-video-generation/amp/); [Tom's Hardware](https://www.tomshardware.com/video-games/ai-powered-minecraft-runs-without-a-game-engine-game-rendered-in-real-time-at-a-continuous-20-fps) [snippet]
- Difference from Cross the Line: Oasis invents a whole world from controller input with no camera input. Ours is anchored to the real room's geometry through ControlNet and keeps the real people.

**Decart MirageLSD** (July 2025)
- Frame rate: Decart claims 24 fps and under 40 ms per frame. Wired (as relayed by The Decoder) reported 20 fps at 768×432 and 100 ms latency.
- It builds on Diffusion Forcing (per-frame noise). "History augmentation" exposes the model to corrupted frames in training so that it corrects drift.
- Decart claims "infinite" streams. Earlier models typically degrade after 5–10 s. — [Decart Mirage page](https://decart.ai/publications/mirage); [The Decoder](https://the-decoder.com/decart-launches-miragelsd-an-ai-model-that-transforms-live-video-feeds-in-real-time); [PetaPixel 18 Jul 2025](https://petapixel.com/2025/07/18/mirage-is-the-worlds-first-ai-video-that-can-transform-live-footage-in-real-time); [Crusoe](https://crusoe.ai/resources/blog/miragelsd-decarts-real-time-ai-video-model-is-now-available-on-crusoe-cloud) [snippet; vendor-reported, no independent benchmark found]
- Difference from Cross the Line: Mirage transforms the entire live frame, the person included. There is no spatial rule that keeps part of the frame real.

**Decart Lucy 2.0 / 2.1 / 2.5** (2026)
- Lucy 2.0 claims 30 fps at 1080p with "near-zero latency", and "Smart History Augmentation" so that "streams run for hours without identity collapse".
- It supports a character-reference image that maps your motion onto another identity. One directory dates its release to 26 Jan 2026 (unconfirmed).
- Lucy 2.1 is marketed as "Motion-Consistent, Flicker-Free". Lucy 2.5's "global style" mode claims to change the whole scene "while preserving structure and identity". — [Decart Lucy 2](https://decart.ai/publications/lucy-2-introducing-sota-video-generation-in-realtime); [The Decoder](https://the-decoder.com/decarts-lucy-2-0-transforms-live-video-in-real-time-using-text-prompts/); [Decart docs](https://docs.platform.decart.ai/models/realtime/lucy-2); [Lucy 2.5](https://decart.ai/publications/lucy-2-5-raising-the-bar-for-live-ai); [fal Lucy 2.1](https://fal.ai/lucy-2.1) [snippet; vendor claims]
- Difference from Cross the Line: Lucy keeps identity statistically, by training the model against drift. Ours keeps it by construction, because person pixels are camera pixels that are only recoloured.

**Runway**
- GWM-1, its first world model family, arrived in Dec 2025 (GWM-Worlds, GWM-Robotics, GWM-Avatars), post-trained from Gen-4.5. — [TechCrunch 11 Dec 2025](https://techcrunch.com/2025/12/11/runway-releases-its-first-world-model-adds-native-audio-to-latest-video-model) [snippet]
- At GTC in March 2026, Runway and NVIDIA showed a real-time preview on Vera Rubin, designed for a first frame in under 100 ms. — [The Decoder](https://the-decoder.com/runway-wants-to-turn-ai-video-generation-into-a-live-stream-you-control-in-real-time/) [snippet]
- GWM Worlds 2 (research preview, 3 Sep 2026): an autoregressive diffusion model producing 720p at 24 fps plus 48 kHz audio, steered by text actions and camera motion, with no fixed length. — [Runway research](https://runway.com/research/introducing-gwm-worlds-2) [snippet]
- Runway Characters (arXiv 3 Nov 2026):
  - A ~57B autoregressive video DiT driving a conversational avatar at 704×1088.
  - Runs on four H100s with FP8, targeting 24 fps. It sustained "above 23.5 fps in 99.5% of sessions".
  - The pipeline takes 0.49 s of a 2.1 s median conversational turn. — [arXiv 2611.05642](https://arxiv.org/abs/2611.05642) [fetched]
- Difference from Cross the Line: Runway's real-time models generate synthetic worlds or avatars and do not composite a real filmed person into a restyled copy of their own room.

**Pika**
- PikaStream 1.0 (2 Apr 2026) is a real-time "AI Self" avatar for video calls, including Google Meet. It uses a 9B audio-conditioned DiT that generates frames chunk by chunk. — [Pika blog](https://experiment.pika.art/blog/introducing-real-time-video-chat); [AlternativeTo](https://alternativeto.net/news/2026/4/pika-labs-launches-real-time-video-chat-with-an-ai-avatar-version-of-yourself-in-meetings) [snippet]
- One third party reports 1.5 s latency (unverified). — [Noqta](https://noqta.tn/en/blog/pika-stream-real-time-ai-video-calls-avatars-2026) [snippet]
- The Enact research preview reportedly runs "live staging at 1.8× real time on one H100", per a secondary source. — [Hermes AI](https://hermes-ai.net/news/pika-enact-lets-directors-drag-speak-and-steer-ai-video-in-real-time/); [Semafor 17 Sep 2026](https://www.semafor.com/article/09/17/2026/video-ai-company-pika-offers-tool-to-speed-up-ai-video-creation) [snippet]
- Difference from Cross the Line: Pika replaces the person with a generated avatar. We keep the real person and generate only the world.

### Inferences
- **The positioning sentence the sources support:** "Real-time generative video in 2025–26 means regenerating every frame on H100/B200-class hardware and fighting drift. We generate each world once on a CPU in seconds and composite forever, so the world can't flicker and the person can't drift, because the person is real."
- **A concrete contrast for the talk:** StreamDiffusionV2 needs 4×H100 for about 58 fps on a 14B model, and Krea needs a B200 for 11 fps. The kiosk's per-frame cost is a texture lookup plus a mask.
- **The honest trade-off:** these systems handle camera motion and changing scenes. Ours assumes a fixed tripod or kiosk camera and a static room, so a moved object stays wrong until the world is regenerated.

### Gaps
- No independent benchmark of MirageLSD or Lucy fps, latency or identity preservation exists; all figures are Decart's or press relays of them.
- I could not confirm whether GWM Worlds 2 accepts live camera input.
- No published identity-drift metric that would allow a numeric comparison across these products was found.

## 2. Consumer AI effects (Snapchat, TikTok, Instagram/Edits, Google, CapCut, video-call backgrounds)

### Takeaway
No consumer product found splits one frame into real and generated by a spatial rule, or changes a person as they cross a boundary:
- Snap, TikTok, Meta, Google and CapCut regenerate or restyle the whole clip or photo, usually after capture rather than live.
- The architectural closest neighbour is the AI-generated virtual background in Zoom and Google Meet. These generate an image once, then composite the real, segmented person over it every frame, which is the same "generate once, composite forever" pattern.
- The background in those products is an unrelated scene, not a geometry-aligned restyle of the real room. That alignment is what lets our line, depth and portal rules mix real and generated pixels coherently.

### Cited Findings
**Snapchat**
- **AI Video Lenses** (12 Mar 2025): powered by Snap's in-house video model. Launch set "Raccoon", "Fox" and "Spring Flowers", Platinum-only ($15.99/mo). — [TechCrunch](https://techcrunch.com/2025/03/12/snap-introduces-ai-video-lenses-powered-by-its-in-house-generative-model); [Snap newsroom](https://newsroom.snap.com/new-video-gen-ai-lenses?lang=en-GB) [snippet]
  - Difference from Cross the Line: these transform the user's clip as a whole. There is no real/generated split and no crossing rule.
- **Imagine Lens** (5 Sep 2025): open-prompt image generation that makes images, not video, with no live overlay preview. Later opened to all US users and then other markets. — [Snap newsroom](https://newsroom.snap.com/imagine-a-new-way-to-create-with-lenses); [TechCrunch](https://techcrunch.com/2025/09/05/snapchats-new-lens-lets-you-create-ai-images-using-text-prompts); [Imagine for Everyone](https://newsroom.snap.com/imagine-for-everyone) [snippet]
  - Difference from Cross the Line: a single still re-imagined from a prompt, as opposed to a live composite.
- **Real-time on-device diffusion** (previewed at AWE, 18 Jun 2024): Snap said the model is small enough for a phone and fast enough to re-render frames live from a prompt. No fps was published. — [TechCrunch](https://techcrunch.com/2024/06/18/snap-previews-its-real-time-image-model-that-can-generate-ar-experiences); [MediaPost](https://www.mediapost.com/publications/article/397021/snaps-real-time-image-model-to-enhance-ar-mobile.html) [snippet]
  - Difference from Cross the Line: per-frame regeneration again, now on-device.

**TikTok**
- **AI Alive** (13 May 2025): image-to-video in Stories from a still photo plus a prompt. Output carries an AI label and C2PA metadata. — [TikTok newsroom](https://newsroom.tiktok.com/en-us/introducing-tiktok-ai-alive); [TechCrunch](https://techcrunch.com/2025/05/13/tiktok-launches-tiktok-ai-alive-a-new-image-to-video-tool) [snippet]
  - Difference from Cross the Line: it animates a photo. It does not composite live people into a restyled world.
- **Symphony** (advertiser suite): Digital Avatars from June 2024, then Creative Studio, with image-to-video and text-to-video added June 2025. Outputs are auto-labelled "AI-generated". — [TikTok newsroom: Symphony Avatars](https://newsroom.tiktok.com/announcing-symphony-avatars); [Symphony updates June 2025](https://newsroom.tiktok.com/tiktok-symphony-updates?lang=en); [TikTok Ads blog](https://ads.tiktok.com/business/en-US/blog/tiktok-symphony-ai-creative-suite) [snippet]
  - Difference from Cross the Line: an ad-production tool that synthesizes people. It is offline and not spatial.

**Instagram / Edits "Restyle"** (June 2025)
- Powered by Meta Movie Gen and available in Edits, the Meta AI app and meta.ai.
- Presets include video game, comic, anime, desert, beach and snowy scenes.
- Adam Mosseri previewed it in Dec 2024. — [PetaPixel 12 Jun 2025](https://petapixel.com/2025/06/12/edits-video-app-for-instagram-gets-new-restyle-generative-ai-tool); [Social Media Today](https://www.socialmediatoday.com/news/meta-adds-ai-video-restyling-instagram-edits-ai-app/750487/); [PetaPixel Dec 2024](https://petapixel.com/2024/12/20/instagram-teases-generative-ai-editing-tool-that-can-change-any-aspect-of-your-video) [snippet]
- The Movie Gen paper's "Movie Gen Edit" shows edits such as "Change background to a city park with a lake". I did not verify whether unedited regions are preserved. — [arXiv 2410.13720](https://www.arxiv.org/abs/2410.13720); [Meta Movie Gen](https://ai.meta.com/research/movie-gen/) [snippet]
- Difference from Cross the Line: Restyle re-renders the whole uploaded clip offline, background swaps included. We keep real pixels and choose real or generated per pixel at runtime.

**Google Photos** (23 Jul 2025)
- "Photo to video" (Veo 2, later Veo 3) makes 6-s clips. "Remix" restyles photos, for example into anime or a sketch, and the two can be chained.
- Both are labelled experimental and carry a SynthID watermark, like "Reimagine" edits in Photos. — [Google blog](https://blog.google/products/photos/photo-to-video-remix-create-tab/); [TechCrunch](https://techcrunch.com/2025/07/23/google-photos-adds-ai-features-for-remixing-photos-in-different-styles-turning-pics-into-videos) [snippet]
- Difference from Cross the Line: these are whole-image restyles or animations of a single still.

**CapCut**
- Template-driven "AI filter" effects, such as "Cartoon Filter AI" and anime templates with hundreds of thousands of uses, plus the viral "AI Age" template. — [CapCut animated effects](https://www.capcut.com/explore/animated-effects); [CapCut anime AI filter](https://www.capcut.com/explore/anime-ai-filter/7520674953060911112); [Yahoo Tech](https://tech.yahoo.com/apps/articles/tiktok-ai-age-filter-using-235121220.html) [snippet]
- Difference from Cross the Line: whole-frame or whole-face stylization after capture.

**Video-call backgrounds (the closest architecture)**
- **Zoom:** AI Companion "Virtual Background Generation" turns a prompt into up to two options. It requires a paid plan (Pro/Business/Enterprise), admin enablement and app version 6.0.0+. — [Zoom Library](https://library.zoom.com/zoom-workplace/artificial-intelligence/artificial-intelligence-bluepaper/ai-companion/ai-companion-features/virtual-background-generation); [Zoom News](https://news.zoom.com/zoom-introduces-ai-virtual-backgrounds-among-other-new-ai-companion-capabilities/) [snippet]
- **Google Meet:** "Generate a background" began as a Workspace Labs experiment, reached Business/Enterprise editions in March 2025 and mobile on 1 Oct 2025. — [Meet Help](https://support.google.com/meet/answer/13784433?hl=en); [Workspace Updates Mar 2025](https://workspaceupdates.googleblog.com/2025/03/updates-for-generating-meeting-backgrounds-with-gemini.html); [Workspace Updates Oct 2025](https://workspaceupdates.googleblog.com/2025/10/generate-ai-backgrounds-google-meet-mobile.html) [snippet]
- **Microsoft Teams:** the only Microsoft guide found tells users to make the image in an external AI generator and upload it, so no native generator was found. — [Microsoft 365 life hacks](https://www.microsoft.com/en-us/microsoft-365-life-hacks/?p=10713) [snippet]
- The browser-tech note already documents how Meet's pipeline works: segmentation plus WebGL2 compositing.
- Difference from Cross the Line: same pipeline shape (generate once, segment, composite per frame), but the generated scene ignores the real room's geometry, it replaces everything behind the person, and there is no line, depth, portal or crossing event.

### Inferences
- **Claim we can safely make:** "We found no consumer effect that keeps part of the same frame real and part generated by a spatial rule, or that changes a person as they cross." Phrase it as "not found", not "first".
- **Best one-line contrast:** "Zoom and Meet generate a background once and paste you on top. We generate *your own room* once, aligned to it, so reality and the world can share one frame with a seam you can walk through."

### Gaps
- I could not confirm whether Snap's AI Video Lenses render live or after capture.
- Nothing was found on Effect House (TikTok's lens tool) offering generative AI effects.
- No Pixel-specific "AI video effects" feature distinct from the Photos features was found.

## 3. AR portals and spatial reveals (ARKit/ARCore portals, Snap portal lenses, visionOS immersion, Time Warp Scan, seasons splits)

### Takeaway
Portal effects since 2017 show a pre-authored virtual 3D space through a doorway, masked by render order. visionOS's "progressive" immersion grows a radial portal until it replaces passthrough, which is the nearest shipped analog to our "hold to flood". TikTok's Time Warp Scan (2020) is the nearest viral line-rule effect, but its line freezes time instead of switching worlds. None of these shows a generated version of the same real scene.

### Cited Findings
- **ARKit portal demos (2017):** Nedd's "interdimensional portal" (1 Jul 2017) placed a doorway in the room that the user walks through into a virtual environment. — [Redmond Pie](https://www.redmondpie.com/ios-11-arkit-gets-coolest-augmented-reality-demo-yet-video/); [iClarified](https://www.iclarified.com/61296/check-out-this-amazing-interdimensional-portal-made-with-arkit-video/comments); [iMore roundup](https://www.imore.com/cool-arkit-portals-worth-checking-out) [snippet]
  - The trick is "to change the rendering order and render invisible 'masks'" that hide the interior. — [GitHub bjarnel/arkit-portal](https://www.github.com/bjarnel/arkit-portal) [snippet]
  - A Kodeco tutorial places "a virtual doorway to a futuristic room" on a detected plane. — [Kodeco](https://www.kodeco.com/5516-building-a-portal-app-in-arkit-getting-started) [snippet]
  - Difference from Cross the Line: the portal content is a hand-built 3D room that does not match the real scene, while our "other side" is the real room restyled, pixel-aligned with the plate.
- **Snapchat World Lenses (Apr 2017) and the Stranger Things portal lens (Oct 2017):**
  - World Lenses were Snap's first rear-camera AR. — [MacRumors](https://www.macrumors.com/2017/04/18/snapchat-debuts-new-3d-world-lenses/) [snippet]
  - Netflix's Stranger Things lens was "Snapchat's first ever Portal Lens". You walk through a door into the Byers' living room and can look back out at the real world. Phones without AR support got a gyroscope version. Cannes Lions lists the campaign under 2018. — [The Drum, 27 Oct 2017](https://www.thedrum.com/news/2017/10/27/snapchats-first-sponsored-world-lens-lets-stranger-things-fans-enter-the-upside-down); [Cannes Lions](https://www.lovethework.com/work-awards/campaigns/stranger-things-snapchats-ar-portal-lens-416365) [snippet]
  - Lens Studio ships a Portal template. — [Snap Lens Studio portal example](https://developers.snap.com/lens-studio/examples/lens-examples/portal) [snippet]
  - Difference from Cross the Line: authored 3D sets entered by the phone camera. Ours is a generated twin of the room entered by the person's body, seen by a fixed camera.
- **visionOS progressive immersion:**
  - The style "initially uses a radial portal effect that replaces passthrough in a portion of the field of view". The Digital Crown resizes it and can grow it until it fully covers passthrough.
  - visionOS 2 added APIs for minimum, maximum and initial immersion.
  - Apple's user guide says Environments use the Crown to set "how much of your surroundings you see". — [Apple docs: ImmersionStyle.progressive](https://developer.apple.com/documentation/swiftui/immersionstyle/progressive.md); [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/immersive-experiences.md); [Vision Pro User Guide](https://support.apple.com/guide/apple-vision-pro/tan899d290e4/visionos) [snippet]
  - Difference from Cross the Line: the same grow-the-portal gesture as our hold-to-flood, but it reveals a canned environment (a mountain, the Moon) with no relation to the room's geometry. Ours floods outward into a restyled copy of the same room, through the model's own partial generations.
- **TikTok "Time Warp Scan" (viral Sep–Oct 2020):** a blue or green line sweeps across the screen, and "everything behind the line" freezes as a still. It runs live while recording, and failures became their own meme. — [Distractify](https://www.distractify.com/p/time-warp-scan-filter-tiktok); [Business Insider India, 19 Oct 2020](https://businessinsider.in/thelife/news/the-tiktok-time-warp-scan-filter-lets-you-create-fun-visual-illusions-here-are-the-biggest-trends-around-the-effect/amp_articleshow/78755695.cms); [Yahoo](https://www.yahoo.com/lifestyle/tiktok-time-warp-scan-filter-172821183.html) [snippet]
  - One source's "16.8 billion views" hashtag figure is unverified.
  - Difference from Cross the Line: a line splits the frame into two regimes, but the regimes are live and frozen-past, and the line moves while the people stay put. Ours fixes the line, the people move, and the regimes are real and generated.
- **Same-place seasons:** Albert Dros's same-spot seasonal series circulated widely. — [Bored Panda](https://boredpanda.com/same-location-different-seasons-photography-albert-dros); [DIY Photography](https://www.diyphotography.net/photos-show-exact-location-changes-different-times-year/) [snippet]
  - Difference from Cross the Line: real photos from different dates, assembled as grids or stills. They are not live and not generated.

### Inferences
- **Lineage to cite:** Snap's portal lens and ARKit portals for "a door you walk through", visionOS for "a portal that grows to swallow passthrough", and Time Warp Scan for "a line that changes what's behind it".
- **Our twist:** the other side is the *same* room, generated, and the person is the thing that crosses.
- **ARCore:** portal demos clearly exist, but I fetched no ARCore-specific primary source. Use ARKit and Snap as the citations.

### Gaps
- I could not identify a specific viral "seasons transition" TikTok or CapCut template. A search summary mentioned a split winter/summer New York aerial by "Paul Seibert", but I could not link it to a source page, so it is unverified.
- ARCore-specific portal app sources were not fetched.

## 4. Spatial blends of time in photography (Wilkes, time-slice photographers, Larenkov)

### Takeaway
precedents_and_inspiration.md covers rephotography tools (Bae et al. 2010, Historypin, WhatWasThere, Berkeley Lab) but not these artists, so everything below is new. They share our setup: a fixed camera and a spatial rule (diagonal, strips, ghosted overlay) that decides which "time" each pixel shows. They differ in three ways:
- they blend real captures, not a generated world;
- the results are stills;
- the compositing is manual, taking weeks to months.

### Cited Findings
- **Stephen Wilkes, "Day to Night" (2009–2018; TASCHEN book 2019):**
  - Shot from one fixed position over 15–30 hours, about 1,500 frames.
  - Time runs "on a diagonal vector", with sunrise beginning in one corner.
  - NPR reports the compositing takes about four months for an image photographed in one day. — [NPR, 19 Feb 2016](https://www.npr.org/sections/alltechconsidered/2016/02/19/467338386/when-people-can-see-time-photographer-captures-day-night-in-one-image); [Smithsonian](https://www.smithsonianmag.com/travel/how-photographer-stephen-wilkes-captures-full-day-single-image-180972935/); [My Modern Met](https://mymodernmet.com/stephen-wilkes-daynight); [Designboom 2015](https://www.designboom.com/art/stephen-wilkess-day-to-night-bryce-wolkowitz-gallery-11-09-2015/) [snippet]
  - Difference from Cross the Line: Wilkes's spatial rule (a diagonal) assigns real times. Our rules (line, depth, portal, wave) assign real versus generated worlds, live, at camera rate, with people moving through the seam.
- **Dan Marker-Moore, time slices:** for example, a Shanghai image built from 65 frames over 1 h 53 min, arranged as strips offset in time. — [My Modern Met](https://mymodernmet.com/dan-marker-moore-time-slice-photography); [Booooooom 2014](https://booooooom.com/2014/09/15/fantastic-timeslices-photographer-dan-marker-moore) [snippet]
  - Difference from Cross the Line: hard strip seams between real times, in a still image.
- **Fong Qi Wei, "Time Is A Dimension":** sunrise and sunset scenes sliced from several times of day into one cohesive image. The requested title "Time Is Art" was not found. — [My Modern Met](https://mymodernmet.com/fong-qi-wei-time-is-a-dimension); [My Modern Met (time slice)](https://mymodernmet.com/time-slice-landscape-photography-fong-qi-wei) [snippet]
  - Difference from Cross the Line: same strip idea, using real captures.
- **Richard Silver, time slice:** 36 photographs per final image ("New York Time Slice"). This rests on one low-confidence source. — [STIR](https://www.stirworld.com/inspire-people-richard-silver-slices-through-time) [snippet]
- **Sergey Larenkov, "Link to the Past" / "Ghosts of WWII" (viral 2010; series begun with the Siege of Leningrad, later Berlin, Vienna, Moscow and others):**
  - Each archival WWII photo is perspective-matched to a modern rephotograph and faded into it. Gizmodo framed them as "time portals". — [Moscow Times, 8 Aug 2010](https://www.themoscowtimes.com/2010/08/08/collage-photos-mix-war-and-present-day-life-a494); [PetaPixel 2012](https://petapixel.com/2012/04/26/glimpses-of-world-war-2-seen-through-photos-of-modern-day-europe); [Core77](https://www.core77.com/posts/17049/ghosts-now-officially-exist-thanks-to-sergey-larenkovs-computational-rephotography-17049); [Gizmodo](https://gizmodo.com/5600272/photoshop-time-portals-to-world-war-ii) [snippet]
  - Difference from Cross the Line: his ghosts are historical people pasted into today's street. In ours, today's people walk into a generated version of the street. Both rely on exact viewpoint alignment, which we get for free from a single tripod plate.

### Inferences
- Wilkes's four months per image is a strong foil: "Wilkes spends months hand-blending 1,500 frames into one still. Our spatial rule does the same kind of per-pixel time and world assignment live, at camera rate."
- A diagonal "day-to-night" rule would be a cheap new mode for the horizon wave.

### Gaps
- No primary artist pages were fetched; everything here is from press summaries.
- I could not verify a Fong Qi Wei series titled "Time Is Art".

## 5. Diffusion morphing and interpolation (SDEdit, DiffMorpher, IMPUS, AID, Smooth Diffusion, DreamMover, newer work; strength-ladder morphs; denoising reveals)

### Takeaway
Published diffusion morphing work (2023–2026) interpolates between two separate images, through LoRA weights, latents, text embeddings or attention.

None of it was found using the strength ladder of a single SDEdit generation (input photo → low-strength → … → full edit) as a time-ordered morph path. The pieces exist separately:
- **CS180 Project 5** itself asks students to produce that ladder as a static figure.
- **Deforum and Loopback scripts** keyframe denoising strength per frame, but resample every frame.
- **Differential Diffusion** varies strength per pixel inside one generation.
- **Wang & Golland** show that low-noise interpolations look like an alpha composite, i.e. a double exposure.

Our "Grow" combination appears unpublished. That is "not found", not proven novel.

### Cited Findings
- **SDEdit** (Meng, He, Song, Song, Wu, Zhu, Ermon; ICLR 2022):
  - "As t0 increases, the generated images become more realistic while less faithful." At large t0 it tends toward unconditional samples.
  - Realism and faithfulness "are not positively correlated". — [arXiv 2108.01073](https://arxiv.org/abs/2108.01073v2); [ar5iv](https://ar5iv.arxiv.org/html/2108.01073); [ICLR 2022](https://iclr.cc/virtual/2022/poster/6268) [snippet]
  - Later work (CODE) restates the realism-versus-fidelity trade-off. — [arXiv 2408.12418](https://arxiv.org/html/2408.12418v1) [snippet]
  - Difference from Cross the Line: SDEdit treats strength as a setting to choose once. We render several strengths and *play them in order* as a transition, so the realism/faithfulness trade-off becomes the animation itself.
- **Wang & Golland, "Interpolating between Images with Diffusion Models"** (arXiv 2307.12560, ICML 2023 workshop):
  - Interpolates noised latents at decreasing noise levels, then denoises.
  - Latents denoised with "less than 25% of the schedule often resemble an alpha composite of their parent images". Above 65%, results deviate strongly. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2307.12560); [project page](https://clintonjwang.github.io/interpolation) [snippet]
  - Difference from Cross the Line: this is independent evidence that naive low-noise blending gives a double exposure. Our high band switches at a per-pixel threshold rather than crossfading, which is exactly what avoids it.
- **DiffMorpher** (Zhang, Zhou, Xu, Dai, Pan; CVPR 2024): fits one LoRA per input image, then interpolates the LoRA parameters and latent noise. It adds self-attention interpolation/substitution and AdaIN colour adjustment, on an SD 2.1-base default. — [CVPR paper](https://openaccess.thecvf.com/content/CVPR2024/papers/Zhang_DiffMorpher_Unleashing_the_Capability_of_Diffusion_Models_for_Image_Morphing_CVPR_2024_paper.pdf); [GitHub](https://github.com/kevin-thu/diffmorpher) [snippet]
  - Difference from Cross the Line: DiffMorpher needs two LoRA trainings and many denoising passes per in-between frame. We reuse rungs the model already produced and blend them on the GPU in real time.
- **IMPUS** (ICLR 2024): interpolates optimized text embeddings and probability-flow-ODE latents, with perceptually uniform sampling. Its own limitations: abrupt transitions for semantically distant pairs, and bad hands. — [arXiv 2311.06792](https://arxiv.org/abs/2311.06792); [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/08bd07d567d77d6dd8d82a4474706a5e-Abstract-Conference.html) [snippet]
  - Difference from Cross the Line: morphs between two images. We morph between a photo and its own edit, where the model supplies the path.
- **AID / PAID** (He, Wang, Liu, Yao; NeurIPS 2024): training-free inner/outer attention interpolation with Beta-distributed coefficients. Supports SD 1.4, 1.5, 2.1 and SDXL. — [arXiv 2403.17924](https://arxiv.org/html/2403.17924v3); [NeurIPS](https://papers.nips.cc/paper_files/paper/2024/hash/b12a1d1014e952e676f5d6931d03241a-Abstract-Conference.html) [snippet]
  - Difference from Cross the Line: interpolates between prompts or conditions at generation time. Ours is precomputed and played back.
- **Smooth Diffusion** (Guo et al.; CVPR 2024): Step-wise Variation Regularization makes the latent space smooth, and is shipped as "Smooth-LoRA". — [CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Guo_Smooth_Diffusion_Crafting_Smooth_Latent_Spaces_in_Diffusion_Models_CVPR_2024_paper.html); [GitHub](https://github.com/shi-labs/smooth-diffusion) [snippet]
  - Difference from Cross the Line: it changes the model through training. We change nothing in the model.
- **DreamMover** (Shen et al.; ECCV 2024): interpolates between frames with large motion, using a diffusion-based flow estimator and high- and low-level feature fusion. Introduces the InterpBench benchmark. — [arXiv 2409.09605](https://arxiv.org/abs/2409.09605); [ECCV](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/2366_ECCV_2024_paper.php) [snippet]
  - Difference from Cross the Line: motion interpolation between two real frames. We do appearance morphing at a fixed camera.
- **FreeMorph** (Cao, Si, Wang, Liu; ICCV 2025): tuning-free, using guidance-aware spherical interpolation and a step-oriented variation trend. Claimed 10–50× faster than prior methods. — [arXiv 2507.01953](https://arxiv.org/abs/2507.01953); [CVF](https://openaccess.thecvf.com/content/ICCV2025/html/Cao_FreeMorph_Tuning-Free_Generalized_Image_Morphing_with_Diffusion_Model_ICCV_2025_paper.html) [snippet]
- **Newer:**
  - CHIMERA (arXiv 2512.07155, v2 24 Mar 2026): cached inversion-guided denoising plus a Global-Local Consistency Score metric. — [arXiv](https://arxiv.org/abs/2512.07155v2) [snippet]
  - AlignMorph (arXiv 2609.24330, Sep 2026): "tuning-free diffusion image morphing via explicit semantic transport". It reports FreeMorph at 90 s under its sampling schedule. — [arXiv PDF](https://arxiv.org/pdf/2609.24330) [snippet; title and one figure only]
  - Difference from Cross the Line: all of these are two-image morphs costing seconds to minutes per sequence on a GPU.
- **Differential Diffusion** (Levin & Fried; arXiv 2306.00950; Eurographics 2025):
  - A per-pixel "change map" generalizes the single img2img strength. The map is split into nested masks, and each region starts denoising at a different timestep.
  - Training-free, with a Diffusers pipeline. — [arXiv](https://arxiv.org/abs/2306.00950v2); [project](https://differential-diffusion.github.io); [Diffusers guide](https://huggingface.co/docs/diffusers/main/en/modular_diffusers/end_to_end_guide) [snippet]
  - Difference from Cross the Line: this is the closest published idea, a spatially varying strength. It is computed inside one generation and is static. Our Grow gives each pixel its own moment along the strength ladder, varying over time, using cached rungs at 60 fps.
- **Deforum `strength_schedule` and Loopback Wave (community tools):**
  - Deforum's strength schedule controls "how much the presence of the previous frame influences the next frame", is keyframed per frame, and defaults to 0.65.
  - Loopback Wave "modulates the denoising strength in a sinusoidal fashion" and renders a video.
  - Parseq keyframes image strength for Deforum. — [Deforum wiki](https://github.com/deforum-art/deforum-for-automatic1111-webui/wiki/Animation-Settings); [Loopback Wave](https://rentry.co/sd-loopback-wave); [Parseq](https://github.com/rewbs/sd-parseq) [snippet]
  - Difference from Cross the Line: these resample every frame with feedback, so they flicker and drift, and they do not end exactly on the input and the final edit. Ours is a fixed ladder from one input, exact at both ends.
- **Denoising-step previews:**
  - DiffusionBrowser (arXiv 2512.13690) trains lightweight decoders to preview any denoising step interactively.
  - "DT-Visualization" (arXiv 2503.10637) shows the model's predicted final image at intermediate steps. — [DiffusionBrowser](https://arxiv.org/html/2512.13690v1); [arXiv 2503.10637](https://arxiv.org/pdf/2503.10637) [snippet]
  - Difference from Cross the Line: these visualize noise → image for analysis. Ours shows photo → edit as a deliberate in-scene transition.

### Inferences
- **Defensible claim:** "We use the img2img strength sequence of one generation as the morph path." SDEdit supplies the path (more strength means more of the world, less of the photo). The two-band walk removes the double exposure that Wang & Golland observe at low noise.
- **Wording:** frame it as "a combination we did not find in the literature or in community tools", not "first ever".
- **Grow in one line:** a time-animated, cached cousin of Differential Diffusion's per-pixel strength.
- **Course tie-in:** Project 5's "series of edits gradually matching the original image" figure, played as a movie, is the same ladder.

### Gaps
- I found no published or named "denoising-trajectory reveal" or "progressive generation" *transition effect* that runs from a real photo to its edit. The many informal "image emerging from noise" visualizations could not be tied to a citable effect name.
- No paper was found that evaluates SDEdit strength sweeps as animation, for example with temporal smoothness metrics.

## 6. Classic transitions (Burt–Adelson, Brown–Lowe two-band, Poisson, Beier–Neely, random dissolves, noise-threshold dissolve shaders)

### Takeaway
Our two-band temporal blend combines two well-known parts:
- **Brown & Lowe's two-band blending** (from panorama stitching, a simplification of Burt–Adelson): low frequencies are blended over a wide range, and high frequencies over a narrow range or winner-take-all, to avoid ghosting.
- **The game-dev noise-threshold "dissolve" shader / Wolfenstein "fizzlefade"**: a per-pixel random switch.

Our contribution is moving the two-band idea from space to time: crossfade the low band, switch the high band at a per-pixel noise threshold. CS180's own mosaic spec says a 2-level pyramid fixes high-frequency ghosting. I found no name for the temporal version; the closest named analogue is audio "frequency-selective crossfading".

### Cited Findings
- **Burt & Adelson (1983):** "A Multiresolution Spline with Application to Image Mosaics", ACM TOG 2(4):217–236, DOI 10.1145/245.247. It decomposes images into band-pass components, splines each band over a transition zone proportional to its wavelength, and recombines. — [MIT abstract](https://persci.mit.edu/pub_abstracts/spline83_abs.html); [PDF](https://persci.mit.edu/pub_pdfs/spline83.pdf) [snippet]
  - Difference from Cross the Line: a spatial seam between two images. We use the same frequency-split logic along the time axis of a transition.
- **Brown & Lowe two-band blending (ICCV 2003 "Recognising Panoramas"; IJCV 2007):**
  - They use Burt–Adelson multi-band blending "without loss of high frequency detail".
  - UBC lecture slides define the two-band split as low (λ > 2 px) and high (λ < 2 px), with the low band blended slowly and widely and the high band quickly and narrowly.
  - Frédo Durand's MIT computational-photography notes describe "Brown and Lowe's two-band simplification", with the high band composited winner-take-all. — [Brown & Lowe 2003 PDF](https://www.cs.ubc.ca/labs/lci/papers/docs2003/brown03.pdf); [UBC slides](https://www.cs.ubc.ca/~lowe/425/slides/11-PanoramasAR.pdf); [MIT comp-photo book: blending](https://people.csail.mit.edu/fredo/comp-photo-book/10-multiple-exposure-imaging-07-blending.html); [IJCV 2007 copy](https://courses.cs.washington.edu/courses/cse576/07sp/notes/ijcv2007.pdf) [snippet; exact paper wording not fetched]
  - Difference from Cross the Line: this is the direct spatial precedent. Our temporal version makes the high-band winner-take-all decision with a per-pixel noise threshold that sweeps over time, instead of with the maximum blend weight.
- **Pérez, Gangnet & Blake (2003):** "Poisson Image Editing", ACM TOG 22(3):313–318 (SIGGRAPH 2003), DOI 10.1145/1201775.882269. Guided interpolation of gradients with Dirichlet boundary conditions, used for seamless cloning. — [Princeton copy](https://www.cs.princeton.edu/courses/archive/fall14/cos526/papers/perez03.pdf); [SIGGRAPH history](https://history.siggraph.org/?p=115869); [Wikipedia](https://www.wikipedia.org/wiki/Poisson_image_editing) [snippet]
  - Difference from Cross the Line: a per-image solve, too slow to run every frame. We rely on pixel alignment from ControlNet plus a plate-based recolour instead.
- **Beier & Neely (1992):** "Feature-Based Image Metamorphosis", SIGGRAPH Computer Graphics 26(2):35–42. A warp from line features plus a cross-dissolve, used for the face morphs in Michael Jackson's "Black or White". A typical PDI morph took about 3 weeks of animator time, 75% of it on feature lines. — [Princeton copy](https://www.cs.princeton.edu/courses/archive/spring20/cos426/readings/Beier92.pdf); [SIGGRAPH history](https://history.siggraph.org/?p=120515); [Cornell VMorph](https://www.cs.cornell.edu/zeno/projects/vmorph/mm97/VMorph-MM97.html) [snippet]
  - Difference from Cross the Line: Beier–Neely needs geometric correspondence, which our scene doesn't need because the plate and the world are already aligned. The model's partial generations take the place of the warp.
- **Random pixel dissolve, "fizzlefade" (Wolfenstein 3D, 1992):** turns screen pixels to a new colour "one at a time, seemingly at random", with a Galois LFSR. The 17-bit register gives 131,072 values for 64,000 pixels, so out-of-range values are skipped. — [Fabien Sanglard, 28 Aug 2017](https://fabiensanglard.net/fizzlefade) [snippet]
  - Difference from Cross the Line: a full-band random switch between two images. Ours randomizes only the high band, which avoids the speckle a full-band switch shows in flat regions.
- **Noise-threshold dissolve shaders (game dev):**
  - Recipe: sample noise, `step`/`clip` against a threshold, output alpha. "Virtually every dissolve shader uses the same basic underlying setup."
  - The glowing rim is a smoothstep band between two nearby thresholds, made visible by HDR bloom. — [Mirza Beig, Part 1](https://mirzabeig.substack.com/p/unity-tutorial-dissolve-shader-part-1); [Xibanya tutorial](https://xibanya.github.io/ShaderTutorials/tutorial/Part12Dissolve.html); [GameDev.net sprite dissolve](https://gamedev.net/shaderlab/14-sprite-dissolve-effect/); [Habr](https://habr.com/post/427401) [snippet]
  - Difference from Cross the Line: game dissolves reveal transparency or a second texture across all frequencies. We apply the threshold only to high-frequency detail, while the low band crossfades, and walk it through a ladder of rungs instead of two images.
- **Frequency-selective crossfading in audio:** a Mixxx feature request describes a "frequency-selective crossfader" (separate high, mid and low bands between two tracks). — [Launchpad Mixxx #488363](https://bugs.launchpad.net/mixxx/+bug/488363) [snippet]
  - Difference from Cross the Line: the same idea in sound. No video equivalent with a name was found.

### Inferences
- **Name to use:** something like "two-band temporal dissolve (Brown–Lowe in time)".
- **Precedent framing:** "Brown & Lowe's two-band blend: crossfade the lows, winner-take-all the highs. We apply it over time, and the 'winner' is decided by a per-pixel noise threshold, like a dissolve shader."
- **Why it works:** a low-band crossfade has nothing sharp to ghost, and a high-band hard switch can't double-expose. This matches the CS180 mosaic hint quoted in section 7.

### Gaps
- I could not find a named precedent or paper for "multiband blending over time" (low-band crossfade plus high-band threshold switch) as a video transition. I could not fetch the exact two-band wording in the Brown–Lowe papers either (washington.edu, wisc.edu and csail.mit.edu were blocked).
- No source quantifies ghosting in time-domain crossfades.

## 7. UC Berkeley CS180/280A course projects, Fall 2025 and Fall 2026 (what the specs ask for)

### Takeaway
- **Project list, Fall 2025** (instructors Angjoo Kanazawa and Alexei Efros): Proj 2 Filters & Frequencies (Laplacian stacks and multiresolution blending), Proj 3 (Auto)stitching Photo Mosaics (homographies and blending), Proj 4 NeRF, Proj 5 Fun with Diffusion Models (DeepFloyd IF: SDEdit at several noise levels, inpainting, anagrams, hybrids). There was no face-morphing project in Fall 2025.
- **Face morphing** was Project 3 in Fall 2024 (warp_frac/dissolve_frac).
- **Project list, Fall 2026** (instructors Efros and Ren Ng): Proj 2 Filters & Frequencies, Proj 3 "Fun with Flow Models" (PixNerd SDEdit-style edits at several start times), Proj 4 Mosaics. Diffusion is commented out, NeRF is removed, and morphing is only a lecture.
- **Two quotes map almost one-to-one onto our design:** Proj 5's "series of 'edits' … gradually matching the original image" is the Grow ladder, and the mosaic spec's "2-level pyramid" for high-frequency ghosting is the two-band blend.

### Cited Findings
**Where the specs came from.** inst.eecs.berkeley.edu/~cs180 and cal-cs180.github.io could not be fetched. I read the site source from the public GitHub org [github.com/cal-cs180](https://github.com/cal-cs180) [fetched], which has the repos `cal-cs180.github.io` ("redirects to current semester", fa25 and fa26 folders), `fa25`, `fa24` and `fa23`. The public URLs are presumably cal-cs180.github.io/fa25/hw/… (inferred from the repo layout). Quotes below are as returned by the fetch tool.

**Fall 2025** ([fa25 index.html](https://raw.githubusercontent.com/cal-cs180/fa25/main/index.html)) [fetched]
- **Project list:** Proj0 Camera, Proj1 Prokudin-Gorskii, Proj2 Fun with Filters and Frequencies, Proj3 (Auto)stitching and Photo Mosaics, Proj4 Neural Radiance Field, Proj5 Fun with Diffusion Models. Instructors Angjoo Kanazawa and Alexei Efros. No face-morphing project.
- **Project 2, "Fun with Filters and Frequencies!"** — [fa25/hw/proj2](https://raw.githubusercontent.com/cal-cs180/fa25/main/hw/proj2/index.html) [fetched]
  - Part 2.3: "Implement a Gaussian and a Laplacian stack." "In a stack the images are never downsampled so the results are all the same dimension as the original image."
  - Part 2.4, "Multiresolution Blending (a.k.a. the oraple!)": "Review the 1983 paper by Burt and Adelson". "pick two pairs of images to blend together with an irregular mask, as is demonstrated in figure 8 in the paper". The deliverable includes one irregular-mask blend.
  - Part 2.2, hybrids: "Try creating 2-3 hybrid images (change of expression, morph between different objects, change over time, etc.)"
- **Project 3, "[Auto]Stitching Photo Mosaics", Part A** — [index](https://raw.githubusercontent.com/cal-cs180/fa25/main/hw/proj3/index.html); [partA](https://raw.githubusercontent.com/cal-cs180/fa25/main/hw/proj3/partA.html) [fetched]
  - "Implement computeH(im1_pts, im2_pts) function." "Use inverse warping (to avoid holes in the output image)." Compare nearest-neighbour and bilinear interpolation.
  - Rectify "2+ images".
  - Blending: "use weighted averaging", "or use the distance transform", "a more sophisticated blending technique, such as a Laplacian pyramid". The key line: **"If your only problem is 'ghosting' of high-frequency terms, then a 2-level pyramid should be enough."** Deliverable: "Show 3 mosaics".
- **Project 4, "Neural Radiance Field!"** (due 14 Nov 2025): ArUco calibration, a 2-D neural field, NeRF on Lego (23 PSNR target) and your own capture. — [fa25/hw/proj4](https://raw.githubusercontent.com/cal-cs180/fa25/main/hw/proj4/index.html) [fetched]
- **Project 5, "Fun With Diffusion Models!"** (Part A due 11/25/2025, Part B due 12/12/2025) — [index](https://raw.githubusercontent.com/cal-cs180/fa25/main/hw/proj5/index.html); [parta](https://raw.githubusercontent.com/cal-cs180/fa25/main/hw/proj5/parta.html) [fetched]
  - Model: "DeepFloyd is a two stage model trained by Stability AI."
  - §1.7, Image-to-image translation (SDEdit): denoise from starting indices "[1, 3, 5, 7, 10, 20]". This pushes the image back "onto the image manifold without any conditioning", and students should see "a series of 'edits' to the original image, gradually matching the original image closer and closer."
  - §1.7.1: hand-drawn and web images, "project it onto the natural image manifold", at "noise levels [1, 3, 5, 7, 10, 20]".
  - §1.7.2: Inpainting (cites RePaint).
  - §1.7.3: Text-conditional image-to-image ("adds control using language"), at the same noise levels.
  - §1.8: Visual anagrams ("an oil painting of people around a campfire" / "an oil painting of an old man").
  - §1.9: Hybrid images, "low frequencies from one noise estimate with high frequencies of the other."

**Fall 2024** — [fa24/hw/proj3](https://raw.githubusercontent.com/cal-cs180/fa24/main/hw/proj3/index.html) [fetched]
- Project 3, "Face Morphing" (due 8 Oct 2024):
  - "define pairs of corresponding points on the two images by hand". A Delaunay triangulation, and "the triangulation has to be the same throughout the morph!" "implementing an affine warp for each triangle".
  - Each frame is "warped into an intermediate shape configuration controlled by warp_frac" and "then cross-dissolved according to dissolve_frac". These "are the only parameters that will vary from frame to frame".
  - Also: a mean face, and "a caricature of your face by extrapolating from the population mean".

**Fall 2026** (current semester) — [fa26 index](https://raw.githubusercontent.com/cal-cs180/cal-cs180.github.io/main/fa26/index.html) [fetched]
- **Project list:** Proj0, Proj1, Proj2 Filters & Frequencies, Proj3 Fun with Flow Models, Proj4 (Auto)stitching and Photo Mosaics, and a Final Project for teams of four (proposal, two GSI check-ins, presentation, deliverable).
- Instructors Alexei Efros and Ren Ng. "Fun with Diffusion Models" is commented out, the NeRF entry is removed by script, and morphing appears only as a lecture (8 Oct).
- **Project 2** (due 29 Sep 2026): stacks "never downsampled"; built-in pyramid functions such as cv2.pyrDown() are disallowed. "Multiresolution blending computes a gentle seam between the two images seperately at each band of image frequencies" (Burt & Adelson 1983). An irregular mask "(something besides a line)". Hybrids cite Oliva, Torralba and Schyns 2006. — [fa26/hw/proj2](https://raw.githubusercontent.com/cal-cs180/cal-cs180.github.io/main/fa26/hw/proj2/index.html) [fetched]
- **Project 3, "Fun with Flow Models"** (due 20 Oct 2026) — [index](https://raw.githubusercontent.com/cal-cs180/cal-cs180.github.io/main/fa26/hw/proj3-flow/index.html); [parta](https://raw.githubusercontent.com/cal-cs180/cal-cs180.github.io/main/fa26/hw/proj3-flow/parta.html) [fetched]
  - Part A uses PixNerd-XXL-P16-T2I (512×512) with no training. Part B builds a UNet and trains flow matching on MNIST.
  - §3.1: take "the original Campanile image, noise it a little" and edit with "starting time of [0.02,0.04,0.06,0.10,0.14,0.25,0.5]".
  - §3.2: text-guided editing with the same start times.
  - §3.3: visual anagrams.
  - §3.4: hybrids, which "combine low frequencies from one velocity estimate with high frequencies of the other".
- **Project 4, "[Auto]Stitching Photo Mosaics"** (Part A due 27 Oct 2026, Part B due 10 Nov 2026). It lives in the folder `fa26/hw/proj3`. — [fa26/hw/proj3](https://raw.githubusercontent.com/cal-cs180/cal-cs180.github.io/main/fa26/hw/proj3/index.html) [fetched]

### Inferences
How each part of our project maps onto course material:
- **Grow ladder:** Fa25 Proj5 §1.7 / Fa26 Proj3 §3.1. Their "series of edits at noise levels [1…20]" (or start times [0.02…0.5]) figure, played as a time sequence from plate to world.
- **Two-band blend:** Fa25/Fa26 Proj2 §2.4 (Burt–Adelson stacks and per-band seams), plus the Proj3 mosaic hint that "a 2-level pyramid should be enough" for high-frequency ghosting. Also the Proj5 §1.9 / Fa26 §3.4 low/high frequency split.
- **Irregular-mask blending:** Proj2's irregular mask "(something besides a line)" maps to our portal ring, depth rule and horizon wave as irregular, time-varying masks.
- **Morph:** the Fa24 Proj3 warp_frac/dissolve_frac becomes our ladder index plus two-band dissolve. No warp is needed because the plate and the world are geometry-aligned.
- **Homographies/mosaics:** the existing pipeline's homography alignment (per the precedents note) uses the Proj3/Proj4 `computeH` and inverse warping.

### Gaps
- I could not fetch the official rendered pages (inst.eecs.berkeley.edu and cal-cs180.github.io are blocked), so the quotes come from the GitHub-hosted source HTML. The public URL mapping is inferred.
- The Fall 2026 final-project spec is a Google Doc linked from the index and was not fetched.
- I did not read Fa25 Proj5 Part B or Fa25 Proj3 Part B.
