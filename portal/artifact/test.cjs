// Test the hosted portal page in a CSP harness: no camera, recorded scenes, on-screen controls.
//   python scripts/build_portal_artifact.py SITE --harness && (cd SITE && python -m http.server 8770) &
//   node portal/artifact/test.cjs http://127.0.0.1:8770/harness.html some_fixed_camera_clip.mp4 OUT_DIR
// Checks: errors and CSP; the opening crossing; colour parity of every generated world against the
// Python colour field; real side vs world side (video paused); Grow, the default seam (video paused: the
// real side is the camera bit for bit, no step at the line, the world forms across the band, every
// ladder exact at its rungs, depth leaves nearer rows untouched) and Cut; Hold to flood (held at phases
// with the video paused, the mouse gesture, a held full flood with the clip playing, its sound, a phone
// long press); a person-only burst (deterministic, video paused); Layers; Depth; the world-change wave
// (held at half way); Paint (exact outside the paint, erasing, several worlds at once, undo, the controls,
// a crossing onto it); the other scenes; your own video; phone.
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

    // real side matches the clip, the world side differs. Measured on a paused frame drawn just before:
    // with the clip playing, compare() can read a newer video frame than the one drawn (2-6 levels in
    // either seam), so that reading is only reported (live)
    await page.evaluate(() => { const p = window.__portal; p.setMode(0); p.setLine(0.5); });
    await page.waitForFunction(() => window.__portal.state.flash === 0 && !window.__portal.state.wave, null, { timeout: 20000 });
    report.sides = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      const live = { real: p.compare(0.02, 0.45), other: p.compare(0.55, 0.98) };
      s.video.pause(); s.autoGlitch = false; s.burst = null;
      await new Promise((r) => setTimeout(r, 400));
      p.renderNow();
      const out = { real: p.compare(0.02, 0.45), other: p.compare(0.55, 0.98), live };
      s.video.play(); s.autoGlitch = true;
      return out;
    });
    check(report.sides.real < 8 && report.sides.other > 2 * report.sides.real, `sides ${JSON.stringify(report.sides)}`);

    // Grow, the default seam: video paused, Winter, line at 0.5, band 120 px; then the same frame in Cut
    report.grow = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      s.video.pause(); s.autoGlitch = false; s.burst = null;
      await new Promise((r) => setTimeout(r, 400));
      const winter = s.worlds.findIndex((w) => w.kind === 0 && w.name === 'Winter');
      p.setWorld(winter, true); p.setMode(0); p.setLine(0.5); p.setBand(120);
      const bands = [[0.52, 0.56], [0.60, 0.66], [0.75, 0.98]];
      const look = (seam) => {
        p.setSeam(seam); p.renderNow();
        return { real: p.compare(0.02, 0.45), step: p.compare(0.500, 0.506), other: p.compare(0.55, 0.98),
                 bands: bands.map((b) => p.compare(b[0], b[1])) };
      };
      const grow = look('grow'), cut = look('cut');
      p.setSeam('grow');
      // every generated world's ladder at its integer rungs against the JPEGs it was made from
      const sc = s.scenes[s.scene], ladders = {};
      for (const wj of sc.worlds) {
        p.setWorld(s.worlds.findIndex((w) => w.kind === 0 && w.name === wj.name), true);
        const n = await p.rungView(0), refs = [sc.plate, ...(wj.ladder || []).map((r) => r.src), wj.src];
        ladders[wj.name] = { n, want: refs.length - 1, diffs: [] };
        for (let k = 0; k <= n; k++) ladders[wj.name].diffs.push(+(await p.rungView(k, refs[k])).toFixed(3));
      }
      p.setWorld(winter, true);
      // depth ('AI fog') at tau 0.45: rows nearer than tau (by 0.05, all along the row) stay the camera's
      p.setMode(4); p.setTau(0.45); p.renderNow();
      const f = s.far, H = s.video.videoHeight;
      let y0 = H;
      for (let y = H - 1; y >= 0; y--) {
        const fy = Math.min(f.h - 1, Math.floor((y + 0.5) / H * f.h));
        let mx = 0;
        for (let x = 0; x < f.w; x++) mx = Math.max(mx, f.f[fy * f.w + x]);
        if (mx < 0.40) y0 = y; else break;
      }
      const depth = { fromRow: y0 / H, near: p.compareRows(y0 / H, 1), far: p.compareRows(0, 0.3) };
      p.setMode(0); s.video.play(); s.autoGlitch = true;
      return { grow, cut, ladders, depth };
    });
    {
      const g = report.grow;
      check(g.grow.real === 0, `grow: the real side is not the camera (${g.grow.real})`);
      check(g.grow.step < 6, `grow: step across the line ${g.grow.step} (cut ${g.cut.step})`);
      // how far the world has formed: each band against the full world over the same columns (Cut),
      // since columns differ in how much Winter changes them
      g.formed = g.grow.bands.map((v, i) => +(v / Math.max(1e-6, g.cut.bands[i])).toFixed(3));
      check(g.formed[0] < g.formed[1] && g.formed[1] < g.formed[2] && g.formed[2] > 0.97, `grow: not rising into the band ${JSON.stringify(g.formed)}`);
      // every world has the rungs scenes.json lists (n = rungs + 1), and some have an SD middle rung
      for (const [name, l] of Object.entries(g.ladders)) {
        check(l.n === l.want && l.n >= 2 && l.diffs[0] < 1.5 && l.diffs[l.n] < 1.5 && Math.max(...l.diffs) < 1.5,
              `ladder ${name} ${JSON.stringify(l)}`);
      }
      check(Object.values(g.ladders).some((l) => l.n === 3), 'no plaza world has a middle rung (plate, filter, SD rung, world)');
      check(g.depth.near === 0 && g.depth.far > 10, `grow depth ${JSON.stringify(g.depth)}`);
      check(g.cut.real < 8 && g.cut.other > 2 * g.cut.real && g.cut.step > 30, `cut sides ${JSON.stringify(g.cut)}`);
    }

    // Paint, video paused, Winter, in Grow and in Cut: nothing painted is the camera; a stroke changes only
    // where it is painted (outside it the camera, exactly); erasing it gives the camera back, exactly
    report.paint = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      s.video.pause(); s.autoGlitch = false; s.burst = null;
      await new Promise((r) => setTimeout(r, 400));
      p.setWorld(s.worlds.findIndex((w) => w.kind === 0 && w.name === 'Winter'), true);
      p.setMode(5);
      const path = [[0.08, 0.75], [0.25, 0.8], [0.42, 0.72]], out = {};
      for (const seam of ['grow', 'cut']) {
        p.setSeam(seam); p.clearPaint(); p.renderNow();
        const empty = p.compare(0, 1);
        p.paint(path, { r: 40 }); p.renderNow();
        const stroke = { inside: p.compareBox(0.15, 0.3, 0.74, 0.86), outside: p.compareBox(0, 1, 0, 0.45),
                         at: p.paintAt(0.25, 0.8) };
        p.paint(path, { r: 90, erase: true }); p.renderNow();
        out[seam] = { empty, stroke, erased: p.compare(0, 1) };
      }
      p.clearPaint(); p.setSeam('grow');
      return out;
    });
    for (const [seam, r] of Object.entries(report.paint)) {
      check(r.empty === 0 && r.stroke.outside === 0 && r.stroke.inside > 20 && r.stroke.at > 0.99 && r.erased === 0,
            `paint (${seam}) ${JSON.stringify(r)}`);
    }
    // Several worlds at once, video paused, in Cut and Grow: Winter painted on the left lawn and Night on the
    // right each look as they do painted alone; outside both the frame is the camera; Night painted over
    // Winter takes that part over; undo brings Winter back; Clear gives the camera back, and undo the paint
    report.paintMulti = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      s.video.pause(); s.autoGlitch = false; s.burst = null;
      await new Promise((r) => setTimeout(r, 400));
      const idx = (n) => s.worlds.findIndex((w) => w.kind === 0 && w.name === n);
      const W = idx('Winter'), N = idx('Night');
      const L = [[0.05, 0.85], [0.3, 0.85]], R = [[0.6, 0.8], [0.9, 0.85]];
      const boxL = [0.1, 0.78, 0.25, 0.9], boxR = [0.65, 0.75, 0.85, 0.88];
      const mean = (a, b) => { let t = 0; for (let i = 0; i < a.length; i++) t += Math.abs(a[i] - b[i]); return t / a.length; };
      p.setMode(5);
      const out = {};
      for (const seam of ['grow', 'cut']) {
        p.setSeam(seam);
        p.resetPaint(); p.paint(L, { r: 50, world: W }); const refL = p.regions(boxL).inside;
        p.resetPaint(); p.paint(R, { r: 50, world: N }); const refR = p.regions(boxR).inside;
        p.resetPaint(); p.paint(L, { r: 50, world: W }); p.paint(R, { r: 50, world: N });
        const both = { left: mean(p.regions(boxL).inside, refL), right: mean(p.regions(boxR).inside, refR),
                       outside: p.compareBox(0, 1, 0, 0.5), worlds: p.paintedWorlds().length };
        p.paint([[0.1, 0.85], [0.2, 0.85]], { r: 50, world: N });
        const takenOver = p.paintWorldAt(0.15, 0.85) === N;
        p.undoPaint();
        const undone = { winter: p.paintWorldAt(0.15, 0.85) === W, left: mean(p.regions(boxL).inside, refL) };
        p.clearPaint(); p.renderNow();
        const cleared = p.compare(0, 1);
        p.undoPaint();
        out[seam] = { both, takenOver, undone, cleared, afterUndoClear: p.paintedWorlds().length };
      }
      p.resetPaint(); p.setSeam('grow'); p.setMode(0);
      return out;
    });
    for (const [seam, m] of Object.entries(report.paintMulti)) {
      check(m.both.left < 1.5 && m.both.right < 1.5 && m.both.outside === 0 && m.both.worlds === 2 && m.takenOver &&
            m.undone.winter && m.undone.left < 1.5 && m.cleared === 0 && m.afterUndoClear === 2,
            `paint, several worlds (${seam}) ${JSON.stringify(m)}`);
    }
    // the Paint controls: the button, a mouse stroke, a right-drag erases, the wheel sizes the brush, the
    // Eraser toggle, Clear; the brush tools hide again on another rule
    {
      const view = await page.locator('#view').boundingBox();
      const at = (x, y) => [view.x + x * view.width, view.y + y * view.height];
      await page.click('[data-mode="5"]');
      const tools = await page.evaluate(() => !document.getElementById('paint-tools').hidden);
      await page.mouse.move(...at(0.45, 0.12)); await page.mouse.down();
      await page.mouse.move(...at(0.75, 0.15), { steps: 10 }); await page.mouse.up();
      const painted = await page.evaluate(() => window.__portal.paintAt(0.6, 0.135));
      await page.mouse.move(...at(0.45, 0.13)); await page.mouse.down({ button: 'right' });
      await page.mouse.move(...at(0.75, 0.14), { steps: 10 }); await page.mouse.up({ button: 'right' });
      const erased = await page.evaluate(() => window.__portal.paintAt(0.6, 0.135));
      const r0 = await page.evaluate(() => window.__portal.state.brush.r);
      await page.mouse.wheel(0, -100); await sleep(200);
      const r1 = await page.evaluate(() => window.__portal.state.brush.r);
      await page.click('#b-erase');
      const eraser = await page.getAttribute('#b-erase', 'aria-pressed');
      await page.click('#b-erase');
      await page.evaluate(() => window.__portal.paint([[0.2, 0.5], [0.8, 0.5]], { r: 60 }));
      await page.click('#b-undo');
      const undone = await page.evaluate(() => window.__portal.paintAt(0.5, 0.5));
      await page.evaluate(() => window.__portal.paint([[0.2, 0.5], [0.8, 0.5]], { r: 60 }));
      await page.click('#b-clear');
      const cleared = await page.evaluate(() => { const p = window.__portal; p.renderNow(); return p.compare(0, 1); });
      await page.click('[data-mode="0"]');
      const hidden = await page.evaluate(() => document.getElementById('paint-tools').hidden);
      report.paintUi = { tools, painted, erased, r0, r1, eraser, undone, cleared, hidden };
      check(tools && painted > 0.99 && erased === 0 && r1 > r0 && eraser === 'true' && undone === 0 && cleared === 0 && hidden,
            `paint controls ${JSON.stringify(report.paintUi)}`);
    }
    // a walker steps onto painted ground and crosses into the world (as at the opening, the right half is
    // painted instead of the line drawn there)
    report.paintCross = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      p.setMode(5); p.clearPaint(); s.tracks = []; s.crossings = 0;
      for (const x of [0.6, 0.72, 0.84, 0.96]) p.paint([[x, 0], [x, 1]], { r: 60 });
      s.video.currentTime = s.scenes[s.scene].startTime || 0; s.video.play(); s.autoGlitch = true;
      const t0 = performance.now();
      while (s.crossings === 0 && performance.now() - t0 < 25000) await new Promise((r) => setTimeout(r, 250));
      const out = { crossings: s.crossings, seconds: (performance.now() - t0) / 1000 };
      p.clearPaint(); p.setMode(0);
      return out;
    });
    check(report.paintCross.crossings > 0, `paint: nobody crossed onto the paint ${JSON.stringify(report.paintCross)}`);

    // drag the line (the handle takes no pointer events)
    const box = await page.locator('#view').boundingBox();
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.mouse.down(); await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.5, { steps: 8 }); await page.mouse.up();
    report.lineAfterDrag = await page.evaluate(() => window.__portal.state.line.x);
    check(Math.abs(report.lineAfterDrag - 0.3) < 0.02, 'line drag');
    await page.evaluate(() => window.__portal.setLine(0.5));

    // the Morph chip and key E switch Grow and Cut; the wheel on the line widens the band
    await page.click('#b-seam');
    const afterChip = await page.evaluate(() => window.__portal.state.seam);
    await page.keyboard.press('e');
    const afterKey = await page.evaluate(() => window.__portal.state.seam);
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.mouse.wheel(0, -100); await sleep(300);
    report.seamUi = { afterChip, afterKey, band: await page.evaluate(() => window.__portal.state.band),
                      chipPressed: await page.getAttribute('#b-seam', 'aria-pressed') };
    check(afterChip === 'cut' && afterKey === 'grow' && report.seamUi.band > 120 && report.seamUi.chipPressed === 'true',
          `morph chip ${JSON.stringify(report.seamUi)}`);
    await page.evaluate(() => window.__portal.setBand(120));

    // Hold to flood, held at phases (video paused, Winter, line at 0.5), in Grow and in Cut: a small flood
    // changes the ground around the press and leaves the far corner the camera's; a full one covers the
    // frame; let go, it drains back to the line (in Grow, the real side is the camera again, exactly)
    report.flood = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      s.video.pause(); s.autoGlitch = false; s.burst = null;
      await new Promise((r) => setTimeout(r, 400));
      p.setWorld(s.worlds.findIndex((w) => w.kind === 0 && w.name === 'Winter'), true);
      p.setMode(0); p.setLine(0.5);
      const out = {};
      for (const seam of ['grow', 'cut']) {
        p.setSeam(seam);
        p.flood(0.3, 0.8, 0.15); p.renderNow();
        const early = { near: p.compareBox(0.25, 0.35, 0.74, 0.86), corner: p.compareBox(0.9, 1, 0, 0.1) };
        p.flood(0.3, 0.8, 1); p.renderNow();
        const full = { real: p.compare(0.02, 0.45), top: p.compareRows(0, 0.1), bottom: p.compareRows(0.9, 1) };
        p.flood(null);
        await new Promise((r) => setTimeout(r, 700));      // (runs after the drain's own 620-ms timer)
        const drained = !s.flood;
        p.renderNow();
        out[seam] = { early, full, drained, after: { real: p.compare(0.02, 0.45), other: p.compare(0.55, 0.98) } };
      }
      p.setSeam('grow'); s.video.play(); s.autoGlitch = true;
      return out;
    });
    {
      const { grow: g, cut: c } = report.flood;
      check(g.early.near > 10 && g.early.corner === 0 && g.full.real > 20 && g.full.top > 10 && g.full.bottom > 10 &&
            g.drained && g.after.real === 0, `flood (grow) ${JSON.stringify(g)}`);
      check(c.early.near > 10 && c.early.corner < 1 && c.full.real > 20 && c.full.top > 10 && c.full.bottom > 10 &&
            c.drained && c.after.real < 8 && c.after.other > 2 * c.after.real, `flood (cut) ${JSON.stringify(c)}`);
    }

    // the gesture, with the mouse: held still for 700 ms it floods; let go, the flood is gone 900 ms later
    // (on the page's clock: a check timer due then runs after the drain's own timer, however busy the
    // page) and the line has not moved; a quick click still moves the line; the drag above still works.
    // A hold needs 280 ms and 3 drawn frames, which here (1-3 fps) can take longer than 700 ms: it waits.
    await page.evaluate(() => {
      window.__portal.setLine(0.5);
      const c = document.getElementById('view'), fp = (window.__floodProbe = {});
      c.addEventListener('pointerup', () => setTimeout(() => { fp.goneAt900 = !window.__portal.state.flood; }, 900), { once: true });
    });
    await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.7);
    await page.mouse.down(); await sleep(700);
    const heldMouse = await page.waitForFunction(() => { const f = window.__portal.state.flood; return !!(f && f.held); },
      null, { timeout: 3000, polling: 50 }).then(() => true, () => false);
    await page.mouse.up();
    await page.waitForFunction(() => window.__floodProbe.goneAt900 !== undefined, null, { timeout: 15000 });
    report.holdMouse = await page.evaluate((held) => ({ held, goneAt900: window.__floodProbe.goneAt900,
      lineAfterHold: window.__portal.state.line.x }), heldMouse);
    await page.mouse.click(box.x + box.width * 0.7, box.y + box.height * 0.5);
    report.holdMouse.lineAfterClick = await page.evaluate(() => window.__portal.state.line.x);
    {
      const h = report.holdMouse;
      check(h.held && h.goneAt900 && h.lineAfterHold === 0.5 && Math.abs(h.lineAfterClick - 0.7) < 0.02, `hold to flood (mouse) ${JSON.stringify(h)}`);
    }

    // a held full flood with the clip playing: walkers cross as its front reaches their feet (at least one
    // crossing), their bursts stay at least 900 ms apart, and, held full, it stays after the release until
    // a tap lets it go (the tap does not move the line). A busy stretch of the clip, and the line at the
    // right edge, so that the walkers start in the filmed scene.
    report.floodPlay = await page.evaluate(async () => {
      const p = window.__portal, s = p.state;
      p.setLine(0.98); s.autoGlitch = true;
      s.video.currentTime = 22;
      await new Promise((r) => s.video.addEventListener('seeked', r, { once: true }));
      await s.video.play();
      await new Promise((r) => setTimeout(r, 1500));
      return { c0: s.crossings, t0: performance.now(), tracks: s.tracks.length };
    });
    await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.8);
    await page.mouse.down(); await sleep(6000); await page.mouse.up(); await sleep(1500);
    Object.assign(report.floodPlay, await page.evaluate((t0) => {
      const s = window.__portal.state, b = s.burstLog.filter((t) => t > t0), gaps = b.slice(1).map((t, i) => t - b[i]);
      return { crossings: s.crossings, bursts: b.length, gapsMs: gaps.map(Math.round),
               minGapMs: gaps.length ? Math.round(Math.min(...gaps)) : null, kept: !!(s.flood && s.flood.keep) };
    }, report.floodPlay.t0));
    report.floodPlay.crossings -= report.floodPlay.c0;
    await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.5);
    report.floodPlay.letGo = await page.waitForFunction(() => !window.__portal.state.flood, null, { timeout: 15000 }).then(() => true, () => false);
    report.floodPlay.lineAfterTap = await page.evaluate(() => window.__portal.state.line.x);
    await page.evaluate(() => window.__portal.setLine(0.5));
    {
      const f = report.floodPlay;
      check(f.crossings >= 1 && (f.minGapMs == null || f.minGapMs >= 900) && f.kept && f.letGo && f.lineAfterTap === 0.98,
            `flood with the clip playing ${JSON.stringify(f)}`);
    }

    // the flood's sound (sound on, clip paused): a rush while it grows, which ends at full cover, so a
    // flood held full and kept is quiet (no hiss until the next tap), and quiet again once let go
    await page.click('#b-sound'); await sleep(600);
    report.floodSound = await page.evaluate(() => {
      const p = window.__portal, s = p.state;
      s.video.pause(); s.autoGlitch = false; s.burst = null;
      const r = (window.__rush = { max: 0 });
      r.timer = setInterval(() => { r.max = Math.max(r.max, p.floodGain() || 0); }, 40);
      return { state: p.audioState() };
    });
    await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.6);
    await page.mouse.down(); await sleep(6000); await page.mouse.up(); await sleep(1500);
    Object.assign(report.floodSound, await page.evaluate(() => { const p = window.__portal, s = p.state;
      return { kept: !!(s.flood && s.flood.keep), rising: +window.__rush.max.toFixed(3), whileKept: p.floodGain() }; }));
    await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.5);
    report.floodSound.letGo = await page.waitForFunction(() => !window.__portal.state.flood, null, { timeout: 15000 }).then(() => true, () => false);
    await sleep(1200);
    Object.assign(report.floodSound, await page.evaluate(() => { const p = window.__portal, s = p.state;
      clearInterval(window.__rush.timer);
      const after = p.floodGain();
      s.video.play(); s.autoGlitch = true; p.setLine(0.5);
      return { afterLetGo: after }; }));
    await page.click('#b-sound'); await sleep(300);
    {
      const f = report.floodSound;
      check(f.state !== 'running' || (f.rising > 0.05 && f.kept && f.whileKept === 0 && f.letGo && f.afterLetGo === 0),
            `flood sound ${JSON.stringify(f)}`);
    }

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
    check(Math.abs(report.phone.lineAfterTap - 0.7) < 0.02, `phone tap ${report.phone.lineAfterTap}`);
    // a long press floods: a 700-ms touch (the browser's own touch input, so its pointer events, any
    // context menu and selection are real; as above, it waits for the hold if 3 frames take longer); let
    // go, it drains; the line stays; nothing on the page is selected
    {
      const cdp = await ctx.newCDPSession(page);
      const tx = box.x + box.width * 0.4, ty = box.y + box.height * 0.75;
      const n0 = await page.evaluate(() => window.__portal.state.floods);
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: tx, y: ty }] });
      await sleep(700);
      const held = await page.waitForFunction(() => { const f = window.__portal.state.flood; return !!(f && f.held); },
        null, { timeout: 3000, polling: 50 }).then(() => true, () => false);
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      const drained = await page.waitForFunction(() => !window.__portal.state.flood, null, { timeout: 15000 }).then(() => true, () => false);
      report.phone.flood = { held, drained, ...(await page.evaluate((n0) => { const sel = getSelection();
        return { floods: window.__portal.state.floods - n0, line: window.__portal.state.line.x, selected: String(sel),
                 collapsed: sel.rangeCount === 0 || sel.isCollapsed }; }, n0)) };
      const f = report.phone.flood;
      check(f.held && f.floods === 1 && f.drained && f.selected === '' && f.collapsed && Math.abs(f.line - 0.7) < 0.02,
            `phone long press ${JSON.stringify(f)}`);
    }
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
