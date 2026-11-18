'use strict';
/* scene3d.js - a small painter's-algorithm 3D renderer (Canvas 2D) and the device builders
 * (planar MOSFET, FinFET, nanosheet GAA, CMOS pair). Colour = potential, moving dots = conduction current.
 */
(function (G) {
  const { cmapRGB, shadeRGB } = G.UI;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const LIGHT = (() => { const v = [-0.45, -0.55, 0.7], n = Math.hypot(...v); return v.map((x) => x / n); })();

  class Scene {
    constructor(canvas, o) {
      this.cv = canvas; this.o = Object.assign({ height: 300, yaw: -0.72, pitch: 0.55, zoom: 1 }, o || {});
      this.yaw = this.o.yaw; this.pitch = this.o.pitch; this.zoom = this.o.zoom; this.items = []; this.dpr = Math.min(2, window.devicePixelRatio || 1);
      let drag = null;
      canvas.style.touchAction = 'pan-y'; canvas.style.cursor = 'grab';
      canvas.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, yaw: this.yaw, pitch: this.pitch }; canvas.setPointerCapture(e.pointerId); canvas.style.cursor = 'grabbing'; });
      canvas.addEventListener('pointermove', (e) => { if (!drag) return; this.yaw = drag.yaw + (e.clientX - drag.x) * 0.008; if (e.pointerType === 'mouse') this.pitch = clamp(drag.pitch + (e.clientY - drag.y) * 0.006, 0.08, 1.5); if (this.onView) this.onView(); });
      const end = () => { drag = null; canvas.style.cursor = 'grab'; };
      canvas.addEventListener('pointerup', end); canvas.addEventListener('pointercancel', end);
      canvas.addEventListener('dblclick', () => { this.yaw = this.o.yaw; this.pitch = this.o.pitch; if (this.onView) this.onView(); });
    }
    reset() { this.items.length = 0; this.bb = null; }
    _ext(p) { const b = this.bb || (this.bb = { lo: [1e9, 1e9, 1e9], hi: [-1e9, -1e9, -1e9] }); for (let k = 0; k < 3; k++) { b.lo[k] = Math.min(b.lo[k], p[k]); b.hi[k] = Math.max(b.hi[k], p[k]); } }
    quad(pts, rgb, o) { o = o || {}; pts.forEach((p) => this._ext(p)); this.items.push({ t: 'q', pts, rgb, layer: o.layer || 1, alpha: o.alpha === undefined ? 1 : o.alpha, n: o.n, stroke: o.stroke === undefined ? 'rgba(20,30,60,0.35)' : o.stroke, flat: o.flat }); }
    /** faces: rgb or {top,bottom,ym,yp,xm,xp} (each rgb array) */
    box(x0, x1, y0, y1, z0, z1, cols, o) {
      o = o || {}; const C = (k) => (Array.isArray(cols) ? cols : cols[k] || cols.def || [200, 200, 200]);
      const F = [['top', [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], [0, 0, 1]], ['bottom', [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]], [0, 0, -1]],
        ['ym', [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], [0, -1, 0]], ['yp', [[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]], [0, 1, 0]],
        ['xm', [[x0, y0, z0], [x0, y1, z0], [x0, y1, z1], [x0, y0, z1]], [-1, 0, 0]], ['xp', [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]], [1, 0, 0]]];
      for (const [k, pts, n] of F) if (!(o.skip && o.skip.includes(k))) this.quad(pts, C(k), Object.assign({}, o, { n }));
    }
    line(p0, p1, o) { this._ext(p0); this._ext(p1); this.items.push(Object.assign({ t: 'l', p0, p1, layer: 4, width: 2, color: '#222', head: false }, o || {})); }
    dot(p, r, fill, o) { this.items.push(Object.assign({ t: 'd', p, r, fill, layer: 4, stroke: 'rgba(0,0,0,0.65)' }, o || {})); }
    label(p, text, o) { this.items.push(Object.assign({ t: 't', p, text, layer: 5, color: '#111', dx: 0, dy: 0, font: '600 11px system-ui, sans-serif', align: 'center' }, o || {})); }

    render() {
      const cv = this.cv, w = Math.max(240, cv.clientWidth || 400), hgt = this.o.height;
      if (cv.width !== w * this.dpr || cv.height !== hgt * this.dpr) { cv.width = w * this.dpr; cv.height = hgt * this.dpr; cv.style.height = hgt + 'px'; }
      const c = cv.getContext('2d'); c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      const g = c.createLinearGradient(0, 0, 0, hgt); g.addColorStop(0, '#ffffff'); g.addColorStop(1, '#eef1f6'); c.fillStyle = g; c.fillRect(0, 0, w, hgt);
      if (!this.bb) return;
      const cph = Math.cos(this.yaw), sph = Math.sin(this.yaw), cth = Math.cos(this.pitch), sth = Math.sin(this.pitch);
      const ctr = this.bb.lo.map((v, k) => (v + this.bb.hi[k]) / 2), R = Math.hypot(...this.bb.hi.map((v, k) => v - this.bb.lo[k])) / 2 || 1;
      const sc = 0.66 * Math.min(w, hgt * 1.25) / R * this.zoom;
      const P = (p) => { const x = p[0] - ctr[0], y = p[1] - ctr[1], z = p[2] - ctr[2]; const X = x * cph - y * sph, Y = x * sph + y * cph; return [w / 2 + X * sc, hgt / 2 + 6 - (Y * sth + z * cth) * sc, Y * cth - z * sth]; };
      const f = [cth * sph, cth * cph, -sth]; // camera forward in world coordinates
      const list = [];
      for (const it of this.items) {
        if (it.t === 'q') {
          if (it.n && it.n[0] * f[0] + it.n[1] * f[1] + it.n[2] * f[2] >= -1e-9) continue; // back face
          const pp = it.pts.map(P); it._pp = pp; it._d = pp.reduce((a, q) => a + q[2], 0) / 4; list.push(it);
        } else if (it.t === 'l') { it._a = P(it.p0); it._b = P(it.p1); it._d = (it._a[2] + it._b[2]) / 2; list.push(it); }
        else { it._a = P(it.p); it._d = it._a[2]; list.push(it); }
      }
      list.sort((a, b) => a.layer - b.layer || b._d - a._d);
      for (const it of list) {
        if (it.t === 'q') {
          let s = 0.78; if (it.n && !it.flat) s = 0.62 + 0.5 * Math.max(0, it.n[0] * LIGHT[0] + it.n[1] * LIGHT[1] + it.n[2] * LIGHT[2]);
          c.beginPath(); c.moveTo(it._pp[0][0], it._pp[0][1]); for (let k = 1; k < 4; k++) c.lineTo(it._pp[k][0], it._pp[k][1]); c.closePath();
          c.fillStyle = shadeRGB(it.rgb, s, it.alpha); c.fill();
          if (it.stroke) { c.strokeStyle = it.stroke; c.lineWidth = 0.6; c.stroke(); }
        } else if (it.t === 'l') {
          c.strokeStyle = it.color; c.fillStyle = it.color; c.lineWidth = it.width; c.beginPath(); c.moveTo(it._a[0], it._a[1]); c.lineTo(it._b[0], it._b[1]); c.stroke();
          if (it.head) { const a = Math.atan2(it._b[1] - it._a[1], it._b[0] - it._a[0]), L = 6 + it.width * 1.4; c.beginPath(); c.moveTo(it._b[0], it._b[1]); c.lineTo(it._b[0] - L * Math.cos(a - 0.45), it._b[1] - L * Math.sin(a - 0.45)); c.lineTo(it._b[0] - L * Math.cos(a + 0.45), it._b[1] - L * Math.sin(a + 0.45)); c.closePath(); c.fill(); }
        } else if (it.t === 'd') {
          c.beginPath(); c.arc(it._a[0], it._a[1], it.r, 0, 6.2832); c.fillStyle = it.fill; c.fill(); c.lineWidth = 0.9; c.strokeStyle = it.stroke; c.stroke();
        } else {
          c.font = it.font; c.textAlign = it.align; c.lineWidth = 3; c.strokeStyle = 'rgba(255,255,255,0.92)'; c.strokeText(it.text, it._a[0] + it.dx, it._a[1] + it.dy); c.fillStyle = it.color; c.fillText(it.text, it._a[0] + it.dx, it._a[1] + it.dy);
        }
      }
    }
  }

  // ------------------------------------------------------------------ shared helpers for the device builders
  const vcol = (v, st) => cmapRGB((v - st.vmin) / ((st.vmax - st.vmin) || 1));
  const mag = (I) => clamp((Math.log10(Math.max(Math.abs(I), 1e-13)) + 10) / 7, 0, 1);          // 0.1 nA -> 0, 1 mA -> 1 (log scale)
  /** u (0 = source terminal, 1 = drain terminal) at which the cumulative charge reaches c in [0,1] (carriers dwell where q is large) */
  function makeInvCdf(prof) {
    const n = prof.u.length, cum = [0];
    for (let k = 1; k < n; k++) cum.push(cum[k - 1] + 0.5 * (prof.q[k] + prof.q[k - 1]) * (prof.u[k] - prof.u[k - 1]) + 1e-4 * (prof.u[k] - prof.u[k - 1]));
    const tot = cum[n - 1];
    return (c) => { const t = c * tot; let k = 1; while (k < n - 1 && cum[k] < t) k++; const a = cum[k - 1], b = cum[k]; return prof.u[k - 1] + (prof.u[k] - prof.u[k - 1]) * (b > a ? (t - a) / (b - a) : 0); };
  }
  /** profile value at u by linear interpolation */
  const atU = (prof, arr, u) => { const n = prof.u.length - 1, x = clamp(u, 0, 1) * n, k = Math.min(n - 1, Math.floor(x)), f = x - k; return arr[k] * (1 - f) + arr[k + 1] * f; };
  const dotFill = (I) => (I > 0 ? '#fff7d6' : '#d6f0ff');

  // number of rows x dots and their motion are decided from |I| only (log scale), so small currents are visibly slow and sparse
  function flowParams(I, rows, cap) {
    const m = mag(I), per = Math.max(2, Math.round((2 + 6 * m) * (cap || 1)));
    return { m, per, speed: 0.08 + 0.5 * m, r: 1.5 + 1.7 * m, on: Math.abs(I) > 1e-12 };
  }

  // ------------------------------------------------------------------ planar MOSFET (also used twice for the CMOS pair)
  /** st: {v:{s,d,g,b}, vmin, vmax, prof, I, phase, ptype} ; off = [dx, dy, dz] */
  function planar(sc, st, off) {
    off = off || [0, 0, 0]; const [ox, oy, oz] = off;
    const Lg = 56, Lsd = 44, Wd = 70, depth = 14, sub = 24, tqmax = 9, tox = 2.5;
    const cS = vcol(st.v.s, st), cD = vcol(st.v.d, st), Ns = st.prof.u.length - 1;
    sc.box(ox - Lsd - 8, ox + Lg + Lsd + 8, oy - 6, oy + Wd + 6, oz - depth - sub, oz - depth, [196, 206, 222], { layer: 0 });           // body
    sc.box(ox - Lsd, ox, oy, oy + Wd, oz - depth, oz, cS, { layer: 1 });                                                                 // source
    sc.box(ox + Lg, ox + Lg + Lsd, oy, oy + Wd, oz - depth, oz, cD, { layer: 1 });                                                       // drain
    const qref = st.qmax || 1;
    for (let k = 0; k < Ns; k++) {
      const x0 = ox + Lg * k / Ns, x1 = ox + Lg * (k + 1) / Ns, v = (st.prof.v[k] + st.prof.v[k + 1]) / 2, q = (st.prof.q[k] + st.prof.q[k + 1]) / 2;
      const col = vcol(v, st), tq = tqmax * Math.sqrt(clamp(q / qref, 0, 1));
      sc.box(x0, x1, oy, oy + Wd, oz - depth, oz, col, { layer: 1, stroke: null });
      if (tq > 0.25) sc.box(x0, x1, oy, oy + Wd, oz - tq, oz, { top: col, ym: [60, 200, 214], yp: [60, 200, 214], xm: col, xp: col, def: col }, { layer: 2, stroke: null });
    }
    sc.box(ox - 4, ox + Lg + 4, oy - 4, oy + Wd + 4, oz + 0.6, oz + 0.6 + tox, [246, 226, 122], { layer: 3, alpha: 0.9 });               // gate oxide
    sc.box(ox - 4, ox + Lg + 4, oy - 4, oy + Wd + 4, oz + 0.6 + tox, oz + 28, vcol(st.v.g, st), { layer: 3, alpha: 0.42 });              // gate
    const nm = Object.assign({ s: 'S', d: 'D', g: 'G' }, st.names || {});
    if (nm.s) sc.label([ox - Lsd / 2, oy + Wd / 2, oz + 2], `${nm.s}  ${st.v.s.toFixed(2)} V`, { dy: -12 });
    if (nm.d) sc.label([ox + Lg + Lsd / 2, oy + Wd / 2, oz + 2], `${nm.d}  ${st.v.d.toFixed(2)} V`, { dy: -12 });
    if (nm.g) sc.label([ox + Lg / 2, oy + Wd / 2, oz + 30], `${nm.g}  ${st.v.g.toFixed(2)} V`, { dy: -6 });
    sc.label([ox + Lg / 2, oy - 8, oz - depth - sub / 2], `B  ${st.v.b.toFixed(2)} V`, { color: '#4a5160', dy: 16 });
    // conduction current: dots from the drain terminal to the source terminal (id > 0) or the other way round.
    // Path parameter s in [0,1): first S/D block (20 %), the channel (60 %, carriers dwell where the charge is large), last block (20 %).
    const fp = flowParams(st.I, 3);
    if (fp.on) {
      const inv = makeInvCdf(st.prof), fromD = st.I > 0, rows = [0.22, 0.5, 0.78];
      const xD = ox + Lg, xS = ox;                                   // channel ends
      const first = fromD ? [xD + 0.9 * Lsd, xD] : [xS - 0.9 * Lsd, xS];
      const last = fromD ? [xS, xS - 0.9 * Lsd] : [xD, xD + 0.9 * Lsd];
      rows.forEach((ry, ri) => {
        for (let i = 0; i < fp.per; i++) {
          const s = ((i + 0.31 * ri) / fp.per + (st.phase || 0) * fp.speed) % 1;
          let x;
          if (s < 0.2) x = first[0] + (first[1] - first[0]) * (s / 0.2);
          else if (s < 0.8) { const a = (s - 0.2) / 0.6; x = ox + Lg * inv(fromD ? 1 - a : a); }
          else x = last[0] + (last[1] - last[0]) * ((s - 0.8) / 0.2);
          sc.dot([x, oy + Wd * ry, oz + 1.8], fp.r, dotFill(st.I));
        }
      });
    }
  }

  // ------------------------------------------------------------------ FinFET
  /** st.geo = {H, Wf, pitch, N, L}; the channel profile is the same for every fin */
  function finfet(sc, st) {
    const { H, Wf, pitch, N, L } = st.geo, Lv = 2 * L + 30, Lsd = 26, Wy = N * pitch, sub = 20;
    const cS = vcol(st.v.s, st), cD = vcol(st.v.d, st), Ns = st.prof.u.length - 1;
    sc.box(-Lsd - 6, Lv + Lsd + 6, -8, Wy + 8, -sub, 0, [196, 206, 222], { layer: 0 });
    sc.box(-Lsd, 0, 0, Wy, 0, 0.7 * H, cS, { layer: 1 });
    sc.box(Lv, Lv + Lsd, 0, Wy, 0, 0.7 * H, cD, { layer: 1 });
    for (let j = N - 1; j >= 0; j--) {
      const yc = (j + 0.5) * pitch;
      for (let k = 0; k < Ns; k++) {
        const col = vcol((st.prof.v[k] + st.prof.v[k + 1]) / 2, st);
        sc.box(Lv * k / Ns, Lv * (k + 1) / Ns, yc - Wf / 2, yc + Wf / 2, 0, H, col, { layer: 1, stroke: null });
      }
    }
    sc.box(Lv * 0.18, Lv * 0.82, -4, Wy + 4, 0.2, H + 9, vcol(st.v.g, st), { layer: 3, alpha: 0.38 });
    sc.label([-Lsd / 2, Wy / 2, 0.7 * H], `S  ${st.v.s.toFixed(2)} V`, { dy: -12 });
    sc.label([Lv + Lsd / 2, Wy / 2, 0.7 * H], `D  ${st.v.d.toFixed(2)} V`, { dy: -12 });
    sc.label([Lv / 2, Wy / 2, H + 12], `G  ${st.v.g.toFixed(2)} V`, { dy: -6 });
    const fp = flowParams(st.I / N, 3, Math.min(1, 3 / (N + 1.5)));
    if (fp.on) {
      const inv = makeInvCdf(st.prof), fromD = st.I > 0;
      for (let j = 0; j < N; j++) {
        const yc = (j + 0.5) * pitch;
        [[yc - Wf / 2 - 0.9, H * 0.55], [yc + Wf / 2 + 0.9, H * 0.55], [yc, H + 0.9]].forEach(([y, z], ri) => {
          for (let i = 0; i < fp.per; i++) {
            const s = ((i + 0.31 * ri + 0.13 * j) / fp.per + (st.phase || 0) * fp.speed) % 1;
            const u = inv(fromD ? 1 - s : s);
            sc.dot([Lv * u, y, z], fp.r, dotFill(st.I));
          }
        });
      }
    }
  }

  // ------------------------------------------------------------------ nanosheet GAA
  /** st.geo = {N, W, T, L, gap} */
  function gaa(sc, st) {
    const { N, W, T, L } = st.geo, gap = st.geo.gap || 10, Lv = 2 * L + 30, Lsd = 26, stack = N * T + (N - 1) * gap, z0 = 8, sub = 16;
    const cS = vcol(st.v.s, st), cD = vcol(st.v.d, st), Ns = st.prof.u.length - 1;
    sc.box(-Lsd - 6, Lv + Lsd + 6, -14, W + 14, -sub, 0, [196, 206, 222], { layer: 0 });
    sc.box(-Lsd, 0, -6, W + 6, 0, z0 + stack + 5, cS, { layer: 1 });
    sc.box(Lv, Lv + Lsd, -6, W + 6, 0, z0 + stack + 5, cD, { layer: 1 });
    for (let j = 0; j < N; j++) {
      const zb = z0 + j * (T + gap);
      for (let k = 0; k < Ns; k++) sc.box(Lv * k / Ns, Lv * (k + 1) / Ns, 0, W, zb, zb + T, vcol((st.prof.v[k] + st.prof.v[k + 1]) / 2, st), { layer: 1, stroke: null });
    }
    sc.box(Lv * 0.18, Lv * 0.82, -9, W + 9, 0.2, z0 + stack + 8, vcol(st.v.g, st), { layer: 3, alpha: 0.34 });
    sc.label([-Lsd / 2, W / 2, z0 + stack + 6], `S  ${st.v.s.toFixed(2)} V`, { dy: -12 });
    sc.label([Lv + Lsd / 2, W / 2, z0 + stack + 6], `D  ${st.v.d.toFixed(2)} V`, { dy: -12 });
    sc.label([Lv / 2, W / 2, z0 + stack + 12], `G  ${st.v.g.toFixed(2)} V`, { dy: -6 });
    const fp = flowParams(st.I / N, 2, Math.min(1, 3 / (N + 1.2)));
    if (fp.on) {
      const inv = makeInvCdf(st.prof), fromD = st.I > 0;
      for (let j = 0; j < N; j++) {
        const zb = z0 + j * (T + gap);
        [[W * 0.3, zb + T + 0.9], [W * 0.7, zb + T + 0.9], [W * 0.5, zb - 0.9]].forEach(([y, z], ri) => {
          for (let i = 0; i < fp.per; i++) {
            const s = ((i + 0.31 * ri + 0.13 * j) / fp.per + (st.phase || 0) * fp.speed) % 1;
            sc.dot([Lv * inv(fromD ? 1 - s : s), y, z], fp.r, dotFill(st.I));
          }
        });
      }
    }
  }

  // ------------------------------------------------------------------ DRAM 1T1C cell (lesson 11)
  /** st: planar state of the access transistor with s = storage-node side (left), d = bit-line side (right), plus {vdd, vbl, vsn, vwl}. */
  function dram(sc, st) {
    const Lg = 56, Lsd = 44, Wd = 70, H = 64, hBL = 50, xc = Lg + Lsd / 2;
    planar(sc, Object.assign({}, st, { names: { s: '', d: '', g: '' } }), [0, 0, 0]);
    const cG = vcol(st.vwl, st);
    sc.box(-4, Lg + 4, -56, -4, 3.1, 28, cG, { layer: 3, alpha: 0.42 });                                                                  // the word line continues along y
    sc.box(-4, Lg + 4, Wd + 4, Wd + 56, 3.1, 28, cG, { layer: 3, alpha: 0.42 });
    sc.label([Lg / 2, -56, 30], `WL  ${st.vwl.toFixed(2)} V`, { dy: -4 });
    sc.box(xc - 4, xc + 4, Wd / 2 - 4, Wd / 2 + 4, 0, hBL, vcol(st.vbl, st), { layer: 2 });                                                // bit-line contact
    sc.box(xc - 4, xc + 118, Wd / 2 - 5, Wd / 2 + 5, hBL, hBL + 9, vcol(st.vbl, st), { layer: 3 });                                        // the bit line runs along x, perpendicular to the word line
    sc.label([xc + 100, Wd / 2, hBL + 12], `BL  ${st.vbl.toFixed(2)} V`, { dy: -6 });
    const frac = clamp(st.vsn / (st.vdd || 1), 0, 1), cSN = vcol(st.vsn, st);                                                              // storage capacitor: the fill height = stored voltage
    if (frac > 0.01) sc.box(-40, -8, 10, Wd - 10, 0.5, 0.5 + H * frac, cSN, { layer: 2 });
    sc.box(-43, -5, 6, Wd - 6, 0.5, 0.5 + H, [176, 184, 198], { layer: 3, alpha: 0.2 });                                                   // plate electrode (glass-like shell)
    sc.label([-24, Wd / 2, H + 4], `SN  ${st.vsn.toFixed(2)} V`, { dy: -6 });
    sc.label([-24, Wd / 2, H * 0.45], 'Cs', { color: '#1f3b73', font: '700 12px system-ui' });
    const fp = flowParams(st.I, 1);
    if (fp.on) for (let i = 0; i < fp.per; i++) { const s = ((i + 0.17) / fp.per + (st.phase || 0) * fp.speed) % 1; sc.dot([xc, Wd / 2, hBL * (st.I > 0 ? 1 - s : s)], fp.r, dotFill(st.I)); }
  }

  /** NMOS + PMOS pair (lesson 4): st.n and st.p are planar states */
  function cmos(sc, st) {
    const Wd = 70, dx = 200;    // the two devices side by side so that nothing hides behind anything
    sc.box(dx - 60, dx + 130, -12, Wd + 12, -46, -38, [190, 226, 190], { layer: 0, alpha: 0.95 });   // n-well under the PMOS
    planar(sc, st.n, [0, 0, 0]);
    planar(sc, st.p, [dx, 0, 0]);
    sc.label([30, Wd / 2, 36], 'NMOS', { color: '#1f3b73', font: '700 12px system-ui', dy: -14 });
    sc.label([dx + 30, Wd / 2, 36], 'PMOS (n-well)', { color: '#1f3b73', font: '700 12px system-ui', dy: -14 });
  }

  G.Scene3D = { Scene, planar, finfet, gaa, cmos, dram, flowParams, mag };
})(typeof window !== 'undefined' ? window : globalThis);
