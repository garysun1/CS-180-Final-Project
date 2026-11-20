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

// Colour for people in a world made on the spot (a dropped image, a kiosk world from the server):
// one robust colour affine  world ~ A [plate, 1], a port of the global fit in crossover/colormap.py.
// A ridge pulls it toward the identity (lam = 0.02 n), and Cauchy re-weighting (c = 0.08, 4 rounds)
// stops pixels whose content changed (snow over grass, painted strokes) from pulling the fit, so
// people keep their own contrast instead of collapsing into the world's average colour. Worlds
// built offline carry the full local field instead (scripts/build_portal_artifact.py).
// Returns a 1x1 colour field: rows r, g, b of (coefficients of r, g, b, offset), blended toward the
// identity by `strength` as the paper does (LocalAffineColor(strength=0.9)).
export function fitColourField(plate, world, samples = 4000, strength = 0.9) {
  const n = plate.width * plate.height, p = plate.data, q = world.data;
  const X = [], Y = [];
  let seed = 12345;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let s = 0; s < samples; s++) {
    const i = Math.floor(rnd() * n) * 4;
    X.push([p[i] / 255, p[i + 1] / 255, p[i + 2] / 255, 1]);
    Y.push([q[i] / 255, q[i + 1] / 255, q[i + 2] / 255]);
  }
  const prior = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]];
  const lam = 0.02 * samples, c2 = 0.08 * 0.08;
  const w = new Float64Array(samples).fill(1);
  let A = prior;
  for (let it = 0; it < 4; it++) {
    A = solveWeighted(X, Y, w, prior, lam);
    for (let s = 0; s < samples; s++) {
      const x = X[s];
      let r2 = 0;
      for (let k = 0; k < 3; k++) {
        const d = Y[s][k] - (A[k][0] * x[0] + A[k][1] * x[1] + A[k][2] * x[2] + A[k][3]);
        r2 += d * d;
      }
      w[s] = 1 / (1 + r2 / c2);
    }
  }
  const out = [];
  for (let k = 0; k < 3; k++) for (let j = 0; j < 4; j++) out.push(strength * A[k][j] + (1 - strength) * prior[k][j]);
  return out;
}

// argmin_A sum_s w_s |Y_s - A X_s|^2 + lam |A - prior|^2, solved row by row (A is 3x4).
function solveWeighted(X, Y, w, prior, lam) {
  const M = Array.from({ length: 4 }, () => new Float64Array(4));
  const R = Array.from({ length: 3 }, () => new Float64Array(4));
  for (let s = 0; s < X.length; s++) {
    const x = X[s], ws = w[s];
    for (let a = 0; a < 4; a++) {
      for (let b = 0; b < 4; b++) M[a][b] += ws * x[a] * x[b];
      for (let k = 0; k < 3; k++) R[k][a] += ws * x[a] * Y[s][k];
    }
  }
  for (let a = 0; a < 4; a++) M[a][a] += lam;
  return [0, 1, 2].map((k) => solve4(M.map((row) => Array.from(row)), R[k].map((v, a) => v + lam * prior[k][a])));
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
