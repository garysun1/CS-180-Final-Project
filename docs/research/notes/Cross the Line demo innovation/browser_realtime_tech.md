# In-browser real-time techniques (2024–2026) for a live "Cross the Line" demo

Scope: what a student team can ship as a static site (no backend) in 1–3 weeks to turn the offline pipeline (median background plate, restyled plate from SD + ControlNet, person masks, compositing by line, depth threshold or portal) into a live web or webcam demo. Research date: 2026-11-19.

Method note: web.dev, ai.google.dev, developers.google.com, developer.chrome.com and info.nianticspatial.com could not be fetched from this session (network policy). Claims from those pages come from search-engine snippets of them and are marked "(via search snippet)". Package versions and dates were read directly from the npm registry, model file sizes from the Hugging Face API and Google Cloud Storage HTTP headers, and browser-support data from the raw caniuse and MDN browser-compat-data JSON on GitHub, all on 2026-11-19.

## 1. WebGL2 vs WebGPU for per-pixel video compositing (support, frame upload, performance)

### Takeaway
WebGPU now ships by default in Chrome/Edge (desktop since 113, Android 12+ since 121), Safari 26 (macOS, iOS, iPadOS, visionOS) and Firefox (Windows 141+, Apple Silicon Mac 145/147+). It is still missing by default in Firefox on Linux, Intel Mac and Android, and in Chrome on many Linux GPUs. A compositor that only blends 2–4 textures (video, mask, restyled plate, depth) with a threshold is trivial in WebGL2, which runs everywhere, so build on WebGL2 (or three.js, which can use either backend) and treat WebGPU as an optional path, needed mainly for the ML inference libraries.

