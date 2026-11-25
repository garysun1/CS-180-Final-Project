// Cross the Line — live portal kiosk. See README.md.
// The same code runs the local kiosk (index.html: camera, server, segmenter) and the hosted demo
// (artifact/page.html: recorded scenes with pre-made worlds), configured by window.PORTAL_CONFIG.
import { Compositor, IDENTITY_FIELD } from './compositor.js';
import { PlateCapture, fitColourField, toImageData } from './plate.js';
import { PortalAudio } from './audio.js';
import { Painting } from './paint.js';

const params = new URLSearchParams(location.search);
// floodHint: after the first crossing, say once that holding floods (the hosted page)
const CFG = Object.assign({
  camera: true, server: true, segmenter: true, muted: false, autostart: params.get('autostart') === '1',
  scenes: null, startScene: 0, floodHint: false,
}, window.PORTAL_CONFIG || {});
const $ = (id) => document.getElementById(id);
const canvas = $('view');
// Shader rule indices; the buttons and the M key go through them in UI order (paint after the line,
// depth before whole). FEET: rules where a person changes as a whole, by where their feet are.
const MODES = ['line', 'portal', 'lens', 'whole frame', 'depth', 'paint'];
const UI_MODES = [0, 5, 1, 2, 4, 3];
const FEET = new Set([1, 4, 5]);
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
const PORTAL_SQUASH = 0.38;              // the portal ring lies on the ground
// Hold to flood: a press held still for HOLD_MS and 3 drawn frames (moving less than SLOP_PX) opens a
// flood. It covers the frame after FLOOD_GROW, takes over the rule over its first FLOOD_TAKE, drains over
// FLOOD_DRAIN when let go, and stays (until the next tap) if it was held full for FLOOD_KEEP. Times in ms.
const HOLD_MS = 280, SLOP_PX = 8, FLOOD_GROW = 1400, FLOOD_TAKE = 300, FLOOD_DRAIN = 600, FLOOD_KEEP = 500;

const S = {
  worlds: SHADER_WORLDS.map((w) => ({ ...w })), world: 0, mode: Math.max(0, MODES.indexOf(params.get('mode') || 'line')),
  mirror: params.get('mirror') !== '0', debug: params.get('debug') === '1', diff: true,
  glitchUntil: 0, autoGlitch: !REDUCED, autoCycle: false, lastCycle: 0, flash: 0, muted: !!CFG.muted,
  line: { x: 0.5, y: 0.5, angle: 0 }, portal: { x: 0.5, y: 0.78, r: 0.17 }, lens: { x: 0.5, y: 0.5, r: 0.2 },
  tau: 0.45, far: null,
  // the seam: 'grow' (the world grows through its ladder, in a band band px wide at 768 on the line) or
  // 'cut' (the exact 3-px seam)
  seam: params.get('seam') === 'cut' ? 'cut' : 'grow', band: 120, prevW: null, slots: [null, null],
  source: params.get('source') === 'clip' || !CFG.camera ? 'clip' : 'camera', video: null,
  plate: null, plateData: null, capture: null, gain: 1,
  mask: null, segMs: 0, delegate: '', fps: 0, frames: 0, lastFpsT: performance.now(),
  tracks: [], trackId: 0, burst: null, across: 0, crossings: 0, bursts: 0, burstLog: [],
  server: false, job: null, loaded: new Set(), log: [],
  scenes: [], scene: -1, layers: false, layer: -1, wave: null, waveHold: null, dragged: false,
  flood: null, floods: 0, floodUsed: false, floodHinted: false,
  // the brush: radius in px at 768 wide, erasing or not, and where the pointer is (for its outline)
  brush: { r: 36, erase: false, at: null },
};
const painting = new Painting();
const paintTex = new Map();                  // world index -> its mask's GPU texture
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
  S.tracks = []; S.mask = null; S.burst = null; S.flood = null; lastBlobs = [];
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
  comp.setLadder(0, [image]);                     // rung 0 of every ladder
  S.plate = true;
  S.slots = [null, null];
  syncRungs();
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
// from the empty scene. Both are combined.
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
    const q = Math.hypot((x - S.portal.x) * W / r, (y - S.portal.y) * H / (r * PORTAL_SQUASH));
    return Math.min(1, Math.max(0, (1 - q) / 0.06 + 0.5));
  }
  if (S.mode === 2) {
    const d = Math.hypot((x - S.lens.x) * W, (y - S.lens.y) * H);
    return Math.min(1, Math.max(0, (S.lens.r * H - d) / (3 * s) + 0.5));
  }
  if (S.mode === 4) return smooth01((farAt(x, y) - S.tau) / 0.06 + 0.5);
  if (S.mode === 5) return Math.min(1, Math.max(0, (painting.top(x, y).v - 0.5) / 0.06 + 0.5));
  return 1;
}
// Grow: how far the world has grown at a point, 0 .. 1 (compositor.js growU); people's colour follows it
function ruleU(x, y) {
  const W = canvas.width, H = canvas.height, s = W / 768, c01 = (v) => Math.min(1, Math.max(0, v));
  if (S.mode === 0) {
    const d = (x - S.line.x) * W * Math.cos(S.line.angle) + (y - S.line.y) * H * Math.sin(S.line.angle);
    return c01(d / (S.band * s));
  }
  if (S.mode === 1) {
    const r = S.portal.r * W * breath();
    return c01((1 - Math.hypot((x - S.portal.x) * W / r, (y - S.portal.y) * H / (r * PORTAL_SQUASH))) / 0.6);
  }
  if (S.mode === 2) {
    const R = S.lens.r * H;
    return c01((R - Math.hypot((x - S.lens.x) * W, (y - S.lens.y) * H)) / (0.5 * R));
  }
  if (S.mode === 4) return c01((farAt(x, y) - S.tau) / 0.25);
  if (S.mode === 5) return painting.top(x, y).v;
  return 1;
}
function breath() { return REDUCED ? 1 : 1 + 0.05 * Math.sin(performance.now() / 1000 * 2 * Math.PI / 3); }

