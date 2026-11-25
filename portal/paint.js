// The paint mask: where the world shows, painted by hand.
//
// One grey value per frame pixel on an opaque canvas: black (0) is the filmed scene, white (1) the world.
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
}
