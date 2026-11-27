# Open-source repos and models to build on

> Research sweep of 27 November 2026. Evidence marks: **read** (the page was opened), **snippet** (search-result text only), **memory** (unverified). Social and product sites were blocked in the session, so product facts are mostly snippets.

## Summary

As of late November 2026, the parts worth reusing have changed a lot since the 19 November notes. Four new things matter. FLUX.3 Image Klein (BFL, 15 Oct 2026) is a 5.6B editor with an INT8 build that runs on 8 GB cards. Qwen-Image-2.1 (14 Sep 2026) is a 7B model that does both generation and editing, takes masks or painted annotations as edit regions, and outputs RGBA, but it is under the Qwen Research licence. RMBG-3.0 (Nov 2026) is CC-BY-NC and gated. LTX-2.5 has an official IC-LoRA called Clean-Plate (Sep 2026). For people mattes, BackgroundMattingV2 (MIT) fits us best because it takes our clean plate as an input, which is exactly our setup. Robust Video Matting (GPL-3.0) ships ONNX/TF.js exports and a browser webcam demo. MatAnyone 2 (Mar 2026, NTU S-Lab licence) is the quality ceiling on a Colab GPU, seeded by SAM 3.1 masks. For clicking regions on the single plate image, SlimSAM through transformers.js costs about 14 MB quantized and SAM 2.1-tiny ONNX is also ready. Text prompts in the browser ("building", "lawn") rest only on a community SAM 3 ONNX port, because transformers.js has no SAM 3 image class yet. For export, Mediabunny (MPL-2.0, v1.66.5, updated 26 Nov 2026) is the answer: mp4-muxer is officially superseded by it, and ffmpeg.wasm has not been released since April 2025. For the flicker claim, VBench's temporal_flickering dimension and the RAFT warping error (torchvision raft_small runs on a CPU) are the standard measures. The archived Colab notebook is stale: as written, Qwen-Image-Edit-2511 at bf16 and FLUX.2 Klein 9B will not fit a free T4 or its RAM, and the T4 has no native bf16. Swap in FLUX.3 Klein INT8 or FLUX.2 Klein 4B, Qwen Lightning with a quantized build, ControlNet-Union, and SAM 3.1. For painted multi-world plates, I recommend keeping separate per-world images and compositing them. Use Differential Diffusion or Qwen-Image-2.1 mask edits only to blend the seams, because one jointly generated plate would tie the worlds together and break the "each world drawn once, reusable" property.

## Findings

### [BackgroundMattingV2 (Real-Time High-Resolution Background Matting)](https://github.com/PeterL1n/BackgroundMattingV2) (2020-12 (MIT relicence 2020-12-21))
*repo · evidence: read · relevance 5/5*

- **What:** Video matting that takes the frame plus a pre-captured background image as input. The README claims state-of-the-art mattes at 4K 30 fps and HD 60 fps on a GPU. It ships TorchScript/ONNX weights in GitHub releases.
- **Relevance:** Stage a (people mask). It is the only matting model in the list that uses a clean plate as input, which is exactly what crossover/background.py produces. It is a direct replacement for the colour difference + morphology step.
- **How we differ:** It produces a soft alpha with hair detail, not a binary difference mask. Like us, it assumes a fixed camera and a clean background. It does not handle shadows (they end up in the foreground or are lost). Lighting changes between plate and frame hurt it.
- **What to take:** Run the mobilenetv2 ONNX on the CPU offline over the 40-s clip, with our median plate as the background input, and write per-frame alpha PNGs. The portal then reads them in place of combineMasks(). The licence is MIT. The speed on a 4-core CPU is not measured; I expect a few fps at 768x576, so minutes for the whole clip (memory, unverified).

### [SlimSAM-77 in transformers.js (plus the Xenova segment-anything-webgpu demo)](https://huggingface.co/Xenova/slimsam-77-uniform) (2026-03 (last modified))
*model · evidence: read · relevance 5/5*

- **What:** A pruned SAM under Apache-2.0. Quantized ONNX is about 8.9 MB for the vision encoder and 4.9 MB for the prompt encoder plus mask decoder (fp16: 12.2 + 8.6 MB). The Xenova 'segment-anything-webgpu' Space is a ready click-to-segment page.
- **Relevance:** Stage b: click-to-select on the one plate image. The encoder runs once and each click only runs the small decoder.
- **How we differ:** It is points/boxes only, with no text prompts. Quality is below SAM 2.1.
- **What to take:** Copy the Space's index.js pattern into a 'magic wand' tool in paint.js. Encode the plate once, then each click adds its mask to the current world's painted mask, with shift to subtract. About 1 day.

