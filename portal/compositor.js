// WebGL2 compositor: the project's composite equation, run per pixel on the GPU.
//
//   out = (1 - w) * F + w * [ P + (1 - a) * (R - Q) * S ]
//
// F camera frame, B clean plate, R the world (a generated image or a shader world computed from B),
// a person alpha (live mask, holes filled by a plate-difference test near people), P the person in
// the world's style, Q the plate in that same style (swaps the old background out of soft edges),
// S shadow ratio near people, w the rule: a line, a ring on the floor, a lens, a depth split, a mask
// painted by hand (paint.js), or all.
//
// People entering a generated world get the paper's local colour field (crossover/colormap.py): a
// smooth grid of 3x4 colour affines fitted from the empty scene to the world, baked per world by
// scripts/build_portal_artifact.py (or a robust global fit, plate.js, for worlds made on the spot).
//
// Two seams (uSeam). Cut (0): the rule is a 3-px cut with a thin glow. Grow (1): the rule becomes a
// one-sided band u in [0, 1] where the world is still forming. The background walks the world's
// ladder (crossover/morph.py, the same maths): the plate, the exact image img2img started from, a
// lower-strength SD image, the world. Colour crossfades while detail switches in noise patches (or
// halftone dots), so nothing is double-exposed. Where u = 0 the output is the camera pixel itself.
// The ladders of the current world and the one before it share one mipmapped 2D-array texture.
//
// Hold to flood: a ring of its own (uFlood: centre and radius in px, squashed onto the ground by
// uFloodSq) opens from a press, over the rule, which it takes over as it opens (uFloodK 0 .. 1) and
// gives back as it drains. People change by where their feet are (uPW). In Grow its front is a morph
// band 160 px wide (uFloodBand, a fraction of the radius); in Cut a 3-px edge. Its rim is in px.
//
// Written for software renderers too (SwiftShader in tests): code costs time even where it does not
// run, so compose() appears once (the glitch loops over it) and the ladder has four texture reads.

const VS = `#version 300 es
in vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }`;

const FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D uCam, uMask, uPlate, uWorld, uPW, uWorldPrev, uPaint;
uniform highp sampler2D uAffT, uFar;
uniform highp sampler2DArray uLad;
uniform vec2 uRes;
uniform vec4 uVP;
uniform int uBg, uPer, uMode, uView, uBgPrev, uBurstPer, uSeam, uMorphPat, uPrevPat, uPerPrev, uAffPrevRow;
uniform ivec2 uAffN, uAffNPrev;
uniform vec2 uP0, uN, uLens;
uniform vec3 uPortal;
uniform vec4 uGlitchBox;
uniform float uSquash, uLensR, uGlitch, uSeed, uFlash, uMirror, uDebug, uHasPlate, uDiff, uGain, uS;
uniform float uHasFar, uTau, uWave, uWaveOn, uBurst, uBurstEdge;
uniform float uBand, uLadN, uLadBase, uPrevN, uPrevBase, uForceRung, uBurstC;
uniform vec3 uFlood;
uniform float uFloodOn, uFloodSq, uFloodBand, uFloodK;
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

