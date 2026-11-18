'use strict';
// node tests/js_parity.js reference.json  ->  prints JSON with the largest deviations between the JS port and minispice
const MS = require('../textbook/js/core.js');
const ref = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const rel = (a, b, floor) => Math.abs(a - b) / Math.max(Math.abs(b), floor);
const out = {};

if (process.argv[3] === 'dram') {          // lesson 11 reference: node tests/js_parity.js dram.json dram
  let ww = 0, ws = 0, mr = 0, finite = 0;
  for (const c of ref.write) {
    const r = MS.dramSim({ mode: 'write1', vdd: 1.2, vpp: c.vpp, vth: c.vth, wlr: 1, cs: 25e-15, cbl: 150e-15, voff: 0, gmsa: 2e-3, method: 'trap', dt: 10e-12 });
    for (let k = 0; k < c.idx.length; k++) ww = Math.max(ww, Math.abs(r.sn[c.idx[k]] - c.sn[k]));
  }
  for (const c of ref.share) {
    const r = MS.dramSim({ mode: c.vcell > 0.6 ? 'read1' : 'read0', vdd: 1.2, vpp: c.vpp, vth: c.vth, wlr: 1, cs: c.cs, cbl: c.cbl, voff: 0, gmsa: 2e-3, method: 'trap', dt: 10e-12 });
    for (let k = 0; k < c.idx.length; k++) ws = Math.max(ws, Math.abs(r.bl[c.idx[k]] - c.bl[k]), Math.abs(r.sn[c.idx[k]] - c.sn[k]));
  }
  for (const c of ref.ret) {
    const r = MS.dramRetention({ vdd: 1.2, vpp: 2.0, vth: c.vth, vwl: c.vwl, data1: c.data1, vbl: c.vbl, n: 1.3, cs: 25e-15, cbl: 150e-15, voff: 0.02, ij: 0.2e-15, wlr: 1 });
    if (c.tret === null) { if (r.tret !== Infinity) mr = Infinity; }
    else { finite++; mr = Math.max(mr, Math.abs(r.tret - c.tret) / c.tret); }
    mr = Math.max(mr, Math.abs(r.vs[r.vs.length - 1] - c.v_end) / 1e3 + (r.ts.length === c.n ? 0 : 1));
  }
  out.write = { cases: ref.write.length, max_abs_dv: ww }; out.share = { cases: ref.share.length, max_abs_dv: ws }; out.ret = { cases: ref.ret.length, finite_cases: finite, max_rel_dt: mr };
  console.log(JSON.stringify(out));
  process.exit(0);
}

// 1) device models: id and conductances, charges
let worst = { id: 0, gd: 0, gg: 0, gs: 0, gb: 0, q: 0 };
for (const c of ref.models) {
  const m = MS.makeModel(c.kind, c.pol, c.params);
  const r = MS.evaluate(m, c.v[0], c.v[1], c.v[2], c.v[3], c.w, c.l);
  const scale = Math.max(Math.abs(c.out.id), Math.abs(c.out.gd), Math.abs(c.out.gg), 1e-15);
  worst.id = Math.max(worst.id, rel(r.id, c.out.id, 1e-18));
  worst.gd = Math.max(worst.gd, Math.abs(r.gd - c.out.gd) / scale);
  worst.gg = Math.max(worst.gg, Math.abs(r.gg - c.out.gg) / scale);
  worst.gs = Math.max(worst.gs, Math.abs(r.gs - c.out.gs) / scale);
  worst.gb = Math.max(worst.gb, Math.abs(r.gb - c.out.gb) / scale);
  if (c.q) {
    const q = MS.charges(m, c.v[0], c.v[1], c.v[2], c.v[3], c.w, c.l), qs = Math.max(...c.q.map(Math.abs), 1e-30);
    for (let k = 0; k < 4; k++) worst.q = Math.max(worst.q, Math.abs(q[k] - c.q[k]) / qs);
  }
}
out.models = Object.assign({ cases: ref.models.length }, worst);

