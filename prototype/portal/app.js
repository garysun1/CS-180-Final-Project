// Cross the Line — live portal kiosk. See README.md.
// The same code runs the local kiosk (index.html: camera, server, segmenter) and the hosted demo
// (artifact/page.html: recorded scenes with pre-made worlds), configured by window.PORTAL_CONFIG.
import { Compositor, IDENTITY_FIELD } from './compositor.js';
import { PlateCapture, fitColourField, toImageData } from './plate.js';
import { PortalAudio } from './audio.js';

const params = new URLSearchParams(location.search);
const CFG = Object.assign({
  camera: true, server: true, segmenter: true, muted: false, autostart: params.get('autostart') === '1',
  scenes: null, startScene: 0,
}, window.PORTAL_CONFIG || {});
const $ = (id) => document.getElementById(id);
const canvas = $('view');
// Shader rule indices; the buttons and the M key go through them in UI order (depth before whole).
const MODES = ['line', 'portal', 'lens', 'whole frame', 'depth'];
const UI_MODES = [0, 1, 2, 4, 3];
const SHADER_WORLDS = [
  { name: 'Night', kind: 1 }, { name: '1920s', kind: 2 }, { name: 'Winter', kind: 3 },
  { name: 'Comic', kind: 4 }, { name: 'Thermal', kind: 5 }, { name: 'Neon', kind: 6 },
];
// The Layers view: the pipeline, one layer per tile (shader views; 0 is the result).
const LAYERS = [
  { view: 1, name: 'Filmed', note: 'person mask, every frame' },
  { view: 2, name: 'Empty scene', note: 'median, captured once' },
  { view: 3, name: 'The world', note: 'one image, made once' },
  { view: 4, name: 'People', note: 'cut out every frame' },
  { view: 5, name: 'The rule', note: 'where the other world is' },
  { view: 0, name: 'Result', note: 'one equation per pixel' },
];
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

const S = {
  worlds: SHADER_WORLDS.map((w) => ({ ...w })), world: 0, mode: Math.max(0, MODES.indexOf(params.get('mode') || 'line')),
  mirror: params.get('mirror') !== '0', debug: params.get('debug') === '1', diff: true,
  glitchUntil: 0, autoGlitch: !REDUCED, autoCycle: false, lastCycle: 0, flash: 0, muted: !!CFG.muted,
  line: { x: 0.5, y: 0.5, angle: 0 }, portal: { x: 0.5, y: 0.78, r: 0.17 }, lens: { x: 0.5, y: 0.5, r: 0.2 },
  tau: 0.45, far: null,
  source: params.get('source') === 'clip' || !CFG.camera ? 'clip' : 'camera', video: null,
  plate: null, plateData: null, capture: null, gain: 1,
  mask: null, segMs: 0, delegate: '', fps: 0, frames: 0, lastFpsT: performance.now(),
  tracks: [], trackId: 0, burst: null, across: 0, crossings: 0, bursts: 0,
  server: false, job: null, loaded: new Set(), log: [],
  scenes: [], scene: -1, layers: false, layer: -1, wave: null, waveHold: null, dragged: false,
};
let comp, seg = null, segmentFrame = null, audio;
const work = document.createElement('canvas');
const wctx = work.getContext('2d', { willReadFrequently: true });

function log(msg) { S.log.push(msg); console.log('[portal]', msg); }
let toastTimer;
function toast(msg, ms = 2600) {
  const t = $('toast'); t.textContent = msg; t.classList.add('on');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('on'), ms);
}
function flash(v) { if (!REDUCED) S.flash = Math.max(S.flash, v); }
const smooth01 = (x) => { const t = Math.min(1, Math.max(0, x)); return t * t * (3 - 2 * t); };

// ------------------------------------------------------------------ sound (only once the browser allows it)
function aud() { return audio && audio.ctx.state === 'running' ? audio : null; }
async function ensureAudio() {
  try {
    if (!audio) audio = new PortalAudio();
    audio.setMuted(S.muted);
    if (!S.muted) { await audio.resume(); audio.setWorld(S.world); }
  } catch (e) { log(`audio: ${e}`); }
}
function audioOnFirstGesture() {
  const go = () => { removeEventListener('pointerdown', go); removeEventListener('keydown', go); ensureAudio(); };
  addEventListener('pointerdown', go); addEventListener('keydown', go);
}

// ------------------------------------------------------------------ sources
async function startCamera() {
  const v = $('cam');
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } }, audio: false });
  v.srcObject = stream;
  await v.play();
  return v;
}
async function startClip(src, startTime = 0) {
  const v = $('clip');
  if (src) {
    if (v.src.startsWith('blob:') && v.src !== src) URL.revokeObjectURL(v.src);
    v.src = src;
  } else if (!v.src) v.src = params.get('clip') || './clips/fallback.mp4';
  if (startTime) {                                 // seek before play(): the first analysed frame is the start
    if (v.readyState < 1) await new Promise((r) => v.addEventListener('loadedmetadata', r, { once: true }));
    const seeked = new Promise((r) => v.addEventListener('seeked', r, { once: true }));
    v.currentTime = startTime;
    await seeked;
  }
  await v.play();
  return v;
}
// opts.src: clip URL; opts.plate: a ready empty scene (ImageBitmap) instead of capturing one;
// opts.startTime: where the clip starts (seconds into the clip)
async function useSource(name, opts = {}) {
  try {
    S.video = name === 'camera' ? await startCamera() : await startClip(opts.src, opts.startTime);
    S.source = name;
  } catch (e) {
    if (name === 'camera') { toast('No camera available, using the recorded clip'); log(`camera: ${e}`); return useSource('clip'); }
    throw e;
  }
  const w = S.video.videoWidth, h = S.video.videoHeight;
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  work.width = w; work.height = h;
  S.mirror = name === 'camera' ? params.get('mirror') !== '0' : false;
  fitCanvas();
  S.plate = null; S.plateData = null; S.plateSmall = null; S.capture = null; S.gain = 1;
  S.tracks = []; S.mask = null; S.burst = null;
  scheduleSegmentation(true);
  if (opts.plate) setPlate(toImageData(opts.plate, w, h));
  else capturePlate(name === 'camera' ? 3 : 0);
}
function fitCanvas() {
  const st = $('stage').getBoundingClientRect();
  const s = Math.min(st.width / canvas.width, st.height / canvas.height);
  if (!(s > 0)) return;
  canvas.style.width = `${Math.floor(canvas.width * s)}px`;
  canvas.style.height = `${Math.floor(canvas.height * s)}px`;
}
new ResizeObserver(fitCanvas).observe($('stage'));