// ---- filter worlds (GLSL ports of crossover/styles.py; RGB order) ----
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
// Comic: posterize the value only (4 levels) and keep the hue, so grey and noisy pixels stay grey
// instead of breaking into per-channel colour confetti.
vec3 comicGrade(vec3 c, vec2 uv) {
  vec3 h = rgb2hsv(c);
  h.y = clamp(h.y * 1.6, 0.0, 1.0);
  if (h.y < 0.12) h.y = 0.0;
  h.z = floor(h.z * 3.0 + 0.5) / 3.0;
  vec3 f = hsv2rgb(h);
  float dots = halftone(uv * uRes) < clamp((1.0 - luma(f)) * 1.15 - 0.15, 0.0, 1.0) ? 1.0 : 0.0;
  return f * (1.0 - 0.6 * dots) + 0.04;
}
vec3 thermalPlate(vec3 c) { return inferno(0.06 + 0.40 * clamp((luma(c) - 0.1) / 0.75, 0.0, 1.0)); }
vec3 thermalPerson(vec3 c) { return inferno(0.70 + 0.28 * (1.0 - luma(c))); }
vec3 neonGrade(vec3 c) {
  float y = luma(c);
  return clamp(pow(y, 1.5) * 0.55 * (vec3(0.15, 0.75, 0.95) * (1.0 - y) + vec3(0.95, 0.25, 0.95) * y) * 1.4 + 0.02, 0.0, 1.0);
}
vec3 plateAt(vec2 uv) { return textureLod(uPlate, uv, 0.0).rgb; }
vec2 sobel(vec2 uv, float s) {
  vec2 t = s / uRes;
  float a = luma(plateAt(uv + t * vec2(-1.0, -1.0))), b = luma(plateAt(uv + t * vec2(0.0, -1.0)));
  float c = luma(plateAt(uv + t * vec2(1.0, -1.0))), d = luma(plateAt(uv + t * vec2(-1.0, 0.0)));
  float f = luma(plateAt(uv + t * vec2(1.0, 0.0))), g = luma(plateAt(uv + t * vec2(-1.0, 1.0)));
  float h = luma(plateAt(uv + t * vec2(0.0, 1.0))), i = luma(plateAt(uv + t * vec2(1.0, 1.0)));
  return vec2((c + 2.0 * f + i) - (a + 2.0 * d + g), (g + 2.0 * h + i) - (a + 2.0 * b + c));
}
vec3 filterPlate(int k, vec2 uv) {
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
vec3 worldPlate(int k, vec2 uv) { return k == 0 ? textureLod(uWorld, uv, 0.0).rgb : filterPlate(k, uv); }
vec3 worldPrev(int k, vec2 uv) { return k == 0 ? textureLod(uWorldPrev, uv, 0.0).rgb : filterPlate(k, uv); }

// ---- the morph (twin of crossover/morph.py): a world's ladder, walked in two bands ----
// lowbias32 on uint; the value-noise lattice is bit for bit morph.vnoise's: corner (i, j) holds
// (hash(i + hash(j + hash(seed))) >> 8) / 2^24, read at pixel centres, y down, smoothstep-interpolated
uint hashU(uint x) {
  x ^= x >> 16u; x *= 0x7FEB352Du; x ^= x >> 15u; x *= 0x846CA68Bu;
  return x ^ (x >> 16u);
}
float vnoise(vec2 px, float cell, uint seed) {
  vec2 p = px / cell, i = floor(p), t = p - i;
  t = t * t * (3.0 - 2.0 * t);
  uint ix = uint(int(i.x)), iy = uint(int(i.y)), s = hashU(seed);
  uint r0 = hashU(iy + s), r1 = hashU(iy + 1u + s);
  float a = float(hashU(ix + r0) >> 8u), b = float(hashU(ix + 1u + r0) >> 8u);
  float c = float(hashU(ix + r1) >> 8u), d = float(hashU(ix + 1u + r1) >> 8u);
  float top = a + (b - a) * t.x, bot = c + (d - c) * t.x;
  return (top + (bot - top) * t.y) / 16777216.0;
}
// where a pixel's detail switches as f runs 0..1, in [0.15, 0.85] so every rung stays exact: 18-px
// noise patches spread evenly by a logistic (morph.threshold 'noise'), or the halftone screen's dots
// (pat 1: dot centres first, so dots grow until they merge)
float morphTh(vec2 px, int pat) {
  float n;
  if (pat == 1) n = halftone(px);
  else {
    n = 0.65 * vnoise(px, 18.0 * uS, 0u) + 0.35 * vnoise(px, 6.0 * uS, 1u);
    n = 1.0 / (1.0 + exp(-10.0 * (n - 0.5)));
  }
  return clamp(0.15 + 0.7 * n, 0.15, 0.85);
}
// The ladders live in uLad: layer 0 the plate, layers base+1 .. base+n the rungs above it of one world
// (n steps; the last is the world itself), base 0 or 3. All mipmapped and read with explicit levels.
vec3 rungAt(float base, int k, vec2 uv, float lod) {
  vec3 c = textureLod(uLad, vec3(uv, k == 0 ? 0.0 : base + float(k)), lod).rgb;
  return k == 0 ? c * uGain : c;                          // the plate under the camera's exposure
}
// r in [0, n]: rungs k = floor(r) and k + 1, f = r - k. Colour (mip level 2.5, about morph's 3-px blur)
// crossfades with f; detail switches where f passes th. Exact at every integer r (one read there).
vec3 ladderAt(bool prev, float r, vec2 uv, vec2 px) {
  int n = int((prev ? uPrevN : uLadN) + 0.5);
  float base = prev ? uPrevBase : uLadBase;
  r = clamp(r, 0.0, float(n));
  int k = min(int(r), n - 1);
  float f = r - float(k);
  vec3 A = rungAt(base, k, uv, 0.0);
  if (f <= 0.0) return A;
  vec3 B = rungAt(base, k + 1, uv, 0.0);
  if (f >= 1.0) return B;
  float lod = 2.5 + log2(uS);
  vec3 lowA = rungAt(base, k, uv, lod), lowB = rungAt(base, k + 1, uv, lod);
  float th = morphTh(px, prev ? uPrevPat : uMorphPat);
  float s = smoothstep(th - 0.12, th + 0.12, f);
  return (1.0 - s) * A + s * B + (f - s) * (lowB - lowA);   // = lowA + f(lowB - lowA) + highA + s(highB - highA)
}

// ---- the local colour field: texel (3i + r, j) holds output row r of grid cell (i, j), as
// (coefficient of r, of g, of b, offset). Interpolated like cv2.resize INTER_LINEAR (half-pixel
// centres, edges clamped), which is how crossover/colormap.py expands its grid to every pixel.
// prev: during a world change (Grow) the texture also holds the old world's field, from row uAffPrevRow.
vec4 affRow(int i, int j, int r) { return texelFetch(uAffT, ivec2(3 * i + r, j), 0); }
void fieldAt(vec2 uv, bool prev, out vec4 A0, out vec4 A1, out vec4 A2) {
  ivec2 N = prev ? uAffNPrev : uAffN;
  vec2 g = vec2(N);
  vec2 p = clamp(uv * g - 0.5, vec2(0.0), g - 1.0);
  ivec2 i0 = ivec2(floor(p));
  ivec2 i1 = min(i0 + 1, N - 1);
  vec2 f = p - vec2(i0);
  int row = prev ? uAffPrevRow : 0;
  i0.y += row; i1.y += row;
  A0 = mix(mix(affRow(i0.x, i0.y, 0), affRow(i1.x, i0.y, 0), f.x), mix(affRow(i0.x, i1.y, 0), affRow(i1.x, i1.y, 0), f.x), f.y);
  A1 = mix(mix(affRow(i0.x, i0.y, 1), affRow(i1.x, i0.y, 1), f.x), mix(affRow(i0.x, i1.y, 1), affRow(i1.x, i1.y, 1), f.x), f.y);
  A2 = mix(mix(affRow(i0.x, i0.y, 2), affRow(i1.x, i0.y, 2), f.x), mix(affRow(i0.x, i1.y, 2), affRow(i1.x, i1.y, 2), f.x), f.y);
}
vec3 person(int k, vec3 c, vec2 uv, vec4 A0, vec4 A1, vec4 A2) {
  if (k < 0) return c;
  if (k == 0) { vec4 x = vec4(c, 1.0); return clamp(vec3(dot(A0, x), dot(A1, x), dot(A2, x)), 0.0, 1.0); }
  if (k == 1) return nightF(c, uv);
  if (k == 2) return centuryF(c, uv);
  if (k == 3) return winterGrade(c);
  if (k == 4) return comicGrade(c, uv);
  if (k == 5) return thermalPerson(c);
  return neonGrade(c);
}

// ---- rules: which side of the seam is a pixel on ----
float ringQ(vec2 px) { return length((px - uPortal.xy) / vec2(uPortal.z, uPortal.z * uSquash)); }
// farness (0 near .. 1 far) and its gradient magnitude per pixel; without a depth map, lower = nearer
vec2 farAt(vec2 uv) { return uHasFar > 0.5 ? texture(uFar, uv).rg : vec2(1.0 - uv.y, 1.0 / uRes.y); }
float modeWeight(vec2 px, float a, vec2 uv) {
  if (uMode == 0) return clamp(0.5 + dot(px - uP0, uN) / (3.0 * uS), 0.0, 1.0);
  if (uMode == 1) {
    float wb = clamp((1.0 - ringQ(px)) / 0.06 + 0.5, 0.0, 1.0);
    return a * texture(uPW, uv).r + (1.0 - a) * wb;      // a person changes by where their feet are
  }
  if (uMode == 2) return clamp((uLensR - length(px - uLens)) / (3.0 * uS) + 0.5, 0.0, 1.0);
  if (uMode == 4) {                                       // everything farther than tau
    float wb = smoothstep(0.0, 1.0, (farAt(uv).x - uTau) / 0.06 + 0.5);
    return a * texture(uPW, uv).r + (1.0 - a) * wb;      // people by the depth at their feet
  }
  if (uMode == 5) {                                       // painted by hand: the seam at half coverage
    float wb = clamp((texture(uPaint, uv).r - 0.5) / 0.06 + 0.5, 0.0, 1.0);
    return a * texture(uPW, uv).r + (1.0 - a) * wb;      // people by the paint under their feet
  }
  return 1.0;
}
// Grow: how far the world has grown at a pixel, 0 (the filmed scene) .. 1 (the whole world), one-sided:
// a band uBand px wide past the line, the outer half of the lens, the ring's pool, depth beyond tau
float ruleGrow(vec2 px, vec2 uv) {
  if (uMode == 0) return clamp(dot(px - uP0, uN) / (uBand * uS), 0.0, 1.0);
  if (uMode == 1) return clamp((1.0 - ringQ(px)) / 0.6, 0.0, 1.0);
  if (uMode == 2) return clamp((uLensR - length(px - uLens)) / (0.5 * uLensR), 0.0, 1.0);
  if (uMode == 4) return clamp((farAt(uv).x - uTau) / 0.25, 0.0, 1.0);
  if (uMode == 5) return texture(uPaint, uv).r;          // the brush's soft edge is the band
  return 1.0;
}
// A person's level where they stand: uPW holds each tracked person's value (r) where they are (g = 1),
// premultiplied, so it blends smoothly. Elsewhere alpha is only the mask's fading trail or a filled
// hole, not a person: those pixels take the ground's level, or they would show the empty scene.
float feetAt(vec2 uv, float ground) { vec2 p = texture(uPW, uv).rg; return p.r + (1.0 - p.g) * ground; }
// the flood: how far inside its ring a pixel is, in px (the ellipse scaled to a circle of radius uFlood.z)
float floodIn(vec2 px) { return uFlood.z - length((px - uFlood.xy) * vec2(1.0, 1.0 / uFloodSq)); }
// ... and the rule with a flood over it: the flood's own band, or what the rule still shows
float growU(vec2 px, vec2 uv) {
  float u = ruleGrow(px, uv);
  if (uFloodOn < 0.5) return u;
  return max(clamp(floodIn(px) / max(uFloodBand * uFlood.z, 1e-3), 0.0, 1.0), (1.0 - uFloodK) * u);
}
// Cut's weight; with a flood, its 3-px edge over the rule's floor, and people by their feet (uPW)
float cutWeight(vec2 px, float a, vec2 uv) {
  if (uFloodOn < 0.5) return modeWeight(px, a, uv);
  float wf = max(clamp(floodIn(px) / (3.0 * uS) + 0.5, 0.0, 1.0), (1.0 - uFloodK) * modeWeight(px, 0.0, uv));
  return a * feetAt(uv, wf) + (1.0 - a) * wf;
}
// grow: line and lens keep a 0.3x glint on the world side only, rising from nothing at the edge so it
// marks no edge there; the ring keeps its rim; depth draws no contour. A flood's rim is measured in px,
// so it stays thin as the ring grows; the rule's glow fades as the flood takes over.
vec3 seamGlow(vec2 px, float a, vec2 uv, bool grow) {
  float g = 0.0;
  if (uMode == 0) {
    float d = dot(px - uP0, uN) / uS;
    g = (exp(-(d / 2.0) * (d / 2.0)) + 0.35 * exp(-(d / 8.0) * (d / 8.0))) * 0.55;
    if (grow) g *= 0.3 * smoothstep(0.0, 6.0, d);
  } else if (uMode == 1) {
    float t = (ringQ(px) - 1.0) / 0.035;
    g = exp(-t * t) * 0.9 * (1.0 - a);                      // the ring is on the floor, behind people
  } else if (uMode == 2) {
    float d = (length(px - uLens) - uLensR) / uS;
    g = exp(-(d / 2.5) * (d / 2.5)) * 0.7;
    if (grow) g *= 0.3 * smoothstep(0.0, 6.0, -d);
  } else if (uMode == 4 && !grow) {
    vec2 fg = farAt(uv);
    float d = (fg.x - uTau) / max(fg.y, 1e-4) / uS;        // distance to the contour, in pixels
    g = exp(-(d / 2.5) * (d / 2.5)) * 0.85 * (1.0 - a);
  } else if (uMode == 5 && !grow) {                       // a thin outline where the paint crosses half
    vec2 t = 1.0 / vec2(textureSize(uPaint, 0));
    float p = texture(uPaint, uv).r;
    vec2 gr = vec2(texture(uPaint, uv + vec2(t.x, 0.0)).r - texture(uPaint, uv - vec2(t.x, 0.0)).r,
                   texture(uPaint, uv + vec2(0.0, t.y)).r - texture(uPaint, uv - vec2(0.0, t.y)).r) * 0.5;
    float d = (p - 0.5) / max(length(gr), 1e-3) / uS;       // distance to the outline, in pixels
    g = exp(-(d / 2.0) * (d / 2.0)) * 0.6 * (1.0 - a) * step(0.02, length(gr));
  }
  if (uFloodOn > 0.5) {
    float t = floodIn(px) / (4.5 * uS);
    g = g * (1.0 - uFloodK) + exp(-t * t) * 0.9 * (1.0 - a);   // on the floor, behind people
  }
  return g * vec3(0.75, 0.92, 1.0);
}
float maskAt(vec2 uv) { return texture(uMask, uv).r; }
// person alpha: the live mask, with holes filled by a plate-difference test near people
float alphaAt(vec2 uv, vec3 F, vec3 B, out float md, out float mb) {
  float m = maskAt(uv);
  md = m; mb = 0.0;
  for (int i = 0; i < 8; i++) {
    float an = float(i) * 0.7853982;
    vec2 dir = vec2(cos(an), sin(an));
    md = max(md, maskAt(uv + dir * 10.0 * uS / uRes));
    mb += maskAt(uv + dir * vec2(0.035 * uRes.y / uRes.x, 0.035));
  }
  mb /= 8.0;
  return max(m, uDiff * step(0.3, md) * smoothstep(0.12, 0.25, length(F - B)));
}
// just outside a person's silhouette: the ink outline drawn around the one who crosses
float edgeAt(vec2 uv) {
  if (maskAt(uv) > 0.5) return 0.0;
  vec2 t = 2.5 * uS / uRes;
  float n = max(max(maskAt(uv + vec2(t.x, 0.0)), maskAt(uv - vec2(t.x, 0.0))),
                max(maskAt(uv + vec2(0.0, t.y)), maskAt(uv - vec2(0.0, t.y))));
  return step(0.5, n);
}
bool inGlitchBox(vec2 uv) {
  return uBurst > 0.5 && uv.x >= uGlitchBox.x && uv.y >= uGlitchBox.y && uv.x <= uGlitchBox.z && uv.y <= uGlitchBox.w;
}

// Grow's background: a world grown to t in [0, 1]. A generated world walks its ladder (a world not loaded
// in uLad, during the manual glitch, fades in instead); a filter world fades in over the plate. prev: the
// world a world change is leaving. Rn, Ro: the new and the old world as Cut shows them.
vec3 growBackground(float t, bool prev, vec2 uv, vec2 px, vec3 B, vec3 Rn, vec3 Ro) {
  float n = prev ? uPrevN : uLadN;
  if ((prev ? uBgPrev : uBg) != 0 || n < 0.5) {
    vec3 W = prev ? Ro : Rn;
    return t <= 0.0 ? B : t >= 1.0 ? W : mix(B, W, t);
  }
  return ladderAt(prev, uForceRung >= 0.0 ? uForceRung : n * t, uv, px);
}

// The composite, for both seams. Cut (uSeam 0) is the seam as it always was. Grow (uSeam 1) is the
// same equation with the rule as a band where the world is still forming:
//   R = the world grown to u (growBackground)
//   P = mix(F, A(F), c), Q = mix(B, A(B), c): people take the world's colour with c = u per pixel
//       (line, lens) or u at their feet (portal, depth; uPW), and in full inside a burst box
//   w = smoothstep(0, 0.12, u): the band starts as the camera frame and crossfades into the plate
// and where u = 0 (and no one's feet are in the world) the pixel is the camera's, bit for bit.
// A world change is a 0.30-farness front rolling in from the horizon: behind it the old world unmakes
// back to the plate through its own ladder, beyond it the new one grows, and people follow the ground
// (the old world's colour behind the front, the new one's beyond), so at the front, where the rim is,
// the picture is the filmed scene. A flood adds its ring to u (growU) and to Cut's w (cutWeight), and
// people then go by their feet, as on the portal.
vec3 compose(vec2 uv) {
  vec2 px = uv * uRes;
  vec3 F = texture(uCam, uv).rgb;
  bool grow = uSeam == 1;
  if (uHasPlate < 0.5) return 1.0 - (1.0 - F) * (1.0 - seamGlow(px, 0.0, uv, false));
  bool flood = uFloodOn > 0.5;
  bool box = inGlitchBox(uv), feet = uMode == 1 || uMode == 4 || uMode == 5 || flood;   // feet: people change by where they stand
  float u = 1.0, up = 1.0;
  if (grow) {
    u = uForceRung >= 0.0 ? 1.0 : growU(px, uv);
    up = feet ? feetAt(uv, u) : u;
    float e = uMode == 1 ? (ringQ(px) - 1.0) / 0.035 : 9.0;      // the ring's rim also lights the floor outside it
    if (flood) e = min(abs(e), abs(floodIn(px) / (4.5 * uS)));    // and so does the flood's
    if (u <= 0.0 && up <= 0.0 && !box && abs(e) > 3.1) {           // the filmed side
      return uDebug > 0.5 ? mix(F, vec3(1.0, 0.1, 0.1), 0.45 * maskAt(uv)) : F;
    }
  }
  bool prev = false;                                      // grow, during a world change: behind the front
  float side = 1.0, fw = 0.0;                             // how far this side's world has grown, of u
  if (grow && uWaveOn > 0.5) {
    fw = farAt(uv).x;
    float uw = clamp((fw - uWave) / 0.30 + 0.5, 0.0, 1.0);
    prev = uw <= 0.5;
    side = prev ? 1.0 - 2.0 * uw : 2.0 * uw - 1.0;
  }
  vec3 B = plateAt(uv) * uGain;
  float md, mb;
  float a = alphaAt(uv, F, B, md, mb);
  float dark = clamp((1.0 - luma(F) / (luma(B) + 1e-3) - 0.05) / 0.95, 0.0, 1.0) * (1.0 - step(0.1, md));
  float S = 1.0 - clamp(mb * 2.0, 0.0, 1.0) * dark * 0.9;
  int per = box ? uBurstPer : prev ? uPerPrev : uPer;     // only the one who crosses flashes through styles
  vec4 A0 = vec4(1.0, 0.0, 0.0, 0.0), A1 = vec4(0.0, 1.0, 0.0, 0.0), A2 = vec4(0.0, 0.0, 1.0, 0.0);
  if (per == 0) fieldAt(uv, prev && !box, A0, A1, A2);
  vec3 R = worldPlate(uBg, uv);
  vec3 Ro = uWaveOn > 0.5 ? worldPrev(uBgPrev, uv) : R;
  if (grow) {
    R = growBackground(u * side, prev, uv, px, B, R, Ro);
    if (uForceRung >= 0.0) return R;                      // (test hook: the background alone, at that rung)
    if (uWaveOn > 0.5) {                                  // the rim, where the image is the plate
      float e = (fw - uWave) / 0.012;
      R = 1.0 - (1.0 - R) * (1.0 - exp(-e * e) * 0.9 * vec3(1.0, 0.95, 0.85));
    }
  } else if (uWaveOn > 0.5) {                             // the new world rolls in from the horizon
    float f = farAt(uv).x, t = (f - uWave) / 0.012;
    R = mix(Ro, R, smoothstep(0.0, 1.0, (f - uWave) / 0.05 + 0.5));
    R = 1.0 - (1.0 - R) * (1.0 - exp(-t * t) * 0.9 * vec3(1.0, 0.95, 0.85));
  }
  vec3 P = person(per, F, uv, A0, A1, A2), Q = person(per, B, uv, A0, A1, A2);
  float w;
  if (grow) {
    float cp = (a > 0.004 ? up : u) * side, pw = up;
    if (box) { cp = max(cp, uBurstC); pw = max(pw, uBurstC); }   // the one who crosses flashes in full
    P = mix(F, P, cp); Q = mix(B, Q, cp);
    w = smoothstep(0.0, 0.12, feet ? a * pw + (1.0 - a) * u : u);
  } else {
    w = cutWeight(px, a, uv);
  }
  vec3 rs = a > 0.004 ? P + (1.0 - a) * (R - Q) * S : R * S;
  vec3 c = mix(F, clamp(rs, 0.0, 1.0), w);
  c = 1.0 - (1.0 - c) * (1.0 - seamGlow(px, a, uv, grow));
  if (box && a < 0.5) {                                   // ink outline; misregistered edges right after a switch
    if (edgeAt(uv) > 0.5) c = vec3(0.07, 0.06, 0.08);
    if (uBurstEdge > 0.5) {
      vec2 sh = vec2(4.0 * uS / uRes.x, 0.0);
      if (edgeAt(uv - sh) > 0.5) c = vec3(0.0, 1.0, 1.0);
      else if (edgeAt(uv + sh) > 0.5) c = vec3(1.0, 0.0, 1.0);
    }
  }
  if (uDebug > 0.5) c = mix(c, vec3(1.0, 0.1, 0.1), 0.45 * maskAt(uv));
  return c;
}

// ---- the Layers view: the pipeline, one layer per tile ----
vec3 layerView(int v, vec2 uv) {
  vec2 px = uv * uRes;
  vec3 F = texture(uCam, uv).rgb;
  vec3 B = plateAt(uv) * uGain;
  float md, mb;
  float a = uHasPlate > 0.5 ? alphaAt(uv, F, B, md, mb) : maskAt(uv);
  if (v == 1) return mix(F, vec3(1.0, 0.18, 0.15), 0.55 * a);                  // filmed + the mask
  if (v == 2) return B;                                                        // the empty scene
  if (v == 3) return worldPlate(uBg, uv);                                      // the one generated image
  if (v == 4) {                                                                // people, cut out
    float ch = mod(floor(px.x / (14.0 * uS)) + floor(px.y / (14.0 * uS)), 2.0);
    return mix(vec3(0.09 + 0.05 * ch), F, a);
  }
  if (v == 5) {                                                                // the rule (grow: u, a gradient)
    float u = growU(px, uv);
    bool feet = uMode == 1 || uMode == 4 || uMode == 5 || uFloodOn > 0.5;
    float w = uSeam == 1 ? (feet ? a * feetAt(uv, u) + (1.0 - a) * u : u) : cutWeight(px, a, uv);
    return mix(vec3(0.04, 0.05, 0.07), vec3(0.42, 0.72, 1.0), w) + seamGlow(px, a, uv, uSeam == 1);
  }
  // 6: the person colour of the empty scene in this world, without gain (colour parity test)
  vec4 A0 = vec4(1.0, 0.0, 0.0, 0.0), A1 = vec4(0.0, 1.0, 0.0, 0.0), A2 = vec4(0.0, 0.0, 1.0, 0.0);
  if (uPer == 0) fieldAt(uv, false, A0, A1, A2);
  return person(uPer, plateAt(uv), uv, A0, A1, A2);
}

void main() {
  vec2 fc = gl_FragCoord.xy - uVP.xy;                     // this tile's pixel (GL: bottom-left origin)
  vec2 uv = vec2(fc.x / uVP.z, 1.0 - fc.y / uVP.w);
  if (uMirror > 0.5) uv.x = 1.0 - uv.x;
  vec3 c = vec3(0.0);
  if (uView != 0) {
    c = layerView(uView, uv);
  } else {
    // the manual glitch tears the frame into bands and splits its channels, composing once per channel
    // (a loop, so the shader holds one copy of compose)
    int n = 1;
    float off = 0.0;
    if (uGlitch > 0.0) {
      float band = floor(uv.y * 36.0);
      if (hash1(band + uSeed) > 1.0 - 0.35 * uGlitch) uv.x += (hash1(band * 1.7 + uSeed * 3.1) - 0.5) * 0.15 * uGlitch;
      n = 3; off = 0.008 * uGlitch;
    }
    for (int i = 0; i < n; i++) {
      vec3 ci = compose(uv + vec2(off * float(1 - i), 0.0));   // red from +off, green at 0, blue from -off
      if (n == 1) c = ci; else c[i] = ci[i];
    }
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
    this.tex = { cam: this.newTexture(), mask: this.newTexture(), plate: this.newTexture(), pw: this.newTexture(),
                paint: this.newTexture() };
    this.identityField = this.newField(1, 1, IDENTITY_FIELD);
    this.noFar = this.newFar(1, 1, new Float32Array([0, 0]));
    this.lad = null;
    this.noLad = this._newLadder(1, 1);
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

  // The ladders (Grow): one 2D-array texture at the frame size, mipmapped (the morph reads the colour
  // band at level 2.5). Layer 0 is the plate; layers 1-3 (slot 0) and 4-6 (slot 1) hold the rungs above
  // it of two worlds, the current one and the one before it, the last of each being the world itself.
  _newLadder(w, h) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, t);
    gl.texStorage3D(gl.TEXTURE_2D_ARRAY, Math.floor(Math.log2(Math.max(w, h))) + 1, gl.RGBA8, w, h, 7);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }

  // Upload frame-size images to consecutive layers from `first` (0 the plate; 1 + 3*slot the rungs of a
  // world) and regenerate the mip chain, as after every upload. A new frame size starts a new texture
  // whose world slots are empty: the returned generation changes then.
  setLadder(first, images) {
    const gl = this.gl, W = this.canvas.width, H = this.canvas.height;
    if (!this.lad || this.lad.w !== W || this.lad.h !== H) {
      if (this.lad) gl.deleteTexture(this.lad.tex);
      this.lad = { tex: this._newLadder(W, H), w: W, h: H, gen: (this.lad ? this.lad.gen : 0) + 1 };
    }
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.lad.tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    images.forEach((img, i) => gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, first + i, W, H, 1, gl.RGBA, gl.UNSIGNED_BYTE, img));
    gl.generateMipmap(gl.TEXTURE_2D_ARRAY);
    return this.lad.gen;
  }

  // A colour field: gx x gy cells of 3x4 affines (RGB rows; coefficients of r, g, b, then the offset),
  // as a float texture read with texelFetch only. NEAREST is required: float textures are not
  // filterable in WebGL2 without an extension, and an incomplete texture would read as black.
  newField(gx, gy, coeffs) {
    return { tex: this._fieldTex(3 * gx, gy, Float32Array.from(coeffs)), gx, gy };
  }

  // Grow, during a world change: the new world's field (rows from 0) and the old world's (rows from
  // cur.gy) in one texture, so people behind the front keep the old world's colour. cur, prev: {gx, gy,
  // coeffs} as for newField.
  newWaveField(cur, prev) {
    const W = 3 * Math.max(cur.gx, prev.gx), H = cur.gy + prev.gy, data = new Float32Array(4 * W * H);
    const put = (f, row0) => {
      for (let j = 0; j < f.gy; j++) data.set(Float32Array.from(f.coeffs.slice(12 * f.gx * j, 12 * f.gx * (j + 1))), 4 * W * (row0 + j));
    };
    put(cur, 0); put(prev, cur.gy);
    return { tex: this._fieldTex(W, H, data), gx: cur.gx, gy: cur.gy, prevGx: prev.gx, prevGy: prev.gy, prevRow: cur.gy };
  }

  _fieldTex(w, h, data) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, w, h, 0, gl.RGBA, gl.FLOAT, data);
    return t;
  }

  // Farness and its gradient magnitude per pixel, as a filterable half-float texture.
  newFar(w, h, fg) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RG16F, w, h, 0, gl.RG, gl.FLOAT, fg);
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

  // the paint mask (paint.js): its canvas's red channel, one byte per frame pixel
  uploadPaint(canvas) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.tex.paint);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, gl.RED, gl.UNSIGNED_BYTE, canvas);
  }

  // two bytes per texel (the per-person weights: value, and 255 where a person is)
  uploadRG8(t, data, w, h) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RG8, w, h, 0, gl.RG, gl.UNSIGNED_BYTE, data);
  }

  _u(name) {
    if (!(name in this.loc)) this.loc[name] = this.gl.getUniformLocation(this.prog, name);
    return this.loc[name];
  }

  // Clear the whole canvas (the Layers view letterboxes its tiles).
  clear() {
    const gl = this.gl;
    gl.disable(gl.SCISSOR_TEST);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0.02, 0.025, 0.035, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }

  // p.vp = [x, y, w, h] in GL window pixels (bottom-left origin); defaults to the whole canvas.
  // Grow: p.seam 1, p.band (px at 768 wide), p.lad = {n, slot}: the current world's ladder, n steps
  // above the plate (1 plate -> world, 2 via the filter image, 3 via a lower-strength SD image too; 0
  // not loaded), p.pattern ('dots' or noise); p.prevLad, p.prevPattern: the world a wave is leaving.
  // p.forceRung >= 0 draws the background alone at that rung (test hook).
  // Hold to flood: p.flood = [x, y, r] in frame px, or null; p.floodSq its squash, p.floodBand its Grow
  // band as a fraction of r, p.floodK how far it has taken over the rule (0 .. 1).
  draw(p) {
    const gl = this.gl, W = this.canvas.width, H = this.canvas.height;
    const vp = p.vp || [0, 0, W, H];
    gl.viewport(vp[0], vp[1], vp[2], vp[3]);
    gl.useProgram(this.prog);
    gl.bindVertexArray(this.vao);
    const field = p.field || this.identityField;
    const units = [['uCam', this.tex.cam], ['uMask', this.tex.mask], ['uPlate', this.tex.plate],
                   ['uWorld', p.worldTex || this.tex.plate], ['uPW', this.tex.pw], ['uAffT', field.tex],
                   ['uFar', p.farTex || this.noFar], ['uWorldPrev', p.prevTex || this.tex.plate]];
    units.forEach(([name, t], i) => {
      gl.activeTexture(gl.TEXTURE0 + i);
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.uniform1i(this._u(name), i);
    });
    gl.activeTexture(gl.TEXTURE8);
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.lad ? this.lad.tex : this.noLad);
    gl.uniform1i(this._u('uLad'), 8);
    gl.activeTexture(gl.TEXTURE9);
    gl.bindTexture(gl.TEXTURE_2D, this.tex.paint);
    gl.uniform1i(this._u('uPaint'), 9);
    const f = (n, v) => gl.uniform1f(this._u(n), v);
    const i1 = (n, v) => gl.uniform1i(this._u(n), v);
    gl.uniform2f(this._u('uRes'), W, H);
    gl.uniform4f(this._u('uVP'), vp[0], vp[1], vp[2], vp[3]);
    i1('uBg', p.bg); i1('uPer', p.per); i1('uMode', p.mode); i1('uView', p.view || 0);
    i1('uBgPrev', p.prevKind == null ? 1 : p.prevKind); i1('uBurstPer', p.burstPer == null ? -1 : p.burstPer);
    gl.uniform2i(this._u('uAffN'), field.gx, field.gy);
    gl.uniform2i(this._u('uAffNPrev'), field.prevGx || field.gx, field.prevGy || field.gy);
    i1('uAffPrevRow', field.prevRow || 0); i1('uPerPrev', p.perPrev == null ? -1 : p.perPrev);
    gl.uniform2f(this._u('uP0'), p.p0[0], p.p0[1]);
    gl.uniform2f(this._u('uN'), p.n[0], p.n[1]);
    gl.uniform2f(this._u('uLens'), p.lens[0], p.lens[1]);
    gl.uniform3f(this._u('uPortal'), p.portal[0], p.portal[1], p.portal[2]);
    const box = p.burstBox || [0, 0, 0, 0];
    gl.uniform4f(this._u('uGlitchBox'), box[0], box[1], box[2], box[3]);
    f('uSquash', p.squash); f('uLensR', p.lensR); f('uGlitch', p.glitch); f('uSeed', p.seed);
    f('uFlash', p.flash); f('uMirror', p.mirror ? 1 : 0); f('uDebug', p.debug ? 1 : 0);
    f('uHasPlate', p.hasPlate ? 1 : 0); f('uDiff', p.diff ? 1 : 0); f('uGain', p.gain);
    f('uS', W / 768);
    f('uHasFar', p.farTex ? 1 : 0); f('uTau', p.tau == null ? 0.5 : p.tau);
    f('uWaveOn', p.waveOn ? 1 : 0); f('uWave', p.wave == null ? -1 : p.wave);
    f('uBurst', p.burst ? 1 : 0); f('uBurstEdge', p.burstEdge ? 1 : 0);
    i1('uSeam', p.seam ? 1 : 0); f('uBand', p.band || 120);
    const lad = p.lad || { n: 0, slot: 0 }, pl = p.prevLad || { n: 0, slot: 0 };
    f('uLadN', lad.n); f('uLadBase', 3 * lad.slot); f('uPrevN', pl.n); f('uPrevBase', 3 * pl.slot);
    i1('uMorphPat', p.pattern === 'dots' ? 1 : 0); i1('uPrevPat', p.prevPattern === 'dots' ? 1 : 0);
    f('uForceRung', p.forceRung == null ? -1 : p.forceRung); f('uBurstC', p.burstC == null ? 1 : p.burstC);
    const fl = p.flood || [0, 0, 0];
    f('uFloodOn', p.flood ? 1 : 0); gl.uniform3f(this._u('uFlood'), fl[0], fl[1], fl[2]);
    f('uFloodSq', p.floodSq || 1); f('uFloodBand', p.floodBand || 0.6); f('uFloodK', p.floodK || 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  readPixels() {
    const gl = this.gl, w = this.canvas.width, h = this.canvas.height;
    const px = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
    return { px, w, h };            // bottom-up rows
  }
}

// The identity colour transform as a 1x1 field (rows r, g, b): people keep their own colours.
export const IDENTITY_FIELD = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0];