### [Mediabunny](https://www.npmjs.com/package/mediabunny) (2026-11-26 (v1.66.5))
*repo · evidence: read · relevance 5/5*

- **What:** A pure TypeScript media toolkit to read, write and convert MP4/WebM in the browser with WebCodecs. MPL-2.0. mp4-muxer (v5.2.2) is now marked 'superseded by Mediabunny. Please migrate'. ffmpeg.wasm was last released as 0.12.15 in April 2025.
- **Relevance:** Stage g: export the composited video from portal/compositor.js.
- **How we differ:** Not applicable (it is infrastructure).
- **What to take:** Decode the source with Mediabunny's sample sink (frame-exact, no video.seek), render each frame through compositor.js into the WebGL canvas, encode it via a CanvasSource and write MP4 (H.264) or WebM. Fall back to WebM/VP9 in Firefox. About 1 to 1.5 days.

### [Robust Video Matting (RVM)](https://github.com/PeterL1n/RobustVideoMatting) (2021-09 (GPL-3.0 re-release))
*repo · evidence: read · relevance 4/5*

- **What:** A recurrent human video matting model with no background input. It has official ONNX fp32/fp16 exports, 'tested on ONNX Runtime with CPU and CUDA', a TF.js int8 export, and a live webcam demo in the browser.
- **Relevance:** Stage a, offline on a CPU and in the browser kiosk. It is a step up from the MediaPipe selfie segmenter, with a temporally stable alpha.
- **How we differ:** It does not use our plate. It is trained on humans only. GPL-3.0 is fine for a course project but contaminates redistributed code.
- **What to take:** Take rvm_mobilenetv3 ONNX into onnxruntime-web (WebGPU/WASM) for the kiosk, or into Python onnxruntime on the CPU for uploaded clips. Feed the alpha into combineMasks() as one more mask source. About 1 day.

### [MatAnyone 2 (Scaling Video Matting via a Learned Quality Evaluator)](https://huggingface.co/PeiqingYang/MatAnyone2) (2026-03)
*model · evidence: read · relevance 4/5*

- **What:** Human video matting that propagates a first-frame mask and keeps fine detail without segmentation-like edges. Inference code, a CLI, a Gradio demo and a Colab notebook came out in March 2026, and a third-party Core ML real-time port in June 2026. The licence is NTU S-Lab License 1.0 (non-commercial).
- **Relevance:** Stage a: the best-quality offline matte, made on Colab and then frozen as PNGs for the portal.
- **How we differ:** It needs a first-frame mask (from SAM 3.1) and a GPU. It does not use the plate.
- **What to take:** Add a Colab cell: SAM 3.1 'person' mask on frame 0, then MatAnyone2, then alpha PNGs. We already have the --masks path in the archived pipeline. About half a day on Colab.

### [SAM 3 / SAM 3.1 (Object Multiplex)](https://github.com/facebookresearch/sam3) (2025-11 (SAM 3); 2026-03-27 (SAM 3.1))
*repo · evidence: read · relevance 4/5*

- **What:** Promptable concept segmentation and tracking from text ('person', 'building'). SAM 3.1 checkpoints add shared-memory multi-object tracking that is 'significantly faster without sacrificing accuracy'. It is under the SAM License and the HF weights are gated (manual approval). It needs a GPU.
- **Relevance:** Stages a and b: person tracks for the whole clip, and text-prompted region masks on the plate ('lawn', 'sky', 'building').
- **How we differ:** It gives masks, not mattes. On the plate it would replace our hand-painted regions with semantic regions, which complements paint.js.
- **What to take:** Update the notebook to the facebook/sam3.1 checkpoint. Run text prompts on the plate once and export one PNG per concept. Load them in paint.js as an initial mask the user can then edit with the brush.

### [SAM 2.1 hiera-tiny ONNX (onnx-community)](https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX) (2025-11)
*model · evidence: read · relevance 4/5*

- **What:** An official transformers.js-compatible export. The decoder is 21 MB fp32, 10.5 MB fp16 and 8.7 MB int8, with q4/bnb4 variants. The base model is Apache-2.0. It has about 26k monthly downloads.
- **Relevance:** Stage b: a higher-quality alternative to SlimSAM for clicking on the plate.
- **How we differ:** Its encoder is larger than SlimSAM's. Its video tracking is not needed for one plate.
- **What to take:** Drop-in swap with SlimSAM in the same paint.js tool. Measure the encoder time on a laptop with WebGPU on and off.

### [FLUX.3 Image Klein (Black Forest Labs)](https://huggingface.co/black-forest-labs/flux-3-image-klein) (2026-10-13 (HF) / 2026-10-15 (announcement))
*model · evidence: snippet · relevance 4/5*

