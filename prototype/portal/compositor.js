// WebGL2 compositor: the same equation as crossover/composite.py, run per pixel on the GPU.
//
//   out = (1 - w) * F + w * [ P + (1 - a) * (R - Q) * S ]
//
// F camera frame, B clean plate, R the world (a generated image or a shader world computed from B),
// a person alpha (live mask, holes filled by a plate-difference test near people), P the person in
// the world's style, Q the plate in that same style (swaps the old background out of soft edges),
// S shadow ratio near people, w the rule: a line, a ring on the floor, a lens, or everything.

const VS = `#version 300 es
in vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }`;

const FS = `#version 300 es
precision highp float;
uniform sampler2D uCam, uMask, uPlate, uWorld, uPW;
uniform vec2 uRes;
uniform int uBg, uPer, uMode;
uniform mat4 uAff;
uniform vec2 uP0, uN, uLens;
uniform vec3 uPortal;
uniform float uSquash, uLensR, uGlitch, uSeed, uFlash, uMirror, uDebug, uHasPlate, uDiff, uGain, uS;
out vec4 o;

float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float hash1(float n) { return fract(sin(n * 12.9898) * 43758.5453); }
vec3 rgb2hsv(vec3 c) {
  vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
  vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
  vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
  float d = q.x - min(q.w, q.y);
  return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + 1e-10)), d / (q.x + 1e-10), q.x);
}
vec3 hsv2rgb(vec3 c) {
  vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}
float vignette(vec2 uv, float s) { vec2 d = (uv - 0.5) / 0.5; return 1.0 - s * clamp(dot(d, d) / 2.0, 0.0, 1.0); }
vec3 inferno(float t) {
  t = clamp(t, 0.0, 1.0);
  const vec3 c0 = vec3(0.0002189403691192265, 0.001651004631001012, -0.01948089843709184);
  const vec3 c1 = vec3(0.1065134194856116, 0.5639564367884091, 3.932712388889277);
  const vec3 c2 = vec3(11.60249308247187, -3.972853965665698, -15.9423941062914);
  const vec3 c3 = vec3(-41.70399613139459, 17.43639888205313, 44.35414519872813);
  const vec3 c4 = vec3(77.162935699427, -33.40235894210092, -81.80730925738993);
  const vec3 c5 = vec3(-71.31942824499214, 32.62606426397723, 73.20951985803202);
  const vec3 c6 = vec3(25.13112622477341, -12.24266895238567, -23.07032500287172);
  return clamp(c0 + t * (c1 + t * (c2 + t * (c3 + t * (c4 + t * (c5 + t * c6))))), 0.0, 1.0);
}

// ---- worlds (GLSL ports of crossover/styles.py; RGB order) ----
vec3 nightF(vec3 c, vec2 uv) {
  vec3 f = pow(max(c, 0.0), vec3(1.7)) * 0.55;
  f = 0.55 * f + 0.45 * luma(f);
  return f * vec3(0.70, 0.95, 1.35) * vignette(uv, 0.55);
}
float grain(vec2 px) { return (hash(px) + hash(px + 17.1) + hash(px + 31.7) - 1.5) * 2.0; }
vec3 centuryF(vec3 c, vec2 uv) {
  float y = clamp((luma(c) - 0.5) * 1.15 + 0.5, 0.0, 1.0);
  y = clamp(y + 0.035 * grain(floor(uv * uRes)), 0.0, 1.0);
  return (0.06 + 0.88 * y * vec3(1.0, 0.84, 0.62)) * vignette(uv, 0.6);
}
vec3 winterGrade(vec3 c) {
  vec3 f = 0.45 * c + 0.55 * luma(c);
  f = pow(max(f, 0.0), vec3(0.9)) * vec3(0.93, 1.02, 1.10);
  return 0.05 + 0.92 * f;
}
vec3 winterPlate(vec3 c, vec2 uv) {
  vec3 h = rgb2hsv(c);
  float hue = h.x * 360.0;
  float grass = (hue > 56.0 && hue < 190.0 && h.y > 0.176) ? 1.0 : 0.0;
  float ground = (h.y < 0.176 && h.z > 0.27 && h.z < 0.84) ? 1.0 : 0.0;
  float cover = clamp(grass * 0.95 + ground * 0.22, 0.0, 1.0);
  vec3 base = winterGrade(c) * (1.0 - 0.25 * ground);
  return mix(base, vec3(0.96, 0.985, 1.0) * 0.95, cover) * vignette(uv, 0.25);
}
float halftone(vec2 px) {
  float cell = 5.0 * max(1.0, uRes.x / 768.0);
  float u = (px.x + px.y) * 0.70710678, v = (px.x - px.y) * 0.70710678;
  return length(vec2(fract(u / cell) - 0.5, fract(v / cell) - 0.5)) / 0.70710678;
}
vec3 comicGrade(vec3 c, vec2 uv) {
  vec3 h = rgb2hsv(c);
  h.y = clamp(h.y * 1.6, 0.0, 1.0);
  vec3 f = hsv2rgb(h);
  vec3 q = floor(f * 3.0 + 0.5) / 3.0;
  float dots = halftone(uv * uRes) < clamp((1.0 - luma(f)) * 1.15 - 0.15, 0.0, 1.0) ? 1.0 : 0.0;
  return q * (1.0 - 0.6 * dots) + 0.04;
}
vec3 thermalPlate(vec3 c) { return inferno(0.06 + 0.40 * clamp((luma(c) - 0.1) / 0.75, 0.0, 1.0)); }
vec3 thermalPerson(vec3 c) { return inferno(0.70 + 0.28 * (1.0 - luma(c))); }
vec3 neonGrade(vec3 c) {
  float y = luma(c);
  return clamp(pow(y, 1.5) * 0.55 * (vec3(0.15, 0.75, 0.95) * (1.0 - y) + vec3(0.95, 0.25, 0.95) * y) * 1.4 + 0.02, 0.0, 1.0);
}
vec3 plateAt(vec2 uv) { return texture(uPlate, uv).rgb; }
vec2 sobel(vec2 uv, float s) {
  vec2 t = s / uRes;
  float a = luma(plateAt(uv + t * vec2(-1.0, -1.0))), b = luma(plateAt(uv + t * vec2(0.0, -1.0)));
  float c = luma(plateAt(uv + t * vec2(1.0, -1.0))), d = luma(plateAt(uv + t * vec2(-1.0, 0.0)));
  float f = luma(plateAt(uv + t * vec2(1.0, 0.0))), g = luma(plateAt(uv + t * vec2(-1.0, 1.0)));
  float h = luma(plateAt(uv + t * vec2(0.0, 1.0))), i = luma(plateAt(uv + t * vec2(1.0, 1.0)));
  return vec2((c + 2.0 * f + i) - (a + 2.0 * d + g), (g + 2.0 * h + i) - (a + 2.0 * b + c));
}
vec3 worldPlate(int k, vec2 uv) {
  if (k == 0) return texture(uWorld, uv).rgb;
  vec3 B = plateAt(uv);
  if (k == 1) return nightF(B, uv);
  if (k == 2) return centuryF(B, uv);
  if (k == 3) return winterPlate(B, uv);
  if (k == 4) return length(sobel(uv, 1.4 * uS)) > 0.38 ? vec3(0.08, 0.07, 0.08) : comicGrade(B, uv);
  if (k == 5) return thermalPlate(B);
  vec3 base = neonGrade(B);
  vec2 g1 = sobel(uv, 1.0 * uS), g2 = sobel(uv, 3.0 * uS);
  float glow = clamp(smoothstep(0.2, 0.5, length(g1)) * 1.4 + smoothstep(0.15, 0.6, length(g2)) * 0.6, 0.0, 1.0);
  vec3 col = abs(g1.y) > abs(g1.x) ? vec3(0.25, 0.95, 1.0) : vec3(1.0, 0.2, 0.85);
  return 1.0 - (1.0 - base) * (1.0 - glow * col);
}
vec3 person(int k, vec3 c, vec2 uv) {
  if (k < 0) return c;
  if (k == 0) return clamp((uAff * vec4(c, 1.0)).rgb, 0.0, 1.0);
  if (k == 1) return nightF(c, uv);
  if (k == 2) return centuryF(c, uv);
  if (k == 3) return winterGrade(c);
  if (k == 4) return comicGrade(c, uv);
  if (k == 5) return thermalPerson(c);
  return neonGrade(c);
}

// ---- rules: which side of the seam is a pixel on ----
float ringQ(vec2 px) { return length((px - uPortal.xy) / vec2(uPortal.z, uPortal.z * uSquash)); }
float modeWeight(vec2 px, float a, vec2 uv) {
  if (uMode == 0) return clamp(0.5 + dot(px - uP0, uN) / (3.0 * uS), 0.0, 1.0);
  if (uMode == 1) {
    float wb = clamp((1.0 - ringQ(px)) / 0.06 + 0.5, 0.0, 1.0);
    return a * texture(uPW, uv).r + (1.0 - a) * wb;      // a person changes by where their feet are
  }
  if (uMode == 2) return clamp((uLensR - length(px - uLens)) / (3.0 * uS) + 0.5, 0.0, 1.0);
  return 1.0;
}
vec3 seamGlow(vec2 px, float a) {
  float g = 0.0;
  if (uMode == 0) {
    float d = dot(px - uP0, uN) / uS;
    g = (exp(-(d / 2.0) * (d / 2.0)) + 0.35 * exp(-(d / 8.0) * (d / 8.0))) * 0.55;
  } else if (uMode == 1) {
    float t = (ringQ(px) - 1.0) / 0.035;
    g = exp(-t * t) * 0.9 * (1.0 - a);                      // the ring is on the floor, behind people
  } else if (uMode == 2) {
    float d = (length(px - uLens) - uLensR) / uS;
    g = exp(-(d / 2.5) * (d / 2.5)) * 0.7;
  }
  return g * vec3(0.75, 0.92, 1.0);
}
float maskAt(vec2 uv) { return texture(uMask, uv).r; }

vec3 compose(vec2 uv) {
  vec2 px = uv * uRes;
  vec3 F = texture(uCam, uv).rgb;
  if (uHasPlate < 0.5) return 1.0 - (1.0 - F) * (1.0 - seamGlow(px, 0.0));
  vec3 B = plateAt(uv) * uGain;
  float m = maskAt(uv), md = m, mb = 0.0;
  for (int i = 0; i < 8; i++) {
    float an = float(i) * 0.7853982;
    vec2 dir = vec2(cos(an), sin(an));
    md = max(md, maskAt(uv + dir * 10.0 * uS / uRes));
    mb += maskAt(uv + dir * vec2(0.035 * uRes.y / uRes.x, 0.035));
  }
  mb /= 8.0;
  float a = max(m, uDiff * step(0.3, md) * smoothstep(0.12, 0.25, length(F - B)));
  float dark = clamp((1.0 - luma(F) / (luma(B) + 1e-3) - 0.05) / 0.95, 0.0, 1.0) * (1.0 - step(0.1, md));
  float S = 1.0 - clamp(mb * 2.0, 0.0, 1.0) * dark * 0.9;
  vec3 R = worldPlate(uBg, uv);
  vec3 P = person(uPer, F, uv), Q = person(uPer, B, uv);
  vec3 rs = a > 0.004 ? P + (1.0 - a) * (R - Q) * S : R * S;
  vec3 c = mix(F, clamp(rs, 0.0, 1.0), modeWeight(px, a, uv));
  c = 1.0 - (1.0 - c) * (1.0 - seamGlow(px, a));
  if (uDebug > 0.5) c = mix(c, vec3(1.0, 0.1, 0.1), 0.45 * m);
  return c;
}

void main() {
  vec2 uv = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
  if (uMirror > 0.5) uv.x = 1.0 - uv.x;
  vec3 c;
  if (uGlitch > 0.0) {
    float band = floor(uv.y * 36.0);
    if (hash1(band + uSeed) > 1.0 - 0.35 * uGlitch) uv.x += (hash1(band * 1.7 + uSeed * 3.1) - 0.5) * 0.15 * uGlitch;
    float off = 0.008 * uGlitch;
    c = vec3(compose(uv + vec2(off, 0.0)).r, compose(uv).g, compose(uv - vec2(off, 0.0)).b);
  } else {
    c = compose(uv);
  }
  o = vec4(mix(c, vec3(1.0), uFlash), 1.0);
}`;