// 2) DC operating points of a one-node circuit: NMOS + Rd, and the CMOS inverter
let w2 = 0;
for (const c of ref.rd) {
  const m = MS.makeModel('level1', 1, c.params);
  const f = (v) => (v - c.vdd) / c.rd + MS.evaluate(m, v, c.vg, 0, 0, c.w, c.l).id;
  w2 = Math.max(w2, Math.abs(MS.bisect(f, -1, c.vdd + 1) - c.vd));
}
out.rd = { cases: ref.rd.length, max_abs_dv: w2 };
let w3 = 0;
for (const c of ref.inv) {
  const mn = MS.makeModel('level1', 1, c.pn), mp = MS.makeModel('level1', -1, c.pp);
  for (let k = 0; k < c.vin.length; k++) {
    const f = (v) => MS.evaluate(mn, v, c.vin[k], 0, 0, c.wn, c.l).id + MS.evaluate(mp, v, c.vin[k], c.vdd, c.vdd, c.wp, c.l).id;
    w3 = Math.max(w3, Math.abs(MS.bisect(f, -1, c.vdd + 1) - c.vout[k]));
  }
}
out.inv = { cases: ref.inv.length, max_abs_dv: w3 };

// 3) transients: lesson 3 (NMOS + Rd + CL, pulse on the gate) and lesson 4 (CMOS inverter + CL)
let w4 = 0, w5 = 0;
for (const c of ref.tran_rd) {
  const m = MS.makeModel('level1', 1, c.params), pu = MS.pulse(c.pulse);
  const r = MS.transient1({
    method: c.method, tstep: c.tstep, tstop: c.tstop, breakpoints: pu.breakpoints(c.tstop),
    dev: (v, t) => { const e = MS.evaluate(m, v, pu.value(t), 0, 0, c.w, c.l); return { i: (v - c.vdd) / c.rd + e.id, g: 0 }; },
    caps: [{ c: c.cl, other: () => 0 }], vmin: -1, vmax: c.vdd + 1 });
  for (let k = 0; k < c.v.length; k++) w4 = Math.max(w4, Math.abs(r.v[c.idx[k]] - c.v[k]));
}
for (const c of ref.tran_inv) {
  const mn = MS.makeModel('level1', 1, c.pn), mp = MS.makeModel('level1', -1, c.pp), pu = MS.pulse(c.pulse);
  const r = MS.transient1({
    method: c.method, tstep: c.tstep, tstop: c.tstop, breakpoints: pu.breakpoints(c.tstop),
    dev: (v, t) => { const vi = pu.value(t); return { i: MS.evaluate(mn, v, vi, 0, 0, c.wn, c.l).id + MS.evaluate(mp, v, vi, c.vdd, c.vdd, c.wp, c.l).id, g: 0 }; },
    caps: [{ c: c.cl, other: () => 0 }], vmin: -1, vmax: c.vdd + 1 });
  for (let k = 0; k < c.v.length; k++) w5 = Math.max(w5, Math.abs(r.v[c.idx[k]] - c.v[k]));
}
out.tran_rd = { cases: ref.tran_rd.length, max_abs_dv: w4 };
out.tran_inv = { cases: ref.tran_inv.length, max_abs_dv: w5 };

// 4) channel profile sanity: V(0) = source, V(1) = drain, monotone
let bad = 0, nprof = 0;
for (const c of ref.models) {
  const m = MS.makeModel(c.kind, c.pol, c.params), P = MS.channelProfile(m, c.v[0], c.v[1], c.v[2], c.v[3], c.w, c.l, 25);
  const vs = c.v[2], vd = c.v[0]; nprof++;
  const tol = 1e-6 + 1e-3 * Math.abs(vd - vs);
  if (Math.abs(P.v[0] - vs) > tol || Math.abs(P.v[P.v.length - 1] - vd) > tol) bad++;
  const dir = Math.sign(vd - vs);
  for (let k = 1; k < P.v.length; k++) if (dir * (P.v[k] - P.v[k - 1]) < -1e-9) { bad++; break; }
}
out.profile = { cases: nprof, violations: bad };
console.log(JSON.stringify(out));