// ------------------------------------------------------------------ hold to flood
// A press held still opens a flood: a ring of its own from where you press (from a walker's feet, if you
// press on one), growing until it covers the frame: radius (rMax + 160 px) *
// (1 - (1 - u)^2.2), squash 0.38 -> 1. It takes over the rule as it opens (k: 0 the rule .. 1 the flood
// alone) and gives it back as it drains, so neither end pops. S.flood: x, y its centre (frame, 0..1);
// held (a pointer or O holds it); t0, u0, k0 (growing since t0 from u0, k0); tr, ur, kr (draining since
// tr); keep (held full: it stays until the next tap); hold (tests: a fixed u, the rule taken over).
function floodState(now) {
  const f = S.flood; if (!f) return null;
  let u, k;
  if (f.hold != null) { u = f.hold; k = 1; }
  else if (f.keep) { u = 1; k = 1; }
  else if (f.held) {
    const dt = Math.max(0, now - f.t0);
    u = Math.min(1, f.u0 + dt / FLOOD_GROW); k = Math.min(1, f.k0 + dt / FLOOD_TAKE);
  }
  else {
    const e = smooth01((now - f.tr) / FLOOD_DRAIN);
    if (e >= 1) { S.flood = null; return null; }
    u = f.ur * (1 - e); k = f.kr * (1 - e);
  }
  const W = canvas.width, H = canvas.height, s = W / 768, cx = f.x * W, cy = f.y * H;
  const rMax = Math.max(Math.hypot(cx, cy), Math.hypot(W - cx, cy), Math.hypot(cx, H - cy), Math.hypot(W - cx, H - cy));
  const r = (rMax + 160 * s) * (1 - Math.pow(1 - u, 2.2));
  // band: Grow's morph band at the front, 160 px (the outer 60% while the ring is small), as a fraction of r
  return { x: f.x, y: f.y, cx, cy, u, kLin: k, k: smooth01(k), r, sq: PORTAL_SQUASH + (1 - PORTAL_SQUASH) * smooth01(u),
           band: Math.min(0.6, 160 * s / Math.max(r, 1e-3)) };
}
// the flood at a point (frame coords): Cut's weight (a 3-px edge) and Grow's u (its band), as the shader
function floodAt(fl, x, y) {
  const s = canvas.width / 768, d = fl.r - Math.hypot(x * canvas.width - fl.cx, (y * canvas.height - fl.cy) / fl.sq);
  return { w: Math.min(1, Math.max(0, d / (3 * s) + 0.5)), u: Math.min(1, Math.max(0, d / Math.max(1e-3, fl.band * fl.r))) };
}
// A person's rule weight w (Cut's, which crossings use) and Grow's u (their colour), from where they
// stand: the lens by their centre, the other rules by their feet. A flood goes by the feet and takes over.
// In Paint, world is the painted world under their feet (-1: none); otherwise the current world.
function personRule(b, fl) {
  const fy = Math.min(0.999, b.fy), [x, y] = S.mode === 2 ? [b.cx, b.cy] : [b.fx, fy];
  if (S.mode === 5) {
    const t = painting.top(x, y);
    return { w: Math.min(1, Math.max(0, (t.v - 0.5) / 0.06 + 0.5)), u: t.v, world: t.world };
  }
  let w = ruleWeight(x, y), u = ruleU(x, y);
  if (fl) {
    const f = floodAt(fl, b.fx, fy);
    w = Math.max(f.w, (1 - fl.k) * w); u = Math.max(f.u, (1 - fl.k) * u);
  }
  return { w, u, world: S.world };
}
// Start holding a flood at (x, y), as of time `at`; snap: on the feet of the walker whose box holds the
// point. A flood still on screen is picked up instead: it keeps its centre and grows on from where it is.
function holdFlood(x, y, by, snap = true, at = performance.now()) {
  if (S.mode === 3 || S.mode === 5 || S.layers || !S.plate || (S.flood && S.flood.held)) return false;
  const cur = floodState(at);
  if (cur) Object.assign(S.flood, { held: true, by, t0: at, u0: cur.u, k0: cur.kLin, keep: false, hold: null, fresh: false });
  else {
    const area = (b) => (b[2] - b[0]) * (b[3] - b[1]);
    const t = snap && S.tracks.filter((t) => t.box && t.fx != null && x >= t.box[0] && x <= t.box[2] && y >= t.box[1] && y <= t.box[3])
      .sort((a, b) => area(a.box) - area(b.box))[0];
    S.flood = { x: t ? t.fx : x, y: t ? Math.min(0.999, t.fy) : y, held: true, by, t0: at, u0: 0, k0: 0, fresh: true };
  }
  S.flood.from = [S.flood.x, S.flood.y, x, y];          // moving steers it, relative to the press
  S.floodUsed = true; S.floods++;
  return true;
}
function steerFlood(x, y) {
  const f = S.flood; if (!f || !f.held || !f.from) return;
  f.x = Math.min(1, Math.max(0, f.from[0] + x - f.from[2]));
  f.y = Math.min(1, Math.max(0, f.from[1] + y - f.from[3]));
}
// Let go at time `at`: it drains back, unless keepIfFull and it was held full for FLOOD_KEEP (then it
// stays, until a tap).
function releaseFlood(keepIfFull, at = performance.now()) {
  const f = S.flood;
  if (!f) return;
  at = Math.max(at, f.t0 || 0);
  const cur = floodState(at);
  if (!cur) return;
  const full = f.held && f.hold == null && f.u0 + (at - f.t0) / FLOOD_GROW >= 1 + FLOOD_KEEP / FLOOD_GROW;
  if (keepIfFull && (full || f.keep)) { Object.assign(f, { held: false, keep: true }); return; }
  Object.assign(f, { held: false, keep: false, hold: null, tr: at, ur: cur.u, kr: cur.kLin });
  setTimeout(() => { if (S.flood === f && !f.held && !f.keep && f.hold == null) S.flood = null; },
             Math.max(0, at + FLOOD_DRAIN + 20 - performance.now()));
}