// ------------------------------------------------------------------ the empty scene
async function capturePlate(countdown = 3) {
  const c = $('count');
  for (let k = countdown; k > 0; k--) {
    c.hidden = false; c.innerHTML = `${k}<small>Capturing the empty scene</small>`;
    await new Promise((r) => setTimeout(r, 900));
  }
  c.hidden = false; c.innerHTML = '<small>Capturing the empty scene…</small>';
  S.capture = new PlateCapture(canvas.width, canvas.height, 30, 4);
}
function setPlate(image) {
  S.plateData = image;
  S.plateSmall = shrink(image, DW, Math.round(DW * canvas.height / canvas.width));
  comp.uploadImage(comp.tex.plate, image);
  S.plate = true;
  $('count').hidden = true;
  // worlds made on the spot are matched to this plate; worlds built offline keep their baked field
  for (const w of S.worlds) if (w.kind === 0 && w.img && !w.baked) setField(w, fitColourField(S.plateData, toImageData(w.img, canvas.width, canvas.height)));
}
function finishPlate() {
  const { image, neverEmpty } = S.capture.result();
  S.capture = null;
  setPlate(image);
  toast(neverEmpty > 0.05 ? `Empty scene captured (${Math.round(neverEmpty * 100)}% was never clear)` : 'Empty scene captured');
  lockExposure();
  if (S.server) sendPlate();
}
async function lockExposure() {
  // Keep the camera from re-exposing after the plate is taken (Chrome; driver-dependent).
  const track = S.video && S.video.srcObject && S.video.srcObject.getVideoTracks()[0];
  if (!track || !track.getCapabilities) return;
  const cap = track.getCapabilities(), adv = {};
  if (cap.exposureMode && cap.exposureMode.includes('manual')) adv.exposureMode = 'manual';
  if (cap.whiteBalanceMode && cap.whiteBalanceMode.includes('manual')) adv.whiteBalanceMode = 'manual';
  if (Object.keys(adv).length) {
    try { await track.applyConstraints({ advanced: [adv] }); log(`locked ${Object.keys(adv).join(', ')}`); }
    catch (e) { log(`exposure lock failed: ${e}`); }
  }
}

// ------------------------------------------------------------------ masks (per video frame)
let segPending = false, segGen = 0;
function scheduleSegmentation(reset = false) {
  if (reset) { segGen++; segPending = false; }      // drop callbacks still queued on a previous source
  const v = S.video;
  if (segPending || !v) return;
  segPending = true;
  const g = segGen;
  const run = () => { if (g !== segGen) return; segPending = false; onVideoFrame(); scheduleSegmentation(); };
  if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(run); else setTimeout(run, 33);
}
function onVideoFrame() {
  const v = S.video;
  if (!comp || !v || v.readyState < 2 || v.videoWidth !== canvas.width) return;
  const t0 = performance.now();
  const res = seg ? segmentFrame(seg, v, t0) : null;     // without the segmenter, the background difference alone
  if (seg && !res) return;
  const comb = combineMasks(res, v);
  S.segMs = 0.9 * S.segMs + 0.1 * (performance.now() - t0);
  if (!S.mask || S.mask.w !== comb.w || S.mask.h !== comb.h) {
    S.mask = { data: comb.data, w: comb.w, h: comb.h, u8: new Uint8Array(comb.w * comb.h) };
  } else {
    // rise at once (a walker's leading edge is solid), fade over a few frames (no flicker at the edges)
    const m = S.mask.data, d = comb.data;
    for (let i = 0; i < d.length; i++) m[i] = d[i] > m[i] ? d[i] : 0.4 * m[i] + 0.6 * d[i];
  }
  const m = S.mask;
  for (let i = 0; i < m.data.length; i++) m.u8[i] = m.data[i] * 255;
  comp.uploadR8(comp.tex.mask, m.u8, m.w, m.h);
  if (S.capture) {
    wctx.drawImage(v, 0, 0, work.width, work.height);
    S.capture.add(wctx.getImageData(0, 0, work.width, work.height), m);
    if (S.capture.done) finishPlate();
  } else if (S.plate && S.frames % 30 === 0) {
    updateGain();
  }
  analysePeople();
  checkCameraMoved();
}
// ------------------------------------------------------------------ background difference (quarter res)
// The selfie model finds people near the camera; a fixed camera also lets us find anyone who differs
// from the empty scene (as crossover/masks.py does offline). Both are combined.
const DW = 320;
const small = document.createElement('canvas');
const sctx = small.getContext('2d', { willReadFrequently: true });
function shrink(img, w, h) {
  const c = new OffscreenCanvas(img.width, img.height); c.getContext('2d').putImageData(img, 0, 0);
  const d = new OffscreenCanvas(w, h), x = d.getContext('2d', { willReadFrequently: true });
  x.drawImage(c, 0, 0, w, h);
  return x.getImageData(0, 0, w, h);
}
function morph(src, w, h, r, op) {                 // separable square min/max filter on 0/1 bytes
  const tmp = new Uint8Array(w * h), out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let v = op ? 0 : 1;
    for (let k = -r; k <= r; k++) { const xx = Math.min(w - 1, Math.max(0, x + k)); v = op ? Math.max(v, src[y * w + xx]) : Math.min(v, src[y * w + xx]); }
    tmp[y * w + x] = v;
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let v = op ? 0 : 1;
    for (let k = -r; k <= r; k++) { const yy = Math.min(h - 1, Math.max(0, y + k)); v = op ? Math.max(v, tmp[yy * w + x]) : Math.min(v, tmp[yy * w + x]); }
    out[y * w + x] = v;
  }
  return out;
}
function combineMasks(seg, video) {
  const w = DW, h = Math.round(DW * canvas.height / canvas.width), n = w * h;
  const out = new Float32Array(n);
  if (seg) for (let y = 0; y < h; y++) {
    const row = Math.min(seg.h - 1, Math.floor((y + 0.5) * seg.h / h)) * seg.w;
    for (let x = 0; x < w; x++) out[y * w + x] = seg.data[row + Math.min(seg.w - 1, Math.floor((x + 0.5) * seg.w / w))];
  }
  if (!S.plate || !S.diff || !S.plateSmall) return { data: out, w, h };
  small.width = w; small.height = h;
  sctx.drawImage(video, 0, 0, w, h);
  const f = sctx.getImageData(0, 0, w, h).data, p = S.plateSmall.data, g = S.gain;
  let bin = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const r = f[4 * i] - g * p[4 * i], gg = f[4 * i + 1] - g * p[4 * i + 1], b = f[4 * i + 2] - g * p[4 * i + 2];
    const dy = 0.299 * r + 0.587 * gg + 0.114 * b, dcb = -0.169 * r - 0.331 * gg + 0.5 * b, dcr = 0.5 * r - 0.419 * gg - 0.081 * b;
    bin[i] = Math.hypot(0.5 * dy, 1.6 * dcb, 1.6 * dcr) > 16 ? 1 : 0;   // brightness down-weighted: shadows stay out
  }
  bin = morph(morph(bin, w, h, 1, 0), w, h, 1, 1);                 // open: drop speckle
  bin = morph(morph(bin, w, h, 3, 1), w, h, 3, 0);                 // close: fill bodies
  for (let i = 0; i < n; i++) if (bin[i]) out[i] = Math.max(out[i], 1);
  return { data: out, w, h };
}