### Cited Findings
**Support matrix (as of Nov 2026)**
- Chromium: WebGPU on by default on Mac, Windows x86/x64 and ChromeOS from Chrome 113. On Android it is on by default for ARM/Qualcomm/Intel GPUs on Android 12+ from Chrome 121, and for Imagination GPUs on Android 16+ from Chrome 139. Samsung Xclipse and other Android GPUs are "TBD". On Linux it is on by default for Intel Gen12+ from Chrome 144 and for NVIDIA (driver 535.183.01+) on Wayland from Chrome 147; other Linux GPUs need flags. Windows ARM64 is behind a flag. — [gpuweb Implementation Status wiki](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status)
- Firefox: Windows from 141. Apple Silicon Mac from 145 on macOS 26, and from 147 on all macOS versions. Intel Mac and Linux are enabled only in Nightly ("Mozilla expects to ship on Linux in 2026"). Android is behind a flag (`gfx.webgpu.ignore-blocklist` in Beta/Nightly). — [gpuweb Implementation Status wiki](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status); [Mozilla gfx blog, Firefox 141](https://mozillagfx.wordpress.com/2025/07/15/shipping-webgpu-on-windows-in-firefox-141/)
- Safari: WebGPU is supported and on by default in macOS Tahoe 26, iOS 26, iPadOS 26 and visionOS 26. — [gpuweb Implementation Status wiki](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status); [web.dev "WebGPU is now supported in major browsers"](https://web.dev/blog/webgpu-supported-major-browsers) (via search snippet)
- caniuse data (Nov 2026): Chrome "y" from 113, with a note that "support on Linux depends on hardware and drivers". Firefox 163 is still "partial" ("only enabled by default on Windows as well as macOS 26 Tahoe or later on Apple Silicon"). iOS Safari "y" from 26.0. Samsung Internet "y" from 24. Firefox for Android "n". — [caniuse webgpu.json](https://github.com/Fyrd/caniuse/blob/main/features-json/webgpu.json) / [caniuse.com/webgpu](https://caniuse.com/webgpu)
- Some press coverage claims WebGPU works "across Windows, Mac, and Android" in every major browser. This is contradicted by the per-platform tables above. — [TechSpot](https://www.techspot.com/news/110456-webgpu-now-brings-desktop-quality-graphics-all-major.html) vs [gpuweb wiki](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status)

**Getting video frames onto the GPU**
- WebGPU has `GPUDevice.importExternalTexture()`, which wraps an `HTMLVideoElement` as an opaque external texture. — [Chrome "What's New in WebGPU 113"](https://developer.chrome.com/blog/new-in-webgpu-113) (via search snippet)
- Chrome 116 added WebCodecs `VideoFrame` as a source for `importExternalTexture()`. The Blink intent says the design allows "zero-copy sampling of YUV frame data", but this is a design goal, not a measured guarantee. At ship time it covered only ChromeOS, macOS and Windows. — [Chrome "What's New in WebGPU 116"](https://developer.chrome.com/blog/new-in-webgpu-116) (via search snippet); [Blink intent-to-ship](https://groups.google.com/a/chromium.org/g/blink-dev/c/QLCfazM8XLQ)
- Side effect: calling `importExternalTexture()` on a video element stops the browser from throttling that video when it is off-screen. — [Blink intent-to-ship](https://groups.google.com/a/chromium.org/g/blink-dev/c/QLCfazM8XLQ) (via search snippet)
- MDN browser-compat-data for `GPUDevice.importExternalTexture`: Chrome Android 121, Safari 26, Firefox 144 (partial), Firefox Android none. The desktop Chrome entry reads "144", which does not match the 113 blog. It probably tracks a later spec change; treat it as unverified. — [MDN BCD GPUDevice.json](https://github.com/mdn/browser-compat-data/blob/main/api/GPUDevice.json)
- `requestVideoFrameCallback()` (rVFC) fires once per newly presented video frame and supplies frame metadata (mediaTime, presentedFrames). Support: Chrome/Edge 83, Safari 15.4 (including iOS), Firefox 132 (2024-10-29). It is now in all engines. — [web-features explorer](https://web-platform-dx.github.io/web-features-explorer/features/request-video-frame-callback); [web.dev rVFC article](https://web.dev/articles/requestvideoframecallback-rvfc) (via search snippet); [MDN BCD HTMLVideoElement.json](https://github.com/mdn/browser-compat-data/blob/main/api/HTMLVideoElement.json)
- WebCodecs (`VideoDecoder`/`VideoFrame`, frame-accurate decoding): Chrome 94+, Firefox 130+, Safari 16.4+ (caniuse notes "video-only" partial support for some versions). Not available in Firefox for Android. — [caniuse webcodecs.json](https://github.com/Fyrd/caniuse/blob/main/features-json/webcodecs.json)
- Chrome's official WebGPU sample "Video Uploading with WebCodecs" lets you switch between `requestAnimationFrame` and `requestVideoFrameCallback` as the frame driver. It is a good starting point to copy. — [copy of the webgpu-samples "videoUploadingWebCodecs" source on diffchecker](https://www.diffchecker.com/FUiV227s/) (via search snippet; the official repo is github.com/webgpu/webgpu-samples, not fetched)

**Performance**
- Google Meet's production in-browser background effects use WebGL2 for mask refinement and compositing. Inference ran in WASM/XNNPACK on the CPU "for low power consumption and widest device coverage", on a downsampled input. — [Google Research blog: Background Features in Google Meet](https://research.google/blog/background-features-in-google-meet-powered-by-web-ml/) (via search snippet)

### Inferences
- For "video + mask + restyled plate + threshold/line/portal", one full-screen fragment shader samples 3–4 textures. That costs nothing on any GPU from the last decade, so the bottleneck is frame upload and ML inference, not the shader. WebGL2 `texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, videoEl)` per frame, driven by rVFC, is the pragmatic path and works in all four engines plus iOS.
- three.js (latest `three@0.187.0`, MIT, 2026-10-30, per [npm](https://www.npmjs.com/package/three)) gives `VideoTexture`, a choice of WebGL or WebGPU renderer, and easy splat integration (section 5). It is a good default if the team wants 3D later. Raw WebGL2 or regl is fine for a pure 2D compositor.
- Pre-recorded "Cross the Line" playback: precompute the person masks offline and ship them in the same video file (for example, RGB on top and mask in the bottom half, or the mask in a spare channel). One `<video>` then keeps color and mask frame-locked, with no ML in the browser. This sidesteps alpha-video codec differences between browsers and needs no WebGPU.

### Gaps
- No published side-by-side benchmark (ms per frame) of WebGL2 `texImage2D(video)` vs WebGPU `importExternalTexture` vs `copyExternalImageToTexture` for 1080p video on laptops or phones. Measure in the target browsers.
- The current Chrome Android device coverage beyond the gpuweb table (for example, the share of Android phones with WebGPU) was not found.

## 2. In-browser person segmentation (MediaPipe Tasks, TF.js, ONNX Runtime Web, transformers.js)

### Takeaway
For a live webcam "magic mirror", MediaPipe Tasks Vision's Image Segmenter with the Selfie Segmenter model is the default choice: about 250 KB, Apache-2.0, with a WebGL2 GPU delegate, built for real-time video. MODNet through transformers.js or ONNX Runtime Web on WebGPU gives softer, higher-quality mattes at a higher cost (6–26 MB). RMBG/BiRefNet-class models are too heavy for per-frame use. TF.js BodyPix and the legacy `@mediapipe/selfie_segmentation` package are deprecated or stale.

### Cited Findings
**MediaPipe Tasks Vision (recommended)**
- Package `@mediapipe/tasks-vision` latest is 1.2.3 (published 2026-11-11), Apache-2.0. — [npm registry](https://www.npmjs.com/package/@mediapipe/tasks-vision)
- Image Segmenter models:
  - SelfieSegmenter square (256×256, float16)
  - SelfieSegmenter landscape (144×256, float16; "may be more efficient" for always-landscape input such as video calls)
  - HairSegmenter
  - SelfieMulticlass 256×256 (classes such as hair, body skin, face skin, clothes)
  - DeepLab-v3

  — [MediaPipe Image Segmenter guide](https://ai.google.dev/edge/mediapipe/solutions/vision/image_segmenter) (via search snippet)
- Model file sizes, from the official model URLs' Content-Length:
  - `selfie_segmenter.tflite` (float16): 249,537 B, about 0.25 MB — [model URL](https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite)
  - `selfie_segmenter_landscape.tflite`: 250,177 B — [model URL](https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter_landscape/float16/latest/selfie_segmenter_landscape.tflite)
  - `selfie_multiclass_256x256.tflite` (float32): 16,371,837 B, about 16 MB — [model URL](https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite)
  - `deeplab_v3.tflite`: 2,780,176 B — [model URL](https://storage.googleapis.com/mediapipe-models/image_segmenter/deeplab_v3/float32/latest/deeplab_v3.tflite)
- Official latency table (native Pixel 6, not browser):

  | Model | CPU | GPU |
  |---|---|---|
  | SelfieSegmenter square | 33.46 ms | 35.15 ms |
  | SelfieSegmenter landscape | 34.19 ms | 33.55 ms |
  | SelfieMulticlass | 217.76 ms | 71.24 ms |

  The snippet's column labels were partly ambiguous. — [MediaPipe Image Segmenter guide](https://ai.google.dev/edge/mediapipe/solutions/vision/image_segmenter) (via search snippet)
- In the browser, MediaPipe Tasks' `delegate` accepts only "CPU" or "GPU", and the GPU path runs on WebGL2, not WebGPU. Per this source, WebGPU belongs in your own compositor. It is a vendor blog, so treat it with caution. — [Fora Soft article](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/mediapipe-selfie-segmentation-webgpu-background-blur)
- Historical web numbers from the related Meet model (2020 stack: WASM inference, WebGL2 rendering):
  - MacBook Pro 2018, 256×144 model: 120 FPS inference, 70 FPS end-to-end
  - Acer Chromebook 11, 160×96 model: 62 FPS inference, 33 FPS end-to-end

  — [Google Research: Background Features in Google Meet](https://research.google/blog/background-features-in-google-meet-powered-by-web-ml/) (via search snippet)
- Running modes are IMAGE, VIDEO and LIVE_STREAM. Outputs are a category mask and/or per-class confidence masks. (Standard MediaPipe Tasks API; from the guide via search snippet.) — [MediaPipe Image Segmenter guide](https://ai.google.dev/edge/mediapipe/solutions/vision/image_segmenter)

**Deprecated or stale options**
- `@tensorflow-models/body-pix` is deprecated in favor of `@tensorflow-models/body-segmentation`. — [npm body-pix](https://www.npmjs.com/package/@tensorflow-models/body-pix)
- `@tensorflow-models/body-segmentation` latest is 1.0.2, last published 2023-07-31, Apache-2.0. It wraps MediaPipe SelfieSegmentation (`general`/`landscape`) with either a MediaPipe or a TF.js runtime. — [npm registry](https://www.npmjs.com/package/@tensorflow-models/body-segmentation); [TF blog 2022](https://blog.tensorflow.org/2022/01/body-segmentation.html)
- The legacy MediaPipe Solutions package `@mediapipe/selfie_segmentation` was last published 2023-02-03 (0.1.1675465747). — [npm registry](https://www.npmjs.com/package/@mediapipe/selfie_segmentation)

**ONNX Runtime Web / transformers.js (WebGPU)**
- `onnxruntime-web` latest is 1.31.1 (2026-10-26, MIT). — [npm registry](https://www.npmjs.com/package/onnxruntime-web)
- The WebGPU execution provider has been stable since ORT Web 1.17. img.ly reports about 20× speedup over multi-threaded CPU for background removal, and WebGPU fp16 session start around 200 ms vs about 320 ms for WASM fp16. — [img.ly blog](https://img.ly/blog/browser-background-removal-using-onnx-runtime-webgpu/)
- `@huggingface/transformers` latest is 4.3.2 (2026-10-27, Apache-2.0); `next` is 4.4.0-next.0. — [npm registry](https://www.npmjs.com/package/@huggingface/transformers)
- The v4 preview was announced 2026-02-09 with a new C++ WebGPU runtime co-developed with the ONNX Runtime team. — [Hugging Face blog: Transformers.js v4](https://huggingface.co/blog/transformersjs-v4)
- A roughly 4× speedup on BERT embeddings for v4 is reported by secondary coverage only. A "10–50×" claim found elsewhere is unverified. — [Groundy](https://groundy.com/articles/transformers-js-v4-moves-transformer-inference-into-the-browser/); [n1n blog](https://n1n-blog.pages.dev/blog/transformers-js-v4-preview-npm-release-2026-02-10)
- MODNet (portrait matting, Apache-2.0) ONNX sizes: fp32 25.9 MB, fp16 13.0 MB, q4f16 11.8 MB, uint8/quantized 6.6 MB. — [Hugging Face Xenova/modnet](https://huggingface.co/Xenova/modnet)
- Xenova's live demo "webgpu-video-background-removal" loads `Xenova/modnet` with `{device: "webgpu", dtype: "fp32"}` and a default input of `shortest_edge: 256`, adjustable with a slider. Last updated 2024-03-13. — [HF Space Xenova/webgpu-video-background-removal](https://huggingface.co/spaces/Xenova/webgpu-video-background-removal) (bundle inspected)
- Heavier options:
  - RMBG-1.4 ONNX is 176 MB fp32 / 88 MB fp16 / 44 MB quantized, under a non-standard license ("other": BRIA's model license) — [briaai/RMBG-1.4](https://huggingface.co/briaai/RMBG-1.4)
  - RMBG-2.0 fp16 is about 490 MB — [RMBG-2.0-WebGPU](https://huggingface.co/yamura4/RMBG-2.0-WebGPU)
  - The Xenova "remove-background-webgpu" Space uses RMBG-1.4 for single images — [HF Space](https://huggingface.co/spaces/Xenova/remove-background-webgpu)

### Inferences
- Webcam mirror: MediaPipe Selfie Segmenter (landscape) in VIDEO mode, GPU delegate. Read back the confidence mask (or keep it on the GPU as a WebGL texture) and feed it to the compositing shader, with temporal smoothing (exponential moving average of the mask) and edge feathering in the shader. Expect real-time (≥30 fps) on recent laptops. On phones, budget about 33 ms per frame for the model alone, based on the Pixel 6 native numbers.
- If edge quality matters more than FPS (hair, a cleaner silhouette on a stylized plate), try MODNet at 256 px with fp16 on WebGPU, with a fallback to MediaPipe when `navigator.gpu` is absent (Firefox Linux/Android, older iOS).
- For the pre-recorded tripod clips, masks from the existing offline pipeline (probably higher quality than any browser model) should simply be baked into the shipped video (section 1).

### Gaps
- No authoritative 2025–2026 browser FPS benchmarks for MediaPipe Tasks Image Segmenter or for MODNet on WebGPU on specific phones and laptops. The team should log `performance.now()` around `segmentForVideo` calls.
- The license of the MediaPipe Selfie Segmenter model file itself (the model card) was not verified. The npm package is Apache-2.0.

## 3. In-browser monocular depth (Depth Anything V2)

### Takeaway
Depth Anything V2 Small runs in the browser through transformers.js on WebGPU. Xenova's official demo is "real-time". Reported throughput is roughly 8–25 fps depending on input size, precision and GPU, and about 1 fps without WebGPU. Only the Small model is Apache-2.0; Base and Large are CC-BY-NC-4.0. For the fixed tripod scene, compute depth once (offline or at load time). Run live depth only if the webcam "depth threshold" variant really needs it.

### Cited Findings
- Model files for `onnx-community/depth-anything-v2-small`: fp32 99.1 MB, fp16 49.6 MB, int8/uint8/quantized 27.3 MB, q4 27.4 MB, bnb4 26.1 MB, q4f16 19.1 MB. — [Hugging Face onnx-community/depth-anything-v2-small](https://huggingface.co/onnx-community/depth-anything-v2-small) (HF API file listing)
- Licenses: Depth-Anything-V2-Small is apache-2.0; Depth-Anything-V2-Base is cc-by-nc-4.0 (Large/Giant are also CC-BY-NC-4.0 per the repo). — [HF depth-anything/Depth-Anything-V2-Small-hf](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf); [HF Depth-Anything-V2-Base-hf](https://huggingface.co/depth-anything/Depth-Anything-V2-Base-hf); [GitHub DepthAnything/Depth-Anything-V2](https://github.com/DepthAnything/Depth-Anything-V2)
- Xenova's "WebGPU Real-time Depth Estimation" Space (created 2024-06-14) loads `onnx-community/depth-anything-v2-small` with `device: "webgpu"` and `dtype` set to fp16 when the GPU supports shader-f16, otherwise fp32. It resizes input to 504×504 by default, with a slider to change it. It runs on webcam video into a canvas. — [HF Space Xenova/webgpu-realtime-depth-estimation](https://huggingface.co/spaces/Xenova/webgpu-realtime-depth-estimation) (bundle inspected)
- Launch claim: "real-time depth estimation directly in your browser with Transformers.js and WebGPU… smallest model is only ~50MB (@ fp16)". — [Xenova on X, June 2024](https://x.com/xenovacom/status/1801672335830798654)
- One project write-up (transformers.js, WebGPU, q4f16) reports 8 fps at 392 px, 16 fps at 504 px and 24 fps at 518 px. The faster modes interpolate between depth samples, so these are not raw per-frame inference rates. — [DEV Community: Video Depth Estimation in the Browser](https://dev.to/martindelophy/video-depth-estimation-in-the-browser-building-with-webgpu-and-depth-anything-v2-4o0m)
- "Depth Twin, an on-device volumetric mirror" (open-source PR) expects about 18 fps with a person in frame on WebGPU, and about 1 fps without WebGPU. That is an author's expectation, not a benchmark. — [GitHub allansli/depth-twin PR #1](https://github.com/allansli/depth-twin/pull/1)
- Native upper bound: DAv2-Small runs at 72 FPS natively in the Online Video Depth Anything paper (not a browser figure). That paper also addresses temporal consistency, which per-frame DAv2 lacks. — [arXiv 2510.09182](https://arxiv.org/html/2510.09182v1)

### Inferences
- Per-frame DAv2 depth flickers. For a live "depth threshold" crossing effect, smooth temporally (EMA on depth, or on the thresholded mask) and combine with the segmentation mask (depth only decides near vs far for pixels that are "person"). A threshold on raw depth alone will be noisy at the boundary.
- Cheaper alternative for "crossing a depth plane" with a webcam: use MediaPipe Pose or Face landmarks (z, or apparent shoulder width) as a per-person depth proxy, and switch that person's whole mask between worlds. This avoids a 20–50 MB depth model. This is a design suggestion and has not been benchmarked.
- Run depth at a lower cadence than segmentation (for example, every 2nd–4th frame, in a Web Worker) to keep the compositor at display rate.

### Gaps
- No standardized benchmark of DAv2-Small on WebGPU on phones (iPhone with iOS 26 WebGPU, Android Chrome) was found.
- Whether transformers.js v4's new WebGPU runtime speeds up DAv2 specifically is not documented.

## 4. Webcam capture, background plate and background subtraction in shaders; secure context; locking exposure/white balance

### Takeaway
`getUserMedia` needs a secure context. Serve from `http://localhost` during development and from HTTPS (GitHub Pages, Netlify, Vercel) for the demo. Do not rely on `file://`. Manual exposure and white-balance locking through `applyConstraints` works only in Chromium (and only on cameras and drivers that expose it), so a pure "median background plus difference threshold" in a shader should be backed by a segmentation mask for robustness.

### Cited Findings
- MDN: `getUserMedia()` is available only in secure contexts (HTTPS, `file:///`, or localhost). Over plain HTTP, `navigator.mediaDevices` is undefined. — [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- In practice `file://` is unreliable. A WebKit bug report says getUserMedia "is also not available with the file:/// protocol". Older Firefox reports showed errors from file:// pages. — [WebKit bug 173457](https://bugs.webkit.org/show_bug.cgi?id=173457); [Mozilla bug 1379511](https://bugzilla.mozilla.org/show_bug.cgi?id=1379511)
- Chrome has exposed `getUserMedia`/`enumerateDevices` only on secure origins since M74, and treats `http://localhost` as secure. — [discuss-webrtc PSA](https://groups.google.com/g/discuss-webrtc/c/QUdwwa-83K8)
- `exposureMode` and `whiteBalanceMode` accept "none" | "manual" | "single-shot" | "continuous" (Image Capture extensions to MediaTrackConstraints). Missing properties mean either the browser or the device does not support them. — [MDN MediaTrackConstraints](https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints)
- Recommended pattern: check `navigator.mediaDevices.getSupportedConstraints()` then `track.getCapabilities()`. Set `exposureMode: 'manual'` first, then `exposureTime`, because exposureTime is ignored until the mode switch completes. As of May 2022, manual exposure worked in Chrome on Windows, Linux and Android, "depending on OS, browser, camera and driver". — [webrtcHacks (May 2022)](https://webrtchacks.com/?p=3807)
- Setting `colorTemperature` switches `whiteBalanceMode` to manual, and one user could not switch it back to continuous (single report). — [discuss-webrtc thread](https://groups.google.com/g/discuss-webrtc/c/HxlubhsoKEo)
- Image Capture API support: Chrome 59+, Safari 18.4+, Firefox only behind `dom.imagecapture.enabled`. This covers the ImageCapture object; per-constraint support for exposure and white balance on Safari is not listed. — [MDN BCD ImageCapture.json](https://github.com/mdn/browser-compat-data/blob/main/api/ImageCapture.json)
- Meet-style pipelines downsample the camera frame for the model and do mask refinement and compositing in WebGL2. — [Google Research Meet blog](https://research.google/blog/background-features-in-google-meet-powered-by-web-ml/) (via search snippet)

### Inferences
- Webcam version of "median background":
  1. Ask the viewer to step out for about 2 s.
  2. Grab N frames (for example, 30) into a texture array or a CPU buffer.
  3. Compute a per-pixel median (JS on a 640×360 frame is fine) or a running mean or min-variance plate in a ping-pong framebuffer.
  4. Send that plate once to the restyle step. Because there is no backend, "restyle" must be a pre-made plate, a client-side style shader (posterize/toon, palette LUT, Kuwahara, edge-ink) or an in-browser image model (not covered here).
- Fragment shader: `fg = max(segMask, smoothstep(t0, t1, length(cam - bgPlate)))`, with morphological cleanup by a small blur plus threshold. Under auto exposure the difference term drifts, so weight the segmentation mask more on non-Chromium browsers, or normalize brightness by matching global mean and std of the live frame to the plate.
- Pin a resolution with `{video: {width: {ideal: 1280}, height: {ideal: 720}, frameRate: {ideal: 30}, facingMode: 'user'}}`. Mirror horizontally for the "magic mirror" feel.

### Gaps
- No current (2025–2026) cross-browser table for exposure/white-balance constraints was found, and Safari 18.4+ per-constraint behavior is unverified. Test `getCapabilities()` on the actual demo laptop and webcam.

## 5. Real-time 2.5D effects: depth parallax, head-coupled "window", Gaussian splats plus video people

### Takeaway
Depth-map parallax ("3D photo") and head-tracked "window" parallax are cheap in WebGL. Several open-source browser demos exist (MediaPipe Face Landmarker plus three.js off-axis camera). Gaussian-splat viewers are mature: Spark 2.4 (World Labs, MIT, three.js, WebGL2, runs on mobile), three.js's native WebGPU splat renderer (r186+), PlayCanvas/SuperSplat and older gsplat.js and GaussianSplats3D. A static scene splat plus a video-textured, alpha-masked person billboard inside the same three.js scene is plausible, because Spark composites splats with normal meshes. Live webcam-to-splat of people is still research.

### Cited Findings
**Gaussian splat renderers**
- Spark (`@sparkjsdev/spark`) latest is 2.4.0 (2026-10-20), MIT, built by World Labs. Per its README it:
  - integrates with the three.js pipeline "to fuse splat and mesh-based objects"
  - targets "98%+ WebGL2 support" and "renders fast even on low-powered mobile devices"
  - reads PLY (including compressed), SPZ, SPLAT, KSPLAT and SOG
  - supports dynamic per-splat editing and animation and multiple viewpoints

  — [npm @sparkjsdev/spark README](https://www.npmjs.com/package/@sparkjsdev/spark); [sparkjs.dev](https://sparkjs.dev/)
- Spark usage: splats are `SplatMesh` objects rendered by the normal `renderer.render(scene, camera)`. The docs recommend `antialias: false` on `WebGLRenderer`. Spark 2.0 added paged/streamed LoD (.RAD chunks). — [Spark docs overview](https://sparkjs.dev/docs/overview/) (via search snippet); [Radiance Fields: Spark v2.3.0](https://radiancefields.com/spark-v2.3.0-fixes-on-demand-rendering-for-paged-lod)
- Spark Radix 0.0.1 is an experimental WebGPU splat renderer for three.js with GPU sorting and a single draw call. — [Radiance Fields: Spark Radix](https://radiancefields.com/spark-radix-brings-webgpu-splat-rendering-to-threejs)
- three.js merged a native WebGPU/TSL Gaussian splat renderer in r186, with GPU counting sort and loaders for PLY, SPZ, KSPLAT and glTF `KHR_gaussian_splatting`. Current `three` is 0.187.0. — [Radiance Fields: three.js r186](https://radiancefields.com/three.js-merges-a-native-gaussian-splat-renderer-for-webgpu-in-r186); [npm three](https://www.npmjs.com/package/three)
- Older or alternative viewers:
  - `gsplat` (Hugging Face gsplat.js) 1.2.9, last published 2025-07-12, MIT — [npm gsplat](https://www.npmjs.com/package/gsplat); [GitHub huggingface/gsplat.js](https://github.com/huggingface/gsplat.js/)
  - `@mkkellogg/gaussian-splats-3d` 0.4.7, last published 2025-01-25, MIT — [npm](https://www.npmjs.com/package/@mkkellogg/gaussian-splats-3d); [GitHub mkkellogg/GaussianSplats3D](https://github.com/mkkellogg/GaussianSplats3D)
  - antimatter15/splat: the original lightweight WebGL viewer that defined the `.splat` format — [GitHub antimatter15/splat](https://github.com/antimatter15/splat)
  - PlayCanvas engine 2.24.2 (2026-11-18) and `@playcanvas/supersplat-viewer` 1.43.3 (2026-11-17), both MIT and actively released — [npm playcanvas](https://www.npmjs.com/package/playcanvas); [npm supersplat-viewer](https://www.npmjs.com/package/@playcanvas/supersplat-viewer)
- Splat plus head-tracked perspective ("pseudo-holographic display") has been prototyped in PlayCanvas. — [PlayCanvas forum PoC](https://forum.playcanvas.com/t/proof-of-concept-3dgs-scene-head-tracked-perspective-pseudo-holographic-display/42098)
- Live webcam to Gaussian splats of a person (VoluMe, ICCV 2025) predicts 3D Gaussians in real time from a single 2D webcam feed. It is a research model, not a browser library. — [arXiv VoluMe](https://arxiv.org/html/2507.21311v1); [ICCV 2025 paper](https://openaccess.thecvf.com/content/ICCV2025/papers/de_La_Gorce_VoluMe_-_Authentic_3D_Video_Calls_from_Live_Gaussian_Splat_ICCV_2025_paper.pdf)

**Head-coupled and depth parallax**
- IvRogoz/Portal: Vite + TypeScript + MediaPipe Face Landmarker. Webcam head pose drives a three.js camera for a "virtual window/parallax" effect. — [GitHub IvRogoz/Portal](https://github.com/IvRogoz/Portal)
- vivien000/trompeloeil: TF.js face landmarks plus three.js. Only one viewer can see the effect correctly. — [GitHub vivien000/trompeloeil](https://github.com/vivien000/trompeloeil); [blog post](https://vivien000.github.io/blog/journal/motion-parallax-with-face-tracking.html)
- Charlie Gerard's head-tracked digital frame (three.js + TF.js MoveNet): the effect comes from changing the camera's projection matrix (off-axis). — [DEV Community](https://dev.to/devdevcharlie/making-an-interactive-digital-frame-with-head-tracking-using-three-js-and-tensorflow-js-5dfo)
- headtrackr (older) uses `camera.setViewOffset` in three.js for the off-axis view. Field-of-view estimation and lighting strongly affect quality. — [GitHub auduno/headtrackr](https://github.com/auduno/headtrackr); [Opera dev article](https://dev.opera.com/articles/view/head-tracking-with-webrtc/)
- `parallax-effect` npm: TF.js face tracking on the WASM/CPU backend, "so your GPU will be free", with a mouse fallback. — [npm parallax-effect](https://npmjs.com/package/parallax-effect)
- DepthFlow is an open-source depth-map parallax animator whose core is a GLSL shader. It uses Depth Anything depth maps and is AGPL-3.0. It is Python/Gradio, not client-side WebGL, but the shader logic is portable. — [GitHub BrokenSource/DepthFlow](https://github.com/BrokenSource/DepthFlow); [PyPI depthflow](https://pypi.org/project/depthflow/0.7.1)

### Inferences
- The cheapest 2.5D upgrade that fits the project: take the restyled plate plus its depth map (DAv2 offline) and render a 3D-photo parallax, either as a displaced grid mesh or as a ray-marched fragment shader like DepthFlow. Drive the virtual camera from the mouse, gyro (`DeviceOrientationEvent`; iOS needs a permission prompt) or MediaPipe face position. Composite the masked person video as a plane at their estimated depth. A team can do this in days.
- Splat version: capture the tripod scene as a splat (Polycam/Luma/Postshot/SuperSplat-made `.spz`/`.ply`) or generate a "world" splat. Render with Spark. Add the person as a three.js plane with a `VideoTexture` and mask (alpha test or premultiplied alpha) at the depth where they stand. Hold the camera near the original tripod pose so the 2D person billboard is not obviously flat. Plausible in 1–2 weeks. The risk is making the restyled world into a splat: per-view SD restyles are not multi-view consistent, so restyle the splat (Spark's color editing or shader graph) or use a single-image-to-world generator.

### Gaps
- No published example composites a live, segmented webcam person into a Spark or three.js splat scene. Feasibility is inferred from Spark's "fuse splat and mesh" design.
- Spark's FPS on specific phones was not quantified in the sources.

## 6. Web Audio for ambient or synthesized sound and audio-reactive visuals

### Takeaway
Web Audio is universally available. Tone.js (MIT) is the easy layer for ambient drones and crossfades between "worlds". `AnalyserNode` (or Meyda) gives FFT and loudness for audio-reactive shader uniforms. The one hard rule is that an `AudioContext` must be created or resumed inside a user gesture, especially on iOS.

### Cited Findings
- Browsers keep a new `AudioContext` suspended until a user gesture. Create or resume it in a click handler. — [MDN Web Audio API best practices](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices)
- iOS requires a user gesture for AudioContext even with no audible output. Developers report iOS problems even inside gesture handlers. — [WebKit bug 180522](https://bugs.webkit.org/show_bug.cgi?id=180522); [CodinGame forum](https://forum.codingame.com/t/struggling-with-a-web-audio-api-issue-on-ios-browsers/96057)
- `AnalyserNode`: `frequencyBinCount = fftSize/2`, and `getByteFrequencyData` fills a `Uint8Array` with 0–255 per bin. This is the standard source for visualizer uniforms. — [MDN Web Audio best practices](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices) (via search summary); [intro-web-tech tutorial](https://intro-web-tech.pages.dev/media/audio-video/tutorials/08_web-audio-api.html)
- Tone.js `tone` latest stable is 15.1.22 (2025-04-27), MIT; the `next` tag is 15.5.72. Tone apps call `await Tone.start()` after a user gesture, and `Tone.context.rawContext` shares the context with other code. — [npm tone](https://www.npmjs.com/package/tone); [web audio overview](https://www.youngju.dev/blog/culture/2026-05-16-web-audio-api-browser-audio-2026-audioworklet-tone-js-howler-wavesurfer-peaks-meyda-faust-csound-web-speech-deep-dive.en)
- Meyda (audio feature extraction: RMS, spectral centroid and similar) is 5.6.3, MIT. — [npm meyda](https://www.npmjs.com/package/meyda)
- AudioWorklet is described as available in all major browsers in 2026 (secondary source). Load it with `audioWorklet.addModule()` before creating nodes. — [youngju.dev overview](https://www.youngju.dev/blog/culture/2026-05-16-web-audio-api-browser-audio-2026-audioworklet-tone-js-howler-wavesurfer-peaks-meyda-faust-csound-web-speech-deep-dive.en)

### Inferences
- Map "how much of the frame is in the other world" (the fraction of mask pixels past the line, computed cheaply on a downsampled mask) to a crossfade between two ambient beds: real-world room tone vs a generated-world pad (Tone.js `CrossFade`). Trigger a "whoosh" or filter sweep when a person's centroid crosses the line. Feed RMS from the microphone or ambient track into a shader uniform (for example, portal edge shimmer). All of this is client-side and takes 1–2 days.
- Use a "Tap to enter" start screen that starts both `getUserMedia` and `Tone.start()` in one gesture. This handles camera permission and audio unlock together on iOS.

### Gaps
- No primary-source compatibility table for AudioWorklet was fetched (the claim above is from a secondary 2026 overview).

## 7. Phone and AR options: WebXR camera access, 8th Wall status, Snap Camera Kit, plain mobile web

### Takeaway
The most reliable phone path is a plain mobile web page (HTTPS, `getUserMedia` with `facingMode`, MediaPipe, WebGL2), which works on iOS Safari and Android Chrome. WebXR AR (`immersive-ar`) works only on Android Chrome (ARCore). iOS Safari has no WebXR at all, and visionOS has VR only. WebXR Raw Camera Access shipped in Chrome 107 but is effectively Android-only. 8th Wall's hosted platform shut down on 2026-02-28 and became an open-source/self-hosted engine; existing hosted projects stay live until 2027-02-28. Snap Camera Kit Web is a free alternative but ties you to Lens Studio and Snap's infrastructure.

### Cited Findings
**WebXR**
- caniuse WebXR Device API: Chrome/Edge 79+ (partial: "very extensive… many features still in development"). Firefox only behind a flag. Safari desktop behind an experimental flag. iOS Safari "n" through 27.2. Samsung Internet 12+. — [caniuse webxr.json](https://github.com/Fyrd/caniuse/blob/main/features-json/webxr.json)
- WebXR Raw Camera Access (`XRView.camera`, `XRWebGLBinding.getCameraImage`): Chrome 107+. Not in Firefox or Safari. It requires WebGL to read camera pixels. — [MDN BCD XRView.json](https://github.com/mdn/browser-compat-data/blob/main/api/XRView.json); [Blink Intent to Ship](https://groups.google.com/a/chromium.org/g/blink-dev/c/LoCH4tthbsI)
- Meta Quest Browser does not offer raw camera access (developers are requesting it). — [Meta community forum](https://communityforums.atmeta.com/discussions/Questions_Discussions/request-webxr-raw-camera-access-camera-access-feature-in-quest-browser/1367463)
- Chrome on Android XR lists these WebXR features: Device API, AR Module, Gamepads, Hit Test, Hand Input, Anchors, Depth Sensing and Light Estimation. Raw Camera Access is not listed. — [Android Developers: Develop for the web on Android XR](https://developer.android.com/develop/xr/web)
- visionOS 2 enabled WebXR by default, but VR only. The AR module is not supported on visionOS or iOS (Apple forum staff), and the Safari "AR module" toggle is non-functional. — [Road to VR](https://roadtovr.com/visionos-2-webxr-support-vision-pro/); [Apple Developer Forums](https://developer.apple.com/forums/thread/756850); [WebKit blog: Natural Input for WebXR](https://webkit.org/blog/15162/introducing-natural-input-for-webxr-in-apple-vision-pro/)

**8th Wall / Niantic**
- The hosted platform stopped accepting logins after 2026-02-28, and the project moved to open source at 8thwall.org. Hosted projects remain live until 2027-02-28, then hosting shuts down. — [8th Wall migration FAQ](https://www.8thwall.com/docs/migration/faq/); [8thwall.org FAQ](https://8thwall.org/docs/migration/faq); [Niantic Spatial blog](https://info.nianticspatial.com/blog/8th-wall-open-source) (via search snippet); [Road to VR](https://roadtovr.com/niantic-webar-platform-8th-wall-open-source/)
- Niantic Spatial services (VPS, Lightship Maps, Geospatial Browser) are not part of the open-source engine distribution. — [Niantic Spatial blog: engine distribution and open source plans](https://info.nianticspatial.com/blog/8th-wall-update-engine-distribution-and-open-source-plans) (via search snippet)
- npm `@8thwall/engine-binary` 1.0.0 was published 2026-04-03 under a custom license ("See LICENSE"). — [npm registry](https://www.npmjs.com/package/@8thwall/engine-binary)
- Niantic sold its games division to Scopely in 2025. The platform and geospatial tech moved to the spun-off Niantic Spatial. — [Skarred Ghost](https://skarredghost.com/2025/11/24/meta-hyperscape-8th-wall/); [VR/AR wiki: Niantic Lightship](https://vrarwiki.com/wiki/Niantic_Lightship)

**Snap Camera Kit (Web)**
- `@snap/camera-kit` latest is 1.23.1 (2026-11-10), under a proprietary license ("SEE LICENSE IN LICENSE.md"). — [npm registry](https://www.npmjs.com/package/@snap/camera-kit)
- Camera Kit runs Lens Studio–built Lenses inside your own web page from a webcam `MediaStream`. It downloads a WASM Lens engine from Snap's CDN, supports one active Lens at a time, and current docs list Chrome 95+ and Safari 16+. There is no SDK fee. — [Snap: Camera Kit](https://developers.snap.com/camera-kit); [Snap AR blog: Guide to WebAR with Camera Kit](https://ar.snap.com/blog/guide-web-ar-camera-kit); [Camera Kit web configuration](https://developers.snap.com/camera-kit/quick-start/integrate-sdk/integrate-sdk-web/web-configuration)
- Push-to-Web (sending Lenses from Lens Studio to a web page for testing) needs a Login Kit access token. — [npm @snap/push2web README](https://cdn.jsdelivr.net/npm/@snap/push2web@1.17.0/README.md)

### Inferences
- For 1–3 weeks with no backend, a responsive mobile web page beats WebXR. Use the rear camera (`facingMode: 'environment'`) for a "portal you hold up", or the front camera for a selfie mirror. Use the same MediaPipe and WebGL2 compositor. Use `DeviceOrientationEvent` (after an iOS permission prompt) to steer parallax. This reaches iPhone and Android alike.
- Use WebXR `immersive-ar` (Android Chrome only) only for a stretch "portal door anchored in the room" demo. three.js plus hit-test is enough. Raw camera access is needed only if the effect must restyle the passthrough itself.
- Avoid starting a new project on 8th Wall's sunsetting hosted platform. The open-source engine is possible but adds self-hosting work. Snap Camera Kit is attractive if the team wants Snap's built-in body segmentation, but it requires a Snap developer account and API token, and the custom compositing shader would have to be rebuilt as a Lens.

### Gaps
- Whether the open-sourced 8th Wall engine's license allows unrestricted student or public use was not verified (the npm license is "See LICENSE").
- No confirmation that Chrome for Android still exposes raw camera access on every ARCore device in 2026. MDN marks it as mirroring desktop Chrome 107.

## 8. Existing open-source demos close to "magic mirror into another world/time"

### Takeaway
No single open-source browser demo was found that does exactly "step across a line or depth and enter a restyled world". The building blocks all exist as open demos: real-time WebGPU depth and background removal Spaces, Meet-style virtual-background pipelines, head-tracked "window" demos and a WebGPU "volumetric mirror". A student team can fork two of these and wire them together.

### Cited Findings
- Xenova "WebGPU Real-time Depth Estimation" (DAv2-Small, webcam, transformers.js) — [HF Space](https://huggingface.co/spaces/Xenova/webgpu-realtime-depth-estimation)
- Xenova "WebGPU Video Background Removal" (MODNet, webcam, transformers.js) — [HF Space](https://huggingface.co/spaces/Xenova/webgpu-video-background-removal)
- Depth Twin, "an on-device volumetric mirror" (WebGPU depth; about 18 fps expected) — [GitHub allansli/depth-twin PR #1](https://github.com/allansli/depth-twin/pull/1)
- Volcomix/virtual-background: a browser virtual background comparing BodyPix and MediaPipe Meet models with a WebGL2 pipeline — [GitHub Volcomix/virtual-background](https://github.com/Volcomix/virtual-background) (listed via [awesome.ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2FVolcomix%2Fvirtual-background); contents not inspected)
- vpalmisano/virtual-background: a client-side webcam background replacement with WebGL, with a write-up on efficiency — [Medium write-up](https://medium.com/@vpalmisano/building-an-efficient-web-based-webcam-virtual-background-7d7cc4e6fa4f)
- gregblur: a WebGL2 blur pipeline on MediaPipe selfie segmentation models — [GitHub gregce/gregblur](https://github.com/gregce/gregblur)
- IvRogoz/Portal (MediaPipe Face Landmarker → three.js "virtual window") — [GitHub](https://github.com/IvRogoz/Portal); trompeloeil — [GitHub](https://github.com/vivien000/trompeloeil)
- deftio/mirrormirror: a pure HTML/JS webcam "infinity mirror" with no segmentation — [awesome.ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2Fdeftio%2Fmirrormirror)
- Neilblaze/Anyxz: real-time video background semantic segmentation in the browser — [GitHub](https://www.github.com/Neilblaze/Anyxz)
- Prior art for installations: SIGGRAPH "The AI-Powered Magic Mirror: Building Immersive AR/VR Experiences with Only Webcams and Deep Learning" — [ACM SIGGRAPH History Archive](https://history.siggraph.org/experience/the-ai-powered-magic-mirror-building-immersive-ar-vr-experiences-with-only-webcams-and-deep-learning-by-kruszewski-and-jan-mahamad)
- A Kurento "magic mirror" tutorial exists, but it is server-side media processing (needs a media server), so it does not fit the no-backend constraint. — [Kurento docs](https://doc-kurento.readthedocs.io/en/latest/tutorials/js/tutorial-magicmirror.html)

### Inferences
- Suggested minimum viable live demo (about 1 week), in three tiers:
  - Tier A (no ML): the existing static page upgraded to a WebGL2 shader that plays the tripod video, its baked mask channel and the restyled plate. Drag-line, depth-threshold or portal-circle uniforms are controlled by mouse or touch, with rVFC-driven updates.
  - Tier B (webcam magic mirror): capture an empty-room plate. MediaPipe Selfie Segmenter gives the mask. A shader composites the live person over the pre-restyled plate (or a stylized version made by a shader filter) on the far side of a line the user drags, or that follows the person's x-centroid. Add Tone.js crossfade audio.
  - Tier C (stretch): DAv2-Small depth threshold on WebGPU, head-coupled parallax of the restyled plate, or a Spark splat world with a person billboard.
- Feature-detect `navigator.gpu` and fall back to MediaPipe/WebGL2. Serve over HTTPS (GitHub Pages). Cache models through the browser cache (transformers.js does this automatically).

### Gaps
- No open-source demo was found that uses a generated (diffusion-restyled) plate as the "other world" behind a live segmented webcam person in the browser. This appears to be a genuine novelty niche for the project, though absence of evidence is not proof of absence.
- FPS numbers for the Volcomix and vpalmisano demos were not retrieved (pages not fetched).
