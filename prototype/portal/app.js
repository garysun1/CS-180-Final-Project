// Cross the Line — live portal kiosk. See README.md.
// The same code runs the local kiosk (index.html: camera, server, segmenter) and the hosted demo
// (artifact/page.html: recorded scenes with pre-made worlds), configured by window.PORTAL_CONFIG.
import { Compositor, IDENTITY_AFF } from './compositor.js';
import { PlateCapture, fitAffine, toImageData } from './plate.js';
import { PortalAudio } from './audio.js';

const params = new URLSearchParams(location.search);
const CFG = Object.assign({
  camera: true, server: true, segmenter: true, muted: false, autostart: params.get('autostart') === '1',
  scenes: null, startScene: 0,
}, window.PORTAL_CONFIG || {});
const $ = (id) => document.getElementById(id);
const canvas = $('view');
const MODES = ['line', 'portal', 'lens', 'whole frame'];
const SHADER_WORLDS = [
  { name: 'Night', kind: 1 }, { name: '1920s', kind: 2 }, { name: 'Winter', kind: 3 },
  { name: 'Comic', kind: 4 }, { name: 'Thermal', kind: 5 }, { name: 'Neon', kind: 6 },
];
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

const S = {
  worlds: SHADER_WORLDS.map((w) => ({ ...w })), world: 0, mode: Math.max(0, MODES.indexOf(params.get('mode') || 'line')),
  mirror: params.get('mirror') !== '0', debug: params.get('debug') === '1', diff: true,
  glitchUntil: 0, autoGlitch: !REDUCED, autoCycle: false, lastCycle: 0, flash: 0, muted: !!CFG.muted,
  line: { x: 0.5, y: 0.5, angle: 0 }, portal: { x: 0.5, y: 0.78, r: 0.17 }, lens: { x: 0.5, y: 0.5, r: 0.2 },
  source: params.get('source') === 'clip' || !CFG.camera ? 'clip' : 'camera', video: null,
  plate: null, plateData: null, capture: null, gain: 1,
  mask: null, segMs: 0, delegate: '', fps: 0, frames: 0, lastFpsT: performance.now(),
  tracks: [], across: 0, crossings: 0, server: false, job: null, loaded: new Set(), log: [],
  scenes: [], scene: -1,
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

// ------------------------------------------------------------------ sources
async function startCamera() {
  const v = $('cam');
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } }, audio: false });
  v.srcObject = stream;
  await v.play();
  return v;
}
async function startClip(src) {
  const v = $('clip');
  if (src) {
    if (v.src.startsWith('blob:') && v.src !== src) URL.revokeObjectURL(v.src);
    v.src = src;
  } else if (!v.src) v.src = params.get('clip') || './clips/fallback.mp4';
  await v.play();
  return v;
}
// opts.src: clip URL; opts.plate: a ready empty scene (ImageBitmap) instead of capturing one
async function useSource(name, opts = {}) {
  try {
    S.video = name === 'camera' ? await startCamera() : await startClip(opts.src);
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
  S.tracks = []; S.mask = null;
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
  for (const w of S.worlds) if (w.kind === 0 && w.img) w.aff = fitAffine(S.plateData, toImageData(w.img, canvas.width, canvas.height));
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
    const m = S.mask.data, d = comb.data;
    for (let i = 0; i < d.length; i++) m[i] = 0.4 * m[i] + 0.6 * d[i];     // temporal smoothing
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
  return 1;
}
function breath() { return REDUCED ? 1 : 1 + 0.05 * Math.sin(performance.now() / 1000 * 2 * Math.PI / 3); }

// People as blobs on a coarse grid: each gets one weight from where they stand (portal mode), and
// crossings (a person going from real to the other world) trigger sound, a flash, and a glitch.
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
    let cnt = 0, sx = 0, sy = 0, maxy = 0, cells = [];
    while (stack.length) {
      const j = stack.pop(), x = j % GW, y = (j / GW) | 0;
      cnt++; sx += x; sy += y; maxy = Math.max(maxy, y); cells.push(j);
      for (const k of [j - 1, j + 1, j - GW, j + GW]) {
        if (k < 0 || k >= grid.length || lab[k] || !grid[k]) continue;
        if ((k === j - 1 && x === 0) || (k === j + 1 && x === GW - 1)) continue;
        lab[k] = nl; stack.push(k);
      }
    }
    if (cnt < 12) continue;
    const feetXs = cells.filter((j) => ((j / GW) | 0) >= maxy - 1).map((j) => j % GW).sort((a, b) => a - b);
    blobs.push({ cells, cnt, cx: sx / cnt / GW, cy: sy / cnt / GH, fx: (feetXs[feetXs.length >> 1] + 0.5) / GW, fy: (maxy + 1) / GH });
  }
  // track (nearest centroid), smooth each person's weight, detect crossings
  const prev = S.tracks, next = [];
  let massIn = 0, mass = 0;
  for (const b of blobs) {
    const raw = S.mode === 2 ? ruleWeight(b.cx, b.cy) : ruleWeight(b.fx, Math.min(0.999, b.fy));
    let best = null, bd = 0.08;
    for (const t of prev) { const d = Math.hypot(t.cx - b.cx, t.cy - b.cy); if (!t.used && d < bd) { best = t; bd = d; } }
    const t = best ? Object.assign(best, { used: true }) : { w: raw, inside: raw > 0.5 };
    t.cx = b.cx; t.cy = b.cy; t.w = 0.65 * t.w + 0.35 * raw;
    if (!t.inside && t.w > 0.7 && best) onCrossing();
    if (t.w > 0.7) t.inside = true; else if (t.w < 0.3) t.inside = false;
    b.w = t.w; next.push({ cx: t.cx, cy: t.cy, w: t.w, inside: t.inside });
    massIn += b.cnt * t.w; mass += b.cnt;
  }
  S.tracks = next;
  S.across = mass ? massIn / mass : 0;
  if (audio) audio.setAcross(S.across);
  if (S.mode === 1) {
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
function onCrossing() {
  const now = performance.now();
  if (now - (S.lastCrossT || 0) < 600) return;
  S.lastCrossT = now; S.crossings++;
  flash(0.35);
  if (S.autoGlitch) S.glitchUntil = now + 450;
  if (audio && !S.muted) audio.whoosh();
}

// ------------------------------------------------------------------ worlds
function currentWorld() { return S.worlds[S.world]; }
function worldLabel(w) { return w.kind === 0 ? `${w.name} · ${w.group === 'yours' ? 'your image' : 'generated'}` : w.name; }
function setWorld(i, quiet = false) {
  if (i < 0 || i >= S.worlds.length) return;
  S.world = i;
  if (audio) audio.setWorld(i);
  flash(0.25);
  if (!quiet) toast(worldLabel(S.worlds[i]));
  renderControls();
}
function setMode(m, quiet = false) {
  S.mode = m; S.tracks = [];
  if (!quiet) toast(`Rule: ${MODES[m]}`);
  renderControls();
}
async function addImageWorld(name, src, url, { quiet = false, group = 'generated' } = {}) {
  const bmp = src instanceof ImageBitmap ? src : await createImageBitmap(src);
  const w = { name, kind: 0, img: bmp, url, aff: IDENTITY_AFF, group };
  const data = toImageData(bmp, canvas.width, canvas.height);
  w.tex = comp.newTexture();
  comp.uploadImage(w.tex, data);
  if (S.plateData) w.aff = fitAffine(S.plateData, data);
  S.worlds.push(w);
  if (!quiet) toast(`New world: ${name} (key ${S.worlds.length <= 9 ? S.worlds.length : 'N'})`);
  renderControls();
  return S.worlds.length - 1;
}
function removeImageWorlds() {           // image worlds belong to one view; drop them when the view changes
  for (const w of S.worlds) if (w.kind === 0 && w.tex) comp.gl.deleteTexture(w.tex);
  S.worlds = S.worlds.filter((w) => w.kind !== 0);
  S.world = Math.min(S.world, S.worlds.length - 1);
}

// ------------------------------------------------------------------ recorded scenes (hosted demo)
// A scene is a fixed-camera clip with its empty scene and generated worlds made offline
// (scripts/build_portal_artifact.py).
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
    const [clip, plate, ...worlds] = await Promise.all([
      fetchBlob(sc.clip), fetchBlob(sc.plate).then((b) => createImageBitmap(b)),
      ...sc.worlds.map((w) => fetchBlob(w.src).then((b) => createImageBitmap(b)))]);
    if (g !== sceneGen) return;
    removeImageWorlds();
    S.scene = i;
    await useSource('clip', { src: URL.createObjectURL(clip), plate });
    if (sc.line) Object.assign(S.line, sc.line);
    if (sc.portal) Object.assign(S.portal, sc.portal);
    for (let k = 0; k < worlds.length; k++) await addImageWorld(sc.worlds[k].name, worlds[k], sc.worlds[k].src, { quiet: true });
    const start = S.worlds.findIndex((w) => w.kind === 0 && w.name === sc.startWorld);
    setWorld(start >= 0 ? start : 0, true);
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
  S.scene = -1; S.plate = null;
  try {
    await useSource('clip', { src: URL.createObjectURL(file) });
    toast('Your video: capturing its empty scene. Use a fixed camera for the best result.', 5000);
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
  log(`world server: ${S.server ? 'yes' : 'no (shader worlds only)'}`);
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
function frame(now) {
  requestAnimationFrame(frame);
  const v = S.video;
  if (!comp || !v || v.readyState < 2) return;
  comp.uploadImage(comp.tex.cam, v);
  if (S.autoCycle && now - S.lastCycle > 6000) { S.lastCycle = now; setWorld((S.world + 1) % S.worlds.length); }
  const W = canvas.width, H = canvas.height, w = currentWorld();
  let bg = w.kind, per = w.kind, aff = w.aff || IDENTITY_AFF, worldTex = w.tex;
  let glitch = 0;
  if (now < S.glitchUntil) {             // the person flashes through worlds every frame
    glitch = 1;
    const k = S.worlds[(Math.random() * S.worlds.length) | 0];
    per = k.kind; aff = k.aff || IDENTITY_AFF;
    if (Math.random() < 0.15) { const kb = S.worlds[(Math.random() * S.worlds.length) | 0]; bg = kb.kind; worldTex = kb.tex; }
  }
  if (bg === 0 && !worldTex) bg = 1;
  const r = S.portal.r * W * breath();
  comp.draw({
    bg, per, aff, worldTex, mode: S.mode,
    p0: [S.line.x * W, S.line.y * H], n: [Math.cos(S.line.angle), Math.sin(S.line.angle)],
    portal: [S.portal.x * W, S.portal.y * H, r], squash: 0.38,
    lens: [S.lens.x * W, S.lens.y * H], lensR: S.lens.r * H,
    glitch, seed: Math.random() * 100, flash: S.flash, mirror: S.mirror, debug: S.debug,
    hasPlate: !!S.plate, diff: S.diff, gain: S.gain,
  });
  S.flash *= 0.82; if (S.flash < 0.01) S.flash = 0;
  S.frames++;
  if (now - S.lastFpsT > 500) {
    S.fps = (S.frames - (S.fpsBase || 0)) * 1000 / (now - S.lastFpsT); S.fpsBase = S.frames; S.lastFpsT = now;
    const dbg = S.debug ? ` · ${S.fps.toFixed(0)} fps · mask ${S.segMs.toFixed(0)} ms (${S.delegate}) · gain ${S.gain.toFixed(2)}` : '';
    const where = S.scenes[S.scene] ? ` · ${S.scenes[S.scene].name}` : S.source === 'clip' ? ' · recorded clip' : '';
    $('hudsub').textContent = `${w.name} · ${MODES[S.mode]}${where}${S.progress ? ' · ' + S.progress : ''}${dbg}`;
  }
}

// ------------------------------------------------------------------ input
function toFrame(e) {
  const r = canvas.getBoundingClientRect();
  let x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
  if (S.mirror) x = 1 - x;
  return [Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y))];
}
let dragging = false;
canvas.addEventListener('pointerdown', (e) => { dragging = true; canvas.setPointerCapture(e.pointerId); onPointer(e); });
canvas.addEventListener('pointerup', () => { dragging = false; });
canvas.addEventListener('pointercancel', () => { dragging = false; });
canvas.addEventListener('pointermove', (e) => { if (dragging || (S.mode === 2 && e.pointerType === 'mouse')) onPointer(e); });
function onPointer(e) {
  const [x, y] = toFrame(e);
  if (S.mode === 0) { S.line.x = x; S.line.y = y; }
  else if (S.mode === 1) { S.portal.x = x; S.portal.y = y; }
  else if (S.mode === 2) { S.lens.x = x; S.lens.y = y; }
}
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const k = e.deltaY > 0 ? 0.92 : 1.08;
  if (S.mode === 1) S.portal.r = Math.min(0.6, Math.max(0.05, S.portal.r * k));
  if (S.mode === 2) S.lens.r = Math.min(0.8, Math.max(0.05, S.lens.r * k));
}, { passive: false });