function updateGain() {
  // global exposure match between the live frame and the plate, over background pixels
  wctx.drawImage(S.video, 0, 0, work.width, work.height);
  const f = wctx.getImageData(0, 0, work.width, work.height).data, p = S.plateData.data, m = S.mask;
  let a = 0, b = 0;
  for (let y = 0; y < work.height; y += 8) for (let x = 0; x < work.width; x += 8) {
    const mi = m.data[Math.floor(y * m.h / work.height) * m.w + Math.floor(x * m.w / work.width)];
    if (mi > 0.2) continue;
    const i = 4 * (y * work.width + x);
    a += f[i] + f[i + 1] + f[i + 2]; b += p[i] + p[i + 1] + p[i + 2];
  }
  if (b > 0) S.gain = 0.8 * S.gain + 0.2 * Math.min(1.4, Math.max(0.7, a / b));
}
let movedSince = 0, movedWarned = false;
function checkCameraMoved() {                    // a handheld 'your video' makes everything look like a person
  if (S.scene !== -1 || S.source !== 'clip' || !S.plate || movedWarned || S.frames % 10) return;
  const st = window.__portal.maskStats();
  if (st && st.personFrac > 0.5) {
    if (!movedSince) movedSince = performance.now();
    else if (performance.now() - movedSince > 3000) {
      movedWarned = true;
      toast('Looks like the camera moved. This needs a fixed camera: a tripod or a propped phone.', 6000);
    }
  } else movedSince = 0;
}

// ------------------------------------------------------------------ depth (farness: 0 near .. 1 far)
// Shipped as a PNG: R/G = farness as 16 bits, B = its gradient magnitude (scaled by gmax).
async function decodeFar(blob, gmax) {
  const bmp = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  const w = bmp.width, h = bmp.height;
  const c = new OffscreenCanvas(w, h), x = c.getContext('2d', { willReadFrequently: true });
  x.drawImage(bmp, 0, 0);
  const d = x.getImageData(0, 0, w, h).data;
  const f = new Float32Array(w * h), fg = new Float32Array(2 * w * h);
  for (let i = 0; i < w * h; i++) {
    f[i] = (d[4 * i] * 256 + d[4 * i + 1]) / 65535;
    fg[2 * i] = f[i]; fg[2 * i + 1] = d[4 * i + 2] / 255 * gmax;
  }
  return { w, h, f, fg };
}
function setFar(far) {
  if (S.far && S.far.tex) comp.gl.deleteTexture(S.far.tex);
  S.far = far ? { ...far, tex: comp.newFar(far.w, far.h, far.fg) } : null;
}
function farAt(x, y) {                           // CPU copy, for the feet; without a map, lower = nearer
  if (!S.far) return 1 - y;
  const { w, h, f } = S.far;
  return f[Math.min(h - 1, Math.max(0, Math.floor(y * h))) * w + Math.min(w - 1, Math.max(0, Math.floor(x * w)))];
}

// ------------------------------------------------------------------ the rule (also used per person)
function ruleWeight(x, y) {        // normalized camera coords -> 0 real .. 1 other world
  const W = canvas.width, H = canvas.height, s = W / 768;
  if (S.mode === 0) {
    const n = [Math.cos(S.line.angle), Math.sin(S.line.angle)];
    const d = (x - S.line.x) * W * n[0] + (y - S.line.y) * H * n[1];
    return Math.min(1, Math.max(0, 0.5 + d / (3 * s)));
  }
  if (S.mode === 1) {
    const r = S.portal.r * W * breath();
    const q = Math.hypot((x - S.portal.x) * W / r, (y - S.portal.y) * H / (r * 0.38));
    return Math.min(1, Math.max(0, (1 - q) / 0.06 + 0.5));
  }
  if (S.mode === 2) {
    const d = Math.hypot((x - S.lens.x) * W, (y - S.lens.y) * H);
    return Math.min(1, Math.max(0, (S.lens.r * H - d) / (3 * s) + 0.5));
  }
  if (S.mode === 4) return smooth01((farAt(x, y) - S.tau) / 0.06 + 0.5);
  return 1;
}
function breath() { return REDUCED ? 1 : 1 + 0.05 * Math.sin(performance.now() / 1000 * 2 * Math.PI / 3); }

