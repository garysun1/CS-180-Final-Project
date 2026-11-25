// Painting worlds onto the video by hand.
//
// PaintMask: where one world shows. One grey value per frame pixel on an opaque canvas: black (0) is the
// filmed scene, white (1) the world.
// A brush dab is a soft disc, solid out to half its radius and fading to nothing at the edge, so a
// stroke ends in a short ramp. Cut puts its seam at 0.5 on that ramp; Morph uses the ramp itself as the
// band where the world grows in. The eraser paints black.
export class PaintMask {
  constructor() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d', { alpha: false, willReadFrequently: true });
    this.w = 0; this.h = 0;
    this.dirty = true;                 // changed since the last upload to the GPU
    this.empty = true;                 // nothing painted since the last clear
  }

  // Match the frame size; a new size starts empty. Returns true when it changed.
  resize(w, h) {
    if (w === this.w && h === this.h) return false;
    this.canvas.width = this.w = w; this.canvas.height = this.h = h;
    this.clear();
    return true;
  }

  clear() {
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.w, this.h);
    this.dirty = true; this.empty = true;
  }

  // One dab at (x, y) in frame fractions, radius r in px.
  dab(x, y, r, erase = false) {
    if (!this.w) return;
    const c = this.ctx, px = x * this.w, py = y * this.h, rgb = erase ? '0,0,0' : '255,255,255';
    const g = c.createRadialGradient(px, py, 0, px, py, r);
    g.addColorStop(0, `rgba(${rgb},1)`); g.addColorStop(0.5, `rgba(${rgb},1)`); g.addColorStop(1, `rgba(${rgb},0)`);
    c.fillStyle = g;
    c.beginPath(); c.arc(px, py, r, 0, 2 * Math.PI); c.fill();
    this.dirty = true;
    if (!erase) this.empty = false;
  }

  // Dabs from (x0, y0) to (x1, y1), a quarter of the radius apart, so a fast drag leaves no gaps.
  stroke(x0, y0, x1, y1, r, erase = false) {
    const n = Math.max(1, Math.ceil(Math.hypot((x1 - x0) * this.w, (y1 - y0) * this.h) / (0.25 * r)));
    for (let k = 1; k <= n; k++) this.dab(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, r, erase);
  }

  // The painted value (0 .. 1) at (x, y) in frame fractions: how far a person standing there is in.
  at(x, y) {
    if (!this.w) return 0;
    const px = Math.min(this.w - 1, Math.max(0, Math.floor(x * this.w)));
    const py = Math.min(this.h - 1, Math.max(0, Math.floor(y * this.h)));
    return this.ctx.getImageData(px, py, 1, 1).data[0] / 255;
  }

  // Nothing painted (after an eraser stroke, say).
  isEmpty() {
    const d = this.ctx.getImageData(0, 0, this.w, this.h).data;
    for (let i = 0; i < d.length; i += 4) if (d[i]) return false;
    return true;
  }
}

// Painting: several worlds at once, one PaintMask per world, the latest paint on top.
// A stroke paints its world in and erases the same dabs from every other world, so the masks never
// overlap; the eraser erases from all of them. Every stroke is kept (world, radius, points), so undo
// clears the masks and paints the strokes again, all but the last.
export class Painting {
  constructor() {
    this.masks = new Map();            // world index -> PaintMask, in the order first painted
    this.strokes = [];                 // {world, r, erase, pts} or {clear: true}
    this.cur = null;
    this.w = 0; this.h = 0;
  }

  // Match the frame size; a new size (or a new scene: reset) starts with nothing painted and no history.
  resize(w, h) {
    if (w === this.w && h === this.h) return false;
    this.w = w; this.h = h;
    this.reset();
    return true;
  }
  reset() { this.masks.clear(); this.strokes = []; this.cur = null; }

  // The worlds with paint, in the order they were first painted (drawn in that order, later on top).
  worlds() { return [...this.masks].filter(([, m]) => !m.empty).map(([k]) => k); }
  mask(k) {
    let m = this.masks.get(k);
    if (!m) { m = new PaintMask(); m.resize(this.w, this.h); this.masks.set(k, m); }
    return m;
  }

  begin(world, r, erase = false) { this.cur = { world, r, erase, pts: [] }; this.strokes.push(this.cur); }
  to(x, y) {
    const s = this.cur; if (!s) return;
    const [x0, y0] = s.pts.length ? s.pts[s.pts.length - 1] : [x, y];
    s.pts.push([x, y]);
    this._segment(s, x0, y0, x, y);
  }
  end() {
    if (!this.cur) return;
    this.cur = null;
    for (const m of this.masks.values()) if (!m.empty) m.empty = m.isEmpty();
  }
  _segment(s, x0, y0, x1, y1) {
    if (!s.erase) this.mask(s.world).stroke(x0, y0, x1, y1, s.r, false);
    for (const [k, m] of this.masks) if (!m.empty && (s.erase || k !== s.world)) m.stroke(x0, y0, x1, y1, s.r, true);
  }

  clear() { this.strokes.push({ clear: true }); for (const m of this.masks.values()) m.clear(); }

  // Take back the last stroke (or Clear). Returns false when there is nothing to undo.
  undo() {
    if (!this.strokes.length) return false;
    this.strokes.pop(); this.cur = null;
    for (const m of this.masks.values()) m.clear();
    for (const s of this.strokes) {
      if (s.clear) { for (const m of this.masks.values()) m.clear(); continue; }
      s.pts.forEach(([x, y], i) => { const [x0, y0] = s.pts[Math.max(0, i - 1)]; this._segment(s, x0, y0, x, y); });
    }
    for (const m of this.masks.values()) if (!m.empty) m.empty = m.isEmpty();
    return true;
  }

  // The world painted most at a point, and how much (world -1: none).
  top(x, y) {
    let world = -1, v = 0;
    for (const [k, m] of this.masks) {
      if (m.empty) continue;
      const p = m.at(x, y);
      if (p > v) { v = p; world = k; }
    }
    return { world, v };
  }
}
