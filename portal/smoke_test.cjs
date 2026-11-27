// End-to-end smoke test of the portal with a fake webcam (Chromium plays a .y4m file as the camera).
//   python -m crossover.portal_server --no-generate --port 8765 &
//   node portal/smoke_test.cjs http://localhost:8765/ path/to/clip.y4m out_dir [autostart]
// "autostart" opens ?autostart=1 with the browser's normal autoplay policy and clicks nothing: the page
// must start on its own, and its sound must wait for a user gesture instead of queueing up.
// Last, it switches to the recorded clip (B) and exports a second of it: 10 frames at the clip's own 10 fps.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [url, y4m, out, mode] = process.argv.slice(2);
  const autostart = mode === 'autostart';
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           `--use-file-for-fake-video-capture=${y4m}`, '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
           ...(autostart ? [] : ['--autoplay-policy=no-user-gesture-required'])],
  });
  const ctx = await browser.newContext({ viewport: { width: 1000, height: 760 }, deviceScaleFactor: 1,
                                         recordVideo: { dir: out, size: { width: 1000, height: 760 } } });
  const page = await ctx.newPage();
  const errors = [], logs = [];
  page.on('console', (m) => { (m.type() === 'error' ? errors : logs).push(m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  const report = { ok: false };
  try {
    await page.goto(url + '?mirror=0&debug=1' + (autostart ? '&autostart=1' : ''), { waitUntil: 'load' });
    if (!autostart) await page.click('#go');
    const t0 = Date.now();
    await page.waitForFunction(() => window.__portal && window.__portal.state.plate, null, { timeout: 180000 });
    report.secondsToPlate = (Date.now() - t0) / 1000;
    report.audioBeforeGesture = await page.evaluate(() => window.__portal.audioState());
    await page.waitForTimeout(3000);
    const st = await page.evaluate(() => {
      const s = window.__portal.state;
      return { delegate: s.delegate, fps: s.fps, segMs: s.segMs, w: s.video.videoWidth, h: s.video.videoHeight,
               mask: window.__portal.maskStats(), server: s.server, log: s.log };
    });
    Object.assign(report, st);
    // line in the middle: left of it must be the camera frame, right of it the world
    // no auto-glitch while comparing: a crossing would tear the frame for 450 ms
    await page.evaluate(() => { const p = window.__portal; p.setDebug(false); p.setLine(0.5); p.setWorld(0); p.setMode(0); p.state.autoGlitch = false; });
    await page.waitForTimeout(3000);                      // let the world-switch flash fade
    // crossings also flash the frame: compare on a frame with no flash
    await page.waitForFunction(() => window.__portal.state.flash < 0.02, null, { timeout: 30000 });
    report.diffRealSide = await page.evaluate(() => window.__portal.compare(0.02, 0.4));
    report.diffWorldSide = await page.evaluate(() => window.__portal.compare(0.6, 0.98));
    await page.evaluate(() => { window.__portal.state.autoGlitch = true; });
    const shots = [];
    const snap = async (name) => { const p = path.join(out, `${name}.png`); await page.screenshot({ path: p }); shots.push(p); };
    for (let k = 0; k < 6; k++) {
      await page.evaluate((i) => window.__portal.setWorld(i), k);
      await page.waitForTimeout(1800);
      await snap(`world_${k}`);
    }
    await page.evaluate(() => { window.__portal.setWorld(4); window.__portal.setMode(1); });
    await page.waitForTimeout(2500); await snap('mode_portal');
    await page.evaluate(() => { window.__portal.setWorld(1); window.__portal.setMode(2); });
    await page.mouse.move(520, 420); await page.waitForTimeout(1200); await snap('mode_lens');
    await page.evaluate(() => { window.__portal.setMode(0); window.__portal.glitch(3000); });
    await page.waitForTimeout(400); await snap('glitch');
    report.crossings = await page.evaluate(() => window.__portal.state.crossings);
    report.fpsEnd = await page.evaluate(() => window.__portal.state.fps);
    // the recorded clip (B): once its empty scene is in, Export runs at the clip's own rate (10 fps)
    await page.keyboard.press('b');
    await page.waitForFunction(() => { const s = window.__portal.state; return s.source === 'clip' && s.plate; }, null, { timeout: 180000 });
    report.clipExport = await page.evaluate(() => window.__portal.exportClip({ start: 0, end: 1 }));
    report.shots = shots;
    report.ok = errors.length === 0 && report.diffWorldSide > report.diffRealSide * 2 &&
      (!autostart || report.audioBeforeGesture !== 'running') &&
      !!report.clipExport && report.clipExport.fps === 10 && report.clipExport.frames === 10;
  } catch (e) {
    report.error = String(e);
  }
  report.errors = errors;
  report.consoleTail = logs.slice(-12);
  await ctx.close();
  await browser.close();
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report, null, 1));
  process.exit(report.ok ? 0 : 1);
})();