export class Compositor {
  constructor(canvas) {
    const gl = canvas.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false, premultipliedAlpha: false });
    if (!gl) throw new Error('WebGL2 is not available in this browser.');
    this.gl = gl;
    this.canvas = canvas;
    this.prog = this._program(VS, FS);
    this.loc = {};
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    this.vao = gl.createVertexArray();
    gl.bindVertexArray(this.vao);
    const a = gl.getAttribLocation(this.prog, 'aPos');
    gl.enableVertexAttribArray(a);
    gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
    this.tex = { cam: this.newTexture(), mask: this.newTexture(), plate: this.newTexture(), pw: this.newTexture() };
  }

  _program(vs, fs) {
    const gl = this.gl;
    const sh = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('Shader: ' + gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, sh(gl.VERTEX_SHADER, vs));
    gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('Link: ' + gl.getProgramInfoLog(p));
    return p;
  }

  newTexture() {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
    return t;
  }

  uploadImage(t, src) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
  }

  uploadR8(t, data, w, h) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, w, h, 0, gl.RED, gl.UNSIGNED_BYTE, data);
  }

  _u(name) {
    if (!(name in this.loc)) this.loc[name] = this.gl.getUniformLocation(this.prog, name);
    return this.loc[name];
  }

  draw(p) {
    const gl = this.gl;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.useProgram(this.prog);
    gl.bindVertexArray(this.vao);
    const units = [['uCam', this.tex.cam], ['uMask', this.tex.mask], ['uPlate', this.tex.plate],
                   ['uWorld', p.worldTex || this.tex.plate], ['uPW', this.tex.pw]];
    units.forEach(([name, t], i) => {
      gl.activeTexture(gl.TEXTURE0 + i);
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.uniform1i(this._u(name), i);
    });
    const f = (n, v) => gl.uniform1f(this._u(n), v);
    gl.uniform2f(this._u('uRes'), this.canvas.width, this.canvas.height);
    gl.uniform1i(this._u('uBg'), p.bg);
    gl.uniform1i(this._u('uPer'), p.per);
    gl.uniform1i(this._u('uMode'), p.mode);
    gl.uniformMatrix4fv(this._u('uAff'), false, p.aff);
    gl.uniform2f(this._u('uP0'), p.p0[0], p.p0[1]);
    gl.uniform2f(this._u('uN'), p.n[0], p.n[1]);
    gl.uniform2f(this._u('uLens'), p.lens[0], p.lens[1]);
    gl.uniform3f(this._u('uPortal'), p.portal[0], p.portal[1], p.portal[2]);
    f('uSquash', p.squash); f('uLensR', p.lensR); f('uGlitch', p.glitch); f('uSeed', p.seed);
    f('uFlash', p.flash); f('uMirror', p.mirror ? 1 : 0); f('uDebug', p.debug ? 1 : 0);
    f('uHasPlate', p.hasPlate ? 1 : 0); f('uDiff', p.diff ? 1 : 0); f('uGain', p.gain);
    f('uS', this.canvas.width / 768);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  // mean |output - reference| over a column range of the canvas (tests / diagnostics)
  readPixels() {
    const gl = this.gl, w = this.canvas.width, h = this.canvas.height;
    const px = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
    return { px, w, h };            // bottom-up rows
  }
}

export const IDENTITY_AFF = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
