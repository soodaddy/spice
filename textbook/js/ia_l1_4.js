'use strict';
/* ia_l1_4.js - interactive widgets of lessons 1-4 (Level 1 devices, Newton, transient, CMOS inverter). */
(function (G) {
  const { makeWidget, benchSchem, rdSchem, invSchem, fI, rows, KP } = G.IA, MS = G.MS, S3 = G.Scene3D, clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const REG = { cutoff: '차단(cutoff)', triode: '선형(triode)', saturation: '포화(saturation)', weak: '약반전', moderate: '중반전', strong: '강반전' };
  const lin = (a, b, n) => Array.from({ length: n }, (_, i) => a + (b - a) * i / (n - 1));
  const l1 = (pol, p) => MS.makeModel('level1', pol, p);
  const crossing = (t, v, lvl, rising, t0) => { for (let i = 1; i < t.length; i++) if (t[i] >= (t0 || 0) && (rising ? v[i - 1] < lvl && lvl <= v[i] : v[i - 1] > lvl && lvl >= v[i])) return t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1]); return NaN; };
  const profPlot = (p, st, title) => {
    p.begin({ xlabel: '채널 위치 (소스 → 드레인)', ylabel: '채널 전위 [V]', xlim: [0, 1], ylim: [Math.min(0, ...st.prof.v) - 0.05, Math.max(0.3, ...st.prof.v) * 1.08], title: title || '채널 전위 분포 V(x)' });
    p.line(st.prof.u, st.prof.v, { color: '#1f3b73', width: 2.4 });
    if (st.prof.info.region === 'saturation') p.vline(st.prof.info.pinch, { color: '#b03a00' }).text(st.prof.info.pinch, p.o.ylim[1] * 0.92, ' 핀치오프', { color: '#b03a00' });
    p.end();
  };
  const st3 = (st, v) => ({ v, vmin: st.vmin, vmax: st.vmax, prof: st.prof, I: st.I, qmax: st.qmax, phase: st.phase });

  // ================================================================== lesson 1
  G.IA.W.l1 = (root) => makeWidget(root, {
    note: 'Vgs, Vds, Vth, W, L, λ를 바꾸면 영역, 전류, 채널 전위 분포가 어떻게 달라지는지 봅니다.',
    controls: [
      { id: 'vgs', label: 'Vgs', min: 0, max: 2, step: 0.01, value: 1.0, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'vds', label: 'Vds', min: 0, max: 2, step: 0.01, value: 1.8, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'vth', label: 'Vth (VTO)', min: 0.2, max: 1.0, step: 0.01, value: 0.5, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'W', label: 'W', min: 0.2, max: 5, log: true, value: 1, fmt: (v) => v.toFixed(2) + ' µm' },
      { id: 'L', label: 'L', min: 0.1, max: 1, log: true, value: 0.18, fmt: (v) => v.toFixed(2) + ' µm' },
      { id: 'lam', label: 'λ', min: 0, max: 0.2, step: 0.005, value: 0.05, fmt: (v) => v.toFixed(3) + ' /V' },
      { type: 'select', id: 'plot', label: '그래프', value: 'vds', options: [['vds', 'Id–Vds (출력 특성)'], ['vgs', 'Id–Vgs (전달 특성)']] },
    ],
    compute: (v) => {
      const m = l1(1, { vto: v.vth, kp: KP, lambda: v.lam }), w = v.W * 1e-6, l = v.L * 1e-6, vv = { s: 0, d: v.vds, g: v.vgs, b: 0 };
      const ev = MS.evaluate(m, vv.d, vv.g, vv.s, vv.b, w, l), prof = MS.channelProfile(m, vv.d, vv.g, vv.s, vv.b, w, l, 33);
      return { m, w, l, v: vv, ev, prof, beta: KP * w / l, vov: v.vgs - v.vth, I: ev.id, qmax: 1.2, region: prof.info.region, vgs: v.vgs, vds: v.vds, id: ev.id };
    },
    vrange: () => [0, 2],
    readout: (s, v) => {
      const beta = s.beta, vov = s.vov; let hand, f;
      if (vov <= 0) { hand = 0; f = 'Id = 0'; } else if (v.vds < vov) { hand = beta * (vov - v.vds / 2) * v.vds * (1 + v.lam * v.vds); f = 'β(Vov − Vds/2)·Vds·(1+λVds)'; } else { hand = 0.5 * beta * vov * vov * (1 + v.lam * v.vds); f = '½β·Vov²·(1+λVds)'; }
      return rows([['β = KP·W/L', (beta * 1e3).toFixed(3) + ' mA/V²'], ['Vov = Vgs − Vth', vov.toFixed(3) + ' V'], ['동작 영역', REG[s.region], vov > 0 ? `경계: Vds = Vov = ${vov.toFixed(2)} V` : 'Vgs ≤ Vth'],
        ['Id (모델)', fI(s.ev.id)], ['Id (손 계산 식)', fI(hand), f], ['gm = ∂Id/∂Vg', MS.si(s.ev.gg, 'S')], ['gds = ∂Id/∂Vd', MS.si(s.ev.gd, 'S')],
        ['SPICE의 i(Vds)', fI(-s.ev.id), '전원 전류는 + 단자로 들어가는 방향이 양수']]);
    },
    plots: [
      { h: 230, draw: (p, s, v) => {
        if (v.plot === 'vds') {
          const xs = lin(0, 2, 161), curves = [0.6, 0.9, 1.2, 1.5, 1.8].map((g) => xs.map((x) => MS.evaluate(s.m, x, g, 0, 0, s.w, s.l).id)), cur = xs.map((x) => MS.evaluate(s.m, x, v.vgs, 0, 0, s.w, s.l).id);
          const ymax = Math.max(...curves.flat(), ...cur, 1e-6) * 1.1;
          p.begin({ xlabel: 'Vds [V]', ylabel: 'Id [mA]', xlim: [0, 2], ylim: [0, ymax * 1e3], title: 'Id–Vds  (회색: Vgs = 0.6 … 1.8 V)' });
          curves.forEach((c) => p.line(xs, c.map((y) => y * 1e3), { color: '#b9c6dc', width: 1.4 }));
          p.line(xs, cur.map((y) => y * 1e3), { color: '#1f3b73', width: 2.6 });
          const bx = lin(v.vth, 2, 80); p.line(bx, bx.map((g) => MS.evaluate(s.m, g - v.vth, g, 0, 0, s.w, s.l).id * 1e3), { color: '#b03a00', dash: [5, 4], width: 1.4 });
          p.text(1.2, ymax * 1e3 * 0.04, 'Vds = Vov (점선)', { color: '#b03a00' }).marker(v.vds, s.ev.id * 1e3, { label: '동작점' }).end();
        } else {
          const xs = lin(0, 2, 161), ys = xs.map((g) => MS.evaluate(s.m, v.vds, g, 0, 0, s.w, s.l).id * 1e3);
          p.begin({ xlabel: 'Vgs [V]', ylabel: 'Id [mA]', xlim: [0, 2], ylim: [0, Math.max(...ys, 1e-3) * 1.1], title: `Id–Vgs  (Vds = ${v.vds.toFixed(2)} V)` });
          p.line(xs, ys, { color: '#1f3b73', width: 2.6 }).vline(v.vth, { color: '#8a91a0' }).marker(v.vgs, s.ev.id * 1e3, { label: '동작점' }).end();
        }
      } },
      { h: 230, draw: (p, s, v) => {
        const xs = lin(0, 2, 161), ys = xs.map((g) => Math.sqrt(Math.max(0, MS.evaluate(s.m, v.vds, g, 0, 0, s.w, s.l).id * 1e3)));
        p.begin({ xlabel: 'Vgs [V]', ylabel: '√Id  [√mA]', xlim: [0, 2], ylim: [0, Math.max(...ys, 1e-3) * 1.1], title: '√Id–Vgs: 포화에서 직선, x절편 = Vth' });
        p.line(xs, ys, { color: '#1f3b73', width: 2.4 }).vline(v.vth, { color: '#b03a00' }).text(v.vth + 0.03, p.o.ylim[1] * 0.06, 'Vth', { color: '#b03a00' }).marker(v.vgs, Math.sqrt(Math.max(0, s.ev.id * 1e3)), {}).end();
      } },
      { h: 210, draw: (p, s) => profPlot(p, s) },
    ],
    build3d: (sc, s) => S3.planar(sc, st3(s, s.v)),
    schem: (svg) => { const b = benchSchem(svg); return { s: b.s, update: (s) => b.update({ vgs: s.vgs, vds: s.vds, id: s.id, vmin: s.vmin, vmax: s.vmax }) }; },
    foot: '채널 위에 표시된 전위는 Level 1의 전하 시트 식(Id·y = µCox·W·(Vov·V − V²/2))에서 구한 값이고, 드레인 쪽 핀치오프 구간은 선형으로 이었습니다. 소스·드레인·게이트는 단자 전압 그대로입니다.',
  });

  // ================================================================== lesson 2
  G.IA.W.l2 = (root) => makeWidget(root, {
    note: 'Newton 반복을 한 단계씩 따라가 봅니다. k를 바꾸면 그 시점의 Vd 추측값에서 회로의 전압·전류가 어떻게 보이는지 확인할 수 있습니다.',
    controls: [
      { id: 'vdd', label: 'Vdd', min: 0.8, max: 3, step: 0.05, value: 1.8, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'vg', label: 'Vg', min: 0, max: 2.5, step: 0.01, value: 1.4, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'rd', label: 'Rd', min: 1e3, max: 50e3, log: true, value: 5e3, fmt: (v) => MS.si(v, 'Ω') },
      { id: 'vth', label: 'Vth', min: 0.2, max: 1.0, step: 0.01, value: 0.5, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'W', label: 'W', min: 0.2, max: 5, log: true, value: 1, fmt: (v) => v.toFixed(2) + ' µm' },
      { id: 'vd0', label: '초기 추측 Vd0', min: 0, max: 3, step: 0.01, value: 0, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'k', label: 'Newton 반복 횟수 k', min: 0, max: 8, step: 1, value: 8, fmt: (v) => (v === 0 ? '0 (초기 추측)' : v + '회') },
      { type: 'check', id: 'limit', label: '스텝 제한 (한 번에 1 V까지만, 실제 솔버처럼)', value: false },
    ],
    compute: (v) => {
      const m = l1(1, { vto: v.vth, kp: KP, lambda: 0.05 }), w = v.W * 1e-6, l = 0.18e-6;
      const ev = (x) => MS.evaluate(m, x, v.vg, 0, 0, w, l), fg = (x) => { const e = ev(x); return { f: (x - v.vdd) / v.rd + e.id, g: 1 / v.rd + e.gd }; };
      const tr = MS.newton1(fg, v.vd0, 8, v.limit ? 1 : 1e9), star = MS.bisect((x) => fg(x).f, -1, v.vdd + 1);
      const k = Math.min(v.k, tr.trace.length), vs = k === 0 ? v.vd0 : tr.trace[k - 1].v1, e = ev(vs), vv = { s: 0, d: vs, g: v.vg, b: 0 };
      const prof = MS.channelProfile(m, vv.d, vv.g, vv.s, vv.b, w, l, 33), iR = (v.vdd - vs) / v.rd;
      return { m, w, l, ev, fg, trace: tr.trace, star, k, vs, v: vv, prof, I: e.id, qmax: 1.2, iR, iD: e.id, vd: vs, vdd: v.vdd, vg: v.vg, kcl: iR - e.id, estar: ev(star),
        kclText: `KCL 오차 iR − iD = ${fI(iR - e.id)}` };
    },
    vrange: (s) => [0, Math.max(s.vdd, s.vg, 1)],
    readout: (s, v) => {
      const t = s.trace.map((r, i) => `<tr class="${i + 1 === s.k ? 'on' : ''}"><td>${r.k}</td><td>${r.v0.toFixed(4)}</td><td>${MS.si(s.ev(r.v0).id, 'A', 3)}</td><td>${MS.si(s.ev(r.v0).gd, 'S', 3)}</td><td>${r.v1.toFixed(5)}</td></tr>`).join('');
      return rows([['표시 중인 Vd', s.vs.toFixed(4) + ' V', s.k === 0 ? '초기 추측' : `${s.k}번째 반복 후`], ['저항 전류 iR = (Vdd − Vd)/Rd', fI(s.iR)], ['트랜지스터 전류 iD', fI(s.iD)], ['KCL 오차 iR − iD', fI(s.kcl), '0이 되면 해'],
        ['수렴한 해 Vd*', s.star.toFixed(6) + ' V', `Id* = ${fI(s.estar.id)}`]]) +
        `<table class="ia-tab"><thead><tr><th>k</th><th>Vd0 [V]</th><th>Id0</th><th>gds</th><th>새 Vd [V]</th></tr></thead><tbody>${t}</tbody></table>` + (s.trace.length >= 8 && Math.abs(s.trace[7].v1 - s.star) > 1e-3 ? '<p class="ia-warn">8회 안에 수렴하지 못했습니다. 포화 영역에서 시작하면 접선이 거의 수평이라 해에서 멀리 튈 수 있습니다. “스텝 제한”을 켜 보세요.</p>' : '');
    },
    plots: [
      { h: 250, draw: (p, s, v) => {
        const xmax = v.vdd * 1.08, xs = lin(0, xmax, 200), id = xs.map((x) => s.ev(x).id * 1e3), ymax = Math.max(v.vdd / v.rd * 1e3, ...id) * 1.12;
        p.begin({ xlabel: 'Vd [V]', ylabel: '전류 [mA]', xlim: [0, xmax], ylim: [0, ymax], title: '트랜지스터 곡선 ∩ 부하선 = 해 (접선 = Newton의 한 스텝)' });
        p.line(xs, id, { color: '#1f3b73', width: 2.6 }).line(xs, xs.map((x) => (v.vdd - x) / v.rd * 1e3), { color: '#777', width: 2.2 });
        const cols = ['#d95f02', '#7570b3', '#1b9e77', '#e6ab02', '#a6761d', '#666', '#e7298a', '#66a61e'];
        s.trace.slice(0, s.k).forEach((r, i) => { const e = s.ev(r.v0); p.line([0, xmax], [0, xmax].map((x) => (e.id + e.gd * (x - r.v0)) * 1e3), { color: cols[i % 8], dash: [5, 3], width: 1.5 }); p.marker(r.v0, e.id * 1e3, { color: cols[i % 8], r: 4 }); });
        p.marker(s.vs, s.iD * 1e3, { label: s.k ? `k=${s.k}` : 'Vd0', color: '#d73027' }).marker(s.star, s.estar.id * 1e3, { color: '#111', r: 6, label: '해', dy: 16 }).end();
      } },
      { h: 230, draw: (p, s) => {
        const pts = [{ v: s.trace.length ? s.trace[0].v0 : 0 }].concat(s.trace.map((r) => ({ v: r.v1 }))), err = pts.map((q) => Math.abs(s.fg(q.v).f)), pos = err.filter((x) => x > 0);
        const lo = Math.pow(10, Math.floor(Math.log10(Math.min(...pos, 1e-9)))), hi = Math.pow(10, Math.ceil(Math.log10(Math.max(...err, 1e-9)))) * 1.0;
        p.begin({ xlabel: 'Newton 반복 횟수 k', ylabel: '|KCL 오차| [A]', xlim: [-0.2, Math.max(2, pts.length - 1) + 0.2], ylim: [lo, Math.max(hi, lo * 100)], ylog: true, title: '반복할수록 오차가 급격히 줄어든다' });
        p.line(pts.map((_, i) => i), err, { color: '#1f3b73', width: 2 });
        pts.forEach((q, i) => p.marker(i, err[i], { color: i === s.k ? '#d73027' : '#1f3b73', r: i === s.k ? 6 : 3.5 })); p.end();
      } },
      { h: 210, draw: (p, s) => profPlot(p, s) },
    ],
    build3d: (sc, s) => S3.planar(sc, st3(s, s.v)),
    schem: (svg) => { const r = rdSchem(svg); return { s: r.s, update: r.update }; },
    foot: '회로도에는 “표시 중인 Vd”에서 계산한 두 전류(iR과 iD)가 따로 나옵니다. 해에서만 같아지고, k를 줄이면 KCL 오차가 보입니다.',
  });

  // ================================================================== lesson 3
  const PULSE3 = (vgh, tr) => ({ v1: 0, v2: vgh, td: 1e-9, tr, tf: tr, pw: 3e-9, per: 8e-9 });
  G.IA.W.l3 = (root) => makeWidget(root, {
    note: '커패시터가 있는 회로를 시간 순으로 풉니다. 시간 슬라이더를 움직이거나 재생하면 그 순간의 전압 분포와 전류(iR, iD, iC)를 볼 수 있습니다.',
    controls: [
      { id: 'vgh', label: '게이트 High 전압', min: 0.8, max: 2, step: 0.05, value: 1.4, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'rd', label: 'Rd', min: 1e3, max: 20e3, log: true, value: 5e3, fmt: (v) => MS.si(v, 'Ω') },
      { id: 'cl', label: 'CL', min: 10e-15, max: 500e-15, log: true, value: 100e-15, fmt: (v) => MS.si(v, 'F') },
      { id: 'tr', label: '게이트 상승·하강 시간', min: 20, max: 500, step: 10, value: 100, fmt: (v) => v + ' ps' },
      { type: 'select', id: 'method', label: '적분 방법', value: 'be', options: [['be', 'Backward Euler (레슨 3)'], ['trap', 'Trapezoidal']] },
      { id: 'h', label: '시간 스텝 h', min: 5, max: 100, step: 5, value: 20, fmt: (v) => v + ' ps' },
      { id: 't', label: '시간 t', min: 0, max: 8, step: 0.02, value: 1.2, fmt: (v) => v.toFixed(2) + ' ns' },
      { type: 'play', id: 'play' },
    ],
    compute: (v, prev) => {
      const key = [v.vgh, v.rd, v.cl, v.tr, v.method, v.h].join('|'), m = l1(1, { vto: 0.5, kp: KP, lambda: 0.05 }), w = 1e-6, l = 0.18e-6, vdd = 1.8, pu = MS.pulse(PULSE3(v.vgh, v.tr * 1e-12));
      let c = prev && prev.key === key ? prev.c : null;
      if (!c) {
        const r = MS.transient1({ method: v.method, tstep: v.h * 1e-12, tstop: 8e-9, breakpoints: pu.breakpoints(8e-9), vmin: -1, vmax: vdd + 1,
          dev: (x, t) => ({ i: (x - vdd) / v.rd + MS.evaluate(m, x, pu.value(t), 0, 0, w, l).id, g: 0 }), caps: [{ c: v.cl, other: () => 0 }] });
        const vg = r.t.map((t) => pu.value(t)), iD = r.v.map((x, i) => MS.evaluate(m, x, vg[i], 0, 0, w, l).id), iR = r.v.map((x) => (vdd - x) / v.rd), iC = iR.map((a, i) => a - iD[i]);
        const vlow = r.v[Math.round(4e-9 / (v.h * 1e-12))], sw = vdd - vlow, tt = r.t;
        c = { r, vg, iD, iR, iC, vlow, fall: crossing(tt, r.v, vlow + 0.1 * sw, false, 1e-9) - crossing(tt, r.v, vlow + 0.9 * sw, false, 1e-9), rise: crossing(tt, r.v, vlow + 0.9 * sw, true, 4.1e-9) - crossing(tt, r.v, vlow + 0.1 * sw, true, 4.1e-9) };
      }
      const i = clamp(Math.round(v.t * 1e-9 / (v.h * 1e-12)), 0, c.r.t.length - 1), vd = c.r.v[i], vgt = c.vg[i], vv = { s: 0, d: vd, g: vgt, b: 0 };
      const prof = MS.channelProfile(m, vv.d, vv.g, vv.s, vv.b, w, l, 33);
      return { key, c, m, w, l, i, vd, vg: vgt, vdd, v: vv, prof, I: c.iD[i], iR: c.iR[i], iD: c.iD[i], iC: c.iC[i], qmax: 1.2, t: c.r.t[i] };
    },
    onTick: (dt, ctl) => { let t = ctl.t.get() + dt * 1.0; if (t > 8) t = 0; ctl.t.set(t); return true; },
    vrange: () => [0, 2],
    readout: (s, v) => rows([['시간', (s.t * 1e9).toFixed(2) + ' ns'], ['Vg(t)', s.vg.toFixed(3) + ' V'], ['Vd(t)', s.vd.toFixed(4) + ' V'], ['NMOS 영역', REG[s.prof.info.region]],
      ['저항 전류 iR', fI(s.iR)], ['트랜지스터 전류 iD', fI(s.iD)], ['커패시터 전류 iC', fI(s.iC), 'iC = iR − iD (음수 = 방전)'], ['낮은 쪽 전압', s.c.vlow.toFixed(4) + ' V'],
      ['내려갈 때 90→10 %', MS.si(s.c.fall, 's')], ['올라갈 때 10→90 %', MS.si(s.c.rise, 's'), `RC 이론 2.2·Rd·CL = ${MS.si(2.2 * v.rd * v.cl, 's')}`]]),
    plots: [
      { h: 230, draw: (p, s) => { const t = s.c.r.t.map((x) => x * 1e9); p.begin({ xlabel: 't [ns]', ylabel: '전압 [V]', xlim: [0, 8], ylim: [-0.05, 2.1], title: '게이트 전압과 출력 전압' });
        p.line(t, s.c.vg, { color: '#8a91a0', dash: [5, 3], width: 1.6 }).line(t, s.c.r.v, { color: '#1f3b73', width: 2.4 }).vline(s.t * 1e9, { color: '#d73027' }).marker(s.t * 1e9, s.vd, {}).legend([{ color: '#8a91a0', dash: [5, 3], label: 'Vg' }, { color: '#1f3b73', label: 'Vd' }], 'right').end(); } },
      { h: 230, draw: (p, s) => { const t = s.c.r.t.map((x) => x * 1e9), a = [...s.c.iR, ...s.c.iD, ...s.c.iC].map((x) => x * 1e3); p.begin({ xlabel: 't [ns]', ylabel: '전류 [mA]', xlim: [0, 8], ylim: [Math.min(...a) * 1.1, Math.max(...a) * 1.1], title: 'iR = iD + iC (KCL)' });
        p.line(t, s.c.iR.map((x) => x * 1e3), { color: '#1b9e77', width: 1.9 }).line(t, s.c.iD.map((x) => x * 1e3), { color: '#d95f02', width: 1.9 }).line(t, s.c.iC.map((x) => x * 1e3), { color: '#7570b3', width: 1.9 }).vline(s.t * 1e9, { color: '#d73027' })
          .legend([{ color: '#1b9e77', label: 'iR (Rd)' }, { color: '#d95f02', label: 'iD (NMOS)' }, { color: '#7570b3', label: 'iC (CL)' }], 'right').end(); } },
      { h: 200, draw: (p, s) => profPlot(p, s) },
    ],
    build3d: (sc, s) => S3.planar(sc, st3(s, s.v)),
    schem: (svg) => { const r = rdSchem(svg, { cap: true }); return { s: r.s, update: r.update }; },
    foot: '시간 t의 전압·전류는 위 시뮬레이션 결과(레슨 3과 같은 BE/trap 알고리즘, minispice와 같은 시간 격자)에서 읽습니다.',
  });

  // ================================================================== lesson 4
  const PULSE4 = { v1: 0, v2: 1.8, td: 0.2e-9, tr: 0.1e-9, tf: 0.1e-9, pw: 0.8e-9, per: 2e-9 };
  G.IA.W.l4 = (root) => makeWidget(root, {
    note: 'NMOS와 PMOS가 함께 만드는 출력을 봅니다. DC 모드에서는 Vin을, 과도 모드에서는 시간을 움직이세요. 스위칭 순간에만 전원 전류가 흐르는 것을 볼 수 있습니다.',
    controls: [
      { id: 'vdd', label: 'Vdd', min: 0.8, max: 3, step: 0.05, value: 1.8, fmt: (v) => v.toFixed(2) + ' V' },
      { type: 'select', id: 'mode', label: '모드', value: 'dc', options: [['dc', 'DC (Vin 스윕)'], ['tran', '과도 (시간)']] },
      { id: 'vin', label: 'Vin (DC)', min: 0, max: 3, step: 0.005, value: 0.9, fmt: (v) => v.toFixed(3) + ' V' },
      { id: 't', label: '시간 t (과도)', min: 0, max: 4, step: 0.01, value: 0.28, fmt: (v) => v.toFixed(2) + ' ns' },
      { type: 'play', id: 'play' },
      { id: 'ratio', label: 'Wp / Wn', min: 0.5, max: 6, step: 0.1, value: 3, fmt: (v) => v.toFixed(1) },
      { id: 'cl', label: 'CL', min: 5e-15, max: 200e-15, log: true, value: 20e-15, fmt: (v) => MS.si(v, 'F') },
      { id: 'vtn', label: 'Vtn', min: 0.3, max: 0.8, step: 0.01, value: 0.5, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'vtp', label: '|Vtp|', min: 0.3, max: 0.8, step: 0.01, value: 0.5, fmt: (v) => v.toFixed(2) + ' V' },
    ],
    compute: (v, prev) => {
      const mn = l1(1, { vto: v.vtn, kp: 300e-6, lambda: 0.05 }), mp = l1(-1, { vto: -v.vtp, kp: 100e-6, lambda: 0.05 }), vdd = v.vdd, wn = 1e-6, wp = v.ratio * 1e-6, l = 0.18e-6;
      const dcf = (vi) => (x) => MS.evaluate(mn, x, vi, 0, 0, wn, l).id + MS.evaluate(mp, x, vi, vdd, vdd, wp, l).id, solve = (vi) => MS.bisect(dcf(vi), -0.5, vdd + 0.5);
      const vins = lin(0, vdd, 181), vouts = vins.map(solve), isd = vins.map((vi, i) => -MS.evaluate(mp, vouts[i], vi, vdd, vdd, wp, l).id);
      let vm = NaN; for (let i = 1; i < vins.length; i++) if ((vouts[i - 1] - vins[i - 1]) * (vouts[i] - vins[i]) <= 0) { const a = vouts[i - 1] - vins[i - 1], b = vouts[i] - vins[i]; vm = vins[i - 1] + (vins[i] - vins[i - 1]) * a / (a - b); break; }
      // the steepest part of the VTC is narrower than the plot grid: differentiate at Vm with a tiny step
      const dvm = 2e-4, gainMax = isFinite(vm) ? Math.abs((solve(vm + dvm) - solve(vm - dvm)) / (2 * dvm)) : 0;
      const gmh = isFinite(vm) ? (() => { const a = MS.evaluate(mn, vm, vm, 0, 0, wn, l), b = MS.evaluate(mp, vm, vm, vdd, vdd, wp, l); return (a.gg + Math.abs(b.gg)) / (a.gd + b.gd); })() : 0;
      let tr = prev && prev.tkey === [v.vdd, v.ratio, v.cl, v.vtn, v.vtp].join('|') ? prev.tr : null; const tkey = [v.vdd, v.ratio, v.cl, v.vtn, v.vtp].join('|');
      const pu = MS.pulse(Object.assign({}, PULSE4, { v2: vdd }));
      if (!tr) {
        const r = MS.transient1({ method: 'trap', tstep: 5e-12, tstop: 4e-9, breakpoints: pu.breakpoints(4e-9), vmin: -1, vmax: vdd + 1,
          dev: (x, t) => ({ i: MS.evaluate(mn, x, pu.value(t), 0, 0, wn, l).id + MS.evaluate(mp, x, pu.value(t), vdd, vdd, wp, l).id, g: 0 }), caps: [{ c: v.cl, other: () => 0 }] });
        const vin = r.t.map((t) => pu.value(t)), ip = r.v.map((x, i) => -MS.evaluate(mp, x, vin[i], vdd, vdd, wp, l).id), inn = r.v.map((x, i) => MS.evaluate(mn, x, vin[i], 0, 0, wn, l).id);
        tr = { r, vin, ip, inn, tphl: crossing(r.t, r.v, vdd / 2, false, 0) - crossing(r.t, vin, vdd / 2, true, 0), tplh: crossing(r.t, r.v, vdd / 2, true, 0.9e-9) - crossing(r.t, vin, vdd / 2, false, 0.9e-9) };
      }
      let vin, vout, ip, in_, ic = 0, tshow = 0;
      if (v.mode === 'dc') { vin = Math.min(v.vin, vdd); vout = solve(vin); ip = -MS.evaluate(mp, vout, vin, vdd, vdd, wp, l).id; in_ = MS.evaluate(mn, vout, vin, 0, 0, wn, l).id; }
      else { const i = clamp(Math.round(v.t * 1e-9 / 5e-12), 0, tr.r.t.length - 1); vin = tr.vin[i]; vout = tr.r.v[i]; ip = tr.ip[i]; in_ = tr.inn[i]; ic = ip - in_; tshow = tr.r.t[i]; }
      const dn = { s: 0, d: vout, g: vin, b: 0 }, dp = { s: vdd, d: vout, g: vin, b: vdd };
      const pn = MS.channelProfile(mn, dn.d, dn.g, dn.s, dn.b, wn, l, 33), pp = MS.channelProfile(mp, dp.d, dp.g, dp.s, dp.b, wp, l, 33);
      const gain = (() => { const e = (d) => (solve(Math.min(vdd, vin + d)) - solve(Math.max(0, vin - d))) / (Math.min(vdd, vin + d) - Math.max(0, vin - d)); return e(0.002); })();
      return { mn, mp, vdd, wn, wp, l, vins, vouts, isd, vm, gainMax, gainHand: gmh, tr, tkey, mode: v.mode, vin, vout, ip, in_, ic, tshow, dn, dp, pn, pp, gain, solve,
        n: { v: dn, prof: pn, I: in_, qmax: 1.2 }, p: { v: dp, prof: pp, I: -ip, qmax: 1.2 }, I: in_ };
    },
    onTick: (dt, ctl, v) => { if (v.mode !== 'tran') return false; let t = ctl.t.get() + dt * 0.5; if (t > 4) t = 0; ctl.t.set(t); return true; },
    vrange: (s) => [0, s.vdd],
    readout: (s, v) => {
      const bn = 300e-6 * s.wn / s.l, bp = 100e-6 * s.wp / s.l, r = Math.sqrt(bn / bp), vmh = (s.vdd - v.vtp + r * v.vtn) / (1 + r);
      let tr = ''; if (s.mode === 'tran') tr = rows([['tpHL / tpLH', `${MS.si(s.tr.tphl, 's')} / ${MS.si(s.tr.tplh, 's')}`, '입력 50 % → 출력 50 %'], ['CL 전류 iC', fI(s.ic)]]);
      return rows([['Vin → Vout', `${s.vin.toFixed(3)} → ${s.vout.toFixed(4)} V`, s.mode === 'tran' ? `t = ${(s.tshow * 1e9).toFixed(2)} ns` : 'DC'], ['NMOS 영역 / 전류', `${REG[s.pn.info.region]} / ${fI(s.in_)}`], ['PMOS 영역 / 전류', `${REG[s.pp.info.region]} / ${fI(s.ip)}`],
        ['스위칭 문턱 Vm', s.vm.toFixed(4) + ' V', `손 계산(λ 무시) ${vmh.toFixed(4)} V`], ['Vm에서의 이득 |dVout/dVin|', s.gainMax.toFixed(1), `손 계산 (gmn+gmp)/(gdsn+gdsp) = ${s.gainHand.toFixed(1)}`], ['현재 점의 이득', s.gain.toFixed(1)]]) + tr;
    },
    plots: [
      { h: 240, draw: (p, s, v) => {
        if (s.mode === 'dc') { p.begin({ xlabel: 'Vin [V]', ylabel: 'Vout [V]', xlim: [0, s.vdd], ylim: [0, s.vdd * 1.05], title: '전압 전달 곡선 (VTC)' });
          p.line([0, s.vdd], [0, s.vdd], { color: '#c3c9d4', dash: [3, 3], width: 1 }).line(s.vins, s.vouts, { color: '#1f3b73', width: 2.6 }).marker(s.vm, s.vm, { color: '#1b9e77', r: 4, label: 'Vm', dy: 16 }).marker(s.vin, s.vout, { label: '동작점' }).end(); }
        else { const t = s.tr.r.t.map((x) => x * 1e9); p.begin({ xlabel: 't [ns]', ylabel: '전압 [V]', xlim: [0, 4], ylim: [-0.05, s.vdd * 1.08], title: '입력과 출력' });
          p.line(t, s.tr.vin, { color: '#8a91a0', dash: [5, 3], width: 1.6 }).line(t, s.tr.r.v, { color: '#1f3b73', width: 2.4 }).vline(s.tshow * 1e9, { color: '#d73027' }).marker(s.tshow * 1e9, s.vout, {}).legend([{ color: '#8a91a0', dash: [5, 3], label: 'Vin' }, { color: '#1f3b73', label: 'Vout' }], 'right').end(); } } },
      { h: 240, draw: (p, s) => {
        if (s.mode === 'dc') { p.begin({ xlabel: 'Vin [V]', ylabel: '전원 전류 [A]', xlim: [0, s.vdd], ylim: [1e-13, 1e-2], ylog: true, title: '전원 전류 (로그): 한쪽이 꺼지면 거의 0' });
          p.line(s.vins, s.isd.map((x) => Math.max(x, 1e-16)), { color: '#d95f02', width: 2.4 }).marker(s.vin, Math.max(s.ip, 1e-16), {}).end(); }
        else { const t = s.tr.r.t.map((x) => x * 1e9), a = s.tr.ip.map((x) => x * 1e3); p.begin({ xlabel: 't [ns]', ylabel: '전원 전류 [mA]', xlim: [0, 4], ylim: [Math.min(0, ...a) * 1.1, Math.max(...a, 1e-6) * 1.1], title: '전원 전류: 스위칭 순간에만' });
          p.line(t, a, { color: '#d95f02', width: 2 }).vline(s.tshow * 1e9, { color: '#d73027' }).marker(s.tshow * 1e9, s.ip * 1e3, {}).end(); } } },
      { h: 210, draw: (p, s) => { const a = s.pn.v, b = s.pp.v; p.begin({ xlabel: '채널 위치 (소스 → 드레인)', ylabel: '채널 전위 [V]', xlim: [0, 1], ylim: [-0.05, s.vdd * 1.05], title: '채널 전위: NMOS(파랑), PMOS(주황)' });
        p.line(s.pn.u, a, { color: '#1f3b73', width: 2.4 }).line(s.pp.u, b, { color: '#d95f02', width: 2.4 }).end(); } },
    ],
    build3d: (sc, s) => S3.cmos(sc, { n: Object.assign({ vmin: s.vmin, vmax: s.vmax, phase: s.phase }, s.n), p: Object.assign({ vmin: s.vmin, vmax: s.vmax, phase: s.phase }, s.p) }),
    scene: { yaw: -0.8, pitch: 0.6, height: 320 },
    cap3d: '3D 구조(NMOS는 p 기판, PMOS는 n-well): 색 = 전위, 점 = 전류. PMOS는 소스(Vdd)에서 드레인으로 흐릅니다.',
    schem: (svg) => { const r = invSchem(svg); return { s: r.s, update: (s) => r.update({ vdd: s.vdd, vin: s.vin, vout: s.vout, ip: s.ip, in_: s.in_, ic: s.mode === 'tran' ? s.ic : undefined, vmin: s.vmin, vmax: s.vmax }) }; },
  });
})(typeof window !== 'undefined' ? window : globalThis);