// People as blobs on a coarse grid, tracked across frames. Each gets one weight from where they stand
// (portal and depth rules), and a crossing (a person going from real to the other world) plays a
// whoosh and, for a person-shaped track, a short style burst on that person only.
const GW = 160;
let pwU8 = null;
function analysePeople() {
  const m = S.mask; if (!m) return;
  const GH = Math.round(GW * m.h / m.w);
  const grid = new Uint8Array(GW * GH), lab = new Int32Array(GW * GH);
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    grid[y * GW + x] = m.data[Math.floor((y + 0.5) * m.h / GH) * m.w + Math.floor((x + 0.5) * m.w / GW)] > 0.5 ? 1 : 0;
  }
  const blobs = []; let nl = 0;
  const stack = [];
  for (let i = 0; i < grid.length; i++) {
    if (!grid[i] || lab[i]) continue;
    nl++; lab[i] = nl; stack.push(i);
    let cnt = 0, sx = 0, sy = 0, minx = GW, maxx = 0, miny = GH, maxy = 0, cells = [];
    while (stack.length) {
      const j = stack.pop(), x = j % GW, y = (j / GW) | 0;
      cnt++; sx += x; sy += y; cells.push(j);
      if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y;
      for (const k of [j - 1, j + 1, j - GW, j + GW]) {
        if (k < 0 || k >= grid.length || lab[k] || !grid[k]) continue;
        if ((k === j - 1 && x === 0) || (k === j + 1 && x === GW - 1)) continue;
        lab[k] = nl; stack.push(k);
      }
    }
    if (cnt < 12) continue;
    const feetXs = cells.filter((j) => ((j / GW) | 0) >= maxy - 1).map((j) => j % GW).sort((a, b) => a - b);
    blobs.push({ cells, cnt, cx: sx / cnt / GW, cy: sy / cnt / GH, fx: (feetXs[feetXs.length >> 1] + 0.5) / GW, fy: (maxy + 1) / GH,
                 box: [minx / GW, miny / GH, (maxx + 1) / GW, (maxy + 1) / GH], hw: (maxy - miny + 1) / (maxx - minx + 1) });
  }
  // track (nearest centroid; tracks keep their id), smooth each person's weight, detect crossings
  const prev = S.tracks, next = [], now = performance.now();
  for (const t of prev) t.used = false;
  let massIn = 0, mass = 0;
  for (const b of blobs) {
    const raw = S.mode === 2 ? ruleWeight(b.cx, b.cy) : ruleWeight(b.fx, Math.min(0.999, b.fy));
    // match the nearest track; the reach grows with the time since it was seen (a slow device analyses
    // fewer frames, and a walker covers about 0.15 of the frame per second)
    let best = null, bd = Infinity;
    for (const t of prev) {
      if (t.used) continue;
      const d = Math.hypot(t.cx - b.cx, t.cy - b.cy), reach = 0.08 + 0.25 * Math.min(1, (now - t.seen) / 1000);
      if (d < reach && d < bd) { best = t; bd = d; }
    }
    const t = best || { id: ++S.trackId, w: raw, inside: raw > 0.5, lastBurst: 0 };
    t.used = true; t.seen = now;
    t.cx = b.cx; t.cy = b.cy; t.w = 0.65 * t.w + 0.35 * raw;
    t.cnt = b.cnt; t.frac = b.cnt / (GW * GH); t.box = b.box; t.hw = b.hw;
    if (!t.inside && t.w > 0.7 && best) onCrossing(t);
    if (t.w > 0.7) t.inside = true; else if (t.w < 0.3) t.inside = false;
    b.w = t.w; next.push(t);
    massIn += b.cnt * t.w; mass += b.cnt;
  }
  S.tracks = next;
  if (S.burst && !S.burst.fixed) {               // the burst box follows its person
    const t = next.find((x) => x.id === S.burst.id);
    if (t) { S.burst.box = padBox(t.box); S.burst.seen = now; }
    else if (now - S.burst.seen > 300) S.burst = null;
  }
  S.across = mass ? massIn / mass : 0;
  const a = aud(); if (a) a.setAcross(S.across);
  if (S.mode === 1 || S.mode === 4) {
    if (!pwU8 || pwU8.length !== GW * GH) pwU8 = new Uint8Array(GW * GH);
    pwU8.fill(0);
    for (const b of blobs) {
      const v = Math.round(b.w * 255);
      for (const j of b.cells) {
        const x = j % GW, y = (j / GW) | 0;
        for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
          const xx = x + dx, yy = y + dy;
          if (xx >= 0 && yy >= 0 && xx < GW && yy < GH) pwU8[yy * GW + xx] = Math.max(pwU8[yy * GW + xx], v);
        }
      }
    }
    comp.uploadR8(comp.tex.pw, pwU8, GW, GH);
  }
}
function onCrossing(t) {
  const now = performance.now();
  if (now - (S.lastCrossT || 0) >= 600) {
    S.lastCrossT = now; S.crossings++;
    const a = aud(); if (a && !S.muted) a.whoosh();
  }
  if (!S.autoGlitch || S.layers) return;
  // a person, not a car or a merged crowd: upright, and between 0.5% and 8% of the frame
  if (t.hw < 1.3 || t.frac < 0.005 || t.frac > 0.08) return;
  if (now - (t.lastBurst || 0) < 2000 || now - (S.lastBurstT || 0) < 900) return;
  startBurst(t, 900, t.id * 7919 + S.crossings);
}
const padBox = (b) => [Math.max(0, b[0] - 0.04), Math.max(0, b[1] - 0.04), Math.min(1, b[2] + 0.04), Math.min(1, b[3] + 0.04)];
// The crosser flashes through styles, faster and faster (switch every 4, then 2, then 1 frame at 30 fps,
// as in trailer.Glitch), and lands in the world. A figure covering more than 10% of the frame switches
// at most 3 times a second (flash safety).
function startBurst(t, ms, seed, fixed = false) {
  const now = performance.now();
  t.lastBurst = now; S.lastBurstT = now; S.bursts++;
  const box = padBox(t.box);
  const big = (box[2] - box[0]) * (box[3] - box[1]) > 0.10;
  const sched = [];
  for (let k = 0; k < ms;) { sched.push(k); k += big ? 334 : k < ms * 0.5 ? 133 : k < ms * 0.83 ? 67 : 33; }
  const here = currentWorld().kind;
  const kinds = [...new Set([here, 1, 2, 3, 4, 5, 6])];
  let rs = (seed >>> 0) || 1;
  const rnd = () => (rs = (rs * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const styles = [];
  for (let i = 0; i < sched.length; i++) {
    let k;
    do { k = kinds[Math.floor(rnd() * kinds.length)]; } while (styles.length && k === styles[styles.length - 1] && kinds.length > 1);
    styles.push(k);
  }
  styles[styles.length - 1] = here;
  S.burst = { id: t.id, t0: now, ms, box, sched, styles, seen: now, fixed };
}
function burstState(now) {
  const b = S.burst;
  if (!b) return null;
  const el = now - b.t0;
  if (el >= b.ms) { S.burst = null; return null; }
  let i = 0;
  while (i + 1 < b.sched.length && b.sched[i + 1] <= el) i++;
  return { box: b.box, per: b.styles[i], edge: el - b.sched[i] < 70 };
}

// ------------------------------------------------------------------ worlds
function currentWorld() { return S.worlds[S.world]; }
const groupOf = (w) => (w.kind !== 0 ? 'filter' : w.group === 'yours' ? 'yours' : 'generated');
function displayName(w) {
  if (w.kind === 0) return w.name;
  const clash = S.worlds.some((o) => o.kind === 0 && o.name.toLowerCase() === w.name.toLowerCase());
  return clash ? `${w.name} (filter)` : w.name;
}
function worldLabel(w) {
  const g = groupOf(w);
  return g === 'generated' ? `${w.name} · one generated image` : g === 'yours' ? `${w.name} · your image` : `${displayName(w)} · filter`;
}
// generated worlds first, then your images, then the filters: the chips, keys 1-9, N and auto-cycle agree
function visualOrder() {
  const rank = { generated: 0, yours: 1, filter: 2 };
  return S.worlds.map((w, i) => i).sort((a, b) => rank[groupOf(S.worlds[a])] - rank[groupOf(S.worlds[b])] || a - b);
}
function stepWorld(d) { const o = visualOrder(); setWorld(o[(o.indexOf(S.world) + d + o.length) % o.length]); }
function setWorld(i, quiet = false) {
  if (i < 0 || i >= S.worlds.length) return;
  const old = currentWorld();
  if (!quiet && !REDUCED && comp && S.plate && old && i !== S.world) {
    S.wave = { t0: performance.now(), prevKind: old.kind, prevTex: old.tex };   // roll in from the horizon
  } else if (!quiet) flash(0.25);
  S.world = i;
  const a = aud(); if (a) a.setWorld(i);
  if (!quiet) toast(worldLabel(S.worlds[i]));
  renderControls();
}
function setMode(m, quiet = false) {
  S.mode = m; S.tracks = []; S.burst = null;
  if (!quiet) toast(m === 4 ? 'Rule: depth. Tap or drag to choose how far the other world begins.' : `Rule: ${MODES[m]}`);
  renderControls();
}
function setField(w, coeffs, gx = 1, gy = 1) {
  if (w.field) comp.gl.deleteTexture(w.field.tex);
  w.field = comp.newField(gx, gy, coeffs);
}
async function addImageWorld(name, src, url, { quiet = false, group = 'generated', colour = null, gen = null } = {}) {
  const bmp = src instanceof ImageBitmap ? src : await createImageBitmap(src);
  const w = { name, kind: 0, img: bmp, url, group, gen, baked: !!colour, field: null };
  const data = toImageData(bmp, canvas.width, canvas.height);
  w.tex = comp.newTexture();
  comp.uploadImage(w.tex, data);
  if (colour) setField(w, colour.a, colour.gx, colour.gy);
  else setField(w, S.plateData ? fitColourField(S.plateData, data) : IDENTITY_FIELD);
  S.worlds.push(w);
  if (!quiet) toast(`New world: ${name}`);
  renderControls();
  return S.worlds.length - 1;
}
function removeImageWorlds() {           // image worlds belong to one view; drop them when the view changes
  S.wave = null;
  for (const w of S.worlds) if (w.kind === 0) {
    if (w.tex) comp.gl.deleteTexture(w.tex);
    if (w.field) comp.gl.deleteTexture(w.field.tex);
  }
  S.worlds = S.worlds.filter((w) => w.kind !== 0);
  S.world = Math.min(S.world, S.worlds.length - 1);
}

// ------------------------------------------------------------------ recorded scenes (hosted demo)
// A scene is a fixed-camera clip with its empty scene, generated worlds (each with its colour field),
// a depth map, and what Stable Diffusion was given, all made offline (scripts/build_portal_artifact.py).
let sceneGen = 0;
async function fetchBlob(src) {
  const r = await fetch(src);
  if (!r.ok) throw new Error(`could not load ${src} (${r.status})`);
  return r.blob();
}
async function loadScene(i) {
  const sc = S.scenes[i]; if (!sc) return;
  const g = ++sceneGen;
  toast(`Loading ${sc.name}…`, 20000);
  try {
    const [clip, plate, far, ...worlds] = await Promise.all([
      fetchBlob(sc.clip), fetchBlob(sc.plate).then((b) => createImageBitmap(b)),
      sc.far ? fetchBlob(sc.far).then((b) => decodeFar(b, sc.farGmax || 0.02)) : null,
      ...sc.worlds.map((w) => fetchBlob(w.src).then((b) => createImageBitmap(b)))]);
    if (g !== sceneGen) return;
    removeImageWorlds();
    S.scene = i;
    S.layers = false; S.layer = -1;
    await useSource('clip', { src: URL.createObjectURL(clip), plate, startTime: sc.startTime || 0 });
    setFar(far);
    if (sc.line) Object.assign(S.line, sc.line);
    if (sc.portal) Object.assign(S.portal, sc.portal);
    if (sc.tau != null) S.tau = sc.tau;
    for (let k = 0; k < worlds.length; k++) {
      const w = sc.worlds[k];
      await addImageWorld(w.name, worlds[k], w.src, { quiet: true, colour: w.colour, gen: w.gen });
    }
    const start = S.worlds.findIndex((w) => w.kind === 0 && w.name === sc.startWorld);
    setWorld(start >= 0 ? start : visualOrder()[0], true);
    toast(`${sc.name}: ${worldLabel(currentWorld())}`);
  } catch (e) {
    log(`scene ${sc.name}: ${e.message || e}`);
    toast(`Could not load ${sc.name}: ${e.message || e}`, 8000);
  }
  renderControls();
}
async function useVideoFile(file) {
  sceneGen++;
  removeImageWorlds();
  S.scene = -1; S.plate = null; S.layers = false;
  movedSince = 0; movedWarned = false;
  try {
    await useSource('clip', { src: URL.createObjectURL(file) });
    setFar(null);
    toast('Your video: capturing its empty scene from the first seconds.', 5000);
  } catch (e) {
    toast(`This browser could not play ${file.name}. Try an MP4 (H.264) file.`, 8000);
    log(`video file: ${e}`);
  }
  renderControls();
}

// ------------------------------------------------------------------ local server: generated worlds
async function checkServer() {
  try {
    const r = await fetch('./api/status', { cache: 'no-store' });
    S.server = r.ok && (await r.json()).server === true;
  } catch { S.server = false; }
  log(`world server: ${S.server ? 'yes' : 'no (filter worlds only)'}`);
}
async function sendPlate() {
  const c = new OffscreenCanvas(canvas.width, canvas.height);
  c.getContext('2d').putImageData(S.plateData, 0, 0);
  const blob = await c.convertToBlob({ type: 'image/png' });
  try {
    const r = await fetch('./api/plate', { method: 'POST', body: blob, headers: { 'Content-Type': 'image/png' } });
    const j = await r.json();
    S.job = j.job;
    toast('Generating worlds from this scene…', 4000);
  } catch (e) { log(`plate upload failed: ${e}`); }
}
async function pollWorlds() {
  if (!S.server || !S.job) return;
  try {
    const r = await fetch(`./api/worlds?job=${encodeURIComponent(S.job)}`, { cache: 'no-store' });
    const j = await r.json();
    for (const w of j.worlds || []) {
      if (S.loaded.has(w.url)) continue;
      S.loaded.add(w.url);
      const img = await (await fetch(w.url, { cache: 'no-store' })).blob();
      await addImageWorld(w.label, img, w.url);
    }
    S.progress = j.progress || '';
  } catch (e) { log(`poll failed: ${e}`); }
}
setInterval(pollWorlds, 3000);

// ------------------------------------------------------------------ render loop
// Layers view geometry: six frame-shaped tiles of W/3 x H/3, 3x2 on a wide stage and 2x3 on a tall
// one (the drawing buffer stays the frame size). Returns screen-space rects (top-left origin).
function tileRects() {
  const W = canvas.width, H = canvas.height, tw = W / 3, th = H / 3;
  const st = $('stage').getBoundingClientRect();
  const tall = st.height > st.width;
  return LAYERS.map((_, k) => {
    const col = tall ? k % 2 : k % 3, row = tall ? (k / 2) | 0 : (k / 3) | 0;
    const x0 = tall ? W / 6 : 0, y0 = tall ? 0 : H / 6;
    return { x: Math.round(x0 + col * tw), y: Math.round(y0 + row * th), w: Math.round(tw), h: Math.round(th) };
  });
}
const narrowStage = () => $('stage').getBoundingClientRect().width < 520;
function frame(now) {
  requestAnimationFrame(frame);
  render(now);
}
// Draw one frame. `over` lets tests force a view synchronously (then read the pixels in the same task).
function render(now, over = {}) {
  const v = S.video;
  if (!comp || !v) return false;
  if (v.readyState >= 2) comp.uploadImage(comp.tex.cam, v);
  else if (over.view == null) return false;       // (a forced view such as the parity view needs no camera frame)
  if (S.autoCycle && now - S.lastCycle > 6000 && !over.view) { S.lastCycle = now; stepWorld(1); }
  const W = canvas.width, H = canvas.height, w = currentWorld();
  let bg = w.kind, per = w.kind, worldTex = w.tex, field = w.field;
  let glitch = 0;
  if (now < S.glitchUntil) {             // the manual glitch: the person flashes through worlds, the frame tears
    glitch = 1;
    const kinds = [w.kind, 1, 2, 3, 4, 5, 6];
    per = kinds[(Math.random() * kinds.length) | 0];
    if (Math.random() < 0.15) { const kb = S.worlds[(Math.random() * S.worlds.length) | 0]; bg = kb.kind; worldTex = kb.tex; }
  }
  if (bg === 0 && !worldTex) bg = 1;
  const bs = burstState(now);
  let wave = null;
  if (S.wave) {
    const u = S.waveHold != null ? S.waveHold : (now - S.wave.t0) / 1200;
    if (u >= 1 && S.waveHold == null) S.wave = null;
    else wave = 1.08 - 1.2 * smooth01(Math.min(1, u) * 1.15);
  }
  const p = {
    bg, per, worldTex, field, mode: S.mode,
    p0: [S.line.x * W, S.line.y * H], n: [Math.cos(S.line.angle), Math.sin(S.line.angle)],
    portal: [S.portal.x * W, S.portal.y * H, S.portal.r * W * breath()], squash: 0.38,
    lens: [S.lens.x * W, S.lens.y * H], lensR: S.lens.r * H,
    glitch, seed: Math.random() * 100, flash: S.flash, mirror: S.mirror, debug: S.debug,
    hasPlate: !!S.plate, diff: S.diff, gain: S.gain,
    farTex: S.far && S.far.tex, tau: S.tau,
    waveOn: wave != null, wave, prevKind: S.wave && S.wave.prevKind, prevTex: S.wave && S.wave.prevTex,
    burst: !!bs, burstBox: bs && bs.box, burstPer: bs ? bs.per : -1, burstEdge: bs && bs.edge,
  };
  if (over.view != null) {
    comp.draw({ ...p, view: over.view, flash: 0 });
  } else if (S.layers) {
    comp.clear();
    if (S.layer >= 0) comp.draw({ ...p, view: LAYERS[S.layer].view, flash: 0 });
    else for (const [k, r] of tileRects().entries()) comp.draw({ ...p, view: LAYERS[k].view, flash: 0, vp: [r.x, H - r.y - r.h, r.w, r.h] });
  } else {
    comp.draw(p);
  }
  S.flash *= 0.82; if (S.flash < 0.01) S.flash = 0;
  S.frames++;
  placeOverlays();
  if (now - S.lastFpsT > 500) {
    S.fps = (S.frames - (S.fpsBase || 0)) * 1000 / (now - S.lastFpsT); S.fpsBase = S.frames; S.lastFpsT = now;
    const dbg = S.debug ? ` · ${S.fps.toFixed(0)} fps · mask ${S.segMs.toFixed(0)} ms (${S.delegate}) · gain ${S.gain.toFixed(2)}` : '';
    const where = S.scenes[S.scene] ? ` · ${S.scenes[S.scene].name}` : S.source === 'clip' ? ' · recorded clip' : '';
    const view = S.layers ? ' · layers' : '';
    $('hudsub').textContent = `${displayName(w)} · ${MODES[S.mode]}${where}${view}${S.progress ? ' · ' + S.progress : ''}${dbg}`;
  }
  return true;
}

// ------------------------------------------------------------------ on-canvas DOM: line handle, side tags, layer labels
let lastOverlayKey = '';
function placeOverlays() {
  const handle = $('handle'), tagA = $('tag-real'), tagB = $('tag-world'), labels = $('layer-labels'), card = $('sdcard');
  if (!handle && !labels) return;
  const st = $('stage').getBoundingClientRect(), r = canvas.getBoundingClientRect();
  const sx = r.width / canvas.width, ox = r.left - st.left, oy = r.top - st.top;
  const showLine = !S.layers && S.mode === 0 && !!S.plate;
  if (handle) {
    handle.hidden = !showLine; tagA.hidden = !showLine; tagB.hidden = !showLine;
    if (showLine) {
      const mx = (x) => (S.mirror ? 1 - x : x);
      const nx = (S.mirror ? -1 : 1) * Math.cos(S.line.angle), ny = Math.sin(S.line.angle);
      const hx = ox + mx(S.line.x) * r.width, hy = oy + S.line.y * r.height;
      handle.style.transform = `translate(${hx}px, ${hy}px)`;
      handle.classList.toggle('small', S.dragged);
      const ty = oy + Math.max(26, 0.1 * r.height), d = 14;
      // tags sit either side of the line, at the top: the filmed side and the world side
      const xAtTop = hx + (ty - hy) * (-ny / (Math.abs(nx) > 1e-3 ? nx : 1e-3));
      tagA.style.transform = `translate(calc(${xAtTop - d * Math.sign(nx || 1)}px - ${nx >= 0 ? 100 : 0}%), ${ty}px)`;
      tagB.style.transform = `translate(calc(${xAtTop + d * Math.sign(nx || 1)}px - ${nx >= 0 ? 0 : 100}%), ${ty}px)`;
      const name = displayName(currentWorld());
      if (tagB.textContent !== name) tagB.textContent = name;
    }
  }
  if (labels) {
    const key = `${S.layers}|${S.layer}|${Math.round(r.width)}x${Math.round(r.height)}|${narrowStage()}|${st.height > st.width}`;
    if (key !== lastOverlayKey) {
      lastOverlayKey = key;
      labels.replaceChildren();
      if (S.layers) {
        const rects = tileRects();
        const items = S.layer >= 0 ? [[S.layer, { x: 0, y: 0 }]] : LAYERS.map((_, k) => [k, rects[k]]);
        for (const [k, t] of items) {
          const el = document.createElement('div');
          el.className = 'layer-label';
          el.innerHTML = `<b>${LAYERS[k].name}</b> <span>${LAYERS[k].note}</span>`;
          el.style.transform = `translate(${ox + t.x * sx + 6}px, ${oy + t.y * sx + 6}px)`;
          labels.append(el);
        }
      }
      labels.hidden = !S.layers;
    }
  }
  if (card) {
    const sc = S.scenes[S.scene], w = currentWorld();
    const show = S.layers && S.layer < 0 && !narrowStage() && !!(sc && sc.sd && w.kind === 0 && w.gen);
    card.hidden = !show;
    if (show) {
      const key = `${S.scene}|${S.world}`;
      if (card.dataset.key !== key) {
        card.dataset.key = key;
        const gsec = Math.round(w.gen.seconds);
        card.querySelector('.sd-depth').src = sc.sd.depth;
        card.querySelector('.sd-canny').src = sc.sd.canny;
        card.querySelector('.sd-text').textContent =
          `"${w.name}" was made once from the empty scene: Stable Diffusion 1.5 guided by its depth and edges ` +
          `(ControlNet), strength ${w.gen.strength}, ${w.gen.steps} steps, ${Math.floor(gsec / 60)} min ${gsec % 60} s on a CPU.`;
      }
      const rects = tileRects(), bottom = rects[3].y + rects[3].h;
      card.style.transform = `translate(${ox}px, ${oy + bottom * sx + 6}px)`;
      card.style.width = `${r.width}px`;
    }
  }
}

// ------------------------------------------------------------------ input
function toFrame(e) {
  const r = canvas.getBoundingClientRect();
  let x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
  if (S.mirror) x = 1 - x;
  return [Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y))];
}
function tileAt(e) {                             // tiles are laid out on screen: no mirror here
  const r = canvas.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width * canvas.width, y = (e.clientY - r.top) / r.height * canvas.height;
  return tileRects().findIndex((t) => x >= t.x && x < t.x + t.w && y >= t.y && y < t.y + t.h);
}
let dragging = false;
canvas.addEventListener('pointerdown', (e) => {
  if (S.layers) {                                // tap a tile to see it full size; tap again to go back
    if (narrowStage()) S.layer = (S.layer + 1) % LAYERS.length;
    else if (S.layer >= 0) S.layer = -1;
    else S.layer = tileAt(e);
    return;
  }
  dragging = true; canvas.setPointerCapture(e.pointerId); onPointer(e);
});
canvas.addEventListener('pointerup', () => { if (dragging && S.mode === 0) S.dragged = true; dragging = false; });
canvas.addEventListener('pointercancel', () => { dragging = false; });
canvas.addEventListener('pointermove', (e) => { if (!S.layers && (dragging || (S.mode === 2 && e.pointerType === 'mouse'))) onPointer(e); });
function onPointer(e) {
  const [x, y] = toFrame(e);
  if (S.mode === 0) { S.line.x = x; S.line.y = y; }
  else if (S.mode === 1) { S.portal.x = x; S.portal.y = y; }
  else if (S.mode === 2) { S.lens.x = x; S.lens.y = y; }
  else if (S.mode === 4) S.tau = Math.min(0.98, Math.max(0.02, farAt(x, y)));   // the contour goes where you point
}
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const k = e.deltaY > 0 ? 0.92 : 1.08;
  if (S.mode === 1) S.portal.r = Math.min(0.6, Math.max(0.05, S.portal.r * k));
  if (S.mode === 2) S.lens.r = Math.min(0.8, Math.max(0.05, S.lens.r * k));
  if (S.mode === 4) S.tau = Math.min(0.98, Math.max(0.02, S.tau + (e.deltaY > 0 ? -0.02 : 0.02)));
}, { passive: false });

