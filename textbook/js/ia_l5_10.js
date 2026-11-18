'use strict';
/* ia_l5_10.js - interactive widgets of lessons 5, 6, 9, 10 (EKV model, channel charge, FinFET, nanosheet GAA). */
(function (G) {
  const { makeWidget, benchSchem, fI, rows, KP } = G.IA, MS = G.MS, S3 = G.Scene3D, VT = MS.VT, clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const REG = { weak: '약반전 (IC < 0.1)', moderate: '중반전', strong: '강반전 (IC > 10)', cutoff: '차단', triode: '선형', saturation: '포화' };
  const lin = (a, b, n) => Array.from({ length: n }, (_, i) => a + (b - a) * i / (n - 1));
  const ekv = (p) => MS.makeModel('ekv', 1, Object.assign({ kp: KP, lambda: 0.05 }, p));
  const idOf = (m, vd, vg, w, l) => MS.evaluate(m, vd, vg, 0, 0, w, l).id;
  const logLim = (arrs, floor) => { const pos = arrs.flat().filter((x) => x > 0); const lo = Math.max(floor || 1e-16, Math.min(...pos)), hi = Math.max(...pos); return [Math.pow(10, Math.floor(Math.log10(lo))), Math.pow(10, Math.ceil(Math.log10(hi)))]; };
  const profPlot = (p, st, title) => {
    p.begin({ xlabel: '채널 위치 (소스 → 드레인)', ylabel: '채널 전위 [V]', xlim: [0, 1], ylim: [Math.min(0, ...st.prof.v) - 0.02, Math.max(0.1, ...st.prof.v) * 1.08], title: title || '채널 전위 분포 V(x)' });
    p.line(st.prof.u, st.prof.v, { color: '#1f3b73', width: 2.4 }).end();
  };
  const st3 = (s, v) => ({ v, vmin: s.vmin, vmax: s.vmax, prof: s.prof, I: s.I, qmax: s.qmax, phase: s.phase });
  const vtcc = (m, vds, icc, w, l) => MS.bisect((vg) => idOf(m, vds, vg, w, l) - icc, -0.5, 1.5);   // constant-current threshold

  // ================================================================== lesson 5
  G.IA.W.l5 = (root) => makeWidget(root, {
    note: 'Vgs를 문턱 아래에서 위로 올려 보세요. EKV는 문턱 아래에서도 전류가 지수적으로 흐르고, 채널의 전하(청록색 층)가 약반전에서 강반전으로 연속해서 두꺼워집니다.',
    controls: [
      { id: 'vgs', label: 'Vgs', min: 0, max: 1.2, step: 0.005, value: 0.2, fmt: (v) => v.toFixed(3) + ' V' },
      { id: 'vds', label: 'Vds', min: 0, max: 1.8, step: 0.01, value: 1.8, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'n', label: '기울기 계수 n', min: 1.0, max: 2.0, step: 0.01, value: 1.3, fmt: (v) => v.toFixed(2) },
      { id: 'vto', label: 'VTO', min: 0.2, max: 0.8, step: 0.01, value: 0.5, fmt: (v) => v.toFixed(2) + ' V' },
      { type: 'check', id: 'cmp', label: 'Level 1과 비교해서 그리기', value: true },
    ],
    compute: (v) => {
      const m = ekv({ vto: v.vto, n: v.n }), m1 = MS.makeModel('level1', 1, { vto: v.vto, kp: KP, lambda: 0.05 }), w = 1e-6, l = 0.18e-6, vv = { s: 0, d: v.vds, g: v.vgs, b: 0 };
      const ev = MS.evaluate(m, vv.d, vv.g, 0, 0, w, l), prof = MS.channelProfile(m, vv.d, vv.g, 0, 0, w, l, 33), ic = ev.core.if;
      const vgsAt = (t) => MS.bisect((g) => MS.ekvCore(m.p, g, v.vds, 0, w, l).if - t, -0.5, 2);
      const dv = 0.004, slope = 2 * dv / (Math.log10(Math.max(idOf(m, v.vds, v.vgs + dv, w, l), 1e-300)) - Math.log10(Math.max(idOf(m, v.vds, v.vgs - dv, w, l), 1e-300)));
      return { m, m1, w, l, v: vv, ev, prof, ic, I: ev.id, id: ev.id, vgs: v.vgs, vds: v.vds, qmax: 8, region: prof.info.region, is: ev.core.is, i1: idOf(m1, v.vds, v.vgs, w, l), v01: vgsAt(0.1), v10: vgsAt(10), slope };
    },
    vrange: () => [0, 1.8],
    readout: (s, v) => {
      const weakHand = s.is * Math.exp((v.vgs - v.vto) / (v.n * VT)) * (1 + 0.05 * v.vds) * (1 - Math.exp(-v.vds / VT));
      return rows([['Id (EKV)', fI(s.I)], ['반전 계수 IC = i_f', s.ic < 0.01 ? s.ic.toExponential(2) : s.ic.toPrecision(3), REG[s.region]], ['Id (Level 1)', fI(s.i1), s.i1 === 0 ? 'Vgs ≤ Vth: 0' : ''],
        ['특성 전류 Is = 2nβVt²', MS.si(s.is, 'A')], ['약반전 근사식', fI(weakHand), 'Is·e^((Vgs−VTO)/nVt)(1+λVds)(1−e^(−Vds/Vt))'], ['이 점의 기울기', (s.slope * 1e3).toFixed(1) + ' mV/dec', `이론 n·Vt·ln10 = ${(v.n * VT * Math.LN10 * 1e3).toFixed(1)} mV/dec (약반전)`],
        ['약반전 / 강반전 경계', `${s.v01.toFixed(3)} V / ${s.v10.toFixed(3)} V`, 'IC = 0.1 / 10일 때의 Vgs']]);
    },
    plots: [
      { h: 260, draw: (p, s, v) => {
        const xs = lin(0, 1.8, 181), ye = xs.map((g) => idOf(s.m, v.vds, g, s.w, s.l)), y1 = xs.map((g) => idOf(s.m1, v.vds, g, s.w, s.l)), [lo, hi] = logLim([ye, y1, [s.I]], 1e-14);
        p.begin({ xlabel: 'Vgs [V]', ylabel: 'Id [A]', xlim: [0, 1.8], ylim: [Math.max(lo, 1e-14), hi], ylog: true, title: `Id–Vgs (로그), Vds = ${v.vds.toFixed(2)} V` });
        p.band(0, s.v01, 'rgba(120,190,120,0.13)').band(s.v01, s.v10, 'rgba(240,200,60,0.15)').band(s.v10, 1.8, 'rgba(230,110,110,0.12)');
        if (v.cmp) p.line(xs, y1, { color: '#8a91a0', width: 2, dash: [6, 3] });
        p.line(xs, ye, { color: '#d95f02', width: 2.6 }).marker(v.vgs, Math.max(s.I, 1e-15), { label: '동작점' })
          .legend([{ color: '#d95f02', label: 'EKV' }].concat(v.cmp ? [{ color: '#8a91a0', dash: [6, 3], label: 'Level 1' }] : []), 'right').end();
      } },
      { h: 230, draw: (p, s, v) => {
        const xs = lin(0, 0.6, 121), ys = xs.map((d) => idOf(s.m, d, v.vgs, s.w, s.l)), ref = ys[ys.length - 1] || 1e-30;
        p.begin({ xlabel: 'Vds [V]', ylabel: 'Id / Id(Vds = 0.6 V)', xlim: [0, 0.6], ylim: [0, 1.15], title: '현재 Vgs에서 Vds 의존성' });
        p.line(xs, ys.map((y) => y / ref), { color: '#1f3b73', width: 2.4 }).vline(3 * VT, { color: '#b03a00' }).text(3 * VT + 0.01, 0.1, '3·Vt', { color: '#b03a00' });
        if (v.vds <= 0.6) p.marker(v.vds, idOf(s.m, v.vds, v.vgs, s.w, s.l) / ref, {}); p.end();
      } },
      { h: 210, draw: (p, s) => profPlot(p, s) },
    ],
    build3d: (sc, s) => S3.planar(sc, st3(s, s.v)),
    cap3d: '3D 구조: 청록색 층 = 반전 전하(두께는 압축해서 표시), 색 = 전위, 점 = 전류. 약반전에서는 층이 거의 없고 전류가 아주 작습니다.',
    schem: (svg) => { const b = benchSchem(svg); return { s: b.s, update: (s) => b.update({ vgs: s.vgs, vds: s.vds, id: s.id, vmin: s.vmin, vmax: s.vmax }) }; },
    foot: '채널 전위는 EKV의 보간 함수 F의 역함수로 채널 전체에 적용한 근사입니다(국소 전류가 소스 값에서 드레인 값으로 선형으로 줄어든다고 가정). 소스·드레인 끝점은 모델과 정확히 일치합니다.',
  });

  // ================================================================== lesson 6
  const COX = 8.63e-3;
  G.IA.W.l6 = (root) => makeWidget(root, {
    note: 'MOSFET은 자기 자신의 용량(채널 전하)을 가집니다. Vds를 올리면 채널 전하가 소스와 드레인으로 어떻게 나뉘고 Cgs, Cgd가 어떻게 변하는지 확인하세요 (n = 1이면 교과서 값).',
    controls: [
      { id: 'vgs', label: 'Vgs', min: 0, max: 2, step: 0.01, value: 1.8, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'vds', label: 'Vds', min: 0, max: 2, step: 0.01, value: 0, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'n', label: '기울기 계수 n', min: 1.0, max: 1.5, step: 0.01, value: 1.0, fmt: (v) => v.toFixed(2) },
      { id: 'W', label: 'W', min: 0.2, max: 5, log: true, value: 1, fmt: (v) => v.toFixed(2) + ' µm' },
      { id: 'L', label: 'L', min: 0.1, max: 1, log: true, value: 0.18, fmt: (v) => v.toFixed(2) + ' µm' },
    ],
    compute: (v) => {
      const m = ekv({ vto: 0.5, n: v.n, cox: COX, lambda: 0 }), w = v.W * 1e-6, l = v.L * 1e-6, CG = COX * w * l, vv = { s: 0, d: v.vds, g: v.vgs, b: 0 };
      const cj = MS.chargeJac(m, vv.d, vv.g, vv.s, vv.b, w, l), q = cj.q, c = cj.c, ev = MS.evaluate(m, vv.d, vv.g, 0, 0, w, l), prof = MS.channelProfile(m, vv.d, vv.g, 0, 0, w, l, 33);
      const cn = { gg: c[1][1] / CG, gs: -(c[1][2] + c[1][3]) / CG, gd: -c[1][0] / CG, gsRaw: -c[1][2] / CG };
      const sweep = lin(0, 2, 41).map((x) => { const cc = MS.chargeJac(m, x, v.vgs, 0, 0, w, l).c; return { x, gg: cc[1][1] / CG, gs: -(cc[1][2] + cc[1][3]) / CG, gd: -cc[1][0] / CG }; });
      return { m, w, l, CG, q, c, cn, sweep, ev, prof, v: vv, I: ev.id, id: ev.id, vgs: v.vgs, vds: v.vds, qmax: 8, cgs: cn.gs * CG, cgd: cn.gd * CG };
    },
    vrange: () => [0, 2],
    readout: (s, v) => {
      const [qd, qg, qs] = s.q, split = Math.abs(qg) > 1e-30 ? [-qd / qg, -qs / qg] : [NaN, NaN];
      return rows([['Cox·W·L', (s.CG * 1e15).toFixed(3) + ' fF'], ['Qg / Qd / Qs', `${(qg * 1e15).toFixed(3)} / ${(qd * 1e15).toFixed(3)} / ${(qs * 1e15).toFixed(3)} fC`, '합 = 0'], ['Qd : Qs 분배', isFinite(split[0]) ? `${(split[0] * 100).toFixed(1)} % : ${(split[1] * 100).toFixed(1)} %` : '—', '포화에서 40 : 60 (Ward–Dutton)'],
        ['Cgg / (Cox·W·L)', s.cn.gg.toFixed(3), '선형 1, 포화 ⅔'], ['Cgs / (Cox·W·L)', s.cn.gs.toFixed(3), '소스와 벌크를 함께 움직인 정의'], ['Cgd / (Cox·W·L)', s.cn.gd.toFixed(3), '선형 ½, 포화 0'],
        ['전도 전류 Id', fI(s.I)]]);
    },
    plots: [
      { h: 260, draw: (p, s, v) => {
        const xs = s.sweep.map((r) => r.x);
        p.begin({ xlabel: 'Vds [V]', ylabel: '용량 / (Cox·W·L)', xlim: [0, 2], ylim: [-0.05, 1.12], title: `Vgs = ${v.vgs.toFixed(2)} V, n = ${v.n.toFixed(2)}에서 용량 대 Vds` });
        [0.5, 2 / 3, 1].forEach((y) => p.hline(y, { color: '#d5d9e0', dash: [2, 3], width: 1 }));
        p.line(xs, s.sweep.map((r) => r.gg), { color: '#1f3b73', width: 2.4 }).line(xs, s.sweep.map((r) => r.gs), { color: '#d95f02', width: 2.4 }).line(xs, s.sweep.map((r) => r.gd), { color: '#1b9e77', width: 2.4 })
          .vline(v.vds, { color: '#d73027' }).marker(v.vds, s.cn.gg, { color: '#1f3b73', r: 4 }).marker(v.vds, s.cn.gs, { color: '#d95f02', r: 4 }).marker(v.vds, s.cn.gd, { color: '#1b9e77', r: 4 })
          .legend([{ color: '#1f3b73', label: 'Cgg' }, { color: '#d95f02', label: 'Cgs' }, { color: '#1b9e77', label: 'Cgd' }], 'right').end();
      } },
      { h: 230, draw: (p, s) => {
        const mx = Math.max(...s.prof.q, 1e-9); p.begin({ xlabel: '채널 위치 (소스 → 드레인)', ylabel: '반전 전하 밀도 q(x) (정규화)', xlim: [0, 1], ylim: [0, mx * 1.15], title: '채널을 따라 본 반전 전하 밀도: 이것을 적분한 것이 Qd, Qs, Qg' });
        p.line(s.prof.u, s.prof.q, { color: '#27a3b8', width: 2.6 }).end();
      } },
      { h: 210, draw: (p, s) => profPlot(p, s) },
    ],
    build3d: (sc, s) => {
      S3.planar(sc, st3(s, s.v));
      const [qd, , qs] = s.q, tot = Math.abs(qd) + Math.abs(qs) || 1, fd = Math.abs(qd) / tot, fs = Math.abs(qs) / tot;   // charge leaves the channel through source and drain
      if (tot > 1e-22) { sc.line([28, 35, 1.5], [-22, 35, 1.5], { width: 1.5 + 9 * fs, color: '#1b5fb5', head: true, layer: 4 }); sc.line([28, 35, 1.5], [78, 35, 1.5], { width: 1.5 + 9 * fd, color: '#1b5fb5', head: true, layer: 4 });
        sc.label([-22, 35, 1.5], `Qs ${(fs * 100).toFixed(0)} %`, { color: '#1b5fb5', dy: 22 }); sc.label([78, 35, 1.5], `Qd ${(fd * 100).toFixed(0)} %`, { color: '#1b5fb5', dy: 22 }); }
    },
    cap3d: '3D 구조: 청록색 층 = 반전 전하, 파란 화살표 = 채널 전하가 소스·드레인에 귀속되는 몫(굵기). 점 = 전도 전류.',
    schem: (svg) => { const b = benchSchem(svg, { caps: true }); return { s: b.s, update: (s) => b.update({ vgs: s.vgs, vds: s.vds, id: s.id, vmin: s.vmin, vmax: s.vmax, cgs: s.cgs, cgd: s.cgd }) }; },
    capSchem: '회로도: 점선 주황색 = 소자 내부 용량 Cgs, Cgd (바이어스에 따라 값이 변함). 배선 색 = 전압, 점 = 전도 전류.',
    foot: '전하는 모델의 Ward–Dutton 분배로 구하고, 용량은 전하의 수치 미분입니다. 벌크 전하는 모델링하지 않아서 n > 1이면 Cgb가 음수가 됩니다.',
  });

  // ================================================================== lesson 9 (FinFET)
  const PRESET = { planar: { n: 1.45, eta: 0.10 }, fin: { n: 1.15, eta: 0.04 }, gaa: { n: 1.08, eta: 0.02 } };
  const mkM = (p, vto) => ekv({ vto, n: p.n, eta: p.eta });
  const metrics = (m, w, l, vdd) => {
    const icc = 1e-7 * w / l, ss = 0.1 / (Math.log10(idOf(m, 0.1, 0.1, w, l)) - Math.log10(idOf(m, 0.1, 0.0, w, l))) * 1e3;
    return { ioff: idOf(m, vdd, 0, w, l), ion: idOf(m, vdd, vdd, w, l), ss, dibl: (vtcc(m, 0.1, icc, w, l) - vtcc(m, vdd, icc, w, l)) / (vdd - 0.1) * 1e3 };
  };
  G.IA.W.l9 = (root) => makeWidget(root, {
    note: 'fin의 높이·폭·개수와 게이트 길이를 바꾸면 유효 폭과 전류가 어떻게 달라지는지 봅니다. n과 η는 “게이트가 채널을 얼마나 잘 제어하는가”를 나타내는 예시 파라미터입니다.',
    controls: [
      { id: 'H', label: 'fin 높이 H', min: 20, max: 80, step: 1, value: 34, fmt: (v) => v + ' nm' },
      { id: 'Wf', label: 'fin 폭 W_fin', min: 4, max: 20, step: 1, value: 8, fmt: (v) => v + ' nm' },
      { id: 'N', label: 'fin 개수', min: 1, max: 6, step: 1, value: 2, fmt: (v) => v + '개' },
      { id: 'pitch', label: 'fin 피치', min: 30, max: 90, step: 1, value: 60, fmt: (v) => v + ' nm' },
      { id: 'L', label: '게이트 길이 L', min: 10, max: 40, step: 1, value: 20, fmt: (v) => v + ' nm' },
      { id: 'vgs', label: 'Vgs', min: 0, max: 0.8, step: 0.005, value: 0.6, fmt: (v) => v.toFixed(3) + ' V' },
      { id: 'vds', label: 'Vds', min: 0, max: 0.8, step: 0.005, value: 0.8, fmt: (v) => v.toFixed(3) + ' V' },
      { id: 'n', label: 'n (예시값)', min: 1.0, max: 1.6, step: 0.01, value: 1.15, fmt: (v) => v.toFixed(2) },
      { id: 'eta', label: 'η = DIBL (예시값)', min: 0, max: 0.15, step: 0.005, value: 0.04, fmt: (v) => v.toFixed(3) + ' V/V' },
      { id: 'vto', label: 'VTO', min: 0.2, max: 0.6, step: 0.01, value: 0.35, fmt: (v) => v.toFixed(2) + ' V' },
      { type: 'buttons', items: [{ text: '평면형 예시값 (n 1.45, η 0.10)', set: { n: 1.45, eta: 0.10 } }, { text: 'FinFET 예시값 (n 1.15, η 0.04)', set: { n: 1.15, eta: 0.04 } }] },
    ],
    compute: (v) => {
      const weff = v.N * (2 * v.H + v.Wf), w = weff * 1e-9, l = v.L * 1e-9, m = mkM(v, v.vto), vv = { s: 0, d: v.vds, g: v.vgs, b: 0 }, vdd = 0.8;
      const ev = MS.evaluate(m, vv.d, vv.g, 0, 0, w, l), prof = MS.channelProfile(m, vv.d, vv.g, 0, 0, w, l, 33), wpl = v.N * v.pitch * 1e-9, mp = mkM(PRESET.planar, v.vto);
      return { m, mp, w, l, wpl, weff, v: vv, ev, prof, I: ev.id, id: ev.id, vgs: v.vgs, vds: v.vds, qmax: 8, geo: { H: v.H, Wf: v.Wf, pitch: v.pitch, N: v.N, L: v.L }, met: metrics(m, w, l, vdd), metPl: metrics(mp, wpl, l, vdd), mult: v.N };
    },
    vrange: () => [0, 0.9],
    readout: (s, v) => rows([['유효 폭 W_eff = N(2H+W)', `${s.weff.toFixed(0)} nm`, `fin 하나 ${(2 * v.H + v.Wf)} nm`], ['같은 풋프린트의 평면형 폭', `${(s.wpl * 1e9).toFixed(0)} nm`, `FinFET은 ×${(s.weff / (s.wpl * 1e9)).toFixed(2)}`],
      ['Id (현재 바이어스)', fI(s.I), `fin당 ${fI(s.I / v.N)}`], ['Ion / Ioff (Vds = 0.8 V)', `${fI(s.met.ion, 3)} / ${fI(s.met.ioff, 3)}`, `on/off = ${(s.met.ion / s.met.ioff).toExponential(1)}`],
      ['SS (모델)', s.met.ss.toFixed(1) + ' mV/dec', `손 계산 n·Vt·ln10 = ${(v.n * VT * Math.LN10 * 1e3).toFixed(1)}`], ['DIBL (모델)', s.met.dibl.toFixed(1) + ' mV/V', `설정 η = ${(v.eta * 1e3).toFixed(0)} mV/V`],
      ['평면형 예시값과 Ioff 비', (s.metPl.ioff / s.met.ioff).toFixed(1) + '배', '같은 풋프린트·같은 VTO']]),
    plots: [
      { h: 260, draw: (p, s, v) => {
        const xs = lin(0, 0.8, 161), ser = [[s.m, s.w, 0.8, '#d95f02', null, '이 소자 Vds = 0.8 V'], [s.m, s.w, 0.1, '#d95f02', [5, 3], '이 소자 Vds = 0.1 V'], [s.mp, s.wpl, 0.8, '#8a91a0', null, '평면형 Vds = 0.8 V'], [s.mp, s.wpl, 0.1, '#8a91a0', [5, 3], '평면형 Vds = 0.1 V']];
        const ys = ser.map(([m, w, vd]) => xs.map((g) => idOf(m, vd, g, w, s.l))), [lo, hi] = logLim(ys.concat([[s.I]]), 1e-13);
        p.begin({ xlabel: 'Vgs [V]', ylabel: 'Id [A]', xlim: [0, 0.8], ylim: [Math.max(lo, 1e-13), hi], ylog: true, title: 'Id–Vgs: 같은 풋프린트의 평면형(회색, 예시값)과 비교' });
        ser.forEach((r, i) => p.line(xs, ys[i], { color: r[3], dash: r[4], width: r[4] ? 1.8 : 2.4 }));
        p.marker(v.vgs, Math.max(s.I, 1e-14), { label: '동작점' }).legend(ser.map((r) => ({ color: r[3], dash: r[4], label: r[5] })), 'right').end();
      } },
      { h: 230, draw: (p, s, v) => {
        const ns = [1, 2, 3, 4, 5, 6], fin = ns.map((n) => n * (2 * v.H + v.Wf)), pl = ns.map((n) => n * v.pitch);
        p.begin({ xlabel: 'fin 개수 (풋프린트 = N × 피치)', ylabel: '유효 폭 [nm]', xlim: [0.7, 6.3], ylim: [0, Math.max(...fin, ...pl) * 1.12], title: '폭은 fin 개수 단위로만 바뀐다' });
        p.line(ns, pl, { color: '#8a91a0', dash: [5, 3], width: 1.8 }).line(ns, fin, { color: '#d95f02', width: 2.4 });
        ns.forEach((n, i) => p.marker(n, fin[i], { color: n === v.N ? '#d73027' : '#d95f02', r: n === v.N ? 6 : 3.5 })); p.legend([{ color: '#d95f02', label: 'FinFET N(2H+W)' }, { color: '#8a91a0', dash: [5, 3], label: '평면형 N×피치' }]).end();
      } },
      { h: 210, draw: (p, s) => profPlot(p, s) },
    ],
    build3d: (sc, s) => S3.finfet(sc, Object.assign(st3(s, s.v), { geo: s.geo })),
    scene: { yaw: -0.55, pitch: 0.5, height: 320 },
    cap3d: '3D 구조(nm 단위 비례, 길이는 압축): fin의 윗면·양옆 3면에 게이트가 닿습니다. 색 = 채널 전위, 점 = 각 fin의 윗면과 양옆을 흐르는 전류.',
    schem: (svg) => { const b = benchSchem(svg, { label: 'M1 (FinFET)' }); return { s: b.s, update: (s) => b.update({ vgs: s.vgs, vds: s.vds, id: s.id, vmin: s.vmin, vmax: s.vmax, mult: s.mult, mlabel: `×${s.mult} fin` }) }; },
    foot: 'n, η, fin 폭은 <b>교육용 예시값</b>이고 특정 공정에서 추출한 값이 아닙니다. 유효 폭 N(2H+W)와 평면형과의 비교는 교재 본문의 출처(유효 폭 공식, Intel 22 nm의 fin 높이·피치)를 따릅니다.',
  });

  // ================================================================== lesson 10 (GAA)
  const vtcOf = (p, vto, w, l, vdd) => {
    const mn = ekv({ vto, n: p.n, eta: p.eta }), mp = MS.makeModel('ekv', -1, { vto: -vto, kp: 100e-6, n: p.n, eta: p.eta, lambda: 0.05 }), wp = 3 * w;
    const out = (vi) => MS.bisect((x) => MS.evaluate(mn, x, vi, 0, 0, w, l).id + MS.evaluate(mp, x, vi, vdd, vdd, wp, l).id, -0.3, vdd + 0.3);
    const vins = lin(0, vdd, 81), vouts = vins.map(out), vm = MS.bisect((vi) => vi - out(vi), 0, vdd);   // vi - out(vi) increases with vi (the VTC falls)
    const a = MS.evaluate(mn, vm, vm, 0, 0, w, l), b = MS.evaluate(mp, vm, vm, vdd, vdd, wp, l);
    return { vins, vouts, vm, gain: (a.gg + Math.abs(b.gg)) / (a.gd + b.gd) };
  };
  G.IA.W.l10 = (root) => makeWidget(root, {
    note: '나노시트의 장 수·폭·두께를 바꿔 유효 폭을 조절하고, 게이트 제어(n, η)가 좋아질 때 같은 폭에서 전류와 인버터 이득이 어떻게 달라지는지 비교합니다.',
    controls: [
      { id: 'N', label: '시트 장 수 N', min: 1, max: 5, step: 1, value: 3, fmt: (v) => v + '장' },
      { id: 'W', label: '시트 폭 W', min: 10, max: 60, step: 1, value: 30, fmt: (v) => v + ' nm' },
      { id: 'T', label: '시트 두께 T', min: 3, max: 10, step: 0.5, value: 5, fmt: (v) => v + ' nm' },
      { id: 'L', label: '게이트 길이 L', min: 10, max: 40, step: 1, value: 20, fmt: (v) => v + ' nm' },
      { id: 'vgs', label: 'Vgs', min: 0, max: 0.8, step: 0.005, value: 0.6, fmt: (v) => v.toFixed(3) + ' V' },
      { id: 'vds', label: 'Vds', min: 0, max: 0.8, step: 0.005, value: 0.8, fmt: (v) => v.toFixed(3) + ' V' },
      { id: 'n', label: 'n (예시값)', min: 1.0, max: 1.6, step: 0.01, value: 1.08, fmt: (v) => v.toFixed(2) },
      { id: 'eta', label: 'η = DIBL (예시값)', min: 0, max: 0.15, step: 0.005, value: 0.02, fmt: (v) => v.toFixed(3) + ' V/V' },
      { id: 'vto', label: 'VTO', min: 0.2, max: 0.6, step: 0.01, value: 0.35, fmt: (v) => v.toFixed(2) + ' V' },
      { type: 'buttons', items: [{ text: '평면형 (1.45, 0.10)', set: { n: 1.45, eta: 0.10 } }, { text: 'FinFET (1.15, 0.04)', set: { n: 1.15, eta: 0.04 } }, { text: 'GAA (1.08, 0.02)', set: { n: 1.08, eta: 0.02 } }] },
    ],
    compute: (v) => {
      const weff = v.N * 2 * (v.W + v.T), w = weff * 1e-9, l = v.L * 1e-9, m = mkM(v, v.vto), vv = { s: 0, d: v.vds, g: v.vgs, b: 0 }, vdd = 0.8;
      const ev = MS.evaluate(m, vv.d, vv.g, 0, 0, w, l), prof = MS.channelProfile(m, vv.d, vv.g, 0, 0, w, l, 33);
      const vt = { cur: vtcOf(v, v.vto, w, l, vdd), planar: vtcOf(PRESET.planar, v.vto, w, l, vdd), fin: vtcOf(PRESET.fin, v.vto, w, l, vdd), gaa: vtcOf(PRESET.gaa, v.vto, w, l, vdd) };
      return { m, w, l, weff, v: vv, ev, prof, I: ev.id, id: ev.id, vgs: v.vgs, vds: v.vds, qmax: 8, geo: { N: v.N, W: v.W, T: v.T, L: v.L, gap: 10 }, met: metrics(m, w, l, vdd), vt, mult: v.N };
    },
    vrange: () => [0, 0.9],
    readout: (s, v) => rows([['유효 폭 W_eff = N·2(W+T)', `${s.weff.toFixed(0)} nm`, `시트 하나 ${(2 * (v.W + v.T)).toFixed(0)} nm (윗면만이면 ${(v.N * v.W).toFixed(0)} nm)`], ['Id (현재 바이어스)', fI(s.I), `시트당 ${fI(s.I / v.N)}`],
      ['Ion / Ioff (Vds = 0.8 V)', `${fI(s.met.ion, 3)} / ${fI(s.met.ioff, 3)}`], ['SS (모델)', s.met.ss.toFixed(1) + ' mV/dec', `n·Vt·ln10 = ${(v.n * VT * Math.LN10 * 1e3).toFixed(1)}`], ['DIBL (모델)', s.met.dibl.toFixed(1) + ' mV/V'],
      ['인버터 이득 (이 n, η)', s.vt.cur.gain.toFixed(1), `Vm = ${s.vt.cur.vm.toFixed(3)} V, 상한 ≈ 1/η = ${v.eta > 0 ? (1 / v.eta).toFixed(0) : '∞'}`]]),
    plots: [
      { h: 260, draw: (p, s, v) => {
        const xs = lin(0, 0.8, 161), ser = [['평면형', PRESET.planar, '#8a91a0'], ['FinFET', PRESET.fin, '#d95f02'], ['GAA', PRESET.gaa, '#1b5fb5']].map(([nm, pr, c]) => ({ nm, c, y: xs.map((g) => idOf(mkM(pr, v.vto), 0.8, g, s.w, s.l)) }));
        const cur = xs.map((g) => idOf(s.m, 0.8, g, s.w, s.l)), [lo, hi] = logLim(ser.map((r) => r.y).concat([cur, [s.I]]), 1e-13);
        p.begin({ xlabel: 'Vgs [V]', ylabel: 'Id [A]', xlim: [0, 0.8], ylim: [Math.max(lo, 1e-13), hi], ylog: true, title: `같은 폭 W_eff = ${s.weff.toFixed(0)} nm에서 게이트 제어 비교 (Vds = 0.8 V)` });
        ser.forEach((r) => p.line(xs, r.y, { color: r.c, width: 1.8, dash: [5, 3] })); p.line(xs, cur, { color: '#111', width: 2.8 }).marker(v.vgs, Math.max(s.I, 1e-14), { label: '동작점' })
          .legend(ser.map((r) => ({ color: r.c, dash: [5, 3], label: r.nm })).concat([{ color: '#111', label: '현재 n, η' }]), 'right').end();
      } },
      { h: 230, draw: (p, s, v) => {
        p.begin({ xlabel: 'Vin [V]', ylabel: 'Vout [V]', xlim: [0, 0.8], ylim: [0, 0.85], title: '같은 폭의 CMOS 인버터 VTC (PMOS 폭 3배)' });
        const L = [['평면형', s.vt.planar, '#8a91a0'], ['FinFET', s.vt.fin, '#d95f02'], ['GAA', s.vt.gaa, '#1b5fb5']];
        L.forEach(([nm, t, c]) => p.line(t.vins, t.vouts, { color: c, width: 1.8, dash: [5, 3] })); p.line(s.vt.cur.vins, s.vt.cur.vouts, { color: '#111', width: 2.8 })
          .legend(L.map(([nm, t, c]) => ({ color: c, dash: [5, 3], label: `${nm}: 이득 ${t.gain.toFixed(0)}` })).concat([{ color: '#111', label: `현재: 이득 ${s.vt.cur.gain.toFixed(0)}` }]), 'right').end();
      } },
      { h: 210, draw: (p, s) => profPlot(p, s) },
    ],
    build3d: (sc, s) => S3.gaa(sc, Object.assign(st3(s, s.v), { geo: s.geo })),
    scene: { yaw: -0.6, pitch: 0.45, height: 320 },
    cap3d: '3D 구조(nm 단위 비례, 길이는 압축): 게이트가 시트를 4면에서 감쌉니다. 색 = 채널 전위, 점 = 각 시트의 윗면과 아랫면을 흐르는 전류.',
    schem: (svg) => { const b = benchSchem(svg, { label: 'M1 (GAA)' }); return { s: b.s, update: (s) => b.update({ vgs: s.vgs, vds: s.vds, id: s.id, vmin: s.vmin, vmax: s.vmax, mult: s.mult, mlabel: `×${s.mult} 시트` }) }; },
    foot: '나노시트 치수, n, η는 <b>교육용 예시값</b>입니다. “같은 폭에서 비교”는 n과 η만 바꾼 것이고(전류 ∝ 1/n 효과 포함), 실제 GAA 소자의 이득이나 전류를 예측하지 않습니다.',
  });
})(typeof window !== 'undefined' ? window : globalThis);