function glitchBurst() { S.glitchUntil = performance.now() + (REDUCED ? 500 : 1500); }
function toggleCycle() { S.autoCycle = !S.autoCycle; S.lastCycle = performance.now(); toast(`Auto-cycle ${S.autoCycle ? 'on' : 'off'}`); renderControls(); }
async function ensureAudio() {
  try {
    if (!audio) { audio = new PortalAudio(); audio.setWorld(S.world); }
    audio.setMuted(S.muted);
    if (!S.muted) await audio.resume();
  } catch (e) { log(`audio: ${e}`); }
}
function toggleSound() {
  S.muted = !S.muted;
  if (audio || !S.muted) ensureAudio();
  toast(S.muted ? 'Sound off' : 'Sound on');
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
  if (k >= '1' && k <= '9') setWorld(+k - 1);
  else if (k === 'n') setWorld((S.world + 1) % S.worlds.length);
  else if (k === 'm') setMode((S.mode + 1) % MODES.length);
  else if (k === 'c') capturePlate(3);
  else if (k === 'g') glitchBurst();
  else if (k === 'x') { S.autoGlitch = !S.autoGlitch; toast(`Auto-glitch ${S.autoGlitch ? 'on' : 'off'}`); }
  else if (k === ' ') { toggleCycle(); e.preventDefault(); }
  else if (k === 'b') switchSource();
  else if (k === 'r') S.mirror = !S.mirror;
  else if (k === 'd') S.debug = !S.debug;
  else if (k === 't') { S.diff = !S.diff; toast(`Hole filling ${S.diff ? 'on' : 'off'}`); }
  else if (k === 's') toggleSound();
  else if (k === 'f') toggleFullscreen();
  else if (k === 'h' || (k === 'escape' && $('help') && !$('help').hidden)) toggleHelp(k === 'h' ? undefined : false);
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
function chip(label, pressed, onClick, cls = '') {
  const b = document.createElement('button');
  b.type = 'button'; b.className = `chip ${cls}`.trim(); b.textContent = label;
  b.setAttribute('aria-pressed', String(pressed)); b.addEventListener('click', onClick);
  return b;
}
function renderControls() {
  const box = $('worlds');
  if (!box) return;
  const groups = [['generated', 'Generated'], ['yours', 'Yours'], ['shader', 'Instant']];
  const kids = [];
  for (const [g, title] of groups) {
    const idx = S.worlds.map((w, i) => i).filter((i) => (S.worlds[i].kind === 0 ? S.worlds[i].group : 'shader') === g);
    if (!idx.length) continue;
    const t = document.createElement('span'); t.className = 'group'; t.textContent = title; kids.push(t);
    for (const i of idx) kids.push(chip(S.worlds[i].name, i === S.world, () => setWorld(i), g));
  }
  box.replaceChildren(...kids);
  const on = box.querySelector('[aria-pressed="true"]');
  if (on && on.scrollIntoView) on.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  for (const b of document.querySelectorAll('[data-mode]')) b.setAttribute('aria-pressed', String(+b.dataset.mode === S.mode));
  if ($('b-cycle')) $('b-cycle').setAttribute('aria-pressed', String(S.autoCycle));
  if ($('b-sound')) { $('b-sound').setAttribute('aria-pressed', String(!S.muted)); $('b-sound').textContent = S.muted ? 'Sound off' : 'Sound on'; }
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
  on('b-glitch', glitchBurst); on('b-cycle', toggleCycle); on('b-sound', toggleSound);
  on('b-full', toggleFullscreen); on('b-help', () => toggleHelp()); on('help-close', () => toggleHelp(false));
  on('b-upload', () => $('file') && $('file').click());
  if ($('b-full') && !document.fullscreenEnabled) $('b-full').hidden = true;
  if ($('file')) $('file').addEventListener('change', (e) => { takeFile(e.target.files[0]); e.target.value = ''; });
  if ($('scene')) $('scene').addEventListener('change', (e) => { const i = +e.target.value; if (i >= 0) loadScene(i); });
  if ($('help')) $('help').addEventListener('click', (e) => { if (e.target === $('help')) toggleHelp(false); });
}

// ------------------------------------------------------------------ start
async function start() {
  if ($('start')) $('start').hidden = true;
  if (!S.muted) await ensureAudio();      // muted pages create it on the first Sound press (browsers need a gesture)
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

// for tests and debugging
window.__portal = {
  get state() { return S; },
  setWorld, setMode: (m) => setMode(m, true), setMirror: (b) => { S.mirror = b; },
  glitch: (ms) => { S.glitchUntil = performance.now() + ms; }, capture: () => capturePlate(0),
  setLine: (x, angle = 0) => { S.line.x = x; S.line.angle = angle; },
  setDebug: (b) => { S.debug = b; }, loadScene,
  // mean |output - camera| (0-255) over a column band [x0, x1) of the frame, plus the camera frame used
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
