// Export: the result as a video file, every frame of the clip drawn exactly once.
//
// The clip is paused and stepped one frame at a time: seek to the frame, let the page analyse the people
// and draw (step), then hand the canvas to the encoder. Encoding is Mediabunny (MPL-2.0, vendored by
// fetch_vendor.sh) on the browser's WebCodecs: H.264 in MP4 where the browser can, VP9 in WebM otherwise.
// However slow the machine, no frame is dropped, because nothing here runs in real time.
const LIB = './vendor/mediabunny.min.mjs';

let mb = null;
export async function loadEncoder() {
  if (!mb) mb = await import(LIB);
  return mb;
}

// Show frame t (seconds) of a paused video: seek, then wait until that frame is ready to draw. Fails if the
// video is replaced or never finishes seeking, so the export cannot hang; an abort ends the wait at once.
async function seek(video, t, signal) {
  await new Promise((resolve, reject) => {
    const done = (fail) => () => {
      clearTimeout(timer);
      video.removeEventListener('seeked', ok); video.removeEventListener('emptied', gone);
      if (signal) signal.removeEventListener('abort', ok);
      if (fail) reject(new Error(fail)); else resolve();
    };
    const ok = done(null), gone = done('the video was replaced');
    const timer = setTimeout(done('the video stopped seeking'), 10000);
    video.addEventListener('seeked', ok); video.addEventListener('emptied', gone);
    if (signal) signal.addEventListener('abort', ok);
    video.currentTime = t;
  });
  // a hidden page draws nothing, so the frame callback would never come: 'seeked' is enough there
  if (!video.requestVideoFrameCallback || document.hidden) return;
  await new Promise((resolve) => {
    const id = video.requestVideoFrameCallback(() => { clearTimeout(timer); resolve(); });
    const timer = setTimeout(() => { video.cancelVideoFrameCallback(id); resolve(); }, 250);
  });
}

// Encode frames [start, end) seconds of `video` at `fps`. step(i, t) draws frame i (clip time t) on
// `canvas`; onProgress(fraction) reports; an aborted `signal` stops and returns null.
// Returns {blob, ext, frames}.
export async function exportVideo({ canvas, video, fps, start, end, step, onProgress, signal }) {
  const { Output, Mp4OutputFormat, WebMOutputFormat, BufferTarget, CanvasSource, QUALITY_HIGH, canEncodeVideo } =
    await loadEncoder();
  const size = { width: canvas.width, height: canvas.height };
  let codec = 'avc', ext = 'mp4', format = new Mp4OutputFormat({ fastStart: 'in-memory' });
  if (!(await canEncodeVideo('avc', size))) {
    if (!(await canEncodeVideo('vp9', size))) throw new Error('This browser cannot encode video (no WebCodecs).');
    codec = 'vp9'; ext = 'webm'; format = new WebMOutputFormat();
  }
  const output = new Output({ format, target: new BufferTarget() });
  const source = new CanvasSource(canvas, { codec, bitrate: QUALITY_HIGH });
  output.addVideoTrack(source, { frameRate: fps });
  await output.start();
  const frames = Math.max(1, Math.round((end - start) * fps));
  try {
    for (let i = 0; i < frames; i++) {
      // the middle of the frame's interval, so rounding never lands on its neighbour
      await seek(video, Math.min(start + (i + 0.5) / fps, video.duration - 0.001), signal);
      if (signal && signal.aborted) { await output.cancel(); return null; }
      step(i, i / fps);
      await source.add(i / fps, 1 / fps);
      if (onProgress) onProgress((i + 1) / frames);
    }
    await output.finalize();
  } catch (e) {
    await output.cancel().catch(() => {});
    throw e;
  }
  return { blob: new Blob([output.target.buffer], { type: `video/${ext}` }), ext, frames };
}

// A video file's frame rate, read from its frame timestamps (null if the file cannot be read).
export async function probeFps(blob) {
  try {
    const { Input, BlobSource, ALL_FORMATS } = await loadEncoder();
    const track = await new Input({ formats: ALL_FORMATS, source: new BlobSource(blob) }).getPrimaryVideoTrack();
    const fps = track && (await track.computeFrameRateMetrics()).bestGuessFrameRate;
    return fps > 0 && isFinite(fps) ? Math.min(60, fps) : null;
  } catch { return null; }
}

// Frame count, duration and size of an exported file (tests).
export async function probeVideo(blob) {
  const { Input, BlobSource, ALL_FORMATS } = await loadEncoder();
  const input = new Input({ formats: ALL_FORMATS, source: new BlobSource(blob) });
  const track = await input.getPrimaryVideoTrack();
  const stats = await track.computePacketStats();
  return { frames: stats.packetCount, seconds: await input.computeDuration(), width: track.displayWidth,
           height: track.displayHeight, codec: track.codec };
}

// Hand the file to the viewer: the artifact page's `downloads` capability where it exists, else a link.
// A framed page without the capability cannot download at all, so it says so instead of failing silently.
export async function saveFile(blob, filename) {
  const downloads = window.claude && window.claude.use ? await window.claude.use('downloads') : null;
  if (downloads) return (await downloads.save({ filename, data: blob })).status;
  if (window.self !== window.top) throw { code: 'unavailable', message: 'saving is not available in this view' };
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = filename;
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 60000);
  return 'saved';
}
