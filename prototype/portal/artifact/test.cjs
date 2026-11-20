// Test the hosted portal page in a CSP harness: no camera, recorded scenes, on-screen controls.
//   python scripts/build_portal_artifact.py SITE --harness && (cd SITE && python -m http.server 8770) &
//   node portal/artifact/test.cjs http://127.0.0.1:8770/harness.html some_fixed_camera_clip.mp4 OUT_DIR
// Checks: errors and CSP; the opening crossing; colour parity of every generated world against the
// Python colour field; real side vs world side; a person-only burst (deterministic, video paused);
// Layers; Depth; the world-change wave (held at half way); the other scenes; your own video; phone.
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');
const [url, upload, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fails = [];
const check = (ok, what) => { if (!ok) fails.push(what); return ok; };

// Errors only: console errors, page errors, failed requests and CSP violations. GL driver performance notes
// ("GPU stall due to ReadPixels", caused by the test's own readbacks) are not failures.
function watch(page, errors) {
  page.on('console', (m) => {
    if (m.type() === 'error' && !/GL Driver Message/.test(m.text())) errors.push(`${m.type()}: ${m.text()}`);
  });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', (r) => {
    const why = r.failure() && r.failure().errorText;
    // a video element aborts its own range request when it seeks or its blob is replaced: not an error
    if (r.url().startsWith('blob:') && why === 'net::ERR_ABORTED') return;
    errors.push(`requestfailed: ${r.url()} ${why}`);
  });
  page.addInitScript(() => document.addEventListener('securitypolicyviolation',
    (e) => console.error(`CSP blocked ${e.blockedURI} (${e.violatedDirective})`)));
}
const ready = (sc) => { const s = window.__portal && window.__portal.state; return !!(s && s.plate && s.scene === sc && s.worlds.length > 6); };
const meanAbs = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += Math.abs(a[i] - b[i]); return s / a.length; };

