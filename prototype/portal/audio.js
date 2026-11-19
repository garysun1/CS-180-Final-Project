// Sound that follows the line, synthesized with Web Audio (no files): a quiet room tone, a pad chord
// per world that swells as people cross into it, and a whoosh on every crossing.
const CHORDS = [
  [110, 130.8, 164.8], [98, 123.5, 146.8], [87.3, 110, 130.8], [82.4, 103.8, 123.5],
  [73.4, 92.5, 110], [65.4, 82.4, 98], [116.5, 146.8, 174.6], [103.8, 130.8, 155.6], [92.5, 116.5, 138.6],
];

export class PortalAudio {
  constructor() {
    const ctx = (this.ctx = new (window.AudioContext || window.webkitAudioContext)());
    this.master = ctx.createGain();
    this.master.gain.value = 0.8;
    this.master.connect(ctx.destination);
    this.noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const d = this.noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    // room tone
    const bed = ctx.createBufferSource();
    bed.buffer = this.noise; bed.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 420;
    this.bedGain = ctx.createGain(); this.bedGain.gain.value = 0.05;
    bed.connect(lp).connect(this.bedGain).connect(this.master);
    bed.start();
    // world pad
    this.padGain = ctx.createGain(); this.padGain.gain.value = 0;
    const padLp = ctx.createBiquadFilter(); padLp.type = 'lowpass'; padLp.frequency.value = 900;
    padLp.connect(this.padGain).connect(this.master);
    this.osc = [0, 1, 2, 3, 4, 5].map((k) => {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.detune.value = k % 2 ? 7 : -7;
      const g = ctx.createGain(); g.gain.value = 0.12;
      o.connect(g).connect(padLp);
      o.start();
      return o;
    });
    this.setWorld(0);
  }

  resume() { return this.ctx.resume(); }

  setWorld(i) {
    const ch = CHORDS[i % CHORDS.length], t = this.ctx.currentTime;
    this.osc.forEach((o, k) => o.frequency.setTargetAtTime(ch[k % 3] * (k >= 3 ? 2 : 1), t, 0.15));
  }

  // f = share of the people currently in the other world (0..1)
  setAcross(f) {
    const t = this.ctx.currentTime;
    this.padGain.gain.setTargetAtTime(0.09 * f, t, 0.3);
    this.bedGain.gain.setTargetAtTime(0.05 * (1 - 0.6 * f), t, 0.3);
  }

  whoosh() {
    const ctx = this.ctx, t = ctx.currentTime;
    const s = ctx.createBufferSource(); s.buffer = this.noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 1.4;
    bp.frequency.setValueAtTime(300, t); bp.frequency.exponentialRampToValueAtTime(3200, t + 0.35);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.5, t + 0.08); g.gain.exponentialRampToValueAtTime(0.001, t + 0.5);
    s.connect(bp).connect(g).connect(this.master);
    s.start(t); s.stop(t + 0.55);
  }

  setMuted(m) { this.master.gain.setTargetAtTime(m ? 0 : 0.8, this.ctx.currentTime, 0.05); }
}