- **What:** A 5.6B image generation and editing model (HF pipeline tag image-to-image). It comes in base and step-distilled checkpoints, with bf16, INT8, NVFP4 and FP8 builds, and ComfyUI packaging that includes a Qwen3.5-9B prompt upsampler. Press reports INT8 on 8 GB RTX cards, and BFL claims +70 Elo in editing over FLUX.2 Klein 9B. Licence: 'flux-kommunity-license' (gated, auto-approve).
- **Relevance:** Stage c: the current small open editor for restyling the plate. It is the likely best fit for a free T4 (INT8).
- **How we differ:** It is instruction or reference editing, not ControlNet, so geometry preservation is not guaranteed pixel by pixel. Our seam metric (crossover.score) must check it. NVFP4 will not run on a T4.
- **What to take:** Replace FLUX.2 Klein 9B in the notebook with the flux-3-image-klein INT8 build (or FLUX.2 Klein 4B, Apache-2.0, as a fallback). Read the Kommunity licence terms before publishing outputs.

### [Qwen-Image-2.1 (+ Turbo, + lightx2v Lightning)](https://huggingface.co/Qwen/Qwen-Image-2.1) (2026-09-14 (Turbo 2026-10-09))
*model · evidence: read · relevance 4/5*

- **What:** A unified generation and editing model with a 7B visual generator (32 single-stream DiT layers). Per its card it does 'local edits via circles, painted annotations, or separate masks', takes up to 10 reference images, outputs native RGBA, and runs natively near 2048 px. It uses diffusers QwenImage21Pipeline with enable_model_cpu_offload. Licence: Qwen Research License (not Apache).
- **Relevance:** Stages c and d: restyle the plate, and edit only inside a painted region, which our paint tool already produces.
- **How we differ:** It is far smaller than the 20B Qwen-Image-Edit-2511 but has a research-only licence. It has no ControlNet. Its RGBA subject extraction could also cut people out of a still.
- **What to take:** Feed it a paint.js mask exported as a PNG with the prompt 'make this region winter'. Test on Colab with Turbo or Lightning. Check whether it fits a T4 in fp16 with offload; that is unverified.

### [ControlNet-Union SDXL (xinsir)](https://huggingface.co/xinsir/controlnet-union-sdxl-1.0) (2024-07)
*model · evidence: read · relevance 4/5*

- **What:** One SDXL ControlNet for depth, canny, lineart and other controls, including multi-condition use. Apache-2.0, about 233k downloads.
- **Relevance:** Stage c: the most pixel-aligned upgrade from our SD 1.5 + ControlNet, using the same depth (Depth Anything V2) and canny inputs crossover/generate.py already computes.
- **How we differ:** It is an older model family with lower fidelity than FLUX or Qwen editors, but its structure preservation is much stronger and more predictable.
- **What to take:** In crossover/generate.py, add an --sdxl path with ControlNet-Union (depth + canny) and an SDXL Lightning or LCM LoRA. It runs fp16 on a T4. On the CPU it is probably too slow at 1024 px. About 1 day.

### [Differential Diffusion](https://github.com/exx8/differential-diffusion) (2024 (memory))
*repo · evidence: read · relevance 4/5*

- **What:** Img2img in which a per-pixel change map sets how much each pixel may change. It supports SD and SDXL, and has a diffusers community pipeline and a built-in ComfyUI node.
- **Relevance:** Stage d: soft, painted regions with different change strengths, and seam harmonisation between worlds.
- **How we differ:** It changes how much is edited, not which prompt applies where. Several styles need several passes or regional prompts.
- **What to take:** Leave each world as it is, then run one Differential Diffusion pass on the composited still with a change map that is non-zero only in a band around the painted seams. That gives a 'one plate' look while each world stays reusable.

### [VBench (temporal_flickering etc.)](https://github.com/Vchitect/VBench) (2026-03 (I2V Arena update))
*repo · evidence: read · relevance 4/5*

- **What:** The standard video-generation benchmark. Its temporal_flickering dimension is the mean absolute difference between frames (static videos are filtered out first), and it also has subject_consistency and background_consistency (DINO/CLIP features). It runs on custom videos.
- **Relevance:** Stage h: measure 'per-frame AI flickers, ours does not' the standard way.
- **How we differ:** Its flickering score assumes generated videos. We should compute it on the background region only (people masked out), against a per-frame SD baseline.
- **What to take:** Run temporal_flickering and background_consistency on 3 videos: original, per-frame SD 1.5 img2img, and ours. The flicker computation is cheap enough for a CPU, but the CLIP and DINO features will be slow (memory).

### [RAFT warping error (torchvision raft_small)](https://github.com/princeton-vl/RAFT) (2020 (memory))
*repo · evidence: memory · relevance 4/5*

