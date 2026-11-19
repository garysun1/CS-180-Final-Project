# Generative-AI and 3D Tools for "Wow Factor" in Cross the Line (2024–2026 state)

Compiled 2026-11-19. Method note: web search plus direct fetches of GitHub pages. Direct fetches of bfl.ai and huggingface.co were blocked by this session's network policy, so figures from those sites come from search-result excerpts and should be checked on the model card before quoting. Items marked "(prior knowledge, link not fetched this session)" are canonical arXiv/GitHub links I did not re-open here.

## 1. Real-time diffusion for a live webcam restyle station (StreamDiffusion v1/v2, Turbo/LCM/Lightning, FLUX schnell): FPS, flicker, mitigations

### Takeaway
A live "restyle station" is easy on one RTX 4090. StreamDiffusion v1 with SD-Turbo does about 94 fps img2img, but each frame is restyled independently, so it flickers a lot. That flicker is the best possible live counterexample to the project's "one still cannot flicker" claim. StreamDiffusionV2 (Oct 2025, Wan 2.1 video backbone) is temporally coherent and runs in real time, but its headline numbers come from 4×H100. No single-4090 or Colab-T4 figure was published.

### Cited Findings
- **StreamDiffusion v1** (Apache-2.0). Benchmarked on an RTX 4090 with a Core i9-13900K: SD-Turbo at 1 step runs at **106.16 fps txt2img and 93.90 fps img2img**, and LCM-LoRA + KohakuV2 at 4 steps runs at **38.0 fps txt2img and 37.1 fps img2img**. — [GitHub cumulo-autumn/StreamDiffusion](https://github.com/cumulo-autumn/StreamDiffusion)
- StreamDiffusion v1 has a "Stochastic Similarity Filter" that skips conversion when consecutive frames barely change, set by a similarity threshold and a maximum number of skipped frames. It cuts GPU load for video input but does not enforce temporal consistency. — [GitHub StreamDiffusion](https://github.com/cumulo-autumn/StreamDiffusion)
- The paper's headline figure is "up to 91.07 fps on a single RTX 4090" (image pipeline). — [arXiv 2312.12491](https://arxiv.org/html/2312.12491v2)
- **StreamDiffusionV2** was publicly released 2025-10-06 (paper on arXiv 2025-11-10, MLSys 2026) under Apache-2.0. It is built on Wan 2.1 T2V 1.3B and 14B, with examples at 480×832, and has `single` (one GPU), `single-wo` and `pipe` (multi-GPU) modes. Initial NVIDIA Blackwell support was added 2026-05-17. — [GitHub chenfengxu714/StreamDiffusionV2](https://github.com/chenfengxu714/StreamDiffusionV2); [arXiv 2511.07399](https://arxiv.org/abs/2511.07399v1); [MLSys 2026 paper](https://proceedings.mlsys.org/paper_files/paper/2026/file/698cfaf72a208aef2e78bcac55b74328-Paper-Conference.pdf)
- On **4×H100**, without TensorRT or quantization, StreamDiffusionV2 shows its first frame within 0.5 s and reaches **58.28 fps with the 14B model and 64.52 fps with the 1.3B model**. — [arXiv 2511.07399](https://arxiv.org/html/2511.07399v1)
- A third-party vLLM-Omni RFC says a different pipeline-parallel real-time video system reaches about 16 fps on 4×RTX 4090 (PCIe). This is not a StreamDiffusionV2 measurement. — [vLLM-omni issue via goodfirstissue](https://goodfirstissue.org/vllm-project/vllm-omni/issues/2280)
- **StreamV2V** ("Looking Backward") keeps temporal consistency in streaming video-to-video with a feature bank of past frames. It is a direct mitigation for per-frame flicker. — [StreamV2V project page](https://jeff-liangf.github.io/projects/streamv2v)
- **Daydream fork of StreamDiffusion.** Beta SDXL support arrived in November 2025, with up to 25 fps cited "in optimized configurations" and TensorRT acceleration. The fork can be self-hosted. — [BusinessWire, Nov 2025](https://www.businesswire.com/news/home/20251106860538/en); [Daydream changelog](https://daydreamlive.canny.io/changelog)
- **ComfyStream** (Livepeer/Daydream) shows a webcam feed with the workflow applied in near real time. The first TensorRT engine build takes 2–10 minutes. A community figure for SD1.5 + ControlNet on an RTX 4090 is 14–15 fps at 640×360 input. — [Livepeer ComfyStream docs](https://docs.livepeer.org/v2/developers/build/ai-and-agents/realtime-ai/comfystream/overview); [ComfyStream quickstart](https://docs.livepeer.org/v2/developers/build/ai-and-agents/realtime-ai/comfystream/comfystream-quickstart)
- A 2024 StreamDiffusionTD changelog said ControlNet worked only with SD1.5, did not support TensorRT, and that TensorRT did not work with SDXL. This may be outdated given the 2025 Daydream SDXL+TensorRT release. — [Patreon dotsimulate changelog](https://www.patreon.com/dotsimulate/posts/streamdiffusiont-104339324)
- **SDXL-Turbo and SD-Turbo.** Both are built for 512×512. Licensing is ambiguous: the launch announcement said non-commercial research license, while the current model cards say "non-commercial and commercial usage" and point to Stability's license page. — [Stability SDXL-Turbo announcement](https://stability.ai/news/stability-ai-sdxl-turbo); [HF stabilityai/sdxl-turbo](https://huggingface.co/stabilityai/sdxl-turbo); [HF stabilityai/sd-turbo](https://huggingface.co/stabilityai/sd-turbo); [Diffusers docs](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/sdxl_turbo)
- Baseten reports that users often find SDXL-Lightning images much higher quality than SDXL-Turbo's. Lightning can go down to 1 step, but 2–8 steps are typical in practice. — [Baseten few-step comparison](https://www.baseten.co/blog/comparing-few-step-image-generation-models/)
- Hyper-SD (ByteDance) ships as LoRAs for SD1.5 and SDXL, and SDXL-Lightning ships as a checkpoint and as a LoRA. — [PromptZone few-step overview](https://www.promptzone.com/qian_hansen/few-step-diffusion-models-hyper-sd-lightning-and-turbo-je5.md). Papers: Hyper-SD [arXiv 2404.13686](https://arxiv.org/abs/2404.13686), SDXL-Lightning [arXiv 2402.13929](https://arxiv.org/abs/2402.13929), LCM [arXiv 2310.04378](https://arxiv.org/abs/2310.04378) (prior knowledge, links not fetched this session).
- **Krea Realtime 14B** (open weights; a repackager lists Apache-2.0). It runs text-to-video at **11 fps on one B200** with 4 steps. The model card lists video-to-video, including webcam input. A community tip is to keep webcam capture below 10 fps so the model keeps up. — [Krea blog](https://www.krea.ai/blog/krea-realtime-14b); [HF krea/krea-realtime-video](https://huggingface.co/krea/krea-realtime-video); [hyper.ai notebook](https://hyper.ai/en/notebooks/46828)

### Inferences
- **Recommendation: a "flicker vs. no flicker" live booth.** Show three panes side by side: (a) the webcam through StreamDiffusion v1 + SD-Turbo with one style prompt, which runs at tens of fps on a 4090 and flickers visibly; (b) optionally StreamDiffusionV2 1.3B, which is more coherent but heavier; (c) the project's method: compute the median background of the booth camera once, restyle it once, and composite live SAM/RVM mattes on top. Pane (c) runs at matting speed and cannot flicker. This turns the paper's main argument into an interactive demo.
- Cheap mitigations for pane (a): fix the seed, use low img2img strength (around 0.3–0.5), add a depth or canny ControlNet, and apply an EMA over output frames. All of these reduce flicker without removing it. This is inference, not measured.
- A Colab T4 has far less fp16 throughput than a 4090. SD-Turbo 512px img2img will likely run at single-digit to low-teens fps, which is enough for a demo but not smooth (inference). StreamDiffusionV2 and Krea 14B are not realistic on a T4.
- FLUX.1 [schnell] (Apache-2.0, 1–4 steps) is a 12B model. Even distilled, it would not reach webcam rates on consumer GPUs, so SD-Turbo or SDXL-Lightning are better choices for a live booth (inference from model size).

### Gaps
- No published single-RTX 4090, A100 or Colab T4 fps for StreamDiffusionV2, and no fps for Krea Realtime video-to-video on consumer GPUs.
- No measured StreamDiffusion v1 fps on a T4 was found.
- No flicker metric (such as warping error) was found that compares StreamDiffusion v1 against v2.
- FLUX.1 schnell latency on consumer GPUs was not looked up in this session.
- Decart MirageLSD (closed, real-time live-stream restyling) was not researched.

## 2. Relighting people to match the generated world (IC-Light and successors, SwitchLight, LBM, video relighting)

### Takeaway
IC-Light's SD1.5 "fbc" model takes a foreground (the cut-out person) plus a background (the restyled world). It is exactly the right tool for "relight the walker to match the night or Van Gogh world." Per-frame use will flicker, though, so use it on keyframes or use a video-consistent variant (TC-Light, Light-A-Video, RelightVid). LBM relighting is a fast one-step alternative under CC-BY-NC. SwitchLight (Beeble) is commercial and strong on video, but closed.

### Cited Findings
- **IC-Light** (lllyasviel; repo is Apache-2.0). It has two SD1.5 models. `iclight_sd15_fc` is conditioned on text and the foreground, with a lighting-direction preference that sets the initial latent. `iclight_sd15_fbc` is conditioned on text, foreground and **background**. There is also an `fcon` offset-noise variant. The repo warns that its bundled BRIA RMBG 1.4 matting is non-commercial and suggests BiRefNet instead. It gives no VRAM or speed figures. The repo mentions a Flux discussion and an "alternative model" for stronger lighting changes, but it does not publish IC-Light v2 (Flux) weights. — [GitHub lllyasviel/IC-Light](https://github.com/lllyasviel/IC-Light)
- **LBM: Latent Bridge Matching** (Jasper Research, ICCV 2025). It does image-to-image translation in a single inference step and covers object relighting, plus a conditional variant for controllable relighting and shadow generation. — [arXiv 2503.07535](https://arxiv.org/abs/2503.07535v2); [ICCV 2025 paper](https://openaccess.thecvf.com/content/ICCV2025/html/Chadebec_LBM_Latent_Bridge_Matching_for_Fast_Image-to-Image_Translation_ICCV_2025_paper.html)
- The **LBM relighting** model card is licensed CC BY-NC 4.0, and its example runs `num_sampling_steps=1` in bf16 on CUDA. — [HF jasperai/LBM_relighting](https://huggingface.co/jasperai/LBM_relighting); [HF Space demo](https://jasperai-lbm-relighting.hf.space/)
- An informal practitioner test found LBM relighting "not that perfect as IC light." — [stablediffusiontutorials](https://www.stablediffusiontutorials.com/2025/05/relight-image-latent-bridge-matching.html)
- **TC-Light** (arXiv 2506.18904, June 2025, later retitled "Temporally Coherent Generative Rendering for Realistic World Transfer"). It first inflates IC-Light into a video model zero-shot, then optimizes to minimize warping error across frames. The authors report it beats per-frame IC-Light, VidToMe, Slicedit, VideoDirector, Light-A-Video and RelightVid. A review says several competing video relighting methods ran out of memory on long, dynamic videos. — [arXiv 2506.18904v1](https://arxiv.org/html/2506.18904v1); [arXiv v3](https://arxiv.org/html/2506.18904v3); [Moonlight review](https://www.themoonlight.io/review/tc-light-temporally-consistent-relighting-for-dynamic-long-videos)
- **Light-A-Video** (arXiv 2502.08590). Training-free. It adds Consistent Light Attention inside the image relighting model and linearly blends source and relit appearance to keep frames consistent. — [arXiv 2502.08590](https://arxiv.org/html/2502.08590v1)
- **RelightVid** has a public GitHub repo for a temporally consistent diffusion model for video relighting. Its license was not confirmed. — [GitHub aleafy/relightvid](https://github.com/aleafy/relightvid)
- **Lux Post Facto** (CVPR 2025) reports it qualitatively beats NVPR and SwitchLight for relighting in-the-wild portrait videos. Code availability was not confirmed. — [CVPR 2025 supplemental](https://openaccess.thecvf.com/content/CVPR2025/supplemental/Mei_Lux_Post_Facto_CVPR_2025_supplemental.pdf)
- **SwitchLight 3.0 / Beeble Studio** (closed, commercial). The new video-to-PBR model launched in November 2025, and Beeble Studio does 4K relighting locally on Windows workstations. Pricing is credit-based: the SwitchLight 2.0 era had a free Starter tier with 0 credits, Creator at 540 credits/month and Professional at 2,400 credits/month. A third party lists Pro at $29/month, which I could not verify. — [CG Channel](https://www.cgchannel.com/tag/switchlight-3-0); [Beeble Studio](https://beeble.ai/beeble-studio); [Beeble pricing](https://beeble.ai/pricing-studio); [Digital Production, Dec 2025](https://digitalproduction.com/2025/12/10/beeble-studio-4k-ai-relighting-on-your-desktop/)
- Beeble also hosts MatAnyone 2 in the browser at 2K/60 fps. — [Beeble MatAnyone page](https://beeble.ai/models/matanyone)

### Inferences
- **Recommendation: relight only on the restyled side.** Run IC-Light fbc on the person crop with the restyled background as the condition. To avoid flicker and identity drift, either:
  - relight a few keyframes per person and fit a low-frequency per-person color/shading transform (for example a 3×3 color matrix plus a smooth gain map) that is applied consistently to every frame; or
  - run TC-Light or Light-A-Video on the person track.

  This fits the proposal's "match them to the style" option and gives a visible "the person changes as they cross" effect.
- IC-Light is SD1.5-based, so a 512–768px person crop should take seconds per frame on a 4090. That is fine offline for a few hundred frames but not live (inference; no published timing found).
- LBM's one-step design should be the fastest option for per-frame relighting. Its CC-BY-NC license is fine for a class project but not for commercial reuse.
- A classical baseline is worth showing for the "computational photography" grade: histogram or Reinhard color transfer plus a matched blur/grain, compared against IC-Light (inference).

### Gaps
- No published per-frame latency or VRAM for IC-Light, LBM, TC-Light or Light-A-Video.
- IC-Light v2 (Flux) weight availability is unclear. The repo does not publish them.
- Code release and license status for TC-Light and Light-A-Video were not confirmed.
- SwitchLight 3.0's current price was not found.

## 3. Video-to-video editing models as a flicker / drift baseline (Runway Aleph, Luma Modify, Wan VACE, Lucy Edit, CogVideoX, TokenFlow/RAVE/Rerender/FlowEdit)

### Takeaway
For a side-by-side "their method flickers or drifts, ours doesn't" figure, the cheapest closed option is Runway Aleph 2.0 at about $0.28 per second of 1080p video, up to 30 s. The best open, runnable options are Wan 2.1 VACE 1.3B (under 12 GB with Wan2GP), Lucy Edit Dev (Wan2.2 5B, open weights) and the older zero-shot methods (TokenFlow, RAVE, Rerender-A-Video). StreamDiffusion v1 per-frame img2img is the most dramatic flicker baseline and costs nothing.

### Cited Findings
- **Runway Aleph 2.0** (closed, paid). The API costs 28 credits per second with a 56-credit minimum, at $0.01 per credit (about $0.28/s). The cap is 30 s at 1080p, and output length follows the source clip. It is not on the free plan. The Standard plan's 625 monthly credits cover about 22 s of Aleph. Plans are Standard $15/month ($12 yearly), Pro $35 ($28) and Max $95 ($76). — [Dupple Runway pricing 2026](https://dupple.com/learn/runway-pricing); [Creatify Runway pricing 2026](https://creatify.ai/de/blog/runway-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay); [Atlas Cloud Aleph overview](https://www.atlascloud.ai/blog/tips/runway-aleph). These are secondary sources; check against Runway's own pricing page.
- **Luma Modify Video** (closed) is described as Ray3 Modify, with keyframe-based editing and character reference. No official per-second price was found. — [Metavert Runway vs Luma](https://metavert.io/compare/runway-vs-luma-labs); [invideo model pricing](https://invideo.io/help/billing/video-model-pricing/)
- **Wan 2.1 VACE.** In ComfyUI the 1.3B VACE diffusion model is about 7 GB. A community KB recommends about 70 GB of VRAM for the 14B model, or FSDP multi-GPU or FP8. Wan2GP runs VACE ControlNet-style editing on an RTX 4090 for 10 s of 480p video in under 12 GB, and has low-VRAM profiles for 12 GB of VRAM with 32 GB of RAM. The official repo suggests `--offload_model True --t5_cpu` for 1.3B on a single consumer GPU. — [ComfyUI VACE docs](https://docs.comfy.org/tutorials/video/wan/vace); [Banodoco Wan KB](https://nathanshipley.github.io/banodoco-kb/kb/wan/index.html); [Wan2GP GitHub mirror](https://github.com/LifeDepot/Wan2GP); [HF Wan-AI/Wan2.1-VACE-14B](https://huggingface.co/Wan-AI/Wan2.1-VACE-14B)
- **Lucy Edit Dev** (Decart). Weights and reference code were first released 2025-09-18 as an "open-weight instruction-guided video editing model" built on Wan2.2 5B. It supports 480p and 720p, with best results up to about 81 frames per generation. Lucy Edit Pro is API-only. A Lucy Edit 1.1 Dev card also exists. — [HF decart-ai/Lucy-Edit-Dev](https://huggingface.co/decart-ai/Lucy-Edit-Dev); [Lucy Edit paper PDF](https://d2drjpuinn46lb.cloudfront.net/Lucy_Edit__High_Fidelity_Text_Guided_Video_Editing.pdf); [RunComfy Lucy Edit](https://www.runcomfy.com/models/decart/lucy-edit/fast)
- **StreamDiffusionV2** and **Krea Realtime 14B** are streaming video-to-video options (see Section 1). — [GitHub StreamDiffusionV2](https://github.com/chenfengxu714/StreamDiffusionV2); [HF krea-realtime-video](https://huggingface.co/krea/krea-realtime-video)
- Older open zero-shot methods (prior knowledge, links not fetched this session):
  - TokenFlow (ICLR 2024): [arXiv 2307.10373](https://arxiv.org/abs/2307.10373)
  - RAVE (CVPR 2024): [arXiv 2312.04524](https://arxiv.org/abs/2312.04524)
  - Rerender-A-Video (SIGGRAPH Asia 2023): [arXiv 2306.07954](https://arxiv.org/abs/2306.07954)
  - FlowEdit (inversion-free editing for flow models; an image editor, usable per-frame as a flicker baseline): [arXiv 2412.08629](https://arxiv.org/abs/2412.08629)
  - CogVideoX: [arXiv 2408.06072](https://arxiv.org/abs/2408.06072)
  - CoDeF (canonical-image video editing, the method family the proposal cites): [arXiv 2308.07926](https://arxiv.org/abs/2308.07926)

### Inferences
- **Recommendation: a baseline grid.** Use one 5–10 s Sather Gate clip, the same prompt ("winter night"), and four methods: (1) per-frame SD-Turbo or FLUX.2 Klein img2img (maximum flicker), (2) Wan 2.1 VACE 1.3B or Lucy Edit Dev (open video model), (3) Runway Aleph 2.0 (closed state of the art, about $3 for a 10 s clip), and (4) the project's one-still composite. Report a temporal metric such as mean warping error, or simply the frame-to-frame standard deviation on static background pixels. The median-background mask gives you the "should be static" pixels for free. This also yields a clean quantitative figure (inference).
- Open video models top out around 480–720p and roughly 81 frames or 10 s per pass, while the project's method works at 4K for any clip length. That is a strong, citable contrast (inference from the limits above).

### Gaps
- No official Luma Modify Video price, no Runway Aleph pricing confirmed on Runway's own page, and no measured runtime for VACE or Lucy Edit on a 4090 or T4.
- The GitHub status and last commits of TokenFlow, RAVE and Rerender were not checked this session.

## 4. Image editors for the one-shot restyle (FLUX.1/2 Kontext and Klein, Qwen-Image-Edit-2511, Nano Banana / Gemini, GPT-image): geometry preservation, cost, access

### Takeaway
Use Qwen-Image-Edit-2511 (Apache-2.0, December 2025, focused on consistency and "mitigating image drift") and FLUX.2 Klein (January 2026; 4B is Apache-2.0, 9B is non-commercial) as the open candidates. Use Nano Banana / Nano Banana Pro as the closed comparator. Because only a few dozen images are generated, API cost is a few dollars. No rigorous benchmark of geometry or pixel preservation was found. Anecdotally, Kontext is more conservative than (older) Qwen-Image-Edit, so the project's own seam metric (Section 4 of the proposal) would itself be a small contribution.

### Cited Findings
- **FLUX.2 [klein]** (Black Forest Labs), released 2026-01-15 per BFL's GitHub README, in 4B and 9B sizes plus Base variants:
  - Licenses: 4B and 4B Base are Apache-2.0. 9B and 9B Base use the FLUX Non-Commercial License.
  - VRAM sources conflict for 4B: BFL's blog says about 13 GB (RTX 3090/4070 and up), while BFL's README says about 8 GB.
  - One HF card mentions about 29 GB and "RTX 4090 and above" for 9B, but that card is for an NVFP4 build, so treat the figure as uncertain.
  - Official NVFP4 checkpoints exist.

  — [BFL blog](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence) (fetch blocked; via search excerpt); [VentureBeat](https://venturebeat.com/technology/black-forest-labs-launches-open-source-flux-2-klein-to-generate-ai-images-in); [The Decoder](https://the-decoder.com/flux-2-small-brings-ai-image-generation-and-editing-to-consumer-graphics-cards/); [HF FLUX.2-klein-9b-nvfp4](https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-nvfp4)
- **Qwen-Image-Edit-2511** (Alibaba Qwen, December 2025; upgrade of 2509). Apache-2.0 (official HF card), and Chutes' docs say commercial use, modification and redistribution are allowed. Key changes are much better character consistency and identity preservation, better multi-person consistency, and "mitigate image drift." GGUF quantizations exist (Unsloth). — [HF Qwen/Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511); [Unsloth GGUF](https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF); [Chutes docs](https://chutes.ai/docs/models/vonkaiser-qwen-image-edit-2511); [The Decoder](https://the-decoder.com/?p=30348)
- Model size: Qwen-Image-Edit is 20B parameters and FLUX.1 Kontext [dev] is 12B. — [ComfyDeploy Kontext news](https://studio.comfydeploy.com/news/flux-kontext-dev)
- **FLUX.1 Kontext [dev]** (June 2025, 12B). Uses the FLUX.1 Non-Commercial License, which requires content filters or manual review. Sources conflict on whether outputs may be used commercially. — [BFL Kontext dev blog](https://bfl.ai/blog/flux-1-kontext-dev); [AlternativeTo](https://alternativeto.net/news/2025/6/black-forest-labs-launches-flux-1-kontext-dev--a-new-12b-parameter-image-editing-model); [invideo license matrix (Aug 2026)](https://invideo.io/blog/open-source-image-models-licenses/)
- An anecdotal side-by-side found that "Flux.1 Kontext tends to only change what you tell it to, whereas Qwen Image Edit takes a much freer approach." It concluded Kontext "holds truer to the original image," while Qwen did better on object removal. This compared the original Qwen-Image-Edit, not 2511. — [Diffusion Doodles substack](https://diffusiondoodles.substack.com/p/qwen-image-edit-vs-flux1-kontext)
- **Nano Banana (Gemini 2.5 Flash Image)** (closed). $30 per 1M output tokens at 1,290 tokens per image, which is **about $0.039 per image** ($0.0195 batch). One aggregator says gemini-2.5-flash-image retires 2027-03-15 (unverified). — [Google Developers Blog](https://developers.googleblog.com/en/introducing-gemini-2-5-flash-image/); [BenchLM Nano Banana pricing](https://benchlm.ai/media-pricing/nano-banana)
- **Nano Banana Pro** (Gemini 3 Pro Image): about **$0.134 per image at 1K/2K and $0.24 at 4K** (third-party guides). **Nano Banana 2** (Gemini 3.1 Flash Image) starts at $0.045 at 0.5K. — [YingTu Nano Banana Pro pricing](https://yingtu.ai/blog/nano-banana-pro-api-pricing-per-image); [BenchLM](https://benchlm.ai/media-pricing/nano-banana)
- **GPT Image 1.5** (OpenAI, closed). Token pricing is $5 input / $10 output per 1M text tokens and $8 input / $32 output per 1M image tokens, which a third party puts at about $0.034 per 1024² medium-quality image. One source says OpenAI now labels it a previous-generation model. — [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-image-1.5); [aireiter pricing](https://aireiter.com/blog/gpt-image-1-5-api-pricing)

### Inferences
- **Recommendation: run every world through a "geometry-preservation tournament."** Candidates are Qwen-Image-Edit-2511, FLUX.2 Klein 4B/9B, Kontext dev, Nano Banana Pro and SD1.5/SDXL+ControlNet. Score each with the project's own seam or edge-jump metric before and after homography. This turns model selection into a measurable result.
- Expected cost is roughly 10 worlds × 5 tries × $0.134 ≈ $7 on Nano Banana Pro, and under $2 on Nano Banana (inference from prices above).
- Klein 4B (Apache-2.0, about 8–13 GB) is the only one of these likely to fit on a Colab T4 (16 GB), probably with offload. Qwen-Image-Edit-2511 at 20B needs GGUF/FP8 quantization plus offload, or an A100 or 4090-class card (inference from parameter counts).
- Closed editors (Nano Banana, GPT-image) often return a resized or slightly reframed image. The project's homography re-alignment step therefore matters more for them (inference; worth measuring).

### Gaps
- No quantitative benchmark of structure or geometry preservation across these editors (for example LPIPS or edge IoU against the source) was found.
- No official Klein or Qwen-2511 latency on a 4090 or T4 was found.
- Nano Banana Pro, Nano Banana 2 and GPT Image 1.5 prices are from third-party aggregators and were not checked on official pricing pages.

## 5. Better person matting for compositing (SAM 2/3, MatAnyone, RVM, BiRefNet) and shadows/reflections (Omnimatte family, ObjectDrop)

### Takeaway
Use SAM 3 or 3.1 with the text prompt "person" to get per-instance tracks, then feed those masks to MatAnyone 2 (CVPR 2026, inference code out since March 2026) for soft alphas on hair and edges. RVM (GPL-3.0) is the real-time fallback for a live booth. For shadows, the project's ratio-to-clean-background idea is the cheap classical route. Generative Omnimatte and OmnimatteZero are the research routes that extract a person together with their shadow and reflection.

### Cited Findings
- **SAM 3** (Meta), released 2025-11-19.
  - Concept prompting: a noun phrase or exemplar returns masks and IDs for every matching instance.
  - Includes checkpoints, eval data and fine-tuning code under the SAM License. 848M parameters. Needs Python 3.12+, PyTorch 2.7+ and CUDA 12.6+.
  - Gated HF checkpoints. Video predictor API: `build_sam3_video_predictor()` → `start_session` → `add_prompt(text="person")`.

  — [Meta AI blog](https://ai.meta.com/blog/segment-anything-model-3/); [GitHub facebookresearch/sam3](https://github.com/facebookresearch/sam3); [Gigazine](https://gigazine.net/gsc_news/en/20251120-sam-3)
- **SAM 3.1**, released 2026-03-27, adds "Object Multiplex," a shared-memory approach to multi-object tracking, and is "significantly faster without sacrificing accuracy." — [GitHub sam3](https://github.com/facebookresearch/sam3); [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3)
- SAM 3 VRAM figures are unofficial and conflict. One review saw under 4 GB in tests; a blog claims about 4 GB FP16 for 3.1. — [Roboflow blog](https://blog.roboflow.com/what-is-sam3/); [Medium SAM 3.1](https://medium.com/@priyadarshinichavan/sam-3-1-is-here-and-it-changes-everything-about-real-time-object-tracking-7336ad0bd748)
- **MatAnyone** (CVPR 2025, S-Lab NTU) does memory-propagated video matting from a first-frame mask. — [arXiv 2501.14677](https://arxiv.org/html/2501.14677v2)
- **MatAnyone 2** (CVPR 2026). arXiv v1 was 2025-12-12. It adds a learned Matting Quality Evaluator and the VMReal dataset (28K clips, 2.4M frames). Inference code, eval code and a Gradio demo were released in March 2026. Training code, the evaluator checkpoint and VMReal were still listed as TODO. — [arXiv 2512.11782](https://arxiv.org/abs/2512.11782v1); [project page](https://pq-yang.github.io/projects/MatAnyone2); [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Yang_MatAnyone_2_Scaling_Video_Matting_via_a_Learned_Quality_Evaluator_CVPR_2026_paper.html)
- **Robust Video Matting** (ByteDance, 2021). Re-released under GPL-3.0 in September 2021. Trimap-free and real-time. — [RVM README](https://cdn.jsdelivr.net/gh/peterl1n/robustvideomatting@master/README.md)
- IC-Light's repo recommends **BiRefNet** as a commercial-safe replacement for BRIA RMBG 1.4. — [GitHub IC-Light](https://github.com/lllyasviel/IC-Light). BiRefNet paper: [arXiv 2401.03407](https://arxiv.org/abs/2401.03407) (prior knowledge, not fetched).
- **Generative Omnimatte** (arXiv 2411.16683). Fine-tunes a video diffusion inpainting model to split video into RGBA layers. Each layer holds an object **with its shadows and reflections**. The authors say they will release the layered-video dataset. One summary labels it CVPR 2024, which conflicts with its November 2024 arXiv date; it is likely CVPR 2025. — [arXiv 2411.16683](https://arxiv.org/html/2411.16683v2)
- **OmnimatteZero** (arXiv 2503.18033). Training-free omnimatte using off-the-shelf video diffusion models. Self-attention maps locate and inpaint shadows and reflections. Reports **0.04 s/frame on an A100**. — [arXiv 2503.18033](https://arxiv.org/pdf/2503.18033)
- **ObjectDrop** (Google, 2024) removes or inserts objects together with their shadows and reflections using counterfactual training data. No public weights to my knowledge. — [arXiv 2403.18818](https://arxiv.org/abs/2403.18818) (prior knowledge, not fetched)

### Inferences
- **Recommended pipeline:** SAM 3 ("person") → per-ID binary masks → MatAnyone 2 per ID → alpha. Then build a shadow layer as `clip(frame / median_bg, 0, 1)` (a luminance ratio) restricted to a dilated band below each person's feet. Multiply that layer onto the restyled background. This gives the shadow carry-over the proposal describes and is cheap and explainable.
- A tripod with a known clean plate makes omnimatte-style decomposition far easier than in the papers' general case. The ratio method is likely good enough. Generative Omnimatte or OmnimatteZero are worth one figure as the "learned" comparison if code is available (inference).
- For a live booth, RVM or SAM 3.1 at reduced resolution is the realistic choice. MatAnyone 2 is an offline tool (inference; no fps figures found).
- Licensing: SAM License, GPL-3.0 (RVM) and the S-Lab license (MatAnyone; unconfirmed) are all fine for coursework, but should be listed in the report.

### Gaps
- No official SAM 3/3.1 VRAM or fps for video was found.
- MatAnyone 1/2 licenses and BiRefNet's license were not confirmed this session.
- Generative Omnimatte and OmnimatteZero code-release status is unconfirmed.
- No head-to-head comparison of MatAnyone 2 and RVM on hair detail at 4K was found.

## 6. 3D / 2.5D "step into the painting" camera moves (single-image depth parallax, Gaussian splatting, single-image-to-world, world models, 4D)

### Takeaway
The highest wow-per-hour option is Apple SHARP (December 2025). It turns one image into a metric 3D Gaussian splat in under a second and renders at more than 100 fps. Run it on each restyled still and render a short dolly or orbit "into the painting" before or after the crossing. Depth Anything 3 (November 2025) gives depth for classic 2.5D parallax. WonderWorld (CVPR 2025, under 10 s per scene, code released) and HY-World 2.0 (open, custom license) can extend beyond the frame. World Labs Marble and Google Project Genie are closed and paid but very impressive for a trailer shot.

### Cited Findings
- **SHARP** ("Sharp Monocular View Synthesis in Less Than a Second," Apple ML Research, arXiv 2512.10685, December 2025):
  - A single feed-forward pass produces 3DGS in under a second on an A100.
  - Real-time rendering at more than 100 fps; metric scale; "high-resolution photorealistic images for nearby views."
  - Outputs `.ply` compatible with public 3DGS renderers. Code at github.com/apple/ml-sharp.
  - A secondary report says it reduces image-quality errors by 25–43%.
  - One site says MIT license (unconfirmed).

  — [arXiv 2512.10685](https://arxiv.org/html/2512.10685v1); [Apple ml-sharp README](https://cdn.jsdelivr.net/gh/apple/ml-sharp@main/README.md); [9to5Mac](https://9to5mac.com/2025/12/17/apple-sharp-ai-model-turns-2d-photos-into-3d-views/)
- **Depth Anything 3** (ByteDance Seed). Paper, code and models released 2025-11-14. Sizes range from Small to Giant, plus Nested, with Mono and Metric variants. The repo is Apache-2.0, and smaller and mono/metric weights are reportedly Apache-2.0. Giant and Nested are CC BY-NC 4.0. The Base license is disputed (one source says CC BY-NC). — [HF depth-anything/da3-giant](https://huggingface.co/depth-anything/da3-giant); [ComfyUI wiki DA3](https://comfyui-wiki.com/en/models/depth-anything/depth-anything-3); [Voxel51 DA3 base](https://docs.voxel51.com/model_zoo/models/depth_anything_v3_base_torch.html)
- **WonderWorld** (Stanford/MIT; CVPR 2025). Starts from a single image, with interactive camera control and text prompts. Generates connected 3D scenes in **under 10 s on one A6000** using Fast Layered Gaussian Surfels (FLAGS) and guided depth diffusion. The authors say they release full code and demos. — [arXiv 2406.09394](https://arxiv.org/html/2406.09394v4); [CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Yu_WonderWorld_Interactive_3D_Scene_Generation_from_a_Single_Image_CVPR_2025_paper.html)
- **World Labs Marble** (closed, paid; launched November 2025).
  - Worlds export as 3D Gaussian splats (.spz/.ply), with 2M and 500K splat tiers.
  - Standard plan is $20/month for 20,000 credits (about 12 worlds) per invideo. API credits are $1 per 1,250 with a $5 minimum.
  - Free-tier figures conflict (about 4 worlds per month).
  - A beta splat-creation API (posed RGB-D views to SPZ) costs $5 per run (Oct 30, 2026 report).

  — [World Labs export docs](https://docs.worldlabs.ai/marble/export/gaussian-splat.md); [World Labs API pricing](https://docs.worldlabs.ai/api/pricing); [invideo Marble guide](https://invideo.io/blog/world-labs-marble-3d-worlds/); [RadianceFields](https://radiancefields.com/world-labs-unveils-new-model-marble)
- **Google Project Genie** (Genie 3 prototype; closed). Opened 2026-01-29 to US Google AI Ultra subscribers aged 18+ (about $250/month). Users can download videos of their explorations but not 3D assets. Some Genie 3 features, such as prompted world events, are missing. — [Google blog](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/); [9to5Google](https://9to5google.com/2026/01/29/google-project-genie/); [The Decoder](https://the-decoder.com/google-deepmind-opens-project-genie-to-us-subscribers-for-real-time-ai-world-generation/)
- **Tencent HY-World 2.0 / WorldMirror 2.0 / HunyuanWorld-Voyager** (open weights, custom community license).
  - The license excludes the EU, UK and South Korea. Voyager allows commercial use below 1M monthly active users.
  - Voyager (September 2025) generates camera-controlled RGB-D video that can be converted to 3D.
  - A guide estimates 16 GB minimum and 24–80 GB recommended for HY-World 2.0. HunyuanWorld 1.0 Lite runs in under 17 GB.

  — [HF tencent/HY-World-2.0](https://huggingface.co/tencent/HY-World-2.0); [Clore guide](https://docs.clore.ai/guides/3d-generation/hunyuan-world-2); [CGWORLD Voyager](https://cgworld.jp/flashnews/01-202509-HunyuanWorld-Voyager.html); [The Decoder, 1.0 Lite](https://the-decoder.com/tencent-releases-hunyuan-world-model-1-0-lite-for-faster-resource-efficient-3d-scene-generation/)
- Depth Pro (Apple, October 2024) gives sharp metric monocular depth. — [arXiv 2410.02073](https://arxiv.org/abs/2410.02073) (prior knowledge, not fetched)
- Dynamic/4D reconstruction from monocular video (prior knowledge, not fetched):
  - Shape of Motion: [arXiv 2407.13764](https://arxiv.org/abs/2407.13764)
  - MegaSaM: [arXiv 2412.04463](https://arxiv.org/abs/2412.04463)

### Inferences
- **Recommendation: a "step into the painting" shot.**
  1. Freeze the frame where a walker reaches the line.
  2. Run SHARP on the restyled background, and optionally on the composite with the person.
  3. Render a 2–3 s dolly-in or slight orbit in a web 3DGS viewer or gsplat.
  4. Cut back to the tripod video.

  It is cheap (seconds on a 4090 or A100) and fits "nearby views." Large moves will tear, so keep the camera move under roughly 10–20% of scene depth (inference).
- Alternative 2.5D path: run Depth Anything 3 or Depth Pro on the restyled still, split it into 3–5 depth layers, inpaint the occluded regions with the same image editor, then parallax-animate (a "3D Ken Burns" effect). It is fully classical-plus-depth, which suits a computational-photography course (inference).
- The depth map also powers the proposal's stretch goal (a depth-threshold crossing). The same DA3 metric depth of the clean background can define the "portal" plane (inference).
- A tripod video has no camera parallax, so Shape of Motion and MegaSaM cannot recover background 3D from the main clip. For a true splat of the real Sather Gate, shoot an extra 20–30 s handheld orbit and reconstruct with standard 3DGS. Then a "real-to-restyled" fly-through is possible by restyling the splat's training views consistently, which is hard (inference).
- Marble is the fastest "wow" for a trailer: restyled still → explorable world, then export .ply or record a fly-through for about $20. Flag it as closed and paid (inference from pricing).

### Gaps
- SHARP's license and VRAM were not confirmed from the official repo.
- WonderWorld's repo license was not checked.
- No official HY-World 2.0 VRAM figure was found.
- Marble pricing figures conflict across sources.
- No time-to-train figures for 3DGS from a short orbit on a T4 or 4090 were gathered this session.

## 7. Audio generation for a trailer or soundtrack (Stable Audio Open, MusicGen, ACE-Step): licensing for student use

### Takeaway
For a non-commercial class video, all three are usable. ACE-Step (v1 Apache-2.0; 1.5 reportedly MIT) is the most permissive and the strongest for full songs. Stable Audio Open 1.0 (Stability Community License, free under $1M revenue) is best for short SFX and whooshes at the crossing moment. MusicGen weights are CC-BY-NC 4.0, which is fine for coursework but not for monetized uploads.

### Cited Findings
- **Stable Audio Open 1.0** (Stability AI). Weights are under the Stability AI Community License, not OSI-open. It allows non-commercial use and commercial use for individuals or organizations under $1M annual revenue. Stable Audio Tools (training and fine-tuning) has an open-source license. — [HF stabilityai/stable-audio-open-1.0](https://huggingface.co/stabilityai/stable-audio-open-1.0); [arXiv 2407.14358](https://arxiv.org/html/2407.14358v2); [Stability research post](https://stability.ai/news/stable-audio-open-research-paper)
- One guide claims Stable Audio has a "NonCommercial" restriction, which conflicts with the Community License description above. — [Music generation guide](https://learn-traeai.pages.dev/t/ai-engineering/phases/06-speech-and-audio/09-music-generation)
- **MusicGen** (Meta AudioCraft): code is MIT, weights are CC-BY-NC 4.0. One table lists MusicGen-large as MIT, which conflicts. — [MusicGen wiki](https://spokes-wiki.pages.dev/speech-audio-wiki/musicgen); [creativeainews roundup](https://www.creativeainews.com/articles/best-open-source-ai-music-models-2026/)
- **ACE-Step.** v1 is Apache-2.0. ACE-Step 1.5 is described as MIT, with an XL variant listed as MIT by one source and Apache-2.0 by another. Secondary blogs report that 1.5 rivals or beats Suno v5 on benchmark evaluations (vendor/secondary claim). — [ACE-Step 1.5 project page](https://ace-step.github.io/ace-step-v1.5.github.io); [creativeainews](https://www.creativeainews.com/articles/best-open-source-ai-music-models-2026/); [AIFilms blog](https://studio.aifilms.ai/blog/ace-step-1-5-music-generation-open-source); [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/ace-step-1-5-open-source-music-generation-that-rivals-commercial-ai/)
- Stability's own explainer compares Stable Audio's licensing, export rights and self-hosting against competitors. — [Stability explainer](https://stability.ai/explainers/stable-audio-vs-competitors-licensing-export-rights-and-self-hosting-compared)

### Inferences
- **Recommendation:**
  - ACE-Step 1.5 for a 60–90 s trailer bed, with a genre per world (1920s jazz, synthwave for cyberpunk, and so on).
  - Stable Audio Open for a crossing "whoosh/shimmer" SFX that is timed to each line-crossing event. Crossing timestamps come free from the mask centroids crossing the line.
  - The SFX sync is a small but memorable detail.
- Put the model licenses in the credits. If the video goes to YouTube, avoid MusicGen weights because they are CC-BY-NC (inference).

### Gaps
- Official ACE-Step 1.5 license text, VRAM and generation time were not verified from the GitHub repo.
- MusicGen's weight license was not verified on the AudioCraft model card.
- Stable Audio Open Small and Stable Audio 2.5/3 terms were not researched.
