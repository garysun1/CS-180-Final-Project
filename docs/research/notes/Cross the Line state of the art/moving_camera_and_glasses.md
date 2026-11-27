# Moving camera and smart glasses

> Research sweep of 27 November 2026. Evidence marks: **read** (the page was opened), **snippet** (search-result text only), **memory** (unverified). Social and product sites were blocked in the session, so product facts are mostly snippets.

## Summary

Restyling from a moving, head-worn camera already exists as a product, but every product we found redraws everything in the frame, people included, and not in a stable way. Meta's own Restyle, in the Meta AI and Edits apps, works on glasses footage after capture. It handles about 10 seconds per clip, returns lower resolution and frame rate than the original, and also changes the people in front of the camera. Decart XR, an open-source client for Quest 3, streams the passthrough camera to Decart's servers. A hands-on review measured about 1 second of lag and poor consistency, and the result shows as a flat floating window. Neither one keeps real people as filmed or restyles a stable world once, so that combination is still ours for a moving camera. For developers, Meta's Wearables Device Access Toolkit (developer preview, Android SDK v1.1.0) does give a live camera stream. Over Bluetooth it tops out at 720x1280 and 30 fps. Clips recorded on the glasses and imported through the Meta AI app are better quality (Gen 2: up to 3K, about 100 degree field of view), so the best plan for the demo is to record first and process afterwards. The cheapest method is the team's own roadmap step 1. When the wearer only turns, frames are linked by homographies: build one panorama (the median per panorama pixel), restyle it once, and warp it back. This needs only a CPU, OpenCV and the course mosaics project. Later options get more general and much heavier: layered atlases (CoDeF, NaRCan; need a GPU and short clips), feed-forward 3D (VGGT, Depth Anything 3, MASt3R-SLAM, ViPE; free Colab can run them on short clips), feed-forward stylized 3D (Styl3R, Stylos at ICLR 2026, AnyStyle in Feb 2026), and camera-controlled video models (too heavy for 12 days, and they redraw people). The smallest credible experiment: 20 s of turning on the spot, from the team's own glasses or an Aria Everyday Activities clip. Measure loop drift, how much the background flickers, and person-mask quality against two baselines: restyling every frame separately, and Meta Restyle on the same clip.

## Findings

### [Meta AI Restyle (video) in the Meta AI / Edits apps, used on glasses footage](https://www.socialmediatoday.com/news/meta-adds-ai-video-restyling-instagram-edits-ai-app/750487/) (2025-06 (rolled out); glasses use reported in 2025)
*product · evidence: snippet · relevance 5/5*

- **What:** Generative restyling of an uploaded clip using preset prompts (graphic novel, vintage comic, video game). Meta's help page gives a 10 s maximum. Tom's Guide tested Oakley Meta HSTN footage: the output had lower resolution and frame rate than the original, foreground people were transformed and background people were not.
- **Relevance:** Closest product to 'restyle glasses footage'. It is done after capture, it restyles the people too, and it is not a world drawn once. Our pitch differs exactly there: one world image, real people kept real, and the choice of where each world shows.
- **How we differ:** It: one tap, any motion, but only 10 s, and it changes people and the whole frame. Us: a stable background (drawn once), people kept as filmed, worlds per region and crossings; but we need a static or rotating camera.
- **What to take:** Use it as the honest baseline in the talk: run the same 10 s glasses clip through Meta Restyle and through our pipeline, side by side.

### [Decart XR (Quest 3 passthrough to Mirage / Lucy Restyle Live)](https://www.uploadvr.com/decart-xr-intriguing-early-attempt-at-ai-reskinning/) (2025)
*demo · evidence: snippet · relevance 5/5*