- **What:** Optical flow. The standard 'warping error' metric of video-restyling papers warps frame t to t+1 with flow from the original video and measures the error on non-occluded pixels. torchvision ships raft_small with weights.
- **Relevance:** Stage h.
- **How we differ:** Not applicable.
- **What to take:** Write scripts/flicker_eval.py (the team's own code). Compute flow on the original clip, then the warping error for each output, plus the CLIP frame consistency (cosine between consecutive CLIP embeddings). raft_small at 384 px should take minutes on 4 cores.

### [SAM 3 text-prompt ONNX (community port)](https://huggingface.co/danilobukvic/sam3-text-onnx) (2025-11/2026)
*model · evidence: snippet · relevance 3/5*

- **What:** A community export split into vision encoder, text encoder and decoder, with int4 and int8 variants (the decoder is 19.8 MB int4). It runs on onnxruntime-web with WebGPU and uses transformers.js only for the tokenizer. Its card says transformers.js has no SAM 3 image class.
- **Relevance:** Stage b: in-browser 'type building, get a mask'.
- **How we differ:** It is unofficial and the true total size is unclear, because the external data files did not show in the listing. Licence inherits the SAM License.
- **What to take:** Do not depend on it for the demo. If someone has a spare day, try it. Otherwise precompute text masks on Colab with SAM 3.1.

### [Qwen-Image-Edit-2511 + Lightning LoRAs](https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning) (2025-12 (base) / 2026-10 (Lightning update))
*model · evidence: read · relevance 3/5*

- **What:** Both are Apache-2.0. The base model has about 241k downloads and Lightning about 900k. Lightning cuts editing to 4 or 8 steps. There are community int8 and nf4 quantized builds (Nov 2026).
- **Relevance:** Stage c: the strongest permissively licensed instruction editor. It is in the archived notebook.
- **How we differ:** The 20B transformer at bf16 is about 40 GB, so it does not fit a T4 or a free Colab's roughly 12 GB of system RAM for CPU offload (memory). You need nf4, GGUF or Nunchaku plus Lightning.
- **What to take:** Keep it as the commercially clean option, but switch the notebook cell to a quantized transformer plus the Lightning LoRA, with fp16 on the T4.

### [Regional Prompter / MultiDiffusion / attention couple](https://github.com/hako-mikan/sd-webui-regional-prompter) (2023-2025 (memory))
*repo · evidence: memory · relevance 3/5*

- **What:** Mask-based regional prompting for SD and SDXL. MultiDiffusion fuses region-wise denoising. Attention couple is the ComfyUI equivalent with masked conditioning.
- **Relevance:** Stage d: one generation with several worlds in painted regions.
- **How we differ:** One joint plate couples the worlds. Repainting one region regenerates all of them, morph ladders per world break, and our 'pick worlds, then paint where' order becomes 'paint first, then generate'.
- **What to take:** Only worth it as a 'harmonised final plate' option. Our per-world compositing stays the core.

### [LTX-2.5 22B IC-LoRA Clean-Plate (Lightricks)](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Clean-Plate) (2026-09-09 (LTX-2.3 version 2026-07-19))
*model · evidence: read · relevance 3/5*

- **What:** An official video-to-video LoRA that removes subjects to produce a clean plate. It is gated under the LTX-2.x community licence, has about 14.6k downloads, and ships side-by-side example videos. A sibling IC-LoRA, 'Alpha-Gen', generates alpha for hair, smoke and curtains.
- **Relevance:** Stage e (clean plate when the median fails), and Alpha-Gen for stage a.
- **How we differ:** It needs a 22B video model, far beyond a T4. It produces a whole video, but we need only one still plate.
- **What to take:** Mention it as the state of the art. For our single still, a masked median plus image inpainting is enough (see ideas).

### [ProPainter / DiffuEraser / MiniMax-Remover](https://github.com/sczhou/ProPainter) (2023-2025 (ONNX ports 2026-11))
*repo · evidence: read · relevance 3/5*

- **What:** ProPainter is flow-guided video inpainting under the NTU S-Lab licence; it runs memory-efficiently at 576x320 with --fp16. DiffuEraser adds diffusion on top of ProPainter. MiniMax-Remover is DiT-based, needs 6 steps and no CFG, and is CC-BY-NC-4.0. Community ONNX exports of ProPainter and DiffuEraser appeared in Nov 2026.
- **Relevance:** Stage e: filling the region where a person stood still.
- **How we differ:** These are video tools. We need one still, and only where every frame has a person over that pixel.
- **What to take:** Run ProPainter on Colab on a short sub-clip and take its median, or simply inpaint the single still.

### [IC-Light (v1 SD1.5; FLUX v2 notes)](https://github.com/lllyasviel/IC-Light) (2024-05 (v1), FLUX discussion 2024-11)
*repo · evidence: read · relevance 3/5*

- **What:** Foreground relighting under Apache-2.0. The fbc model is conditioned on a foreground plus a background image. It runs per image.
- **Relevance:** Stage f: relight people to a world's light.
- **How we differ:** It works per frame, so on video it will flicker and change identity. That undercuts our core claim.
- **What to take:** Use it only for a still 'hero frame' poster, or to fit our affine colour grid: relight a few keyframes with IC-Light, then fit our existing plate-to-world colour transform for people to those results. That keeps temporal stability.

### [Daydream Scope](https://github.com/daydreamlive/scope) (2026 (alpha))
*repo · evidence: read · relevance 3/5*

- **What:** A tool for real-time interactive generative video pipelines: StreamDiffusionV2, LongLive, Krea Realtime, RewardForcing, MemFlow. Pipelines are composable, with depth and interpolation. Licence CC BY-NC-SA 4.0. It needs a large GPU.
- **Relevance:** Stage i: the closest open 'live generative video' framework. It restyles every frame, which is the opposite of our draw-once approach.
- **How we differ:** It regenerates every frame (flicker and drift, GPU needed). It has no clean-plate or person-preserving composite and no painted regions.
- **What to take:** Use it as the per-frame baseline in the flicker evaluation if Colab can run StreamDiffusionV2, or cite its demos.

### [EdgeTAM / EfficientTAM](https://github.com/facebookresearch/EdgeTAM) (2025 (community ONNX/web ports 2026-09/10))
*repo · evidence: read · relevance 3/5*

- **What:** EdgeTAM is 22 times faster than SAM 2 and reaches 16 fps on an iPhone 15 Pro Max without quantization, under Apache-2.0. Community web and ONNX ports exist (for example RabiatS/edgetam-web, Oct 2026).
- **Relevance:** Stage a in the browser: click a person once, then track them.
- **How we differ:** It gives masks, not mattes. The web ports are unverified.
- **What to take:** An option for the uploaded-clip path in the browser. RVM is simpler for people.

### [Hosted editors: Seedream 4.5 / 5.0, Nano Banana Pro](https://openrouter.ai/bytedance-seed/seedream-4.5/pricing) (2026)
*product · evidence: snippet · relevance 3/5*

- **What:** Seedream 4.5 costs about $0.03-0.04 per image (OpenRouter $0.04). Nano Banana Pro (Gemini 3 Pro Image) costs about $0.134-0.24 per image at official prices. Seedream 5.0 Lite and Pro cost about $0.03-0.045 per image. Most of these figures come from aggregator or reseller pages.
- **Relevance:** Stage c: highest-fidelity restyles for a handful of worlds at negligible cost.
- **How we differ:** They are closed models. They often shift geometry and resample the image, so they need alignment checking.
- **What to take:** For about $1 total, make 7 worlds and 2 seeds via one API. Score them with crossover.score, and keep a world only if its seam error is low.

### [LBM relighting / Light-A-Video / TC-Light](https://huggingface.co/jasperai/LBM_relighting) (2025)
*model · evidence: read · relevance 2/5*

- **What:** LBM relights in one step and is CC-BY-NC-4.0. Light-A-Video does training-free video relighting on IC-Light or Wan2.1. TC-Light targets temporally consistent relighting of long videos. All need a GPU.
- **Relevance:** Stage f.
- **How we differ:** Much heavier than our colour transfer. Light-A-Video and TC-Light address flicker, but cost GPU minutes per clip.
- **What to take:** Report them as related work. Do not build on them in 12 days.

### [BiRefNet_lite ONNX / BEN2 / RMBG-2.0 / RMBG-3.0](https://huggingface.co/onnx-community/BiRefNet_lite-ONNX) (2025-10 to 2026-11)
*model · evidence: read · relevance 2/5*

- **What:** BiRefNet_lite is MIT; its ONNX is 224 MB fp32 and 114.5 MB fp16. BEN2 is MIT. RMBG-2.0 is gated under a BRIA licence. RMBG-3.0 (2026-11-10) is built on Fibo-2.0 and is CC-BY-NC and gated.
- **Relevance:** Stage a: per-frame salient-object cutouts.
- **How we differ:** They work per image (no temporal memory, so they flicker), take no plate, and are heavy for video rate in the browser.
- **What to take:** Skip them for video. BiRefNet_lite could refine the alpha of a single hero frame.

### [MediaPipe tasks-vision / onnxruntime-web current versions](https://www.npmjs.com/package/@mediapipe/tasks-vision) (2026-11)
*repo · evidence: read · relevance 2/5*

- **What:** @mediapipe/tasks-vision latest is 1.2.3, with nightly 1.3.0-rc.20261122. onnxruntime-web is 1.31.1 (2026-11-12). The MediaPipe selfie segmenter ONNX is about 0.2-0.5 MB.
- **Relevance:** Stage a for the kiosk.
- **How we differ:** Not applicable.
- **What to take:** Pin versions. RVM through onnxruntime-web 1.31 is the matting upgrade.

## Ideas to borrow

- **Replace the background-difference mask with BackgroundMattingV2 run offline on the CPU, with our median plate as the background input. Store the alpha per frame and have combineMasks() prefer it when it exists.** Source: BackgroundMattingV2, https://github.com/PeterL1n/BackgroundMattingV2. It is the only model in this survey that uses the clean plate, the asset we already have. It fixes the fringes and trails. It is MIT-licensed and ships ONNX. *Effort: 1-2 days, CPU only. Risk: shadows and lighting drift between plate and frame.*
- **Add a 'magic wand' to paint.js. Encode the plate once with SlimSAM or SAM 2.1-tiny (transformers.js, WebGPU with a WASM fallback). Each click adds or subtracts a SAM mask to the current world's mask, and the brush stays for touch-ups.** Source: Xenova/slimsam-77-uniform and segment-anything-webgpu Space, https://huggingface.co/Xenova/slimsam-77-uniform. The plate is a single image, so one encoder pass costs seconds. Region painting becomes three clicks instead of careful brushwork, which makes a great live demo moment. *Effort: 1 day, browser only, about 14-21 MB download.*
- **Precompute text-prompted region masks ('sky', 'building', 'lawn', 'path') on the plate with SAM 3.1 on Colab. Ship them as preset masks in build_portal_artifact.py so a user can tap 'make the sky cyberpunk'.** Source: SAM 3.1, https://github.com/facebookresearch/sam3. Semantic regions are what people want to paint. Doing it offline avoids the unofficial browser port. *Effort: Half a day on Colab with a gated HF token.*
- **Rewrite the archived Colab notebook for a T4. Use fp16, not bf16. Swap FLUX.2 Klein 9B for FLUX.3 Image Klein INT8 (or FLUX.2 Klein 4B, Apache). Use Qwen-Image-Edit-2511 nf4 or GGUF with the Lightning 8-step LoRA. Use SDXL with ControlNet-Union (depth + canny). Update SAM 3 to SAM 3.1, and add MatAnyone2.** Source: HF model cards: flux-3-image-klein, Qwen-Image-Edit-2511-Lightning, xinsir/controlnet-union-sdxl-1.0. As written, the notebook's 20B and 9B bf16 cells will run out of memory on a free T4 or its 12 GB of RAM. The newer small editors are both better and smaller. *Effort: 1 day of Colab debugging.*
- **Export the video in the browser with Mediabunny. Decode source frames exactly, render each through compositor.js, and encode the canvas to MP4 or WebM, with a progress bar.** Source: Mediabunny, https://www.npmjs.com/package/mediabunny. It is on the roadmap. mp4-muxer is deprecated in favour of it, and ffmpeg.wasm is stale and slow. Frame-exact decoding avoids the inaccuracy of seeking a video element. *Effort: 1-1.5 days, browser only.*
- **A flicker table for the report. Compare three outputs: per-frame SD 1.5 img2img, ours, and optionally StreamDiffusion. Measure the RAFT warping error, the VBench temporal_flickering formula, and CLIP frame consistency, computed on background pixels only.** Source: VBench, https://github.com/Vchitect/VBench; RAFT via torchvision. It turns the pitch's main claim into a standard, citable measurement. *Effort: 1 day, CPU (raft_small at reduced resolution).*
- **Seam harmonisation instead of one joint multi-world generation. After compositing the painted worlds into one still, run Differential Diffusion (or a Qwen-Image-2.1 masked edit) with a change map that is non-zero only within a few pixels of each region boundary. Use the result as an optional 'blended plate'.** Source: Differential Diffusion, https://github.com/exx8/differential-diffusion; Qwen-Image-2.1 mask edits. It keeps each world reusable and independent, which is our core design, while hiding hard seams. *Effort: Half a day to 1 day on Colab.*
- **Stable relighting by distillation. Relight 3-5 keyframes of each person with IC-Light fbc against the world plate. Fit our existing affine colour grid of people to those relit frames instead of to the plate-to-world mapping, and apply it to all frames.** Source: IC-Light, https://github.com/lllyasviel/IC-Light. People look relit, not just tinted, and nothing flickers because the per-frame operation stays a smooth colour transform. *Effort: 1-2 days on Colab plus a change to colormap.py. Risk: identity drift in the keyframes.*
- **A masked median plus image inpainting for people who stand still. Compute the median only over pixels not covered by people (SAM or BMV2 masks), find the pixels where no frame is free, and inpaint just those with LaMa on the CPU or an editor prompt such as 'remove the person'.** Source: LTX-2.5 IC-LoRA Clean-Plate shows the state of the art; ProPainter, https://github.com/sczhou/ProPainter. We need one still, not a video, so a 22B video LoRA is overkill. *Effort: Half a day, CPU.*

## Not reached or not verified

- github.com HTML and api.github.com were blocked (403), so I could not collect star counts or last-commit dates. Licences and dates come from raw README files, the HF API and npm. A human should check stars by hand.
- The model cards for FLUX.3 Image Klein, RMBG-3.0 and the LTX-2.5 Clean-Plate LoRA are gated. I saw only metadata (licence name, files). The FLUX.3 VRAM and parameter figures come from press snippets, and the Kommunity licence terms are unread.
- No CPU timings were found for BMV2, RVM or SAM at 768x576 on a 4-core box. Benchmark 30 frames locally before committing.
- Whether Qwen-Image-2.1 or Turbo fits a T4 in fp16 is unverified. The card shows only bf16 with cpu_offload.
- Unverified items: Z-Image-Edit (no official repo found on HF), OmniGen2, HiDream-E1, SD3.5 ControlNets, ROSE, VACE removal, Generative Omnimatte and OmnimatteZero code, ComfyUI attention-couple nodes, browser SD-Turbo/LCM WebGPU demos (only a stub jsk0/sd-turbo-webgpu found), and FXjutsu workflows.
- Hosted API prices are from aggregators. Check Google AI Studio and BytePlus price pages and their terms on output use.
- Search by hand: X/Reddit r/StableDiffusion for 'FLUX.3 klein ControlNet' or 'structure preserve'; ComfyUI 'Differential Diffusion regional'; HF Spaces tagged transformers.js for 'sam3'; YouTube 'clean plate ComfyUI LTX 2.5'.

## Notes

## Method and evidence
GitHub web and API access was blocked in this session. I used the Hugging Face API (`/api/models`, listings sorted by creation date per organisation), raw.githubusercontent READMEs, the npm registry, and three web searches. Everything marked "fetched" was read from those sources on 27 Nov 2026.

## What is new since the 19 Nov notes
- **FLUX.3 Image Klein**, 13-15 Oct 2026 ([HF](https://huggingface.co/black-forest-labs/flux-3-image-klein), [BFL blog](https://bfl.ai/blog/flux-3-image-klein), snippet). It has 5.6B parameters, base and distilled versions, and INT8, NVFP4 and FP8 builds. There is a `-comfy` repo with `flux3-image-klein-int8-convrot.safetensors` and a Qwen3.5-9B prompt upsampler. Licence: `flux-kommunity-license`. BFL also released `FLUX.2-small-decoder` (Apr 2026) and `FLUX.2-klein-9b-kv` (Mar 2026).
- **Qwen-Image-2.1**, 14 Sep 2026 ([HF](https://huggingface.co/Qwen/Qwen-Image-2.1), fetched). Its visual generator has 7B parameters. It covers generation and editing in one model, edits by masks or painted annotations, takes up to 10 references and outputs RGBA. The licence is **Qwen Research** (a regression from the Apache-2.0 of Edit-2511). lightx2v ships `Qwen-Image-2.1-Lightning` and a `-v2-RL` variant (Nov 2026).
- **RMBG-3.0**, 10 Nov 2026 ([HF](https://huggingface.co/briaai/RMBG-3.0)). It is built on Fibo-2.0-dev and licensed CC-BY-NC.
- **LTX-2.5 IC-LoRAs** (Sep 2026): Clean-Plate, Alpha-Gen, Layout-To-Render, Restore and others ([HF org](https://huggingface.co/Lightricks)). They use the LTX-2.x community licence and a 22B base model.
- **MatAnyone 2** (Mar 2026, [HF](https://huggingface.co/PeiqingYang/MatAnyone2)). The licence is NTU S-Lab and it has a Colab notebook.
- **SAM 3.1** (27 Mar 2026, [repo](https://github.com/facebookresearch/sam3)). No "SAM 4" was found on the facebook HF organisation as of 27 Nov 2026.

## Stage by stage
**a. Mattes.** BackgroundMattingV2 (MIT) is the one built for our setup: a fixed camera plus a captured background. RVM (GPL-3.0) is the browser and kiosk option; it has ONNX opset 12 tested on CPU, a TF.js int8 export and a live web demo. MatAnyone2 with SAM 3.1 sets the quality ceiling on Colab. Per-image models (BiRefNet, BEN2, RMBG) flicker on video and take no plate. RMBG-2.0 and 3.0 are non-commercial or gated. In the browser at video rate, the realistic options are RVM-mobilenetv3 or the MediaPipe selfie segmenter (0.2-0.5 MB ONNX), since BiRefNet_lite is 114 MB fp16.

**b. Click-select on the plate.** SlimSAM-77 is the smallest: quantized ONNX is 8.9 MB for the encoder and 4.9 MB for the decoder. SAM 2.1-tiny ONNX has an 8.7 MB int8 decoder plus its encoder. Both are Apache-2.0 and loadable by transformers.js. Because the plate is one image, the encoder runs once and each click runs only the decoder, so WebGPU is optional. For text prompts in the browser, only a community SAM 3 ONNX exists, and it calls onnxruntime-web directly. Precompute on Colab instead.

**c. Restyle with geometry kept.** There are two ways to work.
1. **Structure-locked:** SDXL with ControlNet-Union, depth plus canny (Apache-2.0). It fits a T4 in fp16, and it is the natural upgrade of crossover/generate.py because the depth and canny inputs already exist.
2. **Instruction editors:** FLUX.3 Klein INT8, FLUX.2 Klein 4B (Apache-2.0), Qwen-Image-Edit-2511 with Lightning (Apache-2.0, but 20B, so it needs nf4 or GGUF), and Qwen-Image-2.1 (research licence). They give higher fidelity but can shift pixels. Gate every output with crossover.score.

Hosted APIs are cheap: Seedream 4.5 costs about $0.04 per image and Nano Banana Pro about $0.13-0.24 (aggregator figures). Nothing of this quality runs on our CPU in under 5 minutes. SD 1.5 with LCM remains the CPU option.

**Verdict on gpu_restyle_and_sam3.ipynb.** The idea is right; it compares editors and scores them on the seam metric. The specific models and settings need updating:
- `torch.bfloat16` everywhere. The T4 has no native bf16, so use fp16.
- Qwen-Image-Edit-2511 at bf16 with cpu_offload needs about 40 GB of system RAM, but free Colab has about 12 GB. Use a quantized transformer plus the Lightning 8-step LoRA.
- FLUX.2 Klein 9B is under a non-commercial licence and is large. Use FLUX.3 Image Klein INT8, or FLUX.2 Klein 4B.
- SDXL canny only: switch to ControlNet-Union with depth plus canny.
- `facebook/sam3`: switch to `facebook/sam3.1`, which needs the latest repo code.
- Add a MatAnyone2 cell.

**d. Multi-region.** Regional Prompter, MultiDiffusion and attention couple all generate one joint image. Qwen-Image-2.1 can now take painted regions natively. I would not replace per-world compositing:
- a joint plate couples all the worlds,
- it breaks the SDEdit morph ladders per world (morph.py),
- and it forces a regeneration on every paint stroke, which loses the live painting.

Use joint generation only for seam harmonisation (see ideas).

**e. Clean plates.** For one still, a masked median plus LaMa or an editor inpaint is enough. The state of the art for video is the LTX-2.5 Clean-Plate IC-LoRA (22B) and MiniMax-Remover (CC-BY-NC).

**f. Relighting.** The per-frame methods (IC-Light, LBM) flicker. The video methods (Light-A-Video, TC-Light) are heavy. Distilling IC-Light keyframes into our colour grid keeps our no-flicker guarantee.

**g. Export.** Mediabunny 1.66.5 is MPL-2.0 and was updated 26 Nov 2026 ([npm](https://www.npmjs.com/package/mediabunny)). mp4-muxer is deprecated in its favour. ffmpeg.wasm (0.12.15, Apr 2025) is a fallback only. Gotchas (from memory):
- H.264 encoding in Firefox on Linux may be missing, so fall back to VP9 in WebM.
- Seeking a video element is not frame-exact; decode with WebCodecs instead.
- Keep frame timestamps in microseconds.
- Encoder dimensions must be even.

**h. Evaluation.** VBench's `temporal_flickering` dimension filters out static videos first and then scores frame-to-frame absolute differences. For us, mask out people and compute it on the background. Add the RAFT warping error (flow from the source clip) and CLIP consecutive-frame cosine.

**i. Closest open projects.** Daydream Scope (CC BY-NC-SA) bundles StreamDiffusionV2, LongLive and Krea Realtime. These are all per-frame generators, which is our foil. What remains ours: draw each world once on a clean plate, keep real people, cross per region with painted and text or click masks, and run it all in the browser without a GPU.
