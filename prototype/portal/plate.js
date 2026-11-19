// The empty scene, and colour matching for generated worlds.

// Masked temporal median over spaced frames: a pixel's value is the median of the frames where no
// person covered it (people standing still are removed by the mask, walkers by the median). Pixels
// that were covered in every frame fall back to the plain median.
export class PlateCapture {
  constructor(w, h, frames = 30, every = 4) {
    this.w = w; this.h = h; this.target = frames; this.every = every; this.seen = 0;
    this.frames = []; this.masks = [];
  }

  add(img, mask) {
    if (this.seen++ % this.every) return;
    const { w, h } = this, keep = new Uint8Array(w * h);
    if (mask) {
      for (let y = 0; y < h; y++) {
        const row = Math.min(mask.h - 1, Math.floor(y * mask.h / h)) * mask.w;
        for (let x = 0; x < w; x++) keep[y * w + x] = mask.data[row + Math.min(mask.w - 1, Math.floor(x * mask.w / w))] < 0.3 ? 1 : 0;
      }
    } else keep.fill(1);
    this.frames.push(new Uint8ClampedArray(img.data));
    this.masks.push(keep);
  }

  get done() { return this.frames.length >= this.target; }

  result() {
    const { w, h, frames, masks } = this, n = frames.length;
    const out = new ImageData(w, h), o = out.data;
    const buf = new Uint8Array(n);
    let blocked = 0;
    for (let i = 0; i < w * h; i++) {
      let valid = 0;
      for (let k = 0; k < n; k++) valid += masks[k][i];
      const useAll = valid < 3;
      if (useAll) blocked++;
      for (let c = 0; c < 3; c++) {
        let m = 0;
        for (let k = 0; k < n; k++) if (useAll || masks[k][i]) buf[m++] = frames[k][4 * i + c];
        const v = buf.subarray(0, m).sort();
        o[4 * i + c] = v[m >> 1];
      }
      o[4 * i + 3] = 255;
    }
    return { image: out, neverEmpty: blocked / (w * h) };
  }
}

// Least-squares colour affine world ~ A [plate, 1], fitted on random pixels. People are then shown
// in the world's light by the same transform; it is fixed per world, so it cannot flicker.
// Returns a column-major mat4 for the shader.
export function fitAffine(plate, world, samples = 4000) {
  const n = plate.width * plate.height, p = plate.data, q = world.data;
  const XtX = Array.from({ length: 4 }, () => new Float64Array(4));
  const XtY = Array.from({ length: 3 }, () => new Float64Array(4));
  let seed = 12345;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let s = 0; s < samples; s++) {
    const i = Math.floor(rnd() * n) * 4;
    const x = [p[i] / 255, p[i + 1] / 255, p[i + 2] / 255, 1];
    const y = [q[i] / 255, q[i + 1] / 255, q[i + 2] / 255];
    for (let a = 0; a < 4; a++) {
      for (let b = 0; b < 4; b++) XtX[a][b] += x[a] * x[b];
      for (let c = 0; c < 3; c++) XtY[c][a] += x[a] * y[c];
    }
  }
  const lam = 1e-3 * samples;
  const A = [];
  for (let c = 0; c < 3; c++) {
    const M = XtX.map((row, a) => row.map((v, b) => v + (a === b ? lam : 0)));
    const rhs = Array.from(XtY[c]);
    rhs[c] += lam;                                       // ridge toward identity
    A.push(solve4(M, rhs));
  }
  const m = new Float32Array(16);
  for (let col = 0; col < 4; col++) for (let row = 0; row < 3; row++) m[col * 4 + row] = A[row][col];
  m[15] = 1;
  return m;
}

function solve4(M, b) {
  const n = 4, a = M.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < n; c++) {
    let piv = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(a[r][c]) > Math.abs(a[piv][c])) piv = r;
    [a[c], a[piv]] = [a[piv], a[c]];
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = a[r][c] / a[c][c];
      for (let k = c; k <= n; k++) a[r][k] -= f * a[c][k];
    }
  }
  return a.map((r, i) => r[n] / r[i]);
}

// Draw any image source at the plate's size and return its pixels.
export function toImageData(src, w, h) {
  const c = new OffscreenCanvas(w, h), x = c.getContext('2d', { willReadFrequently: true });
  x.drawImage(src, 0, 0, w, h);
  return x.getImageData(0, 0, w, h);
}
