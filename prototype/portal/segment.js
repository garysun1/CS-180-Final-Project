// Live person masks in the browser: MediaPipe Tasks Vision, Selfie Segmenter, everything served locally.
import { FilesetResolver, ImageSegmenter } from './vendor/vision_bundle.mjs';

export async function createSegmenter(log) {
  const wasm = new URL('./vendor/wasm', import.meta.url).href;
  const model = new URL('./models/selfie_segmenter_landscape.tflite', import.meta.url).href;
  const fileset = await FilesetResolver.forVisionTasks(wasm);
  for (const delegate of ['GPU', 'CPU']) {
    try {
      const seg = await ImageSegmenter.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: model, delegate },
        runningMode: 'VIDEO',
        outputConfidenceMasks: true,
        outputCategoryMask: false,
      });
      log(`person segmenter ready (${delegate})`);
      return { seg, delegate };
    } catch (e) {
      log(`segmenter on ${delegate} failed: ${e && e.message ? e.message : e}`);
    }
  }
  throw new Error('Could not start the person segmenter.');
}

// Returns {data: Float32Array person confidence, w, h} or null. The person channel is the last mask
// (the selfie model has one channel; multi-class models put background first).
export function segmentFrame(seg, source, tMs) {
  let out = null;
  seg.segmentForVideo(source, tMs, (res) => {
    const masks = res.confidenceMasks;
    if (masks && masks.length) {
      const m = masks[masks.length - 1];
      out = { data: m.getAsFloat32Array().slice(), w: m.width, h: m.height, n: masks.length };
    }
  });
  return out;
}
