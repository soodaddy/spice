'use strict';
/* ia_l7.js - lesson 7 widget: explore the stored minispice and ngspice results (the data is embedded in the page). */
(function (G) {
  const { makeWidget, benchSchem, invSchem, fI, rows } = G.IA, MS = G.MS, S3 = G.Scene3D, { svg } = G.UI, { cmap } = G.UI;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const NM = MS.makeModel('level1', 1, { vto: 0.5, kp: 300e-6, lambda: 0.05 }), PM = MS.makeModel('level1', -1, { vto: -0.5, kp: 100e-6, lambda: 0.05 });
  const WN = 1e-6, WP = 3e-6, L = 0.18e-6, VDD = 1.8;

  function cmosState(vin, vout) {
    const dn = { s: 0, d: vout, g: vin, b: 0 }, dp = { s: VDD, d: vout, g: vin, b: VDD }, en = MS.evaluate(NM, vout, vin, 0, 0, WN, L), ep = MS.evaluate(PM, vout, vin, VDD, VDD, WP, L);
    return { vin, vout, ip: -ep.id, in_: en.id, n: { v: dn, prof: MS.channelProfile(NM, dn.d, dn.g, 0, 0, WN, L, 33), I: en.id, qmax: 1.2 }, p: { v: dp, prof: MS.channelProfile(PM, dp.d, dp.g, VDD, VDD, WP, L, 33), I: ep.id, qmax: 1.2 } };
  }
  const firstCross = (t, v, lvl, t0) => { for (let i = 1; i < t.length; i++) if (t[i] >= t0 && v[i - 1] < lvl && lvl <= v[i]) return t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1]); return NaN; };
  const allCross = (t, v, lvl) => { const out = []; for (let i = 1; i < t.length; i++) if (v[i - 1] < lvl && lvl <= v[i]) out.push(t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1])); return out; };

  /** five inverters in a ring; node wires are coloured by the stored voltages (no current dots: only node voltages are stored) */
  function ringSchem(svgEl) {
    const s = new G.Schem(svgEl, 380, 300), cx = 190, cy = 152, R = 104, P = (a, r) => [cx + (r || R) * Math.cos(a), cy + (r || R) * Math.sin(a)], A = (k) => -Math.PI / 2 + 2 * Math.PI * k / 5;
    const wires = [], badges = [];
    for (let k = 0; k < 5; k++) {
      const am = (A(k) + A(k + 1 > 4 ? 5 : k + 1)) / 2, M = P(am), T = [-Math.sin(am), Math.cos(am)], N = [Math.cos(am), Math.sin(am)];
      const inp = [M[0] - 15 * T[0], M[1] - 15 * T[1]], outp = [M[0] + 19 * T[0], M[1] + 19 * T[1]];
      wires.push({ a: s.wire([P(A(k)), inp]), b: s.wire([outp, P(A(k + 1))]), k });
      const tip = [M[0] + 13 * T[0], M[1] + 13 * T[1]], b1 = [M[0] - 11 * T[0] + 12 * N[0], M[1] - 11 * T[1] + 12 * N[1]], b2 = [M[0] - 11 * T[0] - 12 * N[0], M[1] - 11 * T[1] - 12 * N[1]];
      s.g1.append(svg('polygon', { points: [tip, b1, b2].map((q) => q.join(',')).join(' '), fill: '#dbe9ff', stroke: '#1f3b73', 'stroke-width': 2 })); s.g1.append(svg('circle', { cx: tip[0] + 4 * T[0], cy: tip[1] + 4 * T[1], r: 3.4, fill: '#fff', stroke: '#1f3b73', 'stroke-width': 1.6 }));
      s.text(M[0] + 30 * N[0], M[1] + 30 * N[1] + 4, `INV${k + 1}`, { size: 10, anchor: 'middle', weight: 500, color: '#4a5160' });
    }
    for (let k = 0; k < 5; k++) { const p = P(A(k), R + 4); s.dot(...P(A(k)), 4.2); badges.push(s.badge(p[0] - 36 + 22 * Math.cos(A(k)), p[1] + (k === 0 ? -22 : 4 + 10 * Math.sin(A(k))), `n${k + 1}`)); }
    return { s, update(st) {
      const [a, b] = [st.vmin, st.vmax];
      wires.forEach((w) => { w.a.set(st.ring[w.k], 0, a, b); w.b.set(st.ring[(w.k + 1) % 5], 0, a, b); });
      badges.forEach((bd, k) => bd.set(st.ring[k], a, b));
    } };
  }

  G.IA.W.l7 = (root) => {
    const D = JSON.parse(document.getElementById('ia-data-l7').textContent), CASES = { curves: 'NMOS 출력 특성 (Id–Vds)', vtc: '인버터 VTC (DC)', tran: '인버터 과도 응답', ring: '5단 링 오실레이터' };
    makeWidget(root, {
      note: 'minispice와 ngspice의 저장된 결과를 겹쳐 보고, 커서를 움직여 두 값의 차이를 읽습니다. (ngspice는 브라우저에서 실행하지 않고, 미리 계산한 결과입니다.)',
      controls: [
        { type: 'select', id: 'kase', label: '비교 항목', value: 'curves', options: Object.entries(CASES) },
        { type: 'select', id: 'k', label: 'Vgs (출력 특성에서만)', value: '4', options: D.curves.vgs.map((g, i) => [String(i), g.toFixed(1) + ' V']) },
        { id: 'pos', label: '커서 위치', min: 0, max: 1, step: 0.001, value: 0.9, fmt: (v) => (v * 100).toFixed(1) + ' %' },
        { type: 'play', id: 'play' },
      ],
      compute: (v) => {
        const k = +v.k, kase = v.kase;
        let x, a, b, xl, ratio = 1, unit, dunit, dscale, xs = 1;
        if (kase === 'curves') { x = D.curves.vds; a = D.curves.mini[k]; b = D.curves.ng[k]; xl = 'Vds [V]'; unit = 'mA'; ratio = 1e3; dunit = 'nA'; dscale = 1e9; }
        else if (kase === 'vtc') { x = D.vtc.vin; a = D.vtc.mini; b = D.vtc.ng; xl = 'Vin [V]'; unit = 'V'; dunit = 'µV'; dscale = 1e6; }
        else if (kase === 'tran') { x = D.tran.t.map((t) => t * 1e9); a = D.tran.mini; b = D.tran.ng; xl = 't [ns]'; unit = 'V'; dunit = 'mV'; dscale = 1e3; }
        else { x = D.ring.t.map((t) => t * 1e9); a = D.ring.mini[0]; b = D.ring.ng[0]; xl = 't [ns]'; unit = 'V (n1)'; dunit = 'mV'; dscale = 1e3; }
        const n = x.length, i = clamp(Math.round(v.pos * (n - 1)), 0, n - 1), d = a.map((q, j) => b[j] - q), dmax = Math.max(...d.map(Math.abs)), rms = Math.sqrt(d.reduce((s, q) => s + q * q, 0) / n);
        let st = { kase, x, a, b, d, i, xl, unit, dunit, dscale, ratio, dmax, rms, n };
        if (kase === 'curves') { const vgs = D.curves.vgs[k], vds = x[i], e = MS.evaluate(NM, vds, vgs, 0, 0, WN, L); st = Object.assign(st, { vgs, vds, id: a[i], I: a[i], v: { s: 0, d: vds, g: vgs, b: 0 }, prof: MS.channelProfile(NM, vds, vgs, 0, 0, WN, L, 33), qmax: 1.2 }); }
        else if (kase === 'ring') { const ring = D.ring.mini.map((q) => q[i]); Object.assign(st, cmosState(ring[4], ring[0]), { ring, ringNg: D.ring.ng.map((q) => q[i]) }); }
        else { const vin = kase === 'vtc' ? x[i] : D.tran.vin[i]; Object.assign(st, cmosState(vin, a[i])); st.ic = st.ip - st.in_; }
        if (kase === 'ring') { const tm = allCross(D.ring.t, D.ring.mini[0], 0.9), tg = allCross(D.ring.t, D.ring.ng[0], 0.9); st.tm = tm; st.tg = tg; st.pm = (tm[tm.length - 1] - tm[0]) / (tm.length - 1); st.pg = (tg[tg.length - 1] - tg[0]) / (tg.length - 1); }
        return st;
      },
      onTick: (dt, ctl) => { let p = ctl.pos.get() + dt * 0.08; if (p > 1) p = 0; ctl.pos.set(p); return true; },
      vrange: () => [0, VDD],
      readout: (s) => {
        const f = (q) => (s.ratio === 1 ? q.toPrecision(7) : (q * s.ratio).toPrecision(6)), dv = (s.b[s.i] - s.a[s.i]) * s.dscale;
        let r = rows([['커서', `${s.x[s.i].toPrecision(4)} ${s.xl.replace(/.*\[|\]/g, '')}`], ['minispice', `${f(s.a[s.i])} ${s.unit}`], ['ngspice', `${f(s.b[s.i])} ${s.unit}`], ['차이 (ngspice − minispice)', `${dv.toPrecision(3)} ${s.dunit}`],
          ['전 구간 최대 |차이|', `${(s.dmax * s.dscale).toPrecision(3)} ${s.dunit}`, `rms ${(s.rms * s.dscale).toPrecision(3)} ${s.dunit}`]]);
        if (s.kase === 'ring') r += rows([['주기 (minispice)', MS.si(s.pm, 's', 5)], ['주기 (ngspice)', MS.si(s.pg, 's', 5)], ['주기 차이', `${(Math.abs(s.pm - s.pg) / s.pg * 100).toFixed(2)} %`]]) + '<p class="ia-warn" style="color:var(--mut)">링의 파형 차이는 주기 0.13 %가 40주기 동안 쌓여 생긴 <b>위상 어긋남</b>입니다. 에지에서 차이가 커 보여도 두 결과는 같은 주기로 발진합니다. 레슨 본문은 주기를 비교합니다.</p>';
        if (s.kase === 'tran') r += rows([['전원 전류 첨두', `${MS.si(Math.max(...D.tran.idd_mini), 'A')} / ${MS.si(Math.max(...D.tran.idd_ng), 'A')}`, 'minispice / ngspice']]);
        return r;
      },
      plots: [
        { h: 250, draw: (p, s) => {
          const y = (arr) => arr.map((q) => q * s.ratio), ya = y(s.a), yb = y(s.b), all = ya.concat(yb), lo = Math.min(...all), hi = Math.max(...all), pad = (hi - lo) * 0.08 || 1;
          p.begin({ xlabel: s.xl, ylabel: s.unit, xlim: [s.x[0], s.x[s.n - 1]], ylim: [lo - pad, hi + pad], title: '두 시뮬레이터의 결과 (선: minispice, ○: ngspice)' });
          p.line(s.x, ya, { color: '#1f3b73', width: 2.6 }); const step = Math.max(1, Math.round(s.n / 70)); for (let j = 0; j < s.n; j += step) p.marker(s.x[j], yb[j], { color: '#d95f02', r: 2.4 });
          p.vline(s.x[s.i], { color: '#d73027' }).marker(s.x[s.i], ya[s.i], { color: '#1f3b73', r: 5 }).marker(s.x[s.i], yb[s.i], { color: '#d95f02', r: 3.5 }).end();
        } },
        { h: 250, draw: (p, s) => {
          const dd = s.d.map((q) => q * s.dscale), m = Math.max(...dd.map(Math.abs), 1e-12) * 1.15;
          p.begin({ xlabel: s.xl, ylabel: `차이 [${s.dunit}]`, xlim: [s.x[0], s.x[s.n - 1]], ylim: [-m, m], title: '차이 = ngspice − minispice (확대해서 표시)' });
          p.hline(0, { color: '#8a91a0' }).line(s.x, dd, { color: '#7570b3', width: 2 }).vline(s.x[s.i], { color: '#d73027' }).marker(s.x[s.i], dd[s.i], { color: '#7570b3', r: 4.5 }).end();
        } },
      ],
      build3d: (sc, s) => {
        if (s.kase === 'curves') S3.planar(sc, { v: s.v, vmin: s.vmin, vmax: s.vmax, prof: s.prof, I: s.I, qmax: 1.2, phase: s.phase });
        else S3.cmos(sc, { n: Object.assign({ vmin: s.vmin, vmax: s.vmax, phase: s.phase }, s.n), p: Object.assign({ vmin: s.vmin, vmax: s.vmax, phase: s.phase }, s.p) });
      },
      scene: { yaw: -0.8, pitch: 0.6, height: 300 },
      cap3d: '3D 구조: minispice 결과의 바이어스에서 JS 모델이 그린 전위(색)와 전류(점). 링 오실레이터는 INV1(입력 n5, 출력 n1) 한 단입니다.',
      schem: (svgEl) => {
        const parent = svgEl.parentNode, mk = () => { const e = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); e.setAttribute('class', 'ia-svg'); parent.insertBefore(e, svgEl.nextSibling); return e; };
        const sv2 = mk(), sv3 = mk(), bench = benchSchem(svgEl), inv = invSchem(sv2), ring = ringSchem(sv3);
        const show = (k) => { svgEl.style.display = k === 'curves' ? '' : 'none'; sv2.style.display = k === 'vtc' || k === 'tran' ? '' : 'none'; sv3.style.display = k === 'ring' ? '' : 'none'; };
        let cur = 'curves';
        return { s: { tick: (ph) => { (cur === 'curves' ? bench : cur === 'ring' ? ring : inv).s.tick(ph); } }, update(s) {
          cur = s.kase; show(s.kase);
          if (s.kase === 'curves') bench.update({ vgs: s.vgs, vds: s.vds, id: s.id, vmin: s.vmin, vmax: s.vmax });
          else if (s.kase === 'ring') ring.update({ ring: s.ring, vmin: s.vmin, vmax: s.vmax });
          else inv.update({ vdd: VDD, vin: s.vin, vout: s.vout, ip: s.ip, in_: s.in_, ic: s.kase === 'tran' ? s.ic : undefined, vmin: s.vmin, vmax: s.vmax });
        } };
      },
      capSchem: '회로도: 배선 색 = 노드 전압(minispice 결과). 링 오실레이터는 저장된 것이 노드 전압뿐이라 전류 점은 표시하지 않습니다.',
      foot: 'ngspice 결과는 <code>examples/lesson7_ngspice.py</code>가 ngspice 47로 미리 계산해 둔 것입니다. 입력(바이어스, 시간)을 바꾸면 저장된 결과 위에서 커서가 움직입니다. 입력이 다른 새 조건은 ngspice를 다시 실행해야 비교할 수 있습니다.',
    });
  };
})(typeof window !== 'undefined' ? window : globalThis);