function glitchBurst() { S.glitchUntil = performance.now() + (REDUCED ? 500 : 1500); }
function toggleCycle() { S.autoCycle = !S.autoCycle; S.lastCycle = performance.now(); toast(`Auto-cycle ${S.autoCycle ? 'on' : 'off'}`); renderControls(); }
function toggleSound() {
  S.muted = !S.muted;
  if (audio || !S.muted) ensureAudio();
  toast(S.muted ? 'Sound off' : 'Sound on');
  renderControls();
}
function toggleLayers(on) {
  S.layers = on === undefined ? !S.layers : on;
  S.layer = S.layers && narrowStage() ? 0 : -1;
  if (S.layers) toast(narrowStage() ? 'Layers: tap to step through them' : 'Layers: tap a tile to see it full size');
  renderControls();
}
function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => toast('Full screen is not available here'));
}
function toggleHelp(show) { const h = $('help'); if (h) h.hidden = show === undefined ? !h.hidden : !show; }
function switchSource() {
  if (!CFG.camera) { toast('The live camera runs in the local kiosk (see README)'); return; }
  sceneGen++; S.scene = -1;
  useSource(S.source === 'camera' ? 'clip' : 'camera').then(renderControls);
}

addEventListener('keydown', (e) => {
  if (e.target instanceof HTMLSelectElement || e.target instanceof HTMLInputElement) return;
  const k = e.key.toLowerCase();
  if (e.target instanceof HTMLButtonElement && (k === ' ' || k === 'enter')) return;   // the button's own click
  if (k >= '1' && k <= '9') { const o = visualOrder(); if (o[+k - 1] != null) setWorld(o[+k - 1]); }
  else if (k === 'n') stepWorld(1);
  else if (k === 'm') setMode(UI_MODES[(UI_MODES.indexOf(S.mode) + 1) % UI_MODES.length]);
  else if (k === 'l') toggleLayers();
  else if (k === 'c') capturePlate(3);
  else if (k === 'g') glitchBurst();
  else if (k === 'x') { S.autoGlitch = !S.autoGlitch; toast(`Crossing glitch ${S.autoGlitch ? 'on' : 'off'}`); }
  else if (k === ' ') { toggleCycle(); e.preventDefault(); }
  else if (k === 'b') switchSource();
  else if (k === 'r') S.mirror = !S.mirror;
  else if (k === 'd') S.debug = !S.debug;
  else if (k === 't') { S.diff = !S.diff; toast(`Hole filling ${S.diff ? 'on' : 'off'}`); }
  else if (k === 's') toggleSound();
  else if (k === 'f') toggleFullscreen();
  else if (k === 'escape' && $('help') && !$('help').hidden) toggleHelp(false);
  else if (k === 'escape' && S.layers) { if (S.layer >= 0 && !narrowStage()) S.layer = -1; else toggleLayers(false); }
  else if (k === 'h') toggleHelp();
  else if (e.key === '[') S.line.angle -= 0.05;
  else if (e.key === ']') S.line.angle += 0.05;
  else if (e.key === 'ArrowLeft') S.line.x = Math.max(0, S.line.x - 0.01);
  else if (e.key === 'ArrowRight') S.line.x = Math.min(1, S.line.x + 0.01);
});
async function takeFile(f) {
  if (!f) return;
  if (f.type.startsWith('video/')) await useVideoFile(f);
  else if (f.type.startsWith('image/')) setWorld(await addImageWorld(f.name.replace(/\.[^.]+$/, ''), f, '', { group: 'yours' }));
  else toast('Drop a video of a fixed camera, or an image of the same view');
}
addEventListener('dragover', (e) => e.preventDefault());
addEventListener('drop', async (e) => {
  e.preventDefault();
  const files = [...e.dataTransfer.files];
  await takeFile(files.find((x) => x.type.startsWith('video/')) || files.find((x) => x.type.startsWith('image/')) || files[0]);
});

