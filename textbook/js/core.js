'use strict';
/* core.js - the MOSFET models of minispice (Level 1, EKV with DIBL and channel charges) and small solvers.
 * Every equation is a port of minispice/models.py; tests/test_js_parity.py compares the two implementations.
 */
(function (G) {
  const VT = 0.025865; // kT/q at 300.15 K
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

  // ------------------------------------------------------------------ Level 1 (Shichman-Hodges)
  const L1_DEFAULT = { vto: 0, kp: 2e-5, gamma: 0, phi: 0.6, lambda: 0, cgso: 0, cgdo: 0, cgbo: 0 };
  function level1Core(p, vgs, vds, vbs, w, l) {
    const beta = p.kp * w / l, phi = p.phi, gamma = p.gamma, lam = p.lambda, sphi = Math.sqrt(phi);
    let sarg, dsarg;
    if (vbs <= 0) { sarg = Math.sqrt(phi - vbs); dsarg = -0.5 / sarg; }
    else { const d = 1 + 0.5 * vbs / phi; sarg = sphi / d; dsarg = -sphi * (0.5 / phi) / (d * d); }
    const vth = p.vtoEff + gamma * (sarg - sphi), dvth = gamma * dsarg;
    const vov = vgs - vth;
    if (vov <= 0) return { i: 0, gm: 0, gds: 0, gmb: 0, vth, vov };
    const clm = 1 + lam * vds;
    let i0, gm, gds;
    if (vds < vov) { i0 = beta * (vov - 0.5 * vds) * vds; gm = beta * vds * clm; gds = beta * (vov - vds) * clm + lam * i0; }
    else { i0 = 0.5 * beta * vov * vov; gm = beta * vov * clm; gds = lam * i0; }
    return { i: i0 * clm, gm, gds, gmb: -gm * dvth, vth, vov };
  }

  // ------------------------------------------------------------------ EKV
  const EKV_DEFAULT = { vto: 0.5, kp: 2e-4, n: 1.3, lambda: 0, eta: 0, cgso: 0, cgdo: 0, cgbo: 0, cox: 0 };
  const softplus = (x) => (x > 0 ? x + Math.log1p(Math.exp(-x)) : Math.log1p(Math.exp(x)));
  const sigmoid = (x) => (x >= 0 ? 1 / (1 + Math.exp(-x)) : Math.exp(x) / (1 + Math.exp(x)));
  function ekvF(x) { const h = 0.5 * x, sp = softplus(h); return [sp * sp, sp * sigmoid(h)]; }
  // inverse of F: x = 2 ln(e^sqrt(i) - 1)
  function ekvFinv(i) { return 2 * Math.log(Math.expm1(Math.sqrt(Math.max(i, 1e-300)))); }
  const qOfI = (i) => 2 * i / (Math.sqrt(1 + 4 * i) + 1);
  const GAUSS3 = [[0.5 * (1 - Math.sqrt(0.6)), 5 / 18], [0.5, 8 / 18], [0.5 * (1 + Math.sqrt(0.6)), 5 / 18]];

  function ekvCore(p, vgs, vds, vbs, w, l) {
    const n = p.n, lam = p.lambda, eta = p.eta;
    const is = 2 * n * p.kp * (w / l) * VT * VT;
    const vp = (vgs + eta * vds - vbs - p.vtoEff) / n;
    const vsb = -vbs, vdb = vds - vbs;
    const [ff, dff] = ekvF((vp - vsb) / VT), [fr, dfr] = ekvF((vp - vdb) / VT);
    const i0 = is * (ff - fr), clm = 1 + lam * vds;
    const dVp = is / VT * (dff - dfr), dVsb = -is / VT * dff, dVdb = is / VT * dfr;
    const gm = clm * dVp / n;
    const gds = clm * dVdb + lam * i0 + eta * gm;
    const gmb = clm * (-dVp / n - dVsb - dVdb);
    return { i: i0 * clm, gm, gds, gmb, if: ff, ir: fr, vp, is };
  }
  function ekvChargeCore(p, vgs, vds, vbs, w, l) {
    const n = p.n;
    const vp = (vgs + p.eta * vds - vbs - p.vtoEff) / n;
    const iF = ekvF((vp + vbs) / VT)[0], iR = ekvF((vp - (vds - vbs)) / VT)[0];
    const qs = qOfI(iF), qd = qOfI(iR), bigS = qs + qd + 1, delta = qs - qd;
    let qInv = 0, dFrac = 0;
    for (const [t, wt] of GAUSS3) {
      const q = qd + delta * t, f = q * (2 * q + 1) / bigS;
      qInv += wt * f; dFrac += wt * (1 - t * (q + qd + 1) / bigS) * f;
    }
    const q0 = 2 * n * VT * p.cox * w * l;
    const qiTot = -q0 * qInv, qdTot = -q0 * dFrac;
    return { qg: -qiTot, qd: qdTot, qs: qiTot - qdTot, qb: 0 };
  }

  // ------------------------------------------------------------------ model objects
  function makeModel(kind, polarity, params) {
    const def = kind === 'level1' ? L1_DEFAULT : EKV_DEFAULT;
    const p = Object.assign({}, def, params || {});
    p.vtoEff = polarity * p.vto; // VTO is entered negative for PMOS, as in SPICE
    return { kind, pol: polarity, p };
  }
  const coreOf = (m, vgs, vds, vbs, w, l) => (m.kind === 'level1' ? level1Core : ekvCore)(m.p, vgs, vds, vbs, w, l);

  /** Terminal-voltage interface identical to MosModel.evaluate: id flows INTO the drain terminal. */
  function evaluate(m, vd, vg, vs, vb, w, l) {
    const pol = m.pol; vd *= pol; vg *= pol; vs *= pol; vb *= pol;
    if (vd >= vs) {
      const r = coreOf(m, vg - vs, vd - vs, vb - vs, w, l);
      return { id: pol * r.i, gd: r.gds, gg: r.gm, gs: -(r.gm + r.gds + r.gmb), gb: r.gmb, core: r, swapped: false };
    }
    const r = coreOf(m, vg - vd, vs - vd, vb - vd, w, l);
    return { id: -pol * r.i, gd: r.gm + r.gds + r.gmb, gg: -r.gm, gs: -r.gds, gb: -r.gmb, core: r, swapped: true };
  }
  /** Terminal charges [qd, qg, qs, qb] (EKV with cox > 0 only). */
  function charges(m, vd, vg, vs, vb, w, l) {
    const pol = m.pol; vd *= pol; vg *= pol; vs *= pol; vb *= pol;
    let r, swapped = false;
    if (vd >= vs) r = ekvChargeCore(m.p, vg - vs, vd - vs, vb - vs, w, l);
    else { r = ekvChargeCore(m.p, vg - vd, vs - vd, vb - vd, w, l); swapped = true; }
    const qd = swapped ? r.qs : r.qd, qs = swapped ? r.qd : r.qs;
    return [pol * qd, pol * r.qg, pol * qs, pol * r.qb];
  }
  /** Capacitance matrix C[k][j] = dQ_k/dV_j, order d, g, s, b (central differences, h = 1 uV). */
  function chargeJac(m, vd, vg, vs, vb, w, l, h) {
    h = h || 1e-6;
    const v0 = [vd, vg, vs, vb], q0 = charges(m, vd, vg, vs, vb, w, l), c = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    for (let j = 0; j < 4; j++) {
      const hi = v0.slice(), lo = v0.slice(); hi[j] += h; lo[j] -= h;
      const qh = charges(m, hi[0], hi[1], hi[2], hi[3], w, l), ql = charges(m, lo[0], lo[1], lo[2], lo[3], w, l);
      for (let k = 0; k < 4; k++) c[k][j] = (qh[k] - ql[k]) / (2 * h);
    }
    return { q: q0, c };
  }

  // ------------------------------------------------------------------ channel profiles (for the 3D views)
  /**
   * Potential V(u) and normalised inversion charge q(u) along the channel, u = 0 at the "source" terminal
   * and u = 1 at the "drain" terminal as the device is drawn. N points. Derived from the model equations:
   *  Level 1 : charge-sheet integral  Id*y = mu*Cox*W*(Vov*V - V^2/2); the pinched-off part is a linear ramp.
   *  EKV     : the local current i(u) falls linearly from i_f to i_r, and V = Vp - Vt*F^-1(i(u)).
   */
  function channelProfile(m, vd, vg, vs, vb, w, l, N) {
    N = N || 33;
    const pol = m.pol;
    let d = pol * vd, g = pol * vg, s = pol * vs, b = pol * vb, flip = false;
    if (d < s) { const t = d; d = s; s = t; flip = true; } // the lower terminal (in the n-type frame) acts as the source
    const vgs = g - s, vds = d - s, vbs = b - s;
    const u = [], V = [], q = [];
    let info = {};
    if (m.kind === 'level1') {
      const r = level1Core(m.p, vgs, vds, vbs, w, l), vov = r.vov, clm = 1 + m.p.lambda * vds;
      if (vov <= 0) {
        for (let k = 0; k < N; k++) { const x = k / (N - 1); u.push(x); V.push(s + vds * x); q.push(0); }
        info = { region: 'cutoff', vov, pinch: 1 };
      } else {
        const tri = vds < vov, upinch = tri ? 1 : 1 / clm;          // where the channel is pinched off (u = 1: not pinched)
        const iob = tri ? (vov - 0.5 * vds) * vds : 0.5 * vov * vov;  // I / (beta * clm) without the lambda factor
        for (let k = 0; k < N; k++) {
          const x = k / (N - 1);
          let v, qq;
          if (x <= upinch) { v = vov - Math.sqrt(Math.max(0, vov * vov - 2 * iob * (x / upinch))); qq = vov - v; }
          else { v = vov + (vds - vov) * (x - upinch) / (1 - upinch); qq = 0; }   // depletion region: potential ramps up to Vds
          u.push(x); V.push(s + v); q.push(qq);
        }
        info = { region: tri ? 'triode' : 'saturation', vov, pinch: upinch };
      }
    } else {
      const r = ekvCore(m.p, vgs, vds, vbs, w, l);
      const iF = r.if, iR = r.ir;
      for (let k = 0; k < N; k++) {
        const x = k / (N - 1), i = iF * (1 - x) + iR * x;   // convex combination: no cancellation when iR << iF (saturation)
        const vch = r.vp - VT * ekvFinv(i);            // bulk-referenced
        u.push(x); V.push(b + vch); q.push(qOfI(i));
      }
      info = { region: iF < 0.1 ? 'weak' : iF > 10 ? 'strong' : 'moderate', ic: iF, vov: vgs - m.p.vtoEff };
    }
    // back to real polarity and to the drawn orientation
    const V2 = V.map((v) => pol * v);
    if (flip) { V2.reverse(); q.reverse(); }
    return { u, v: V2, q, info };
  }

  // ------------------------------------------------------------------ solvers
  /** Root of a function that INCREASES with v (the bracket is widened if needed); NaN when no sign change is found. */
  function bisect(f, lo, hi, iters) {
    iters = iters || 100;
    let flo = f(lo), fhi = f(hi), k = 0;
    while (flo > 0 && k++ < 40) { lo -= (hi - lo); flo = f(lo); }
    k = 0;
    while (fhi < 0 && k++ < 40) { hi += (hi - lo); fhi = f(hi); }
    if (!(flo <= 0 && fhi >= 0)) return NaN;   // wrong monotonic direction or no root: fail loudly instead of returning garbage
    for (let i = 0; i < iters; i++) { const mid = 0.5 * (lo + hi); if (f(mid) > 0) hi = mid; else lo = mid; if (hi - lo < 1e-13 * (1 + Math.abs(mid))) break; }
    return 0.5 * (lo + hi);
  }

  /** Newton iteration on a scalar KCL f(v) = 0; returns the whole trace (used by lesson 2). */
  function newton1(fg, v0, maxit, vlimit) {
    maxit = maxit || 30; vlimit = vlimit || 1e9;
    const trace = []; let v = v0;
    for (let k = 0; k < maxit; k++) {
      const { f, g } = fg(v);
      let vn = v - f / g; const step = clamp(vn - v, -vlimit, vlimit); vn = v + step;
      trace.push({ k: k + 1, v0: v, f, g, v1: vn });
      if (Math.abs(vn - v) < 1e-12) { v = vn; break; }
      v = vn;
    }
    return { v, trace };
  }

  // ------------------------------------------------------------------ waveforms and single-node transient
  function pulse(p) { // p = {v1, v2, td, tr, tf, pw, per}
    const value = (t) => {
      if (t < p.td) return p.v1;
      t -= p.td; if (p.per > 0) t %= p.per;
      if (t < p.tr) return p.v1 + (p.v2 - p.v1) * t / p.tr;
      t -= p.tr; if (t < p.pw) return p.v2;
      t -= p.pw; if (t < p.tf) return p.v2 + (p.v1 - p.v2) * t / p.tf;
      return p.v1;
    };
    const breakpoints = (tstop) => {
      const corners = [0, p.tr, p.tr + p.pw, p.tr + p.pw + p.tf], pts = [];
      for (let k = 0; ; k++) {
        const base = p.td + k * p.per; if (base > tstop) break;
        for (const c of corners) if (base + c > 0 && base + c <= tstop) pts.push(base + c);
        if (p.per <= 0) break;
      }
      return pts;
    };
    return { value, breakpoints };
  }

  /**
   * Transient of ONE unknown node. spec.dev(v, t) -> {i, g}: current leaving the node into resistors/transistors
   * and its derivative; spec.caps = [{c, other: (t) => voltage of the other plate}] (other = 0 for ground).
   * Same time grid as minispice (output grid tstep, extra points at source corners); backward Euler or trapezoidal.
   */
  function transient1(spec) {
    const trap = spec.method === 'trap';
    const lo = spec.vmin !== undefined ? spec.vmin : -1, hi = spec.vmax !== undefined ? spec.vmax : 5;
    let t = 0;
    let v = bisect((x) => spec.dev(x, 0).i, lo, hi);                  // DC operating point (capacitors open)
    const caps = spec.caps.map((c) => ({ c: c.c, other: c.other, vc: v - c.other(0), i: 0 }));
    const out = { t: [0], v: [v], iDev: [spec.dev(v, 0).i], iCap: [spec.caps.map(() => 0)] };
    const corners = (spec.breakpoints || []).slice().sort((a, b) => a - b);
    const n = Math.round(spec.tstop / spec.tstep), eps = 1e-6 * spec.tstep;
    const advance = (t0, t1) => {
      const h = t1 - t0, a = (trap ? 2 : 1) / h;
      const f = (x) => {
        let s = spec.dev(x, t1).i;
        for (const c of caps) s += a * c.c * ((x - c.other(t1)) - c.vc) - (trap ? c.i : 0);
        return s;
      };
      v = bisect(f, lo, hi);
      for (const c of caps) { const vc = v - c.other(t1); c.i = a * c.c * (vc - c.vc) - (trap ? c.i : 0); c.vc = vc; }
    };
    for (let k = 1; k <= n; k++) {
      const t0 = (k - 1) * spec.tstep, t1 = k * spec.tstep;
      const inside = corners.filter((x) => x > t0 + eps && x < t1 - eps);
      const pts = [t0].concat(inside, [t1]);
      for (let j = 0; j + 1 < pts.length; j++) advance(pts[j], pts[j + 1]);
      out.t.push(t1); out.v.push(v); out.iDev.push(spec.dev(v, t1).i); out.iCap.push(caps.map((c) => c.i));
    }
    return out;
  }

  // ------------------------------------------------------------------ formatting
  function si(x, unit, digits) {
    digits = digits || 3; unit = unit || '';
    if (!isFinite(x)) return '—';
    if (x === 0) return '0 ' + unit;
    const pre = [[1e-15, 'f'], [1e-12, 'p'], [1e-9, 'n'], [1e-6, 'µ'], [1e-3, 'm'], [1, ''], [1e3, 'k'], [1e6, 'M']];
    const a = Math.abs(x); let best = pre[0];
    for (const p of pre) if (a >= p[0] * 0.9995) best = p;
    return (x / best[0]).toPrecision(digits).replace(/\.?0+$/, (m) => (m.includes('.') ? '' : m)) + ' ' + best[1] + unit;
  }

  const API = { VT, clamp, makeModel, evaluate, charges, chargeJac, channelProfile, bisect, newton1, pulse, transient1, si, ekvF, ekvFinv, qOfI, level1Core, ekvCore };
  if (typeof module !== 'undefined' && module.exports) module.exports = API; else G.MS = API;
})(typeof window !== 'undefined' ? window : globalThis);