(async () => {
  const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const report = {};
  // ---------------- desktop
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1,
      recordVideo: { dir: out, size: { width: 1280, height: 800 } } });
    const page = await ctx.newPage();
    const errors = []; watch(page, errors);
    const t0 = Date.now();
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForFunction(ready, 0, { timeout: 120000 });
    report.secondsToScene = (Date.now() - t0) / 1000;
    // the opening: the clip starts a few seconds before a walker crosses the line
    report.videoTimeAtReady = await page.evaluate(() => window.__portal.state.video.currentTime);
    check(report.videoTimeAtReady > 15, `opening at clip time ${report.videoTimeAtReady}`);
    const tc = Date.now();
    const crossed = await page.waitForFunction(() => window.__portal.state.crossings > 0, null, { timeout: 20000 }).then(() => true, () => false);
    report.firstCrossingS = crossed ? (Date.now() - tc) / 1000 : null;
    report.firstCrossingClipTime = await page.evaluate(() => window.__portal.state.video.currentTime);
    check(crossed, 'no crossing within 20 s of the plaza opening');
    await sleep(1500);
    await page.screenshot({ path: path.join(out, 'd1_opening.png') });
    report.opening = await page.evaluate(() => { const s = window.__portal.state;
      return { world: window.__portal.displayName(s.world), worlds: window.__portal.visualOrder().map((i) => window.__portal.displayName(i)),
               bursts: s.bursts, crossings: s.crossings, videoTime: s.video.currentTime, fps: s.fps, maskMs: s.segMs }; });

    // colour parity of every generated world: the page's person colour of the plate vs the Python field
    report.parity = await page.evaluate(async () => {
      const p = window.__portal, s = p.state, out = {};
      const keep = s.world;
      for (let i = 0; i < s.worlds.length; i++) {
        const w = s.worlds[i];
        if (w.kind !== 0) continue;
        p.setWorld(i, true);
        out[w.name] = +(await p.parity(w.url.replace('.jpg', '_lacref.png'))).toFixed(2);
      }
      p.setWorld(keep, true);
      return out;
    });
    for (const [k, v] of Object.entries(report.parity)) check(v <= 3, `colour parity ${k}: ${v} > 3 levels`);

    // real side matches the clip, the world side differs
    await page.evaluate(() => { const p = window.__portal; p.setMode(0); p.setLine(0.5); });
    await page.waitForFunction(() => window.__portal.state.flash === 0 && !window.__portal.state.wave, null, { timeout: 20000 });
    report.sides = await page.evaluate(() => ({ real: window.__portal.compare(0.02, 0.45), other: window.__portal.compare(0.55, 0.98) }));
    check(report.sides.real < 8 && report.sides.other > 2 * report.sides.real, `sides ${JSON.stringify(report.sides)}`);

    // drag the line (the handle takes no pointer events)
    const box = await page.locator('#view').boundingBox();
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.mouse.down(); await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.5, { steps: 8 }); await page.mouse.up();
    report.lineAfterDrag = await page.evaluate(() => window.__portal.state.line.x);
    check(Math.abs(report.lineAfterDrag - 0.3) < 0.02, 'line drag');
    await page.evaluate(() => window.__portal.setLine(0.5));

    // a burst stays on the person: with the video paused, nothing outside the box changes
    await page.waitForFunction(() => window.__portal.state.tracks.some((t) => t.box && t.hw >= 1.3), null, { timeout: 20000 }).catch(() => {});
    report.burst = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      s.video.pause();
      await new Promise((r) => setTimeout(r, 400));
      const b = p.crossNow({ ms: 5000, seed: 1 });
      if (!b) { s.video.play(); return { ok: false, why: 'no track' }; }
      p.setLine(Math.max(0.01, b.box[0] - 0.05));          // the chosen person stands in the world
      await new Promise((r) => setTimeout(r, 100));
      const samples = [];
      for (let k = 0; k < 4; k++) { samples.push(p.regions(b.box)); await new Promise((r) => setTimeout(r, 300)); }
      let outsideSame = true, insideChanged = false;
      for (let k = 1; k < samples.length; k++) {
        const a = samples[k - 1], c = samples[k];
        for (let i = 0; i < a.outside.length; i++) if (a.outside[i] !== c.outside[i]) { outsideSame = false; break; }
        for (let i = 0; i < a.inside.length; i++) if (a.inside[i] !== c.inside[i]) { insideChanged = true; break; }
      }
      s.video.play(); p.setLine(0.5);
      return { ok: true, box: b.box.map((v) => +v.toFixed(3)), outsideSame, insideChanged };
    });
    check(report.burst.ok && report.burst.outsideSame && report.burst.insideChanged, `burst ${JSON.stringify(report.burst)}`);
    await sleep(500);
    await page.evaluate(() => window.__portal.crossNow({ ms: 3000, seed: 3, fixed: false }));
    await sleep(350);
    await page.screenshot({ path: path.join(out, 'd2_burst.png') });
    await sleep(3000);

    // Layers: six labelled tiles; tap one to see it full size
    await page.click('#b-layers'); await sleep(1200);
    await page.screenshot({ path: path.join(out, 'd3_layers.png') });
    report.layers = await page.evaluate(() => ({ labels: document.querySelectorAll('.layer-label').length,
      sdcard: !document.getElementById('sdcard').hidden, tiles: window.__portal.tiles() }));
    check(report.layers.labels === 6, `layer labels ${report.layers.labels}`);
    const t = report.layers.tiles[2], cw = await page.evaluate(() => document.getElementById('view').width);
    const sc = box.width / cw;
    await page.mouse.click(box.x + (t.x + t.w / 2) * sc, box.y + (t.y + t.h / 2) * sc); await sleep(800);
    report.layerAfterTap = await page.evaluate(() => window.__portal.state.layer);
    check(report.layerAfterTap === 2, `layer tap ${report.layerAfterTap}`);
    await page.screenshot({ path: path.join(out, 'd4_layer_world.png') });
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2); await sleep(300);
    await page.keyboard.press('Escape'); await sleep(300);
    report.layersOff = await page.evaluate(() => !window.__portal.state.layers);
    check(report.layersOff, 'layers did not close');

    // Depth: a tap sets the contour at that distance
    await page.click('[data-mode="4"]');
    await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.3); await sleep(1500);
    report.depth = await page.evaluate(() => ({ mode: window.__portal.state.mode, tau: +window.__portal.state.tau.toFixed(3) }));
    check(report.depth.mode === 4 && report.depth.tau > 0.3, `depth ${JSON.stringify(report.depth)}`);
    await page.screenshot({ path: path.join(out, 'd5_depth.png') });

    // the world-change wave, held half way: far rows already show the new world, near rows the old one
    report.wave = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      p.setMode(3); s.video.pause();
      const gens = s.worlds.map((w, i) => i).filter((i) => s.worlds[i].kind === 0);
      p.setWorld(gens[0], true);
      await new Promise((r) => setTimeout(r, 300));
      const A = p.bands();
      p.setWave(0.5); p.setWorld(gens[1]);
      const M = p.bands();
      p.setWave(null);
      await new Promise((r) => setTimeout(r, 1600));
      const B = p.bands();
      s.video.play(); p.setMode(0);
      const d = (x, y) => { let t = 0; for (let i = 0; i < x.length; i++) t += Math.abs(x[i] - y[i]); return t / x.length; };
      return { topMidVsNew: d(M.topPx, B.topPx), topMidVsOld: d(M.topPx, A.topPx), bottomMidVsOld: d(M.bottomPx, A.bottomPx),
               bottomMidVsNew: d(M.bottomPx, B.bottomPx), waveCleared: !s.wave };
    });
    const w = report.wave;
    check(w.topMidVsNew < w.topMidVsOld && w.bottomMidVsOld < w.bottomMidVsNew && w.waveCleared, `wave ${JSON.stringify(w)}`);

    // the other scenes
    for (const [i, name] of [[1, 'crowd'], [2, 'street']]) {
      const ts = Date.now();
      await page.selectOption('#scene', String(i));
      await page.waitForFunction(ready, i, { timeout: 120000 });
      await sleep(3000);
      report[name] = await page.evaluate(() => { const p = window.__portal, s = p.state;
        return { world: p.displayName(s.world), mask: p.maskStats(), real: p.compare(0.02, 0.45), other: p.compare(0.55, 0.98) }; });
      report[name].seconds = (Date.now() - ts) / 1000;
      await page.screenshot({ path: path.join(out, `d6_${name}.png`) });
    }
    // your own video
    await page.setInputFiles('#file', upload);
    await page.waitForFunction(() => { const s = window.__portal.state; return s.scene === -1 && s.plate && s.video.videoWidth === 640; }, null, { timeout: 120000 });
    await sleep(3000);
    report.upload = await page.evaluate(() => { const p = window.__portal, s = p.state;
      return { worlds: s.worlds.length, mask: p.maskStats(), far: !!s.far, sceneLabel: document.querySelector('#scene').selectedOptions[0].textContent }; });
    check(report.upload.mask && report.upload.mask.personFrac > 0, 'no people found in the uploaded video');
    await page.screenshot({ path: path.join(out, 'd7_upload.png') });
    await page.click('#b-sound'); await sleep(400);
    report.audio = await page.evaluate(() => ({ muted: window.__portal.state.muted, state: window.__portal.audioState() }));
    await page.click('#b-help'); await sleep(300);
    await page.screenshot({ path: path.join(out, 'd8_help.png') });
    await page.keyboard.press('Escape');
    report.helpClosed = await page.evaluate(() => document.getElementById('help').hidden);
    report.desktopErrors = errors;
    check(errors.length === 0, 'desktop errors');
    await ctx.close();
  }
  // ---------------- phone
  {
    const ctx = await browser.newContext({ ...devices['iPhone 13'] });
    const page = await ctx.newPage();
    const errors = []; watch(page, errors);
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForFunction(ready, 0, { timeout: 120000 });
    await sleep(3000);
    await page.screenshot({ path: path.join(out, 'p1_phone.png') });
    report.phone = await page.evaluate(() => ({ scrollW: document.documentElement.scrollWidth, innerW: innerWidth,
      scrollH: document.documentElement.scrollHeight, innerH: innerHeight, narrow: window.__portal.narrow() }));
    check(report.phone.scrollW <= report.phone.innerW && report.phone.scrollH <= report.phone.innerH, 'phone overflow');
    const box = await page.locator('#view').boundingBox();
    await page.touchscreen.tap(box.x + box.width * 0.7, box.y + box.height * 0.5);
    report.phone.lineAfterTap = await page.evaluate(() => window.__portal.state.line.x);
    await page.tap('#b-layers'); await sleep(500);
    await page.touchscreen.tap(box.x + box.width * 0.5, box.y + box.height * 0.5); await sleep(800);
    report.phone.layer = await page.evaluate(() => window.__portal.state.layer);
    await page.screenshot({ path: path.join(out, 'p2_phone_layers.png') });
    report.phoneErrors = errors;
    check(errors.length === 0, 'phone errors');
    await ctx.close();
  }
  await browser.close();
  report.fails = fails;
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report, null, 1));
  process.exit(fails.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