// ------------------------------------------------------------------ on-screen controls (if the page has them)
function chip(label, pressed, onClick, cls = '', key = '') {
  const b = document.createElement('button');
  b.type = 'button'; b.className = `chip ${cls}`.trim(); b.textContent = label;
  if (key) { const s = document.createElement('span'); s.className = 'key'; s.textContent = key; b.prepend(s); }
  b.setAttribute('aria-pressed', String(pressed)); b.addEventListener('click', onClick);
  return b;
}
function renderControls() {
  for (const b of document.querySelectorAll('[data-mode]')) b.setAttribute('aria-pressed', String(+b.dataset.mode === S.mode));
  if ($('b-cycle')) $('b-cycle').setAttribute('aria-pressed', String(S.autoCycle));
  if ($('b-layers')) $('b-layers').setAttribute('aria-pressed', String(S.layers));
  if ($('b-sound')) { $('b-sound').setAttribute('aria-pressed', String(!S.muted)); $('b-sound').textContent = S.muted ? 'Sound off' : 'Sound on'; }
  const box = $('worlds');
  if (box) {
    const titles = { generated: 'AI-generated · made once', yours: 'Your images', filter: 'Filters (no AI)' };
    const order = visualOrder(), kids = [];
    let last = '';
    order.forEach((i, n) => {
      const w = S.worlds[i], g = groupOf(w);
      if (g !== last) { const t = document.createElement('span'); t.className = 'group'; t.textContent = titles[g]; kids.push(t); last = g; }
      kids.push(chip(displayName(w), i === S.world, () => setWorld(i), g, n < 9 ? String(n + 1) : ''));
    });
    box.replaceChildren(...kids);
    const on = box.querySelector('[aria-pressed="true"]');
    if (on && on.scrollIntoView) on.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  const sel = $('scene');
  if (sel) {
    const opts = S.scenes.map((s, i) => new Option(s.name, String(i)));
    if (S.scene < 0) opts.push(new Option(S.source === 'camera' ? 'Live camera' : 'Your video', '-1'));
    sel.replaceChildren(...opts);
    sel.value = String(S.scene);
  }
}
function bindControls() {
  if (!$('controls')) return;
  for (const b of document.querySelectorAll('[data-mode]')) b.addEventListener('click', () => setMode(+b.dataset.mode));
  const on = (id, fn) => { if ($(id)) $(id).addEventListener('click', fn); };
  on('b-glitch', glitchBurst); on('b-cycle', toggleCycle); on('b-sound', toggleSound); on('b-layers', () => toggleLayers());
  on('b-full', toggleFullscreen); on('b-help', () => toggleHelp()); on('help-close', () => toggleHelp(false));
  on('b-upload', () => {
    toast('Pick a clip from a fixed camera (a tripod or a propped phone) with people walking through. MP4 works best.', 5000);
    if ($('file')) $('file').click();
  });
  if ($('b-full') && !document.fullscreenEnabled) $('b-full').hidden = true;
  if ($('file')) $('file').addEventListener('change', (e) => { takeFile(e.target.files[0]); e.target.value = ''; });
  if ($('scene')) $('scene').addEventListener('change', (e) => { const i = +e.target.value; if (i >= 0) loadScene(i); });
  if ($('help')) $('help').addEventListener('click', (e) => { if (e.target === $('help')) toggleHelp(false); });
}

// ------------------------------------------------------------------ start
async function start() {
  if ($('start')) $('start').hidden = true;
  // Sound needs a user gesture. Started by a click (the kiosk's button) it can begin now; otherwise
  // (autostart, the hosted page) it waits for the first touch or key, so nothing queues up silently.
  if (!S.muted) {
    if (navigator.userActivation && navigator.userActivation.isActive) ensureAudio();
    else audioOnFirstGesture();
  }
  try {
    comp = new Compositor(canvas);
  } catch (e) { toast(e.message, 10000); throw e; }
  if (CFG.server) checkServer();
  if (CFG.segmenter) {
    try {
      const m = await import('./segment.js');
      const s = await m.createSegmenter(log);
      seg = s.seg; S.delegate = s.delegate; segmentFrame = m.segmentFrame;
    } catch (e) { log(`person segmenter unavailable, using the background difference: ${e.message || e}`); }
  }
  if (!seg) S.delegate = 'background difference';
  if (typeof CFG.scenes === 'string') {
    try { S.scenes = await (await fetchBlob(CFG.scenes)).text().then(JSON.parse); }
    catch (e) { log(`scenes: ${e.message || e}`); S.scenes = []; }
  } else S.scenes = CFG.scenes || [];
  requestAnimationFrame(frame);
  if (S.scenes.length) await loadScene(Math.min(CFG.startScene, S.scenes.length - 1));
  else await useSource(S.source);
  renderControls();
}
bindControls();
if ($('go')) $('go').addEventListener('click', start);
if (CFG.autostart) start();

// ------------------------------------------------------------------ for tests and debugging
function readFrame() {
  const { px, w, h } = comp.readPixels();
  return { px, w, h, at: (x, y) => 4 * ((h - 1 - y) * w + x) };      // GL rows are bottom-up
}
window.__portal = {
  get state() { return S; },
  setWorld, setMode: (m) => setMode(m, true), setMirror: (b) => { S.mirror = b; },
  glitch: (ms) => { S.glitchUntil = performance.now() + ms; }, capture: () => capturePlate(0),
  setLine: (x, angle = 0) => { S.line.x = x; S.line.angle = angle; },
  setDebug: (b) => { S.debug = b; }, loadScene, visualOrder, displayName: (i) => displayName(S.worlds[i]),
  tiles: () => tileRects(), narrow: () => narrowStage(),
  audioState: () => (audio ? audio.ctx.state : 'none'),
  setTau: (t) => { S.tau = t; },
  // hold the world-change wave at a phase in [0, 1] (null releases it)
  setWave: (u) => { S.waveHold = u; },
  // start a style burst on the largest person-shaped track now (no cooldowns); fixed = the box stays put
  crossNow({ ms = 900, seed = 1, fixed = true } = {}) {
    // prefer a person already in the other world (bursts fire on crossing into it), then person-shaped, then big
    const ts = S.tracks.filter((t) => t.box).sort((a, b) => (b.w > 0.5) - (a.w > 0.5) || (b.hw >= 1.3) - (a.hw >= 1.3) || b.cnt - a.cnt);
    if (!ts.length) return null;
    startBurst(ts[0], ms, seed, fixed);
    return { id: ts[0].id, box: S.burst.box };
  },
  // render synchronously and return mean |a - b| style digests of regions, for deterministic checks
  regions(box) {
    render(performance.now());
    const { px, w, h, at } = readFrame();
    const inside = [], outside = [];
    for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {
      const u = (x + 0.5) / w, v = (y + 0.5) / h, i = at(x, y);
      const inBox = u >= box[0] && u <= box[2] && v >= box[1] && v <= box[3];
      (inBox ? inside : outside).push(px[i], px[i + 1], px[i + 2]);
    }
    return { inside, outside };
  },
  // mean colour of the top and bottom bands of the result (rows as fractions of the height)
  bands(top = 0.1, bottom = 0.9) {
    render(performance.now());
    const { px, w, h, at } = readFrame();
    const mean = (y0, y1) => { let s = 0, n = 0; for (let y = Math.floor(y0 * h); y < Math.floor(y1 * h); y += 2) for (let x = 0; x < w; x += 2) { const i = at(x, y); s += px[i] + px[i + 1] + px[i + 2]; n += 3; } return s / n; };
    const rows = (y0, y1) => { const out = []; for (let y = Math.floor(y0 * h); y < Math.floor(y1 * h); y += 4) for (let x = 0; x < w; x += 4) { const i = at(x, y); out.push(px[i], px[i + 1], px[i + 2]); } return out; };
    return { top: mean(0, top), bottom: mean(bottom, 1), topPx: rows(0, top), bottomPx: rows(bottom, 1) };
  },
  // colour parity: mean |page - reference| (0-255) of the person colour of the empty scene in this world
  async parity(refUrl) {
    const bmp = await createImageBitmap(await fetchBlob(refUrl), { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
    const ref = toImageData(bmp, canvas.width, canvas.height).data;
    render(performance.now(), { view: 6 });
    const { px, w, h, at } = readFrame();
    let sum = 0, n = 0;
    for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {
      const i = at(x, y), j = 4 * (y * w + x);
      sum += Math.abs(px[i] - ref[j]) + Math.abs(px[i + 1] - ref[j + 1]) + Math.abs(px[i + 2] - ref[j + 2]); n += 3;
    }
    return sum / n;
  },
  // mean |output - camera| (0-255) over a column band [x0, x1) of the frame
  compare(x0, x1) {
    const { px, w, h } = comp.readPixels();
    wctx.drawImage(S.video, 0, 0, w, h);
    const cam = wctx.getImageData(0, 0, w, h).data;
    let sum = 0, n = 0;
    for (let y = 0; y < h; y += 2) for (let x = Math.floor(x0 * w); x < Math.floor(x1 * w); x += 2) {
      const xo = S.mirror ? w - 1 - x : x;
      const i = 4 * ((h - 1 - y) * w + xo), j = 4 * (y * w + x);
      sum += Math.abs(px[i] - cam[j]) + Math.abs(px[i + 1] - cam[j + 1]) + Math.abs(px[i + 2] - cam[j + 2]); n += 3;
    }
    return sum / n;
  },
  maskStats() {
    const m = S.mask; if (!m) return null;
    let s = 0, big = 0; for (const v of m.data) { s += v; if (v > 0.5) big++; }
    return { w: m.w, h: m.h, mean: s / m.data.length, personFrac: big / m.data.length };
  },
};