- **What:** An open-source Unity/WebRTC client sends one of the Quest 3's colour passthrough cameras to Decart's server models. 'Warp the World' uses Mirage; Lucy restyles people. Decart claims under 200 ms latency. UploadVR measured about 1 s of lag behind head motion and poor consistency, and the output appears as a 2D rectangle.
- **Relevance:** State of the art for live world restyling on a headset. It shows the failure modes our 'draw once' idea avoids: lag, flicker, people get changed.
- **How we differ:** It: live, any motion, but cloud GPU, about 1 s lag, inconsistent, and people restyled too. Us: drawn once, so no flicker and no per-frame GPU, but currently a tripod only.
- **What to take:** Quote the measured 1 s lag and the flat 2D window as the reason to restyle once and reproject. The client is open source (linked from platform.decart.ai/showcase/decart-xr).

### [Irani-Anandan mosaics / Brown-Lowe panoramas (OpenCV Stitcher)](https://docs.opencv.org/4.x/d1/d46/group__stitching.html) (1996-2007 (classic))
*paper · evidence: memory · relevance 5/5*

- **What:** When the camera only rotates, frames are linked by homographies. Bundle-adjusted stitching onto a cylinder or sphere, plus a median 'background sprite' (the MPEG-4 sprite idea), gives one static background for the whole clip.
- **Relevance:** Roadmap step 1 exactly: the direct extension of our median clean plate to a rotating camera. It is a CPU method and course material (the mosaics project).
- **How we differ:** It: geometry only. Us: add restyle-once and the people layer on top.
- **What to take:** Use cv2.Stitcher (PANORAMA mode, cylindrical warper) or our own course code. Keep each frame's homography, compute a per-panorama-pixel median, run SD once on the panorama, then warp it back with the inverse homography.

### [Meta Wearables Device Access Toolkit (DAT)](https://github.com/facebook/meta-wearables-dat-android) (announced at Connect 2025 (Sep); developer preview 2025-12; Android SDK mwdat 1.1.0 in 2026)
*repo · evidence: read · relevance 4/5*

- **What:** iOS and Android SDK that lets a phone app start a video stream from Ray-Ban/Oakley Meta glasses and receive frames, capture a photo during a stream, and pause/resume/stop. Includes MockDeviceKit for testing without glasses and a CameraAccess sample. Still a developer preview; audio streaming and standalone capture are experimental and cannot be published to production.
- **Relevance:** Answers 'can developers get the camera stream?': yes, live, to a phone app, which could forward frames to our compositor.
- **How we differ:** It is plumbing only; nothing for restyling.
- **What to take:** Optional live mode: phone app (DAT) to WebRTC to the portal kiosk. Our per-frame cost is only the composite, so 30 fps is plausible. Only worth it after recorded clips work.

### [DAT stream limits: 720x1280 maximum, 30 fps, Bluetooth quality ladder](https://mixed-news.com/en/meta-dat-camera-720x1280-lower-resolution-higher-quality/) (2025-12 / 2026)
*post · evidence: snippet · relevance 4/5*

