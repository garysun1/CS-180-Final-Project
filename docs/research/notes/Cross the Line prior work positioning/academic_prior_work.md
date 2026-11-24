# Prior work for "Cross the Line": video restyling, atlas and layer decomposition, compositing people into edited backgrounds (as of 23 Nov 2026)

Every source I checked is real. The README's "FreeVIS" is spelled **FreeViS** (ICLR 2026). "VISTA" is real but has no venue yet, and a second, unrelated paper uses the same name.

**Verification labels used throughout:**
- **[F]**: I fetched the primary page (arXiv abs/HTML or GitHub README) and read the metadata.
- **[S]**: confirmed through search results that list the primary page (CVF, ICLR, ACM, project or official site), but I did not open the page. Several of those hosts are blocked in this session.
- **[U]**: unverified, or from memory only.

**Blocked hosts:** runway.com, help.runwayml.com, docs.lumalabs.ai, ar5iv.labs.arxiv.org and openaccess.thecvf.com are outside this session's network allowlist. export.arxiv.org returned HTTP 429 (rate limit). Product limits below therefore come from search summaries of official pages and from third-party API listings.

## Q0. Are the README's citations real and accurate?

### Takeaway
All ten works cited in §1–2 exist, and the claims made about them hold up. Fix the spelling of FreeViS. Pin VISTA to arXiv 2605.17312 so it isn't confused with the other VISTA. Also give dates for the products, because their limits change month to month.