// People as blobs on a coarse grid, tracked across frames. Each gets one weight from where they stand
// (portal and depth rules), and a crossing (a person going from real to the other world) plays a
// whoosh and, for a person-shaped track, a short style burst on that person only. Crossings always use
// the binary rule (w), so they fire at the line in Grow too; Grow's per-person colour is u at the feet.
// While a flood is open, it decides for everyone by their feet, so crossings and bursts follow its front.
const GW = 160;
let pwU8 = null, lastBlobs = [];
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
  const prev = S.tracks, next = [], now = performance.now(), fl = floodState(now);
  for (const t of prev) t.used = false;
  let massIn = 0, mass = 0;
  for (const b of blobs) {
    const { w: raw, u: rawU, world } = personRule(b, fl);
    // match the nearest track; the reach grows with the time since it was seen (a slow device analyses
    // fewer frames, and a walker covers about 0.15 of the frame per second)
    let best = null, bd = Infinity;
    for (const t of prev) {
      if (t.used) continue;
      const d = Math.hypot(t.cx - b.cx, t.cy - b.cy), reach = 0.08 + 0.25 * Math.min(1, (now - t.seen) / 1000);
      if (d < reach && d < bd) { best = t; bd = d; }
    }
    const t = best || { id: ++S.trackId, w: raw, u: rawU, inside: raw > 0.5, lastBurst: 0 };
    t.used = true; t.seen = now;
    const kw = fl ? 0.7 : 0.35;                  // a flood's front moves fast and one way: follow it closely
    t.cx = b.cx; t.cy = b.cy; t.w = (1 - kw) * t.w + kw * raw; t.u = (1 - kw) * t.u + kw * rawU;
    t.cnt = b.cnt; t.frac = b.cnt / (GW * GH); t.box = b.box; t.hw = b.hw; t.fx = b.fx; t.fy = b.fy;
    if (world >= 0) t.world = world;             // (stepping off the paint, they keep the last one, fading out)
    if (!t.inside && t.w > 0.7 && best) onCrossing(t);
    if (t.w > 0.7) t.inside = true; else if (t.w < 0.3) t.inside = false;
    b.w = t.w; b.u = t.u; b.world = t.world; next.push(t);
    massIn += b.cnt * t.w; mass += b.cnt;
  }
  S.tracks = next; lastBlobs = blobs;
  if (S.burst && !S.burst.fixed) {               // the burst box follows its person
    const t = next.find((x) => x.id === S.burst.id);
    if (t) { S.burst.box = padBox(t.box); S.burst.seen = now; }
    else if (now - S.burst.seen > 300) S.burst = null;
  }
  S.across = mass ? massIn / mass : 0;
  const a = aud(); if (a) a.setAcross(S.across);
  // (while a flood is open, render() uploads them every frame, fresh from its moving front)
  if (FEET.has(S.mode) && S.mode !== 5 && !fl) uploadPW(blobs, (b) => (S.seam === 'grow' ? b.u : b.w));   // (Paint: render, per world)
}
// The per-person weights (uPW) on the GW grid: each person's cells, grown by 2, hold value(blob) in 0..1
// (r) and 255 (g: a person is here; compositor.js feetAt).
function uploadPW(blobs, value) {
  const m = S.mask; if (!m) return;
  const GH = Math.round(GW * m.h / m.w);
  if (!pwU8 || pwU8.length !== 2 * GW * GH) pwU8 = new Uint8Array(2 * GW * GH);
  pwU8.fill(0);
  for (const b of blobs) {
    const v = Math.round(value(b) * 255);
    for (const j of b.cells) {
      const x = j % GW, y = (j / GW) | 0;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= GW || yy >= GH) continue;
        const i = 2 * (yy * GW + xx);
        pwU8[i] = Math.max(pwU8[i], v); pwU8[i + 1] = 255;
      }
    }
  }
  comp.uploadRG8(comp.tex.pw, pwU8, GW, GH);
}
function onCrossing(t) {
  const now = performance.now();
  if (now - (S.lastCrossT || 0) >= 600) {
    S.lastCrossT = now; S.crossings++;
    const a = aud(); if (a && !S.muted) a.whoosh();
  }
  if (CFG.floodHint && !S.floodHinted && !S.floodUsed && !S.layers) { S.floodHinted = true; toast('Hold to flood.', 3000); }
  if (!S.autoGlitch || S.layers) return;
  // a person, not a car or a merged crowd: upright, and between 0.5% and 8% of the frame
  if (t.hw < 1.3 || t.frac < 0.005 || t.frac > 0.08) return;
  if (now - (t.lastBurst || 0) < 2000 || now - (S.lastBurstT || 0) < 900) return;
  startBurst(t, 900, t.id * 7919 + S.crossings);
}
const padBox = (b) => [Math.max(0, b[0] - 0.04), Math.max(0, b[1] - 0.04), Math.min(1, b[2] + 0.04), Math.min(1, b[3] + 0.04)];
// The crosser flashes through styles, faster and faster (switch every 4, then 2, then 1 frame at 30 fps),
// and lands in the world. A figure covering more than 10% of the frame switches
// at most 3 times a second (flash safety).
function startBurst(t, ms, seed, fixed = false) {
  const now = performance.now();
  t.lastBurst = now; S.lastBurstT = now; S.bursts++;
  S.burstLog.push(now); if (S.burstLog.length > 32) S.burstLog.shift();     // (tests: the spacing of bursts)
  const box = padBox(t.box);
  const big = (box[2] - box[0]) * (box[3] - box[1]) > 0.10;
  const sched = [];
  for (let k = 0; k < ms;) { sched.push(k); k += big ? 334 : k < ms * 0.5 ? 133 : k < ms * 0.83 ? 67 : 33; }
  const into = S.mode === 5 && t.world >= 0 ? t.world : S.world;     // Paint: the world they stepped into
  const here = S.worlds[into].kind;
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
  S.burst = { id: t.id, t0: now, ms, box, sched, styles, seen: now, fixed, world: into };
}
function burstState(now) {
  const b = S.burst;
  if (!b) return null;
  const el = now - b.t0;
  if (el >= b.ms) { S.burst = null; return null; }
  let i = 0;
  while (i + 1 < b.sched.length && b.sched[i + 1] <= el) i++;
  // c: in Grow the crosser's colour is in full during the burst, easing back to the rule's own over
  // its last quarter, so the landing does not pop
  return { box: b.box, per: b.styles[i], edge: el - b.sched[i] < 70, c: 1 - smooth01((el / b.ms - 0.75) / 0.25) };
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
  if (old && i !== S.world) S.prevW = old;
  S.world = i;
  syncRungs();
  if (!quiet && !REDUCED && comp && S.plate && old && old !== currentWorld() && S.mode !== 5) {   // roll in from the horizon
    endWave();
    S.wave = { t0: performance.now(), prevKind: old.kind, prevTex: old.tex, prevW: old, prevPattern: old.pattern,
               field: waveField(currentWorld(), old) };
  } else if (!quiet) flash(0.25);
  const a = aud(); if (a) a.setWorld(i);
  if (!quiet) toast(S.mode === 5 ? `Paint with ${displayName(S.worlds[i])}` : worldLabel(S.worlds[i]));
  renderControls();
}
// A generated world's ladder (scenes.json worlds[i].ladder): the rung images between the plate and the
// world. Only the current world and the one before it are on the GPU (a world change unmakes the old
// world through its own rungs), in the two slots of the compositor's ladder texture. A world without
// rungs (made on the spot, or dropped in) grows straight from the plate: one step.
function syncRungs() {
  if (!comp || !S.plate) return;
  const want = [currentWorld(), S.prevW].filter((w) => w && w.kind === 0 && w.img);
  for (const w of want) {
    if (S.slots.includes(w)) continue;
    const s = want.includes(S.slots[0]) ? 1 : 0;
    const imgs = [...(w.ladder || []).slice(0, 2).map((r) => r.img), w.img];
    comp.setLadder(1 + 3 * s, imgs.map((im) => toImageData(im, canvas.width, canvas.height)));
    S.slots[s] = w;
  }
}
// Grow keeps people behind a world change's front in the old world's colour: both colour fields in one
// texture for the wave's 1.4 s (an old filter world colours people with its own filter instead).
function waveField(cur, old) {
  if (old.kind !== 0) return null;
  const id = { gx: 1, gy: 1, coeffs: IDENTITY_FIELD };
  return comp.newWaveField(cur.fieldData || id, old.fieldData || id);
}
function endWave() {
  if (S.wave && S.wave.field) comp.gl.deleteTexture(S.wave.field.tex);
  S.wave = null;
}
function ladderOf(w) {                   // {n steps above the plate, slot}; n 0: not loaded
  const s = w ? S.slots.indexOf(w) : -1;
  return s < 0 ? { n: 0, slot: 0 } : { n: Math.min(2, (w.ladder || []).length) + 1, slot: s };
}
// The per-person weights (uPW) hold each person's value under the current rule and seam. When the rule,
// the seam or the paint changes, recompute them from where people stand now (render does it once per
// frame), or a paused frame keeps the old ones until the next analysed frame. A flood re-uploads its own.
function refreshPW() {
  if (!comp || !FEET.has(S.mode) || floodState(performance.now())) return;
  if (S.mode === 5) {                              // Paint: fresh values on the blobs; render uploads them per world
    for (const b of lastBlobs) { const r = personRule(b, null); b.w = r.w; b.u = r.u; if (r.world >= 0) b.world = r.world; }
    return;
  }
  const grow = S.seam === 'grow';
  uploadPW(lastBlobs, (b) => { const r = personRule(b, null); return grow ? r.u : r.w; });
}
function setSeam(s, quiet = false) {
  S.seam = s === 'cut' ? 'cut' : 'grow';
  S.pwStale = true;
  if (!quiet) toast(S.seam === 'grow' ? 'Morph: the world grows out of the filmed scene' : 'Cut: the exact seam');
  renderControls();
}
const MODE_TIPS = {
  4: 'Rule: depth. Tap or drag to choose how far the other world begins.',
  5: 'Paint where the world shows. Right-drag or the eraser paints reality back; scroll sizes the brush.',
};
function setMode(m, quiet = false) {
  S.mode = m; S.tracks = []; S.burst = null; S.pwStale = true;
  if (!quiet) toast(MODE_TIPS[m] || `Rule: ${MODES[m]}`, m === 5 ? 4500 : 2600);
  renderControls();
}
// ------------------------------------------------------------------ the paint brush (paint.js)
// A stroke paints the current world in (or, erasing, reality back) along the pointer's path. Sizes are
// in px at 768 wide, like every other length on the page.
// Several worlds can be painted at once: the current world chip is the brush's world.
function brushPx(r = S.brush.r) { return r * canvas.width / 768; }
function ensurePainting() { if (painting.resize(canvas.width, canvas.height)) dropPaintTex(); }
function dropPaintTex() { for (const t of paintTex.values()) comp.gl.deleteTexture(t); paintTex.clear(); }
function texOf(k) { if (!paintTex.has(k)) paintTex.set(k, comp.newTexture()); return paintTex.get(k); }
function beginStroke(x, y, erase, r = S.brush.r) {
  ensurePainting();
  painting.begin(S.world, brushPx(r), erase); painting.to(x, y);
  S.pwStale = true;
}
function strokeTo(x, y) { painting.to(x, y); S.pwStale = true; }
function endStroke() { painting.end(); S.pwStale = true; renderControls(); }
function clearPaint(quiet = false) {
  painting.clear(); S.pwStale = true; renderControls();
  if (!quiet) toast('Paint cleared (undo brings it back)');
}
function undoPaint() {
  const ok = painting.undo(); S.pwStale = true; renderControls();
  toast(ok ? 'Undone' : 'Nothing to undo', 1000);
}
function resetPaint() { painting.reset(); if (comp) dropPaintTex(); S.pwStale = true; }   // a new scene
function setEraser(on) { S.brush.erase = on; renderControls(); }
function setField(w, coeffs, gx = 1, gy = 1) {
  if (w.field) comp.gl.deleteTexture(w.field.tex);
  w.field = comp.newField(gx, gy, coeffs);
  w.fieldData = { gx, gy, coeffs };
}
// ladder: [{img, n, src}] rung images from the plate's side (see syncRungs); pattern: 'dots' grows its
// detail in halftone dots (Cyberpunk, Comic)
async function addImageWorld(name, src, url, { quiet = false, group = 'generated', colour = null, gen = null,
                                              ladder = null, pattern = null } = {}) {
  const bmp = src instanceof ImageBitmap ? src : await createImageBitmap(src);
  const w = { name, kind: 0, img: bmp, url, group, gen, baked: !!colour, field: null,
              ladder: (ladder || []).map((r) => ({ img: r.img, n: r.n, src: r.src })),
              pattern: pattern || (/cyberpunk|comic/i.test(name) ? 'dots' : 'noise') };
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
  endWave(); S.prevW = null; S.slots = [null, null];
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
    const bitmap = (src) => fetchBlob(src).then((b) => createImageBitmap(b));
    const [clip, plate, far, ...worlds] = await Promise.all([         // each world: [image, ...its rungs]
      fetchBlob(sc.clip), bitmap(sc.plate),
      sc.far ? fetchBlob(sc.far).then((b) => decodeFar(b, sc.farGmax || 0.02)) : null,
      ...sc.worlds.map((w) => Promise.all([bitmap(w.src), ...(w.ladder || []).map((r) => bitmap(r.src))]))]);
    if (g !== sceneGen) return;
    removeImageWorlds();
    S.scene = i;
    resetPaint();
    S.layers = false; S.layer = -1;
    await useSource('clip', { src: URL.createObjectURL(clip), plate, startTime: sc.startTime || 0 });
    setFar(far);
    if (sc.line) Object.assign(S.line, sc.line);
    if (sc.portal) Object.assign(S.portal, sc.portal);
    if (sc.tau != null) S.tau = sc.tau;
    for (let k = 0; k < worlds.length; k++) {
      const w = sc.worlds[k], [img, ...rungs] = worlds[k];
      const ladder = (w.ladder || []).map((r, j) => ({ img: rungs[j], n: r.n, src: r.src }));
      await addImageWorld(w.name, img, w.src, { quiet: true, colour: w.colour, gen: w.gen, ladder, pattern: w.pattern });
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
  resetPaint();
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
  else if (over.view == null && over.rung == null) return false;   // (a forced view needs no camera frame)
  if (S.autoCycle && now - S.lastCycle > 6000 && !over.view && over.rung == null) { S.lastCycle = now; stepWorld(1); }
  const W = canvas.width, H = canvas.height, w = currentWorld();
  let bg = w.kind, per = w.kind, worldTex = w.tex, field = w.field, lad = ladderOf(w), pattern = w.pattern;
  let glitch = 0;
  if (now < S.glitchUntil) {             // the manual glitch: the person flashes through worlds, the frame tears
    glitch = 1;
    const kinds = [w.kind, 1, 2, 3, 4, 5, 6];
    per = kinds[(Math.random() * kinds.length) | 0];
    if (Math.random() < 0.15) {
      const kb = S.worlds[(Math.random() * S.worlds.length) | 0];
      bg = kb.kind; worldTex = kb.tex; lad = ladderOf(kb); pattern = kb.pattern;
    }
  }
  if (bg === 0 && !worldTex) bg = 1;
  const bs = burstState(now);
  // the world-change wave: Cut rolls a thin front over 1.2 s; Grow a 0.30-farness front over 1.4 s
  const grow = S.seam === 'grow';
  let wave = null;
  if (S.wave) {
    const u = S.waveHold != null ? S.waveHold : (now - S.wave.t0) / (grow ? 1400 : 1200);
    if (u >= 1 && S.waveHold == null) endWave();
    else wave = grow ? 1.25 - 1.5 * smooth01(u * 1.1) : 1.08 - 1.2 * smooth01(Math.min(1, u) * 1.15);
  }
  if (grow && wave != null && S.wave.field) field = S.wave.field;
  // a flood: everyone by their feet, fresh from its front every frame (the clip may be paused)
  holdCheck(now);
  const fl = floodState(now);
  floodShown = fl ? fl.k : 0;
  if (fl) uploadPW(lastBlobs, (b) => { const r = personRule(b, fl); return grow ? r.u : r.w; });
  floodSound(fl);
  ensurePainting();
  for (const [k, m] of painting.masks) if (m.dirty) { comp.uploadPaint(texOf(k), m.canvas); m.dirty = false; }
  if (S.pwStale) { S.pwStale = false; refreshPW(); }
  const p = {
    bg, per, worldTex, field, mode: S.mode,
    seam: grow, band: S.band, lad, pattern, prevLad: S.wave ? ladderOf(S.wave.prevW) : null,
    prevPattern: S.wave && S.wave.prevPattern, perPrev: S.wave ? S.wave.prevKind : -1, burstC: bs ? bs.c : 1,
    p0: [S.line.x * W, S.line.y * H], n: [Math.cos(S.line.angle), Math.sin(S.line.angle)],
    portal: [S.portal.x * W, S.portal.y * H, S.portal.r * W * breath()], squash: PORTAL_SQUASH,
    flood: fl && [fl.cx, fl.cy, fl.r], floodSq: fl ? fl.sq : 1, floodBand: fl ? fl.band : 0.6, floodK: fl ? fl.k : 0,
    lens: [S.lens.x * W, S.lens.y * H], lensR: S.lens.r * H,
    glitch, seed: Math.random() * 100, flash: S.flash, mirror: S.mirror, debug: S.debug,
    hasPlate: !!S.plate, diff: S.diff, gain: S.gain,
    farTex: S.far && S.far.tex, tau: S.tau,
    waveOn: wave != null, wave, prevKind: S.wave && S.wave.prevKind, prevTex: S.wave && S.wave.prevTex,
    burst: !!bs, burstBox: bs && bs.box, burstPer: bs ? bs.per : -1, burstEdge: bs && bs.edge,
    paintTex: paintTex.get(S.world) || null,
  };
  // Paint: the people standing in the current world (drawPainted uploads each painted world's own)
  if (S.mode === 5 && !fl) uploadPW(lastBlobs, (b) => (b.world === S.world ? (grow ? b.u : b.w) : 0));
  if (over.rung != null) {               // the background alone at a ladder rung (exposure gain 1)
    comp.draw({ ...p, view: 0, flash: 0, glitch: 0, seam: true, waveOn: false, forceRung: over.rung, gain: 1 });
  } else if (over.view != null) {
    comp.draw({ ...p, view: over.view, flash: 0 });
  } else if (S.layers) {
    comp.clear();
    if (S.layer >= 0) comp.draw({ ...p, view: LAYERS[S.layer].view, flash: 0 });
    else for (const [k, r] of tileRects().entries()) comp.draw({ ...p, view: LAYERS[k].view, flash: 0, vp: [r.x, H - r.y - r.h, r.w, r.h] });
  } else if (S.mode === 5) {
    drawPainted(p, bs, grow);
  } else {
    comp.draw(p);
  }
  S.flash *= 0.82; if (S.flash < 0.01) S.flash = 0;
  S.frames++;
  placeOverlays();
  placeBrush();
  if (now - S.lastFpsT > 500) {
    S.fps = (S.frames - (S.fpsBase || 0)) * 1000 / (now - S.lastFpsT); S.fpsBase = S.frames; S.lastFpsT = now;
    const dbg = S.debug ? ` · ${S.fps.toFixed(0)} fps · mask ${S.segMs.toFixed(0)} ms (${S.delegate}) · gain ${S.gain.toFixed(2)}` : '';
    const where = S.scenes[S.scene] ? ` · ${S.scenes[S.scene].name}` : S.source === 'clip' ? ' · recorded clip' : '';
    const view = S.layers ? ' · layers' : '';
    const nPainted = S.mode === 5 ? painting.worlds().length : 0;
    const rule = nPainted > 1 ? `paint · ${nPainted} worlds` : MODES[S.mode];
    $('hudsub').textContent = `${displayName(w)} · ${rule}${fl ? ' · flood' : ''}${where}${view}${S.progress ? ' · ' + S.progress : ''}${dbg}`;
  }
  return true;
}
// Paint: one pass per painted world, each laid over the last by its own mask (the masks never overlap, so
// the order only matters at soft edges); the first pass also draws the camera frame everywhere else.
// Each pass gets its world's image, colour field and paint, and the people standing in that world.
function drawPainted(p, bs, grow) {
  const ws = painting.worlds();
  if (!ws.length) { uploadPW(lastBlobs, () => 0); comp.draw(p); return; }   // nothing painted: the camera frame
  ws.forEach((k, i) => {
    const w = S.worlds[k], burst = !!bs && !!S.burst && S.burst.world === k;
    uploadPW(lastBlobs, (b) => (b.world === k ? (grow ? b.u : b.w) : 0));
    comp.draw({ ...p, bg: w.kind === 0 && !w.tex ? 1 : w.kind, per: p.glitch ? p.per : w.kind, worldTex: w.tex,
                field: w.field, lad: ladderOf(w), pattern: w.pattern, paintTex: texOf(k), layer: i > 0,
                flash: i ? 0 : p.flash, waveOn: false, wave: null, burst, burstBox: burst ? bs.box : null,
                burstPer: burst ? bs.per : -1, burstEdge: burst && bs.edge, burstC: burst ? bs.c : 1 });
  });
}
// the flood's sound follows its growth (0 lets it go); the master gain mutes it like the rest
let floodLevel = 0, floodShown = 0;
function floodSound(fl) {
  const a = aud(), v = fl ? fl.u : 0;
  if (a && (v > 0 || floodLevel > 0)) { a.flood(v); floodLevel = v; }
}

// ------------------------------------------------------------------ on-canvas DOM: line handle, side tags, layer labels
let lastOverlayKey = '';
function placeOverlays() {
  const handle = $('handle'), tagA = $('tag-real'), tagB = $('tag-world'), labels = $('layer-labels'), card = $('sdcard');
  if (!handle && !labels) return;
  const st = $('stage').getBoundingClientRect(), r = canvas.getBoundingClientRect();
  const sx = r.width / canvas.width, ox = r.left - st.left, oy = r.top - st.top;
  const showLine = !S.layers && S.mode === 0 && !!S.plate && floodShown < 0.5;     // (a flood has taken over)
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

// The brush's outline follows the pointer in Paint (dashed while erasing).
let brushEl = null;
function placeBrush() {
  const show = !S.layers && S.mode === 5 && !!S.brush.at && !!S.plate;
  if (!brushEl) {
    if (!show) return;
    brushEl = document.createElement('div');
    brushEl.className = 'overlay';
    brushEl.style.cssText = 'border-radius:50%;border:1.5px solid rgba(255,255,255,.9);box-shadow:0 0 0 1px rgba(0,0,0,.45)';
    $('stage').append(brushEl);
  }
  brushEl.hidden = !show;
  if (!show) return;
  const st = $('stage').getBoundingClientRect(), r = canvas.getBoundingClientRect();
  const d = 2 * brushPx() * r.width / canvas.width;
  const x = r.left - st.left + (S.mirror ? 1 - S.brush.at[0] : S.brush.at[0]) * r.width, y = r.top - st.top + S.brush.at[1] * r.height;
  brushEl.style.width = brushEl.style.height = `${d}px`;
  brushEl.style.transform = `translate(${x - d / 2}px, ${y - d / 2}px)`;
  brushEl.style.borderStyle = S.brush.erase || (press && press.erase) ? 'dashed' : 'solid';
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
// A press is a tap (placed on release: the line, ring, lens or depth contour goes there), a drag (once it
// moves more than SLOP_PX: the rule follows, as before), or, held still for HOLD_MS and at least 3 drawn
// frames, a flood (moving then steers it). A tap while a flood stays lets it drain. One pointer at a
// time. Moves arrive with frames, so the frame count keeps a drag a drag on a slow page (at 60 fps it
// adds nothing); an event from before the hold was seen still counts as before it.
let press = null;                                // {id, sx, sy (client px), x, y (frame), t, f, kind, at}
canvas.addEventListener('contextmenu', (e) => e.preventDefault());     // a long press floods; no menu
canvas.addEventListener('pointerdown', (e) => {
  if (S.layers) {                                // tap a tile to see it full size; tap again to go back
    if (narrowStage()) S.layer = (S.layer + 1) % LAYERS.length;
    else if (S.layer >= 0) S.layer = -1;
    else S.layer = tileAt(e);
    return;
  }
  if (press) {                                   // a second finger is ignored; a press that never ended is
    if (press.id !== e.pointerId && canvas.hasPointerCapture(press.id)) return;
    endPress({ pointerId: press.id, timeStamp: e.timeStamp }, true);
  }
  try { canvas.setPointerCapture(e.pointerId); } catch { /* not an active pointer (a synthetic event) */ }
  const [x, y] = toFrame(e);
  press = { id: e.pointerId, sx: e.clientX, sy: e.clientY, x, y, t: performance.now(), f: S.frames, kind: 'tap' };
  if (S.mode === 5) {                            // Paint: every press is a stroke (no tap, drag or flood)
    // the right button, Alt, a pen's eraser end or the Eraser toggle paint reality back
    Object.assign(press, { kind: 'paint', erase: S.brush.erase || e.button === 2 || e.button === 5 || e.altKey });
    beginStroke(x, y, press.erase);
    S.brush.at = [x, y];
  }
});
// (each frame, from render) the press has been held still long enough: a flood, from now
function holdCheck(now) {
  const p = press;
  if (p && p.kind === 'tap' && now - p.t >= HOLD_MS && S.frames - p.f >= 3 && holdFlood(p.x, p.y, 'pointer')) {
    p.kind = 'flood'; p.at = S.flood.t0;
  }
}
// the move or release that ends the hold happened before the hold was seen: no flood after all (one it
// picked up drains)
function unhold(p, at) {
  const fresh = !!(S.flood && S.flood.fresh);
  if (fresh) S.flood = null; else releaseFlood(false, at);
  p.kind = 'tap';
  return fresh;
}
canvas.addEventListener('pointermove', (e) => {
  if (S.layers) return;
  const p = press;
  if (S.mode === 5) S.brush.at = toFrame(e);
  if (p && p.kind === 'paint' && e.pointerId === p.id) {
    // every sample the browser saw since the last event, so a fast stroke follows the hand
    for (const c of (e.getCoalescedEvents ? e.getCoalescedEvents() : []).concat([e])) strokeTo(...toFrame(c));
    return;
  }
  if (p && e.pointerId === p.id) {
    const moved = Math.hypot(e.clientX - p.sx, e.clientY - p.sy) > SLOP_PX;
    if (p.kind === 'flood' && moved && e.timeStamp < p.at) unhold(p, e.timeStamp);
    if (p.kind === 'tap' && moved) {
      p.kind = 'drag';
      if (S.flood && S.flood.keep) releaseFlood(false, e.timeStamp);   // moving the rule lets a flood that stays go
    }
    if (p.kind === 'drag') onPointer(e);
    else if (p.kind === 'flood') steerFlood(...toFrame(e));
  } else if (S.mode === 2 && e.pointerType === 'mouse') onPointer(e);   // the lens follows the mouse
});
function endPress(e, cancelled) {
  const p = press;
  if (!p || e.pointerId !== p.id) return;
  press = null;
  if (p.kind === 'paint') { endStroke(); return; }
  if (p.kind === 'flood' && e.timeStamp < p.at && !cancelled) {   // a tap after all: it places, unless it
    if (unhold(p, e.timeStamp)) place(p.x, p.y);             // let a flood it picked up go
    if (S.mode === 0) S.dragged = true;
    return;
  }
  if (p.kind === 'flood') { releaseFlood(true, e.timeStamp); return; }
  if (p.kind === 'tap' && !cancelled) {
    if (S.flood && S.flood.keep) releaseFlood(false, e.timeStamp);
    else place(p.x, p.y);
  }
  if (!cancelled && S.mode === 0) S.dragged = true;
}
canvas.addEventListener('pointerup', (e) => endPress(e, false));
canvas.addEventListener('pointerleave', () => { S.brush.at = null; });
canvas.addEventListener('pointercancel', (e) => endPress(e, true));
canvas.addEventListener('lostpointercapture', (e) => endPress(e, true));
function onPointer(e) { place(...toFrame(e)); }
function place(x, y) {
  if (S.mode === 0) { S.line.x = x; S.line.y = y; }
  else if (S.mode === 1) { S.portal.x = x; S.portal.y = y; }
  else if (S.mode === 2) { S.lens.x = x; S.lens.y = y; }
  else if (S.mode === 4) S.tau = Math.min(0.98, Math.max(0.02, farAt(x, y)));   // the contour goes where you point
}
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const k = e.deltaY > 0 ? 0.92 : 1.08;
  if (S.mode === 0 && S.seam === 'grow') {       // the morph band on the line: 24 .. 420 px (at 768 wide)
    S.band = Math.min(420, Math.max(24, S.band * k));
    toast(`Morph band ${Math.round(S.band)} px`, 1200);
  }
  if (S.mode === 1) S.portal.r = Math.min(0.6, Math.max(0.05, S.portal.r * k));
  if (S.mode === 2) S.lens.r = Math.min(0.8, Math.max(0.05, S.lens.r * k));
  if (S.mode === 4) S.tau = Math.min(0.98, Math.max(0.02, S.tau + (e.deltaY > 0 ? -0.02 : 0.02)));
  if (S.mode === 5) setBrush(S.brush.r * k);
}, { passive: false });
function setBrush(r) {                           // 6 .. 200 px at 768 wide
  S.brush.r = Math.min(200, Math.max(6, r));
  toast(`Brush ${Math.round(S.brush.r)} px`, 1000);
}

function glitchBurst() { S.glitchUntil = performance.now() + (REDUCED ? 500 : 1500); }
function toggleCycle() { S.autoCycle = !S.autoCycle; S.lastCycle = performance.now(); toast(`Auto-cycle ${S.autoCycle ? 'on' : 'off'}`); renderControls(); }
function toggleSound() {
  S.muted = !S.muted;
  if (audio || !S.muted) ensureAudio();
  toast(S.muted ? 'Sound off' : 'Sound on');
  renderControls();
}
function toggleSeam() { setSeam(S.seam === 'grow' ? 'cut' : 'grow'); }
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
  if ((e.ctrlKey || e.metaKey) && k === 'z') { if (S.mode === 5) { undoPaint(); e.preventDefault(); } return; }
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
  else if (k === 'e') toggleSeam();
  else if (k === 'o') { if (!e.repeat) keyFlood(true, e.timeStamp); }
  else if (k === 'f') toggleFullscreen();
  else if (k === 'escape' && $('help') && !$('help').hidden) toggleHelp(false);
  else if (k === 'escape' && S.layers) { if (S.layer >= 0 && !narrowStage()) S.layer = -1; else toggleLayers(false); }
  else if (k === 'h') toggleHelp();
  else if (k === 'p') setMode(5);
  else if (S.mode === 5 && e.key === '[') setBrush(S.brush.r / 1.2);
  else if (S.mode === 5 && e.key === ']') setBrush(S.brush.r * 1.2);
  else if (S.mode === 5 && (e.key === 'Backspace' || e.key === 'Delete')) clearPaint();
  else if (e.key === '[') S.line.angle -= 0.05;
  else if (e.key === ']') S.line.angle += 0.05;
  else if (e.key === 'ArrowLeft') S.line.x = Math.max(0, S.line.x - 0.01);
  else if (e.key === 'ArrowRight') S.line.x = Math.min(1, S.line.x + 0.01);
});
// O: hold to flood from the centre of the frame (the kiosk's press and hold); O again lets one that stays go
let keyHeld = false;
function keyFlood(down, at = performance.now()) {
  if (down) {
    if (S.flood && S.flood.keep) { releaseFlood(false, at); keyHeld = false; }
    else keyHeld = holdFlood(0.5, 0.5, 'key', false, at);
  } else if (keyHeld) {
    keyHeld = false;
    if (S.flood && S.flood.held && S.flood.by === 'key') releaseFlood(true, at);
  }
}
addEventListener('keyup', (e) => { if (e.key.toLowerCase() === 'o') keyFlood(false, e.timeStamp); });
addEventListener('blur', () => keyFlood(false));
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
  if ($('b-seam')) $('b-seam').setAttribute('aria-pressed', String(S.seam === 'grow'));
  if ($('paint-tools')) $('paint-tools').hidden = S.mode !== 5;
  if ($('b-erase')) $('b-erase').setAttribute('aria-pressed', String(S.brush.erase));
  const box = $('worlds');
  if (box) {
    const titles = { generated: 'AI-generated · made once', yours: 'Your images', filter: 'Filters (no AI)' };
    const order = visualOrder(), kids = [], painted = S.mode === 5 ? new Set(painting.worlds()) : new Set();
    let last = '';
    order.forEach((i, n) => {
      const w = S.worlds[i], g = groupOf(w);
      if (g !== last) { const t = document.createElement('span'); t.className = 'group'; t.textContent = titles[g]; kids.push(t); last = g; }
      kids.push(chip(displayName(w), i === S.world, () => setWorld(i), `${g}${painted.has(i) ? ' painted' : ''}`, n < 9 ? String(n + 1) : ''));
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
  on('b-seam', toggleSeam);
  on('b-erase', () => setEraser(!S.brush.erase)); on('b-clear', () => clearPaint()); on('b-undo', undoPaint);
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
// mean |output - camera| (0-255) over columns [x0, x1) and rows [y0, y1) (fractions), every 2nd pixel
function diffCamera(x0, x1, y0, y1) {
  const { px, w, h } = comp.readPixels();
  wctx.drawImage(S.video, 0, 0, w, h);
  const cam = wctx.getImageData(0, 0, w, h).data;
  let sum = 0, n = 0;
  for (let y = Math.floor(y0 * h); y < Math.floor(y1 * h); y += 2) for (let x = Math.floor(x0 * w); x < Math.floor(x1 * w); x += 2) {
    const xo = S.mirror ? w - 1 - x : x;
    const i = 4 * ((h - 1 - y) * w + xo), j = 4 * (y * w + x);
    sum += Math.abs(px[i] - cam[j]) + Math.abs(px[i + 1] - cam[j + 1]) + Math.abs(px[i + 2] - cam[j + 2]); n += 3;
  }
  return n ? sum / n : 0;
}
// mean |page - reference image| (0-255) of what was just drawn, every 2nd pixel
function diffImage(ref) {
  const { px, w, h, at } = readFrame();
  let sum = 0, n = 0;
  for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {
    const i = at(x, y), j = 4 * (y * w + x);
    sum += Math.abs(px[i] - ref[j]) + Math.abs(px[i + 1] - ref[j + 1]) + Math.abs(px[i + 2] - ref[j + 2]); n += 3;
  }
  return sum / n;
}
async function loadRef(url) {
  const bmp = await createImageBitmap(await fetchBlob(url), { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  return toImageData(bmp, canvas.width, canvas.height).data;
}
window.__portal = {
  get state() { return S; },
  setWorld, setMode: (m) => setMode(m, true), setMirror: (b) => { S.mirror = b; },
  glitch: (ms) => { S.glitchUntil = performance.now() + ms; }, capture: () => capturePlate(0),
  setLine: (x, angle = 0) => { S.line.x = x; S.line.angle = angle; },
  setDebug: (b) => { S.debug = b; }, loadScene, visualOrder, displayName: (i) => displayName(S.worlds[i]),
  tiles: () => tileRects(), narrow: () => narrowStage(),
  audioState: () => (audio ? audio.ctx.state : 'none'),
  // the flood rush's gain (0 when none plays; null without sound)
  floodGain: () => (audio ? audio.floodGain() : null),
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
    const ref = await loadRef(refUrl);
    render(performance.now(), { view: 6 });
    return diffImage(ref);
  },
  // mean |output - camera| (0-255) over a column band [x0, x1) of the frame (of the last frame drawn)
  compare(x0, x1) { return diffCamera(x0, x1, 0, 1); },
  // the same over a row band [y0, y1)
  compareRows(y0, y1) { return diffCamera(0, 1, y0, y1); },
  // ... and over a box, columns [x0, x1) and rows [y0, y1)
  compareBox(x0, x1, y0, y1) { return diffCamera(x0, x1, y0, y1); },
  // analyse the current video frame again, n times: a paused frame's mask settles on it (its fading
  // trail goes, as in motion)
  reanalyse(n = 1) { for (let i = 0; i < n; i++) onVideoFrame(); return window.__portal.maskStats(); },
  // hold a flood centred at (x, y) (frame coords) at phase u in [0, 1], the rule taken over; null lets
  // it drain as a release would
  flood(x, y, u) {
    if (u == null) { if (S.flood) releaseFlood(false); return; }
    S.flood = { x, y, hold: u, held: false, by: 'test' };
  },
  // draw a frame now (then compare() reads it)
  renderNow() { return render(performance.now()); },
  // Paint: a stroke through points [[x, y], ...] (frame fractions) with brush radius r (px at 768 wide);
  // clear; the painted value at a point
  paint(points, { r = 36, erase = false, world = S.world } = {}) {
    const keep = S.world; S.world = world;
    points.forEach(([x, y], i) => (i ? strokeTo(x, y) : beginStroke(x, y, erase, r)));
    endStroke(); S.world = keep;
  },
  clearPaint: () => clearPaint(true),
  undoPaint,
  resetPaint,
  paintAt: (x, y) => painting.top(x, y).v,                 // how much paint, of any world
  paintWorldAt: (x, y) => painting.top(x, y).world,        // which world (-1: none)
  paintedWorlds: () => painting.worlds(),
  // the seam: 'grow' or 'cut'; the line's morph band in px (at 768 wide)
  setSeam: (s) => setSeam(s, true),
  setBand: (px) => { S.band = px; },
  // the current world's background at ladder rung k (0 the plate .. N the world), exposure gain 1; with a
  // reference image, mean |page - reference| (0-255), else N
  async rungView(k, refUrl) {
    const ref = refUrl ? await loadRef(refUrl) : null;
    render(performance.now(), { rung: k });
    return ref ? diffImage(ref) : ladderOf(currentWorld()).n;
  },
  maskStats() {
    const m = S.mask; if (!m) return null;
    let s = 0, big = 0; for (const v of m.data) { s += v; if (v > 0.5) big++; }
    return { w: m.w, h: m.h, mean: s / m.data.length, personFrac: big / m.data.length };
  },
};