- **What:** The stream maximum is 720p at 30 fps because the glasses connect to the phone over Bluetooth Classic. Presets are 720x1280, 504x896 and 360x640, and the stream automatically drops quality when bandwidth falls (UploadVR and Meta's iOS guide say the same).
- **Relevance:** Sets expectations: a live stream is portrait 720p and may degrade, while recorded clips are much better.
- **What to take:** Use recorded clips for the demo; mention the live stream only as future work.

### [Ray-Ban Meta Gen 2 camera specs](https://www.meta.com/ai-glasses/ray-ban-meta-gen-2/) (2025-09)
*product · evidence: snippet · relevance 4/5*

- **What:** 12 MP ultra-wide camera, about 100 degree field of view, '3K Ultra HD' video (about 6.4 MP per frame). Third-party guides list 3K/30, 1440p/30 and 1200p/60 (Gizmodo says 60 fps means 1080p). One guide gives a 3 min maximum clip; Meta's own figure was not confirmed. Clips are imported to the phone through the Meta AI app.
- **Relevance:** Practical facts for filming: a 100 degree wide-angle lens means strong distortion, so frames must be undistorted or projected onto a cylinder before stitching. Clips longer than 20 s are possible.
- **What to take:** Film at 1440p/30 or 3K/30, export from the Meta AI app, and undistort with a checkerboard calibration filmed through the glasses (the course's camera calibration).

### [CoDeF: Content Deformation Fields](https://github.com/ant-research/CoDeF) (2023-08 (CVPR 2024))
*repo · evidence: memory · relevance 4/5*

- **What:** Represents a video as one canonical image plus a deformation field. Edit the canonical image (for example with ControlNet) and the edit propagates to all frames. Training takes minutes per short clip on one GPU, and clips are usually about 100-200 frames.
- **Relevance:** The atlas option for walking (parallax). The canonical image plays the role of our clean plate.
- **How we differ:** It: one canonical image for general motion, but people are usually folded into the same field, and it fails with large camera motion or new content appearing. Us: separate people layer.
- **What to take:** Fallback for a short walking clip on Colab: train on the background (people masked out), restyle the canonical image once, render, then composite the real people with our existing mask.

### [Depth Anything 3](https://arxiv.org/abs/2511.10647) (2025-11)
*model · evidence: snippet · relevance 4/5*

- **What:** A single transformer that predicts depth and camera rays/pose from one or many views (video). It beats VGGT on multi-view pose and geometry. Apache-2.0 small models exist; the team already uses Depth Anything V2.
- **Relevance:** The easiest feed-forward route to camera poses and depth for a walking clip, from the same family as the depth model we already use.
- **What to take:** On Colab: run DA3 on keyframes of a walking clip, get poses and depth, restyle one keyframe, and reproject it to the others by depth warping. Fill holes from a second restyled keyframe.

### [Static Scene Reconstruction from Dynamic Egocentric Videos](https://arxiv.org/abs/2603.22450) (2026-03)
*paper · evidence: read · relevance 4/5*

- **What:** Adapts static reconstruction backbones (improving on MapAnything) to long first-person video. Masks out dynamic foreground (hands, people) in attention, reconstructs in chunks and stitches them with a pose graph. No code linked.
- **Relevance:** The 3D, egocentric version of our clean plate: an empty static scene recovered from worn-camera video with people moving through it.
- **What to take:** Cite it as the 'clean plate for a head-worn camera' state of the art; its idea of masking dynamic pixels matches our median plus person masks.

### [EbSynth 2](https://ebsynth.com/) (2025-09)
*product · evidence: snippet · relevance 4/5*

- **What:** Browser-based keyframe propagation (optical flow plus patch synthesis, not generative). Adds layers, a timeline and real-time preview; the free tier exports MP4 up to 720p.
- **Relevance:** Keyframe propagation: restyle one frame with SD and spread it along the clip. Works on moving cameras for short spans but drifts and smears when new content appears.
- **How we differ:** It: propagates by flow, so people are restyled along with everything else unless masked on a layer. Us: drawn once in a shared frame, people kept real.
- **What to take:** A zero-code baseline: SD frame 0 into EbSynth 2 on the same glasses clip, compared with our panorama result.

### [Aria Everyday Activities dataset](https://huggingface.co/datasets/projectaria/aria-everyday-activities) (2024-02)
*dataset · evidence: snippet · relevance 4/5*

- **What:** 143 egocentric recordings in 5 locations from Project Aria glasses, with 6-DoF trajectories, eye gaze and speech. A sample sequence of about 3 GB can be downloaded after accepting the licence. The RGB camera is a fisheye (needs projectaria_tools to undistort).
- **Relevance:** A glasses-like test clip with ground-truth camera poses for development before the team films its own.
- **What to take:** Pick a stretch where the wearer mostly turns; the trajectory gives ground truth to check whether the motion is near pure rotation.

### [Layered Neural Atlases / NaRCan / Hashing-NVD](https://layered-neural-atlases.github.io) (2021 / NeurIPS 2024 / CVPR 2024)
*paper · evidence: memory · relevance 3/5*

- **What:** Decompose a video into foreground and background atlases. Editing an atlas edits every frame. LNA needs hours of GPU per roughly 70-frame clip; NaRCan adds a diffusion prior and is faster; Hashing-NVD uses hash grids for speed. Code exists for all three.
- **Relevance:** Prior work already covered in academic_prior_work.md Q2. For a moving camera, the background atlas is a learned panorama, the same idea as roadmap step 1 but able to handle parallax.
- **What to take:** Cite it as the general-motion version of what we do with homographies. Not worth building in 12 days.

### [VGGT (Visual Geometry Grounded Transformer)](https://github.com/facebookresearch/vggt) (2025-03 (CVPR 2025 best paper))
*model · evidence: memory · relevance 3/5*

- **What:** Feed-forward network that predicts cameras, depth, point maps and tracks for 1 to hundreds of frames in seconds on a GPU.
- **Relevance:** Same use as DA3: poses and depth for reprojecting a world restyled once.
- **What to take:** Alternative to DA3. Free Colab T4 memory limits it to a few dozen frames.

### [ViPE: Video Pose Engine (NVIDIA)](https://nv-tlabs.github.io/vipe/) (2025-08; DA3 integration added 2026-01 (per a fork))
*repo · evidence: snippet · relevance 3/5*

- **What:** Estimates camera intrinsics, motion and dense near-metric depth from raw, unconstrained videos at 3-5 fps on one GPU. Apache-2.0 apart from a non-commercial component.
- **Relevance:** Built for in-the-wild handheld or worn video, including lens intrinsics, which matters for the 100 degree glasses lens.
- **What to take:** Use it if DA3 poses drift on glasses footage; its intrinsics estimate also helps undistortion.

### [Styl3R: Instant 3D stylized reconstruction](https://arxiv.org/abs/2505.21060) (2025-05)
*paper · evidence: snippet · relevance 3/5*

- **What:** Feed-forward network that predicts stylized 3D Gaussians from unposed sparse views and a style image in under 1 s.
- **Relevance:** Stylized 3D in one pass. Its input is a style image (not a text prompt), and it works on static scenes.
- **How we differ:** It: a 3D-consistent style but no people layer, and style transfer only, not a 'winter' or '1920s' world.
- **What to take:** Possible: use our SD world image as the style reference.

### [Stylos (ICLR 2026) and AnyStyle (2026-02)](https://arxiv.org/abs/2602.04043) (2025-09 / 2026-02)
*paper · evidence: snippet · relevance 3/5*

- **What:** Stylos (arXiv 2509.26455) is single-forward 3D Gaussian style transfer on unposed content and is more consistent across views than Styl3R. AnyStyle is pose-free, zero-shot feed-forward reconstruction plus stylization with multimodal (text or image) conditioning.
- **Relevance:** The 2026 state of the art for 'restyle the 3D scene once' from photos. These are the methods to cite for the far end of the moving-camera roadmap.
- **What to take:** Cite them as where our idea goes when the camera walks: style the 3D scene once, render it from the wearer's pose, and add the people as filmed.

### [VACE / AnyV2V (first-frame-guided video editing)](https://github.com/ali-vilab/VACE) (2025-03 / 2024)
*repo · evidence: memory · relevance 3/5*

- **What:** VACE (on Wan2.1/2.2) does reference- and first-frame-guided video editing and inpainting; the 1.3B model runs on about 8-12 GB of VRAM, about 5 s per clip. AnyV2V edits frame 1 with any image editor, then propagates it with an image-to-video model.
- **Relevance:** The 'fall back to a video model on short clips' option in the roadmap. It handles walking but redraws people and is limited to short clips.
- **What to take:** Could also be used only on the background: mask people out with VACE's mask input, then composite the real people back.

### [MASt3R-SLAM / DUSt3R / MASt3R / CUT3R / MegaSaM / pi3](https://github.com/rmurai0610/MASt3R-SLAM) (2024-2025)
*repo · evidence: memory · relevance 2/5*

- **What:** MASt3R-SLAM runs dense SLAM at about 15 fps on a desktop GPU. MegaSaM handles dynamic scenes with casual camera motion. CUT3R is a streaming recurrent model. pi3 is a permutation-equivariant reconstruction model. DUSt3R/MASt3R are under the non-commercial CC BY-NC licence.
- **Relevance:** Building blocks for a full 3D version. All need a GPU, and none restyles anything.
- **What to take:** Mention them in related work only.

### [Instruct-GS2GS / StyleGaussian](https://github.com/cvachha/instruct-gs2gs) (2023-2024)
*repo · evidence: memory · relevance 2/5*

- **What:** Iterative dataset updates with InstructPix2Pix on a Gaussian splat (needs a GPU, about 30+ min per scene). StyleGaussian embeds features into 3DGS for fast style transfer.
- **Relevance:** The optimisation-based predecessors of Styl3R and Stylos.

### [GEN3C / TrajectoryCrafter / ReCamMaster](https://github.com/nv-tlabs/GEN3C) (2025)
*repo · evidence: memory · relevance 2/5*

- **What:** Video diffusion models with camera control, conditioned on a 3D cache (GEN3C) or the source video (TrajectoryCrafter, ReCamMaster). They need large GPUs (24-80 GB) and produce clips of about 2-5 s.
- **Relevance:** Re-render a scene along new camera paths. Related to reprojection but far too heavy for the team.

### [World Labs Marble / Google DeepMind Genie 3](https://www.worldlabs.ai/) (2025-08 (Genie 3, research preview) / 2025-11 (Marble))
*product · evidence: memory · relevance 2/5*

- **What:** Marble generates persistent, downloadable 3D worlds (Gaussian splats) from text, images or video; Genie 3 is an interactive world model at 720p/24 fps with minutes of consistency, not publicly available.
- **Relevance:** For the talk: 'drawn once' world generation at full 3D scale. Marble's 'world from a video' input is the closest; it does not keep real people.
- **What to take:** Possible stretch: export a Marble splat from our restyled panorama. Not verified.

### [Ego4D / Ego-Exo4D](https://ego4d-data.org/) (2021 / 2023)
*dataset · evidence: memory · relevance 2/5*

- **What:** Thousands of hours of head-worn video (Ego4D), plus egocentric clips paired with exocentric cameras (Ego-Exo4D). Access requires a licence agreement, usually approved within days.
- **Relevance:** More varied footage, but the licence process takes time.
- **What to take:** AEA is faster to get; skip Ego4D unless approval is quick.

### [Snap Specs (2026 consumer AR glasses) and Lens Studio AI](https://techcrunch.com/2025/06/10/snap-plans-to-sell-lightweight-consumer-ar-glasses-in-2026) (announced 2025-06; launch planned for 2026)
*product · evidence: snippet · relevance 2/5*

- **What:** Consumer Specs promised for 2026, with OpenAI/Gemini multimodal lenses, Snap3D generation and 'AI Clips' (image to video lens). No world-restyle lens was found.
- **Relevance:** Snap's phone lenses do restyle the world, but nothing for glasses was found; the launch status in late 2026 is unverified.

## Ideas to borrow

- **'Turn on the spot' pipeline: undistort, OpenCV Stitcher onto a cylinder (keep every frame's homography), per-panorama-pixel temporal median, run SD/ControlNet once on the panorama (tile or run at about 768 px height), warp it back into each frame with the inverse homography, then use the existing person mask (difference to the warped plate) and the existing compositor.** Source: Brown-Lowe / OpenCV stitching (https://docs.opencv.org/4.x/d1/d46/group__stitching.html); roadmap 'Later: a moving camera'. The only option that runs on the team's CPU, reuses course code and every existing module unchanged, and keeps the 'drawn once, never flickers, people stay real' promise. *Effort: 2-4 days, CPU only; the SD panorama call takes a few minutes on CPU*
- **Three-way comparison for the talk on the same 10 s glasses clip: (a) per-frame SD img2img (flickers), (b) Meta Restyle in the Meta AI app (restyles people, 10 s limit), (c) ours (stable world, real people). Show them in a single 3-panel loop.** Source: Meta Restyle (https://www.socialmediatoday.com/news/meta-adds-ai-video-restyling-instagram-edits-ai-app/750487/). Puts us honestly against the closest product, Meta's own one for these glasses, and makes the difference visible in 5 seconds. *Effort: hours; needs a phone with the Meta AI app*
- **Metrics: (1) loop closure drift, the pixel error where the 360 or back-and-forth sweep returns to its start; (2) background flicker, the temporal std of the output at static pixels after compensating for camera motion (ours should be about 0, per-frame SD high); (3) person mask IoU on 5 hand-labelled frames; (4) warp error / tLPIPS against the per-frame baseline.** Source: Roadmap first test; standard video-consistency metrics (warp error as used in atlas papers, https://layered-neural-atlases.github.io). Turns 'it works on glasses footage' into numbers for the report. *Effort: 1 day, CPU*
- **Develop on an Aria Everyday Activities sequence with ground-truth poses before filming. Choose a segment where translation is under a few cm, to show when the homography assumption holds and when it breaks.** Source: AEA dataset (https://huggingface.co/datasets/projectaria/aria-everyday-activities). Unblocks work before glasses footage exists and gives ground truth to check against. *Effort: hours to download and undistort (projectaria_tools)*
- **Walking fallback via feed-forward 3D: Depth Anything 3 (or VGGT) on Colab for poses and depth of keyframes, restyle 2-3 keyframes, forward-warp them by depth into the other frames, fill holes, mask people out.** Source: Depth Anything 3 (https://arxiv.org/abs/2511.10647); ViPE (https://nv-tlabs.github.io/vipe/). Extends 'draw once' to parallax using the depth model family we already use; a credible 'next step' slide even if only half done. *Effort: 3-5 days; free Colab T4 GPU*
- **Zero-code baseline: restyle one keyframe with our SD pipeline and propagate it with EbSynth 2 in the browser; show where it drifts as new content enters the frame.** Source: EbSynth 2 (https://ebsynth.com/). A cheap, recognised comparison for the walking case; shows why a shared panorama or atlas is better. *Effort: hours; free tier exports 720p*
- **Walking clip via CoDeF on Colab: train the canonical field with people masked, restyle the canonical image once, render it, and composite the real people.** Source: CoDeF (https://github.com/ant-research/CoDeF). The atlas option from the roadmap with working code and minute-scale training. *Effort: 2-3 days; Colab GPU; may fail on large motion*
- **Paint masks in panorama coordinates: let the brush tool paint on the stitched panorama, so painted regions stay fixed in the world as the wearer turns (a region 'behind' you appears when you look back).** Source: Our paint tool plus homography warping (roadmap). A distinctive glasses demo that no product does: 'winter is on the left wall of the room', which stays put as you turn your head. *Effort: 1-2 days on top of the panorama pipeline*
- **Optional live path: DAT phone app streams 720p/30 frames to the kiosk; register each frame to the pre-built panorama (feature matching against the panorama) and composite.** Source: Meta DAT (https://github.com/facebook/meta-wearables-dat-android). Live 'glasses see the restyled world' with no per-frame generative model; the per-frame cost is registration plus the composite. *Effort: 1+ week; Android or iOS dev plus glasses; out of scope for 12 days except as future work*

## Not reached or not verified

- Could not fetch wearables.developer.meta.com, meta.com, tomsguide.com or cookbook.decart.ai (hosts blocked in this session). The 720x1280/30 fps limit, Meta Restyle's 10 s cap and the Decart XR lag come from search snippets. Check them by hand in the DAT docs (Camera > resolution/frame rate) and in the Meta AI app.
- Meta's official maximum video length and stabilization behaviour for Ray-Ban Meta Gen 2 / Ray-Ban Display were not confirmed (one guide says 3 min). Check the Meta AI app's capture settings on the actual glasses.
- Whether Meta Restyle in late 2026 handles longer clips or offers 'world-only' styles with people kept was not verified. Try it in the Meta AI app on a glasses clip.
- No 2026 launch coverage for Snap Specs was found, and no world-restyle lens on glasses or Spectacles. Search the Snap newsroom and the Lens Explorer on device.
- Apple Vision Pro and Android XR passthrough restyling were not searched (Vision Pro does not give developers camera access except in enterprise APIs, from memory).
- No 2026 successor to NaRCan / CoDeF was found by search. Check arXiv citations of NaRCan and CoDeF by hand.
- Social media: search X, YouTube and Instagram for 'Ray-Ban Meta AI restyle', 'Decart XR', 'Quest passthrough AI' and 'Mirage LSD glasses' to see real demo quality and frame rates; also r/RaybanMeta for clip-export tips.
- Licences: confirm VGGT and Depth Anything 3 model licences (some large DA3 checkpoints may be non-commercial) before using them in the report.

## Notes

## 1. What exists for glasses and headsets (late 2026)

**Meta's own Restyle.** Video Restyle launched in the Meta AI app, the meta.ai site and Instagram's Edits app around June 2025 ([PetaPixel 2025-06-12](https://petapixel.com/2025/06/12/edits-video-app-for-instagram-gets-new-restyle-generative-ai-tool), snippet). Meta's help page gives a 10 s maximum ([Meta help](https://www.meta.com/help/artificial-intelligence/996454095987249/), snippet). Tom's Guide tried it on Oakley Meta HSTN footage. It "transforms the people directly in front of me but does nothing for everyone else in the background", and the output had lower resolution and frame rate than the original ([Tom's Guide](https://www.tomsguide.com/computing/smart-glasses/these-ai-edited-videos-i-generated-with-the-oakley-meta-hstn-glasses-are-the-stuff-of-my-dreams), snippet). There is also photo restyle on the glasses themselves ([Meta help](https://www.meta.com/help/ai-glasses/1080562823561076/)). **Honest statement for the talk:** "Meta already restyles glasses video, but per clip, about 10 s, and it redraws the people. We draw the world once and leave the people as filmed."

**Decart XR.** An open-source Quest 3 client: passthrough camera, WebRTC, Decart server (Mirage / Lucy Restyle Live), back into VR ([Decart showcase](https://platform.decart.ai/showcase/decart-xr)). Decart claims under 200 ms latency. UploadVR measured about 1 s of lag behind head motion, "poor image consistency", and a flat rectangular window ([UploadVR](https://www.uploadvr.com/decart-xr-intriguing-early-attempt-at-ai-reskinning/)). Lucy is the character model, so people are restyled too. Meta's native passthrough styling only does colour maps and edges ([Meta docs](https://developers.meta.com/horizon/documentation/unity/unity-passthrough/)).

**Snap.** Specs for consumers were promised for 2026 with OpenAI/Gemini lenses, Snap3D and 'AI Clips' ([TechCrunch](https://techcrunch.com/2025/06/10/snap-plans-to-sell-lightweight-consumer-ar-glasses-in-2026)). No glasses world-restyle lens was found.

## 2. Ray-Ban Meta practicalities

- Gen 2: 12 MP ultra-wide, about 100 degree FOV, "3K Ultra HD" (about 6.4 MP per frame); modes reported as 3K/30, 1440p/30, 1200p or 1080p/60 ([Meta product page](https://www.meta.com/ai-glasses/ray-ban-meta-gen-2/), [TechRadar](https://www.techradar.com/computing/virtual-reality-augmented-reality/meta-ray-ban-gen-2-smart-glasses-are-official-here-are-5-key-upgrades-you-need-to-know-about), snippets; sources disagree on 60 fps). One guide says clips can be up to 3 min. Recordings are portrait by default, which suits stitching while turning (more vertical coverage per frame).
- Export: clips go through the Meta AI app (formerly Meta View) to the phone's camera roll ([Meta blog](https://www.meta.com/blog/ray-ban-meta-ai-glasses-new-companion-app/)). Stabilization is applied in capture or import; with stabilization, the cropping and warping change between frames, which slightly breaks the pure-homography model. If a setting allows it, film with stabilization off, or simply accept residual error.
- **Developer access:** the Wearables Device Access Toolkit was announced at Connect 2025, entered developer preview in December 2025, and the Android SDK is `mwdat` 1.1.0 ([GitHub](https://github.com/facebook/meta-wearables-dat-android), fetched). It provides streaming, frames and in-stream photo capture, plus MockDeviceKit. The stream maximum is 720x1280 at 30 fps with presets 504x896 and 360x640, and quality drops automatically when the Bluetooth Classic bandwidth falls ([Mixed](https://mixed-news.com/en/meta-dat-camera-720x1280-lower-resolution-higher-quality/), [UploadVR](https://www.uploadvr.com/meta-wearables-device-access-toolkit-public-preview/), snippets). Display glasses get display access separately.

## 3. Methods ladder: code, hardware, clip length, failure modes, and whether people stay real

| # | Method | Code | Hardware | Clip | Fails when | People real? |
|---|---|---|---|---|---|---|
|1|Homography panorama plus median sprite, restyle once, warp back|OpenCV, course code|CPU|any length, rotation only|translation (parallax of near objects; the neck pivot is about 10 cm from the lens), rolling shutter on fast turns, lens distortion, stabilization crop|yes (our mask on top)|
|2|CoDeF / NaRCan / LNA / Hashing-NVD|yes|GPU, minutes to hours|about 100-200 frames|large motion, new content, thin structures|only if we mask them out and composite|
|3|DA3 / VGGT / ViPE / MASt3R-SLAM / MegaSaM / CUT3R / pi3, then reproject restyled keyframes|yes|GPU (Colab OK for short clips)|tens to hundreds of frames|disocclusion holes, dynamic people corrupt the geometry (mask them; see [arXiv 2603.22450](https://arxiv.org/abs/2603.22450))|yes|
|4|Instruct-GS2GS, StyleGaussian, Styl3R, Stylos (ICLR 2026), AnyStyle (Feb 2026)|mostly yes|GPU|sparse views or a scene|static scenes only; style-image based|no people in the model; composite them|
|5|GEN3C, TrajectoryCrafter, ReCamMaster, Marble, Genie 3|partial|24-80 GB GPU or closed|2-5 s|hallucination, heavy compute|no|
|6|EbSynth 2, VACE, AnyV2V|EbSynth web; VACE code|browser / 12 GB GPU|seconds|drift, new content|EbSynth with layers; VACE with mask|

Note on 1: turning in place is not pure rotation. The camera on the glasses sits roughly 8-12 cm in front of the neck's rotation axis (memory, unverified), so near objects (under about 3 m) will show parallax. Sather Gate seen from a plaza, with mostly distant structure, is a good choice. A wall 1 m away is not.

## 4. Smallest credible experiment (fits about 3 days)

1. Clip: 20 s, standing in one spot, slowly turning about 120-180 degrees and back, people walking through. Film on the Ray-Bans at 1440p/30 (or use an AEA sequence until then).
2. Calibrate the 100 degree lens from a checkerboard video filmed through the glasses, then undistort.
3. Stitch with a cylindrical projection and record each frame's homography to the panorama. Compute the per-panorama-pixel median over the frames that cover it, which gives the panorama clean plate.
4. Run the existing generate.py once on the panorama (depth ControlNet on the panorama).
5. Per frame: warp the world and the plate back, take the person mask as the difference to the warped plate, and run the existing compositor. The rules and painted masks also live in panorama coordinates.
6. Measure: loop drift in pixels at the return to the start; background flicker (temporal std at static pixels), ours against per-frame SD; mask IoU on 5 labelled frames; and a visual side-by-side with Meta Restyle (10 s) and EbSynth 2.

Success: drift under a few pixels, flicker close to 0 against per-frame SD, people untouched. Report honestly where parallax breaks it: near objects, walking.

## 5. What to say in the talk (honest)

"Moving-camera restyling exists. Meta's own app does 10 s clips from these glasses, and Decart streams Quest passthrough to a cloud model. Both redraw every frame, so the world shimmers, and both redraw the people. We extend the 'draw once' idea to a turning head with a 1990s trick, panoramic mosaics: one world per panorama, warped back into every frame, with the people left as filmed. Walking needs 3D (Depth Anything 3, stylized Gaussians in 2026 papers), and that is our next step."