### Cited Findings
- **pix2pix.** Isola, Zhu, Zhou, Efros, "Image-to-Image Translation with Conditional Adversarial Networks," CVPR 2017, arXiv 1611.07004. It needs paired training data. [S] — [GitHub phillipi/pix2pix](https://github.com/phillipi/pix2pix)
- **CycleGAN.** Zhu, Park, Isola, Efros, "Unpaired Image-to-Image Translation using Cycle-Consistent Adversarial Networks," ICCV 2017. The arXiv version is labelled "an extended version of our ICCV 2017 paper." [S] — [arXiv 1703.10593](https://arxiv.org/abs/1703.10593)
  - I did not re-check that the summer↔winter Yosemite example appears in the paper. [U]
- **ControlNet.** Zhang, Rao, Agrawala, "Adding Conditional Control to Text-to-Image Diffusion Models," ICCV 2023, pp. 3836–3847. Conditions include edges, depth, segmentation and pose. [S] — [CVF ICCV 2023](https://openaccess.thecvf.com/content/ICCV2023/html/Zhang_Adding_Conditional_Control_to_Text-to-Image_Diffusion_Models_ICCV_2023_paper.html)
- **VISTA.** Song, Yao, Wang, Shou, "VISTA: Triplet-Supervised Video Style Transfer with Diffusion Transformers," arXiv 2605.17312, 17 May 2026. No venue is listed. [F] — [arXiv](https://arxiv.org/abs/2605.17312)
  - It is a DiT in-context framework trained on the synthetic VISTA-1000 dataset (1,000 styles, 12k motion-aligned triplets). A causal distillation step yields a few-step autoregressive student. [F/S] — [arXiv](https://arxiv.org/abs/2605.17312); [search summary](https://www.alphaxiv.org/abs/2605.17312)
  - The abstract gives no clip length, resolution, base model or GPU. [F]
  - **Name collision:** arXiv 2609.23817, "VISTA: Video-Injected Stylized Text-to-Animation," is a different paper. [S] — [arXiv PDF](https://arxiv.org/pdf/2609.23817)
- **FreeViS** (README: "FreeVIS"). Xu, Mei, Zhang, Patel (JHU and Adobe Research), "FreeViS: Training-free Video Stylization with Inconsistent References," ICLR 2026, arXiv 2510.01686, Oct 2025. [F] — [arXiv HTML](https://arxiv.org/html/2510.01686v1); [S] — [ICLR 2026 proceedings](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1458726f6d5280ae99aee06ddbe455f3-Abstract-Conference.html)
- **Runway Aleph 2.0.** Announced 21 May 2026 together with "Edit Studio." You edit one frame and the edit propagates. It supports multi-shot clips, "up to 30 seconds at 1080p." [S] — [Runway news](https://runway.com/news/introducing-aleph-2-and-edit-studio) (search summary only; host blocked)
  - OpenRouter lists a 2026-07-29 API version at $0.28/s. [S] — [OpenRouter](https://openrouter.ai/runway/aleph-2-20260729)
- **Luma Modify Video.** Real; it was Ray2-based at API launch. [S] — [Luma changelog](https://lumalabs.ai/changelog/modify-video-api-release)
  - It is now also offered as Ray3.2 video-to-video. [S] — [Luma Ray3.2 V2V guide](https://lumalabs.ai/learning-center/articles/ray-3-2-video-to-video)
- **Wan VACE.** Jiang et al. (Tongyi Lab), "VACE: All-in-One Video Creation and Editing," ICCV 2025, arXiv 2503.07598. Wan2.1-VACE 1.3B and 14B were released 14 May 2025. [F] — [GitHub ali-vilab/VACE](https://github.com/ali-vilab/VACE)
- **Layered Neural Atlases.** Kasten, Ofri, Wang, Dekel, SIGGRAPH Asia 2021, ACM TOG 40(6), arXiv 2109.11418. [F] — [arXiv](https://arxiv.org/abs/2109.11418); [GitHub](https://github.com/ykasten/layered-neural-atlases)
- **CoDeF.** Ouyang et al., CVPR 2024, pp. 8089–8099, arXiv 2308.07926. [F] — [arXiv](https://arxiv.org/abs/2308.07926); [S] — [CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Ouyang_CoDeF_Content_Deformation_Fields_for_Temporally_Consistent_Video_Processing_CVPR_2024_paper.html)
- **SAM 3** (README §2 step 4). "SAM 3: Segment Anything with Concepts," arXiv 2511.16719, 20 Nov 2025, ICLR 2026. Prompts can be noun phrases and/or image exemplars. [S] — [arXiv](https://arxiv.org/abs/2511.16719v1); [ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/e0982cbc81401df3430ee1ff780dc7a2-Abstract-Conference.html)

### Inferences
- "Regenerate every pixel of every frame" is accurate for all five video systems the README names.
  - VISTA and FreeViS are video diffusion generators.
  - Aleph, Modify Video and VACE are V2V models.
- The README's "quality degrades on clips longer than a few seconds" is best supported by the documented clip caps (Q4). I found no vendor statement that geometry drifts, so phrase that claim as our own observation, or cite MLV-Edit's "cumulative structural drift."

### Gaps
- I did not verify FLUX.2 Klein 9B, Qwen-Image-Edit-2511, LCM-LoRA or Depth Anything V2. They are our own tools, so I kept them out of scope.

## Q1. Per-frame and zero-shot diffusion video editing: what causes flicker or drift, what clip length, what compute?

### Takeaway
Zero-shot editors run an image diffusion model on every frame and bolt consistency on afterwards. The tools they use are shared or extended attention, feature propagation along flow, token merging, inversion features, and EbSynth propagation from keyframes. Flicker comes back wherever those soft constraints fail: occlusion, fast motion, bad flow, batch boundaries, and error accumulating frame by frame. Clip length is capped by GPU memory, which forces batches or keyframes. Speeds run from about 0.1 to 1 fps on datacenter GPUs, with live streaming as the exception.

### Cited Findings
- **Rerender-A-Video.** Yang, Zhou, Liu, Loy, SIGGRAPH Asia 2023, arXiv 2306.07954. [F] — [arXiv](https://arxiv.org/abs/2306.07954)
  - Keyframes are generated with hierarchical cross-frame constraints on shape, texture and colour, then propagated to the other frames by temporal-aware patch matching and frame blending. It is training-free.
  - Differs from ours: it still diffuses every keyframe, and its consistency is only as good as the optical flow.
- **TokenFlow.** Geyer, Bar-Tal, Bagon, Dekel, ICLR 2024, arXiv 2307.10373. [F] — [arXiv](https://arxiv.org/abs/2307.10373); [S] — [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/069274129275ec1c6511abb5f6d96a31-Abstract-Conference.html)
  - It enforces consistency in diffusion-feature space "by explicitly propagating diffusion features based on inter-frame correspondences." It is training-free and preserves "the spatial layout and motion of the input video." [F]
  - The repo says it is designed for structure-preserving edits. [S] — [GitHub](https://github.com/omerbt/TokenFlow)
- **FateZero.** Qi et al., ICCV 2023 Oral, arXiv 2303.09535. [F] — [arXiv](https://arxiv.org/abs/2303.09535)
  - It stores attention maps during DDIM inversion and fuses them during editing, adds spatial-temporal self-attention, and uses a blending mask from cross-attention.
  - Differs from ours: it needs per-video inversion and edits all frames.
- **Pix2Video.** Ceylan, Huang, Mitra, ICCV 2023, pp. 23206–23217, arXiv 2303.12688. [F] — [arXiv](https://arxiv.org/abs/2303.12688); [S] — [CVF](https://openaccess.thecvf.com/content/ICCV2023/html/Ceylan_Pix2Video_Video_Editing_using_Image_Diffusion_ICCV_2023_paper.html)
  - It edits an anchor frame with a depth-conditioned image diffusion model, then propagates the edit through self-attention feature injection and a latent update. It is training-free.
- **Text2Video-Zero.** Khachatryan et al., ICCV 2023, arXiv 2303.13439. [F] — [arXiv](https://arxiv.org/abs/2303.13439); [S] — [CVF](https://openaccess.thecvf.com/content/ICCV2023/html/Khachatryan_Text2Video-Zero_Text-to-Image_Diffusion_Models_are_Zero-Shot_Video_Generators_ICCV_2023_paper.html)
  - It adds motion dynamics to the latents and makes every frame attend to the first frame. It includes Video Instruct-Pix2Pix editing and is training-free.
- **ControlVideo.** Zhang et al., ICLR 2024, arXiv 2305.13077. [F] — [arXiv](https://arxiv.org/abs/2305.13077); [S] — [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/ef74413c7bf1d915c3e45c72e19a5d32-Abstract-Conference.html)
  - It uses fully cross-frame attention, an "interleaved-frame smoother" against flicker, and a hierarchical sampler for long videos.
  - It generates short and long videos "within several minutes using one NVIDIA 2080Ti."
- **VidToMe.** Li, Ma, Yang, Yang, CVPR 2024, arXiv 2312.10656. [F] — [arXiv](https://arxiv.org/abs/2312.10656); [S] — [CVF PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Li_VidToMe_Video_Token_Merging_for_Zero-Shot_Video_Editing_CVPR_2024_paper.pdf)
  - It merges self-attention tokens across frames using temporal correspondence. Long videos are split into chunks, with local merging inside a chunk and global merging across chunks. Merging also reduces memory.
- **FRESCO.** Yang, Zhou, Liu, Loy, CVPR 2024, arXiv 2403.12962. [F] — [arXiv](https://arxiv.org/abs/2403.12962); [F] — [arXiv HTML](https://arxiv.org/html/2403.12962v1)
  - Method: intra-frame plus inter-frame correspondence constraints, with explicit feature optimisation (K = 20 Adam steps).
  - Its analysis of what causes flicker:
    - Attention-only guidance is a "soft constraint" that can be "insufficient."
    - Flow guidance fails under occlusion or rapid motion, and when edits change the flow.
    - "Frame-by-frame generation is only locally optimized," so errors accumulate.
    - Inversion-free ControlNet methods are "prone to flickering."
  - Compute: one V100, batches of N = 6–8 frames. "The number of frames N that can be processed at one time is limited by GPU memory."
  - Long video: a 400-frame clip is handled by translating 32 keyframes with diffusion and filling the other 368 frames with EbSynth.
  - Stated limits: it "does not support large shape deformations and significant appearance changes." Rerender beats it when optical flow is good.
- **RAVE** (randomized noise shuffling), CVPR 2024. [S] — [CVF PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Kara_RAVE_Randomized_Noise_Shuffling_for_Fast_and_Consistent_Video_Editing_CVPR_2024_paper.pdf)
- **StreamV2V** ("Looking Backward: Streaming Video-to-Video Translation with Feature Banks"). Liang et al. (UT Austin and UC Berkeley), ICLR 2025, arXiv 2405.15757. [S] — [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/7280f65ed571b7b28321f2c7cf4c60c8-Abstract-Conference.html); [project](https://jeff-liangf.github.io/projects/streamv2v)
  - It keeps a feature bank of past frames and extends self-attention over it. It is built on StreamDiffusion with LCM-LoRA on SD 1.5 and targets webcam translation.
  - It runs at 20 FPS on one A100 and reports being "15×, 46×, 108×, 158× faster than FlowVid, CoDeF, Rerender, TokenFlow." The authors concede it "may not yet match" TokenFlow or FlowVid in quality.
- **FreeViS** (2025–26 successor). [F] — [arXiv HTML](https://arxiv.org/html/2510.01686v1)
  - Several stylised references (first, middle and last frame, stylised with InstantStyle-plus) are fed to an I2V model, Wan2.1-Fun-Control. It adds high-frequency compensation from PnP inversion and RAFT optical-flow masks.
  - Limits it states:
    - Naively concatenating references causes "flicker and stutter."
    - Inversion "usually doubles the inference time," and the method adds about 30% over AnyV2V.
    - I2V models are "typically limited to about 81 frames."
    - Style texture can vanish in plain regions under large motion.
    - Flow fails under severe occlusion.
    - Output quality "is fully determined by the chosen image model."
- **MLV-Edit.** Cao, Li, Chen, Mao, arXiv 2602.02123, Feb 2026, no venue. [F] — [arXiv](https://arxiv.org/abs/2602.02123)
  - It is a training-free, flow-based editor for minute-level video that edits segment by segment.
  - It names the problems of long video: "prohibitive computational overhead," "cumulative structural drift," and "flickering and boundary artifacts commonly observed in fragmented video processing."
- **Other long-video editors (search snippets only):** AdaFlow (arXiv 2502.05433) claims minutes-long edits in one inference, and AnchorSync (arXiv 2508.14609) claims consistency up to several minutes. [S] — [AdaFlow](https://arxiv.org/pdf/2502.05433); [AnchorSync](https://arxiv.org/pdf/2508.14609)
- **UniVST** (arXiv 2410.20084) is training-free localized video style transfer with latent optical flow. It cites RSCT, which stylises foreground and background separately and then combines them. [S] — [arXiv HTML](https://arxiv.org/html/2410.20084v5)

### Inferences
- Derived throughput from StreamV2V's 20 FPS and its speed-up ratios: TokenFlow ≈ 0.13 fps, Rerender ≈ 0.19 fps, CoDeF ≈ 0.43 fps, FlowVid ≈ 1.3 fps, all on an A100. This is my calculation, not a reported table.
- Flicker in all of these comes from the same root: per-frame stochastic generation that is held together only by approximate correspondence. Our pipeline has no per-frame generation of the background at all, so for static pixels there is no correspondence to get wrong.
- StreamV2V is the closest neighbour to the live kiosk: the same SD 1.5 + LCM-LoRA stack, but it re-diffuses every frame on an A100 or RTX 4090. The kiosk diffuses once and then only composites, on CPU.

### Gaps
- Per-frame runtimes for Rerender, TokenFlow and FateZero come only from StreamV2V's ratios. I could not open the full papers because ar5iv is blocked.
- I did not verify the venues of FLATTEN or AnyV2V.

## Q2. Canonical-image and atlas methods, and why a static camera is the degenerate case

### Takeaway
These methods fit a per-video mapping from every pixel (x,y,t) to a shared 2D canvas, edit the canvas once, and map the edit back to every frame. With a tripod, the background part of that mapping is the same for every t: identity, up to the fixed normalisation into atlas coordinates. The canvas then is the clean plate, and the median recovers it in closed form with no optimisation. No paper I found says this explicitly. The closest are CoDeF's "deformation = 0 gives the canonical image" and Generative Omnimatte's criticism that earlier work assumes a static background.

### Cited Findings
- **Layered Neural Atlases (2021).** [F] — [arXiv](https://arxiv.org/abs/2109.11418); [GitHub](https://github.com/ykasten/layered-neural-atlases)
  - For each video pixel it estimates "its corresponding 2D coordinate in each of the atlases" plus an alpha, using coordinate MLPs optimised per video.
  - An edit to one atlas is mapped back to all frames, preserving "occlusions, deformation, shadows, and reflections."
  - It is purely 2D, with no camera poses.
  - Inputs are rough Mask R-CNN masks and RAFT optical flow. Atlas edits are 1000×1000 RGBA images.
  - Differs from ours: it handles moving cameras and also lets you edit a foreground atlas, at the cost of per-video optimisation (about 10 h according to CoDeF).
- **Text2LIVE.** Bar-Tal et al., ECCV 2022 Oral, arXiv 2204.02491. [F] — [arXiv](https://arxiv.org/abs/2204.02491); [GitHub](https://github.com/omerbt/Text2LIVE)
  - It trains, per input, an "edit layer" (colour plus opacity) that is "composited over the original input," guided by CLIP. For video it uses pretrained Layered Neural Atlases models.
  - Its limits: it changes textures and adds semi-transparent effects, but cannot add new objects or change the layout. It needs about a V100 32 GB.
- **StableVideo.** Chai et al., ICCV 2023, arXiv 2308.09592. [F] — [arXiv](https://arxiv.org/abs/2308.09592)
  - Diffusion editing plus "layered representations to propagate the appearance information from one frame to the next."
  - A search summary says it gives "high-quality video background replacement" but produces "noticeable seams along background and foreground objects." [S] — [arXiv PDF](https://arxiv.org/pdf/2308.09592)
  - I did not confirm in the fetched abstract that its layered representation is the neural atlas. [U]
- **CoDeF.** CVPR 2024. [F] — [arXiv HTML](https://arxiv.org/html/2308.07926v2)
  - It uses a canonical content field (a 2D hash grid plus MLP) and a temporal deformation field (a 3D (x,y,t) hash grid plus MLP mapping to (x′,y′)).
  - The canonical image is "retrieved by setting the deformation of all points to zero."
  - Training takes about 5 min for 100 frames on one A6000 (1–10 min overall), against "10 hours (atlas)."
  - Stated challenges: per-scene optimisation, "extreme changes in viewing points," and "large non-rigid deformations."
- **Hashing-NVD.** Chan, Yuan, Sun, Chen, ICCV 2023, pp. 7743–7753, arXiv 2309.14022. [S] — [CVF](https://openaccess.thecvf.com/content/ICCV2023/html/Chan_Hashing_Neural_Video_Decomposition_with_Multiplicative_Residuals_in_Space-Time_ICCV_2023_paper.html); [project](https://lightbulb12294.github.io/hashing-nvd)
  - Each layer has a 2D texture, a mask, and a **multiplicative residual** for spatio-temporal lighting change.
  - It learns 1080p video at about 25 s per frame and renders edits at 71 fps.
  - Multiplicative residuals beat additive ones, which "overfit lighting into the editable texture."
- **NaRCan.** NeurIPS 2024, arXiv 2406.06523. [S] — [arXiv](https://arxiv.org/abs/2406.06523); [NeurIPS poster](https://neurips.cc/virtual/2024/poster/94507)
  - It uses a hybrid deformation field plus a LoRA diffusion prior so the canonical image looks natural. Reconstruction-only canonicals can be "unnatural," which hurts prompt editing.
  - Training drops from 4.8 h to 20 min.
- **GenDeF** (arXiv 2312.04561) is a possible successor, but I did not fetch it (the API returned 429). [U]

### Inferences
- **Statement for the paper (my derivation, not a citation):** Neural Atlases reconstruct each pixel as a blend of foreground and background atlases, roughly α·A_f(M_f(x,y,t)) + (1−α)·A_b(M_b(x,y,t)).
  - With a fixed camera and a static scene, a background pixel at (x,y) images the same scene point at every t. So the optimal M_b(x,y,t) = M_b(x,y), a fixed rescaling of (x,y), and the same holds for CoDeF's deformation (zero for all t) and Omnimatte's per-frame homographies (identity).
  - The atlas or canonical image is then the clean plate. A per-pixel temporal median is a closed-form, optimisation-free estimate of it.
  - What we give up: moving cameras, editing the people themselves (the foreground atlas), and learned alpha.
- Hashing-NVD's multiplicative residual is the learned analogue of our frame/plate ratio for carrying shadows and lighting change. Cite it next to Chuang 2003 in Q6.
- **Caveat for the claim:** the tripod makes *geometry* degenerate, not *photometry*. Sun and clouds still change, and those changes ride in our ratio term just as they would in Hashing-NVD's residual.

### Gaps
- I found no paper that explicitly analyses or exploits the static-camera, identity-mapping case for atlas editing. I also found no paper that does "restyle the clean plate once, composite people back." A targeted search found none. Treat this as "we found no prior work," not as proof.
- I could not read the Neural Atlases PDF: at 10 MB it exceeded the fetch limit. Its limitations section and runtime are unverified, apart from CoDeF's "10 hours" claim.

## Q3. Example-based and classic stylization, and blind flicker removal

### Takeaway
Before diffusion, video stylisation and flicker removal relied on optical flow and patch synthesis. Example-based work propagates artist keyframes, and blind methods stabilise any per-frame filter using the original video as a guide. All of them still have to solve correspondence for every pixel. We sidestep that for the background.

### Cited Findings
- **Ruder, Dosovitskiy, Brox, "Artistic style transfer for videos,"** GCPR 2016, arXiv 1604.08610. [F] — [arXiv](https://arxiv.org/abs/1604.08610)
  - It adds "new initializations and loss functions applicable to videos" to get stable stylised sequences "even in cases with large motion and strong occlusion."
  - Differs from ours: it optimises every frame.
- **Jamriška et al., "Stylizing Video by Example" (EbSynth),** ACM TOG 38(4):107, SIGGRAPH 2019 (CTU Prague and Adobe). [S] — [project](https://dcgi.fel.cvut.cz/home/sykorad/ebsynth); [SIGGRAPH history archive](https://history.siggraph.org/learning/stylizing-video-by-example-by-jamriska-sochorova-texler-lukac-fiser-et-al/)
  - It is example-based patch synthesis guided by keyframes, with temporal blending between keyframes that "preserves texture coherence, contrast and high frequency."
  - EbSynth is the public implementation, and Rerender and FRESCO use it for propagation (see Q1).
- **Bonneel, Tompkin, Sunkavalli, Sun, Paris, Pfister, "Blind Video Temporal Consistency,"** ACM TOG 34(6), SIGGRAPH Asia 2015, DOI 10.1145/2816795.2818107. [S] — [project](https://perso.liris.cnrs.fr/nbonneel/consistency/)
  - It is a gradient-domain method that is blind to the filter. It takes flickering processed frames and "infer[s] the temporal regularity from the original unprocessed video."
  - Lai et al. measure it at 0.25 FPS on CPU. [S] — [Lai et al.](https://arxiv.org/pdf/1808.00449)
- **Lai et al., "Learning Blind Video Temporal Consistency,"** ECCV 2018, arXiv 1808.00449. [F] — [arXiv](https://arxiv.org/abs/1808.00449)
  - A recurrent network takes the original and the per-frame processed video. It is trained with short- and long-term temporal losses plus a perceptual loss, needs no flow at test time, and runs in real time.
  - Differs from ours: it repairs flicker after the fact, whereas our background never flickers in the first place.

### Inferences
- Our pipeline is the limiting case of keyframe propagation: one "keyframe" (the plate) and identity propagation. Unlike EbSynth, nothing has to be propagated through motion.

### Gaps
- I did not fetch the full texts of Bonneel 2015 or Jamriška 2019 (non-arXiv hosts).

## Q4. Commercial and open V2V editors: documented limits as of Nov 2026

### Takeaway
Every current V2V editor caps the input at a short clip:
- original Gen-4 Aleph: 5 s
- Kling O1: 10 s
- Wan VACE: about 81 frames
- Luma: 10–20 s
- Aleph 2.0 and wan2.7-videoedit: up to 30 s and 10 s respectively

Resolution tops out at 720p–1080p, and cost is charged per second. None of them documents geometric fidelity. Our approach runs at any resolution and any length because the generated part is a single still.

### Cited Findings
- **Runway Gen-4 Aleph** was announced 25 July 2025 as an "in-context video model" that can add, remove and transform objects and change camera angle, lighting or style. [S] — [Runway research](https://runwayml.com/research/introducing-runway-aleph)
  - Hosted listings say "only 5s of the input video will be used" and the file must be under 16 MB. [S] — [Replicate gen4-aleph](https://replicate.com/runwayml/gen4-aleph); [JAI Portal](https://www.jaiportal.com/model/runway-gen-4-aleph)
- **Runway Aleph 2.0** (21 May 2026) handles up to 30 s at 1080p and multi-shot clips. You edit one frame and it propagates. [S] — [Runway news](https://runway.com/news/introducing-aleph-2-and-edit-studio); [Replicate aleph-2](https://replicate.com/runwayml/aleph-2)
  - Third-party sources conflict on the input range (2–10 s vs 2–30 s). [S] — [itechguides](https://www.itechguides.com/runway-gen-4-5-or-aleph-2-0-choosing-the-right-model-for-generation-vs-editing)
- **Luma Modify Video (Ray2):** maximum input 10 s and 100 MB. [S] — [Luma changelog](https://lumalabs.ai/changelog/modify-video-api-release)
  - **Ray3.2 V2V:** output "always matches the source duration, up to a maximum of 20 seconds," at 360p–1080p.
  - fal.ai lists 5 or 10 s for the same model, which conflicts. [S] — [Luma guide](https://lumalabs.ai/learning-center/articles/ray-3-2-video-to-video); [fal.ai](https://fal.ai/models/luma/agent/ray/v3.2/video-to-video/api)
- **Wan VACE (open source):** the listed sizes are about 81×480×832 (1.3B) and about 81×720×1280 (14B). Single-GPU inference is supported for 1.3B; the examples use 8 GPUs; no VRAM figures are given. [F] — [GitHub VACE](https://github.com/ali-vilab/VACE)
- **Alibaba cloud editors** (Model Studio docs, search summary):
  - wan2.7-videoedit: 720P/1080P, 2–10 s, 30 fps.
  - wan2.1-vace-plus: 720P, at most 5 s.
  - Wan 2.6 (16 Dec 2025): 2–15 s, multi-shot. [S] — [Alibaba Model Studio](https://www.alibabacloud.com/help/en/model-studio/wanx2-1-vace-plus); [Wan2.6 press release](https://www.alibabacloud.com/press-room/alibaba-unveils-wan2-6-series-enabling-everyone)
- **Kling O1 video edit:** 3–10 s input, 720p/1080p, 100–200 MB cap. For longer footage, split it into segments. These are third-party sources; I found no official Kling spec. [S] — [fal.ai](https://fal.ai/models/fal-ai/kling-video/o1/video-to-video/edit); [JAI Portal](https://www.jaiportal.com/model/kling-o1-edit-video)
- **Google Veo 3.1** (Oct 2025): Flow offers "Insert object," which matches shadows and lighting. "Remove object" was still rolling out at launch. I found no clip-length or resolution limits for editing. [S] — [Google blog](https://blog.google/technology/ai/veo-updates-flow/)

### Inferences
- At an assumed 16 fps, VACE's 81 frames is about 5 s [U for the fps]. So the open model and the commercial tools all sit at roughly 5–30 s.
- Our 1–3 min 4K clips exceed every documented cap. They would have to be split into segments, which brings back the boundary discontinuities MLV-Edit describes.

### Gaps
- No vendor documents geometric drift or seam stability. The README's claim that "building geometry drifts" is therefore our own hypothesis, and our seam metric could test it.
- I couldn't fetch any official Runway or Luma pages (blocked hosts), so the numbers above come from search summaries.
- I did not check pricing beyond OpenRouter's Aleph 2.0 rate.

## Q5. Layer decomposition and person extraction

### Takeaway
Omnimatte-style methods learn each person plus their effects (shadows, reflections) as a layer. They need per-video optimisation or a finetuned video diffusion model. The background-matting line is the direct precedent for our kiosk: capture the empty background, then matte against it.

### Cited Findings
- **Layered Neural Rendering for Retiming People in Video.** Lu et al., SIGGRAPH Asia 2020, arXiv 2009.07833. [F] — [arXiv](https://arxiv.org/abs/2009.07833)
  - Each person becomes an RGBA layer that also holds "correlated" effects (shadows, reflections, loose clothing). Layers can be retimed or removed.
- **Omnimatte.** Lu et al., CVPR 2021 Oral, arXiv 2105.06993. [F] — [arXiv](https://arxiv.org/abs/2105.06993)
  - It produces an alpha matte plus colour per subject, including shadows, reflections and smoke. Inputs are the video plus rough masks. It is self-supervised and trained per video.
  - According to search summaries, Omnimatte3D describes it as assuming the video maps "onto a fixed 2D canvas." [S]
  - Its homography-based camera model is unverified. [U]
- **Omnimatte3D.** Suhail et al., CVPR 2023, pp. 630–639. [S] — [CVF](https://openaccess.thecvf.com/content/CVPR2023/html/Suhail_Omnimatte3D_Associating_Objects_and_Their_Effects_in_Unconstrained_Monocular_Video_CVPR_2023_paper.html)
  - It builds an RGBD background from monocular pose and depth (CasualSAM) for complex camera motion.
- **OmnimatteRF.** Lin et al., ICCV 2023, arXiv 2309.07749. [F] — [arXiv](https://arxiv.org/abs/2309.07749)
  - 2D foreground layers plus a 3D background model, because "prior works represent video backgrounds as 2D image layers," which limits scene complexity.
- **Generative Omnimatte.** Lee et al., CVPR 2025, arXiv 2411.16683. [F] — [arXiv](https://arxiv.org/abs/2411.16683)
  - A video inpainting diffusion model, finetuned to remove a specific object's effects. Input is video plus masks.
  - It explicitly notes that prior methods "assume a static background or accurate pose and depth."
- **Background Matting: The World is Your Green Screen.** Sengupta et al., CVPR 2020, arXiv 2004.00626. [F] — [arXiv](https://arxiv.org/abs/2004.00626)
  - It needs "an additional photo of the background without the subject," taken with "a handheld camera."
  - Differs from ours: it learns an alpha matte, where we threshold the difference from the plate.
- **Real-Time High-Resolution Background Matting.** Lin et al., CVPR 2021, pp. 8762–8771, arXiv 2012.07810. [F] — [arXiv](https://arxiv.org/abs/2012.07810); [S] — [CVF](https://openaccess.thecvf.com/content/CVPR2021/html/Lin_Real-Time_High-Resolution_Background_Matting_CVPR_2021_paper.html)
  - It also needs a captured background frame. It runs at 30 fps at 4K and 60 fps at HD on "a modern GPU."
- **Robust Video Matting.** Lin et al., WACV 2022, pp. 238–247, arXiv 2108.11515. [F] — [arXiv](https://arxiv.org/abs/2108.11515); [S] — [CVF](https://openaccess.thecvf.com/content/WACV2022/html/Lin_Robust_High-Resolution_Video_Matting_With_Temporal_Guidance_WACV_2022_paper.html)
  - A recurrent network that needs no trimap and no pre-captured background. It runs at 76 fps at 4K and 104 fps at HD on a GTX 1080Ti.
- **Later matting work:** MatAnyone (CVPR 2025) and MatAnyone 2 (CVPR 2026). [S] — [CVF MatAnyone](https://openaccess.thecvf.com/content/CVPR2025/papers/Yang_MatAnyone_Stable_Video_Matting_with_Consistent_Memory_Propagation_CVPR_2025_paper.pdf); [CVF MatAnyone 2](https://openaccess.thecvf.com/content/CVPR2026/papers/Yang_MatAnyone_2_Scaling_Video_Matting_via_a_Learned_Quality_Evaluator_CVPR_2026_paper.pdf)
- **SAM 2.** Ravi et al., ICLR 2025 (oral), arXiv 2408.00714. [F] — [arXiv](https://arxiv.org/abs/2408.00714); [S] — [ICLR](https://iclr.cc/virtual/2025/oral/31878)
  - Promptable image and video segmentation with streaming memory for "real-time video processing."
- **SAM 3.** ICLR 2026, arXiv 2511.16719. [S] — [arXiv](https://arxiv.org/abs/2511.16719v1)
  - Detects, segments and tracks all instances of a concept from text or exemplar prompts. It reports 48.8 mask AP on zero-shot LVIS.

### Inferences
- Our "person = pixels that differ from the plate" rule is classical background subtraction, the same signal BGM and BGMv2 learn from.
  - It captures shadows and carried objects for free, which Omnimatte has to learn.
  - It also picks up any non-person change (cars, foliage). Learned mattes and SAM 3 are more selective.

### Gaps
- I did not check whether Layered Neural Rendering assumes a static camera or homography; its abstract is silent. [U]

## Q6. Shadows, harmonization and relighting for compositing people into a generated scene

### Takeaway
Physically, a shadow is a multiplicative attenuation of the background, the basis of Chuang 2003 shadow matting. Harmonisation methods then push the foreground's colour and lighting toward the background. Diffusion relighters (IC-Light and successors) do this generatively, but per-frame use flickers unless consistency is added.

### Cited Findings
- **Chuang, Goldman, Curless, Salesin, Szeliski, "Shadow Matting and Compositing,"** ACM TOG 22(3):494–500, SIGGRAPH 2003. [S] — [UW GRAIL project](https://grail.cs.washington.edu/projects/digital-matting/shadow-matting/); [SIGGRAPH archive](https://history.siggraph.org/?p=115892)
  - It derives physically based shadow matting and compositing equations, pulls a shadow matte from a source scene, and warps it onto a target scene's geometry.
- **DoveNet.** Cong et al., CVPR 2020, pp. 8394–8403, arXiv 1911.13239. [S] — [CVF](https://openaccess.thecvf.com/content_CVPR_2020/html/Cong_DoveNet_Deep_Image_Harmonization_via_Domain_Verification_CVPR_2020_paper.html)
  - A domain-verification discriminator pushes the foreground into the background's capture "domain" (weather, season, time of day). It introduced the iHarmony4 dataset.
- **Relightful Harmonization.** Ren et al. (NYU and Adobe), CVPR 2024, arXiv 2312.06886. [S] — [CVF PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Ren_Relightful_Harmonization_Lighting-aware_Portrait_Background_Replacement_CVPR_2024_paper.pdf)
  - A lighting-aware diffusion model for portrait background replacement. Its listed failure case: strong cast shadows are not fully removed.
- **IC-Light.** Zhang, Rao, Agrawala, "Scaling In-the-Wild Training for Diffusion-based Illumination Harmonization and Editing by Imposing Consistent Light Transport," ICLR 2025 Oral. [S] — [ICLR PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/1cce374fec7829c24a97ae0e91cd0999-Paper-Conference.pdf)
  - It imposes light-transport independence during training. Secondary sources report about 10M training images.
- **Light-A-Video.** ICCV 2025, arXiv 2502.08590. [S] — [arXiv](https://arxiv.org/abs/2502.08590)
  - Training-free video relighting. It notes that per-frame IC-Light shows "noticeable jitter between frames, especially in the generated background lighting."
  - It adds Consistent Light Attention and Progressive Light Fusion, and also supports relighting a given foreground sequence.
- **ZeroComp.** Zhang et al., WACV 2025 Oral, pp. 483–494, arXiv 2410.08168. [F] — [arXiv](https://arxiv.org/abs/2410.08168); [S] — [CVF](https://openaccess.thecvf.com/content/WACV2025/html/Zhang_ZeroComp_Zero-Shot_Object_Compositing_from_Image_Intrinsics_via_Diffusion_WACV_2025_paper.html)
  - A ControlNet plus SD renderer conditioned on intrinsics (depth, normals, albedo, masked shading). It inpaints shading for an inserted object and is trained on synthetic indoor data only.
- **Hashing-NVD's multiplicative residuals** (Q2) are a learned per-pixel lighting ratio.

### Inferences
- Our frame/plate ratio is the simplest form of Chuang's multiplicative shadow model, with the clean plate standing in for the "lit" image. Hashing-NVD shows that multiplicative is the right choice over additive.
- Our per-world global recolouring is closer to classic colour transfer and DoveNet-style domain matching than to IC-Light. Because it is one global transform applied identically to every frame, it cannot jitter, whereas Light-A-Video reports that per-frame IC-Light does.
- Our ratio cannot relight the person's own shading to match a new light direction. IC-Light, Relightful Harmonization and ZeroComp can.

### Gaps
- I did not verify any video harmonisation benchmark (e.g., HYouTube) or a classic colour-transfer citation (e.g., Reinhard 2001). [U]

## Q7. VFX practice: the manual version of our pipeline

### Takeaway
In VFX, a clean plate is the same framing shot without actors. A locked-off camera makes it easy to get. Roto, paint and prep build the mattes and clean-ups, and digital matte painting replaces environments that rotoscoped elements are composited over. Our pipeline automates the clean plate (median), the roto (difference mask), the matte painting (diffusion) and the composite.

### Cited Findings
- **Definition:** a clean background filmed "without actors or other unwanted moving elements, usually so it can be used later in visual effects compositing." Effects plates match "the lighting, camera position, lens characteristics." [S] — [HowToFilmSchool: Plate shot](https://howtofilmschool.com/dictionary/plate-shot/); [Effects plate](https://howtofilmschool.com/dictionary/effects-plate/)
- **Foundry's Nuke user guide:** "shooting a clean plate if the camera is locked off is easy." [S] — [Foundry Nuke 8 docs](https://learn.foundry.com/nuke/8.0/content/furnacecore/background.html)
- **Division of labour:**
  - "Roto = mattes; roto-paint = pixel fixes; prep = broader plate cleanup."
  - Digital matte painting is used for "set extensions and environments," with rotoscoped elements composited in so they "interact with the digital environment."
  - At one studio, roto, paint and prep take "half a day … to 20–25 days" per shot. [S] — [frame.io workflow guide](https://workflow.frame.io/guide/rotoscoping); [Boris FX / Image Engine](https://blog.borisfx.com/image-engine-the-emmy-award-winning-team-behind-the-book-of-boba-fett)
- **A textbook source:** Steve Wright, *Compositing Visual Effects* (Focal Press), on O'Reilly. [S] — [O'Reilly](https://www.oreilly.com/library/view/compositing-visual-effects/9780240809632/12_Chapter_06.xhtml)
- **AI clean plates in industry:** Wonder Dynamics (Wonder Studio) exports an AI-generated "Clean Plate." [S] — [Wonder Dynamics help](https://help.wonderdynamics.com/working-with-wonder-studio/export-elements/clean-plate)

### Inferences
- For the paper, the Foundry quote is the most citable line for "the tripod is what makes the plate free." The Wright textbook is the best formal citation once someone opens the chapter.

### Gaps
- All sources here are glossaries, vendor docs and tutorials from search results. I fetched none of them, and found no peer-reviewed VFX-pipeline paper. The VES Handbook would be a stronger citation but is unverified. [U]

## Q8. Classic background estimation (temporal median) and close "static-camera compositing" neighbours

### Takeaway
The temporal median as a background model is standard. Lo and Velastin proposed the median of the last n frames, and Cucchiara et al. (TPAMI 2003) showed a sub-sampled median suffices; Piccardi's 2004 review is the usual survey citation. Video Synopsis (CVPR 2006) is a close neighbour: a stationary camera, a background, and moving objects pasted back in.

### Cited Findings
- **Piccardi, "Background subtraction techniques: a review,"** IEEE SMC 2004. [S] — [Zenodo PDF](https://zenodo.org/records/891536/files/article.pdf); [NCCU copy](https://www.cs.nccu.edu.tw/~whliao/es2008/BackgroundSubtractionReview-Piccardi.pdf)
  - It says "Lo and Velastin proposed to use the median value of the last n frames as the background model." Cucchiara et al. "argued that such a median value provides an adequate background model even if the n frames are sub-sampled."
  - It names the drawbacks: median "requires a buffer," has no "rigorous statistical description," and gives no "deviation measure for adapting the subtraction threshold."
- **Cucchiara, Grana, Piccardi, Prati,** "Detecting moving objects, ghosts and shadows in video streams," IEEE TPAMI 25(10):1337–1342, 2003. This reference was found in Piccardi's reference list; I did not fetch the paper. [S]
- **Rav-Acha, Pritch, Peleg, "Making a Long Video Short: Dynamic Video Synopsis,"** CVPR 2006, pp. 435–441, DOI 10.1109/CVPR.2006.179. [S] — [HUJI PDF](https://vision.huji.ac.il/synopsis/cvpr06-synopsis.pdf)
  - It shows activities from different times simultaneously over a background, from stationary surveillance-style cameras.
  - Its use of a temporal-median background is unverified. [U]
- **SDEdit** (Meng et al., ICLR 2022, arXiv 2108.01073) adds noise, then denoises, to balance "realism and faithfulness." [F] — [arXiv](https://arxiv.org/abs/2108.01073); [S] — [ICLR poster](https://iclr.cc/virtual/2022/poster/6268)
  - Relevance: it is the canonical citation for img2img strength, which our "Grow" ladder walks.
- **SOYO** (arXiv 2503.06998, tuning-free video style morphing via interpolation) may neighbour "Grow." I only saw it in search snippets. [S] — [arXiv HTML](https://arxiv.org/html/2503.06998v1)

### Inferences
- Cite Piccardi 2004 together with Cucchiara 2003 for "per-pixel temporal median = clean plate." Note the documented failure: anyone who stands still for more than half the clip is absorbed into the plate.
- Video Synopsis is the closest classical precedent for "static camera → background + pasted-back people." Ours differs by replacing the background with a generated world and adding a per-pixel spatial rule (line, depth, portal) for real vs generated.

### Gaps
- I did not verify Lo & Velastin 2001 bibliographic details, cinemagraph or de-animation papers (Bai et al. 2012; Liao et al. 2013), or Interactive Digital Photomontage (Agarwala 2004, per-pixel source selection). All are plausible neighbours for the "spatial rule" idea. [U]
- In this session I could not fetch export.arxiv.org (429), ar5iv, openaccess.thecvf.com, runway.com, help.runwayml.com or docs.lumalabs.ai. If those hosts are allowed, [S] items could be upgraded to [F].
