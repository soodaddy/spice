'use strict';
/* ia_l12.js - lesson 12 widgets: N DRAM cells (access NMOS + storage node) sharing one bit line, N = 2 (l12a) and N = 4 (l12b). */
(function (G) {
  const { makeWidget, fI, rows } = G.IA, MS = G.MS, S3 = G.Scene3D, { svg } = G.UI, clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const lin = (a, b, n) => Array.from({ length: n }, (_, i) => a + (b - a) * i / (n - 1));
  const DT = 10e-12, COL = ['#1b9e77', '#d95f02', '#7570b3', '#e6ab02'], VDD = 1.2;
  const fIs = (I) => (Math.abs(I) < 1e-21 ? '0 A' : (I < 0 ? '−' : '') + MS.si(Math.abs(I), 'A', 3));
  const fV = (v) => v.toFixed(3) + ' V', fT = (t) => (isFinite(t) ? MS.si(t, 's') : '∞');
  const handDv = (levels, sel, cs, cbl) => sel.reduce((a, k) => a + cs * (levels[k] - VDD / 2), 0) / (cbl + sel.length * cs);

  /** vAt of a retention curve (as in lesson 11): linear in t on the first segment, linear in log t afterwards */
  function vAt(r, t) {
    const ts = r.ts, vs = r.vs, n = ts.length;
    if (t >= ts[n - 1]) return vs[n - 1];
    let k = 1; while (k < n && ts[k] < t) k++;
    const t0 = ts[k - 1], t1 = ts[k], f = t0 <= 0 ? t / t1 : Math.log(t / t0) / Math.log(t1 / t0);
    return vs[k - 1] + (vs[k] - vs[k - 1]) * f;
  }

  /** schematic: shared bit line with n cell branches, Cbl and the sense amplifier / write driver */
  function arraySchem(svgEl, n) {
    const s = new G.Schem(svgEl, 380, 305), sz = n === 2 ? 15 : 12, gap = n === 2 ? 128 : 76, g0 = n === 2 ? 56 : 40, yb = 44, ym = 150;
    const dx = (k) => g0 + gap * k + 1.6 * sz, taps = [], cells = [];
    const sax = 330, cbx = n === 2 ? 296 : 306;
    s.g1.append(svg('rect', { x: sax, y: 24, width: 46, height: 40, rx: 5, fill: '#e8e0f5', stroke: '#1f3b73', 'stroke-width': 1.8 }));
    s.text(sax + 23, 40, 'SA /', { size: 10, anchor: 'middle', weight: 600 }); s.text(sax + 23, 53, '드라이버', { size: 9, anchor: 'middle', weight: 500 });
    s.text(8, 22, 'BL (공유 비트라인)', { size: 11, color: '#b03a00' });
    // bit line pieces from the right (SA) to the left; the current along the point order (right -> left) is positive when it flows towards the cells
    const xs = [sax, cbx].concat(Array.from({ length: n }, (_, i) => dx(n - 1 - i)));
    const pieces = []; for (let i = 0; i + 1 < xs.length; i++) pieces.push(s.wire([[xs[i], yb], [xs[i + 1], yb]]));
    const wCb1 = s.wire([[cbx, yb], [cbx, 74]]), wCb2 = s.wire([[cbx, 112], [cbx, 128]]), wCbb = s.wire([[cbx, 74], [cbx, 112]], { width: 0.1 });
    wCbb.path.setAttribute('stroke', 'none'); s.capacitor(cbx, 74, 112, ''); s.ground(cbx, 128); s.dot(cbx, yb);
    const tC = s.text(cbx + 14, 112, '', { size: 9.5, color: '#b03a00' }); s.text(cbx + 14, 96, 'Cbl', { size: 10.5 });
    for (let k = 0; k < n; k++) {
      const gx = g0 + gap * k, x = dx(k), m = s.mos(gx, ym, { size: sz });
      const wD = s.wire([[x, yb], [x, ym - 1.4 * sz]]), wS = s.wire([[x, ym + 1.4 * sz], [x, 205]]), wCs = s.wire([[x, 205], [x, 235]], { width: 0.1 }), wG = s.wire([[gx - 22, ym], [gx, ym]], { width: 2.8 });
      wCs.path.setAttribute('stroke', 'none'); s.capacitor(x, 205, 243, ''); s.text(x + 13, 228, 'Cs', { size: 10 }); s.wire([[x, 243], [x, 258]], { width: 0.1 }); s.ground(x, 258); s.dot(x, yb);
      const tW = s.text(gx - 24, ym - 7, '', { size: 9, color: '#b03a00' }), tS = s.text(x + 5, 196, '', { size: 9.5, weight: 700 }), tI = s.text(x + 6, 100, '', { size: 8.5, color: '#b03a00', weight: 500 });
      cells.push({ wD, wS, wG, tW, tS, tI, k });
    }
    const tS = s.text(8, 298, '', { size: 10, weight: 500, color: '#4a5160' });
    return { s, update(st) {
      const { vmin, vmax } = st;
      let I = st.isrc; pieces[0].set(st.vbl, I, vmin, vmax); I -= st.icbl; pieces[1].set(st.vbl, I, vmin, vmax);
      wCb1.set(st.vbl, st.icbl, vmin, vmax); wCb2.set(0, st.icbl, vmin, vmax); wCbb.I = st.icbl;
      for (let k = n - 1; k >= 1; k--) { I -= st.iacc[k]; pieces[2 + (n - 1 - k)].set(st.vbl, I, vmin, vmax); }   // the piece between cell k and cell k-1
      cells.forEach((c) => {
        const k = c.k; c.wD.set(st.vbl, st.iacc[k], vmin, vmax); c.wS.set(st.vsn[k], st.iacc[k], vmin, vmax); c.wG.set(st.vwl[k], 0, vmin, vmax);
        c.tW.textContent = `WL${k}`; c.tS.textContent = `SN${k} ${st.vsn[k].toFixed(2)}V`; c.tI.textContent = Math.abs(st.iacc[k]) > 1e-12 ? fIs(st.iacc[k]) : '';
      });
      tC.textContent = st.cblValue || ''; tS.textContent = st.sText || '';
    } };
  }

  function makeL12(N) {
    const bitsCtl = Array.from({ length: N }, (_, k) => ({ type: 'check', id: 'b' + k, label: `셀 ${k}의 저장값 = 1`, value: k % 2 === 0 || (N === 4 && k === 3) }));
    const selOpts = Array.from({ length: N }, (_, k) => [String(k), `셀 ${k} (WL${k})`]);
    return (root) => makeWidget(root, {
      note: `비트라인 하나에 셀 ${N}개가 붙어 있습니다. 워드라인을 올린 셀만 비트라인과 연결됩니다. 저장값과 읽을 셀을 골라 보고, 워드라인을 두 개 동시에 올리면 어떻게 되는지도 보세요.`,
      controls: [
        { type: 'select', id: 'mode', label: '동작', value: 'read', options: [['read', '읽기 (전하 공유 → 센스앰프 → 복원)'], ['ret', '유지(retention): 이웃 셀 접근의 영향']] },
        ...bitsCtl,
        { type: 'select', id: 'selA', label: '읽을 셀 (워드라인 1)', value: '0', options: selOpts },
        { type: 'select', id: 'selB', label: '워드라인 2 (동시에 켜기)', value: 'none', options: [['none', '켜지 않음'], ...selOpts] },
        { id: 't', label: '시간 t (읽기)', min: 0, max: 12, step: 0.01, value: 3.9, fmt: (v) => v.toFixed(2) + ' ns' },
        { id: 'tr', label: '경과 시간 (유지)', min: 1e-3, max: 1e3, log: true, value: 1, fmt: (v) => MS.si(v, 's') },
        { type: 'play', id: 'play' },
        { id: 'vpp', label: 'Vpp (WL 높은 값)', min: 1.0, max: 3.0, step: 0.05, value: 2.0, fmt: (v) => v.toFixed(2) + ' V' },
        { id: 'vth', label: '액세스 Vth', min: 0.4, max: 1.0, step: 0.01, value: 0.7, fmt: (v) => v.toFixed(2) + ' V' },
        { id: 'cs', label: 'Cs', min: 10e-15, max: 50e-15, log: true, value: 25e-15, fmt: (v) => MS.si(v, 'F') },
        { id: 'cw', label: 'Cw (BL 배선 용량)', min: 50e-15, max: 300e-15, log: true, value: 145e-15, fmt: (v) => MS.si(v, 'F') },
        { id: 'cj', label: 'Cj (셀 1개가 BL에 더하는 용량)', min: 1e-15, max: 40e-15, log: true, value: 5e-15, fmt: (v) => MS.si(v, 'F') },
        { id: 'voff', label: '센스앰프 오프셋 (+ = 0 쪽으로 치우침)', min: -0.06, max: 0.06, step: 0.001, value: 0.0, fmt: (v) => (v * 1e3).toFixed(0) + ' mV' },
        { id: 'act', label: '이웃 접근 활동도 (유지)', min: 0, max: 1, step: 0.05, value: 0.5, fmt: (v) => v.toFixed(2) },
        { id: 'vwl', label: 'WL 낮은 값 (유지)', min: -0.6, max: 0.2, step: 0.01, value: 0, fmt: (v) => v.toFixed(2) + ' V' },
        { id: 'ij', label: '접합 누설 Ij (유지)', min: 1e-17, max: 1e-14, log: true, value: 0.2e-15, fmt: (v) => MS.si(v, 'A') },
      ],
      compute: (v, prev) => {
        const bits = Array.from({ length: N }, (_, k) => (v['b' + k] ? 1 : 0)), a = +v.selA, b = v.selB === 'none' ? -1 : +v.selB, sel = b >= 0 && b !== a ? [a, b] : [a];
        const cbl = v.cw + N * v.cj, vh = Math.min(VDD, v.vpp - v.vth), levels = bits.map((x) => (x ? vh : 0)), w = 1e-7, l = 1e-7;
        const ret = v.mode === 'ret';
        if (!ret) {
          const key = JSON.stringify(['r', bits, sel, v.vpp, v.vth, v.cs, v.cw, v.cj, v.voff]);
          const sim = prev && prev.key === key ? prev.sim : MS.arraySim({ n: N, bits, sel, vdd: VDD, vpp: v.vpp, vth: v.vth, wlr: 1, cs: v.cs, cw: v.cw, cj: v.cj, voff: v.voff, gmsa: 2e-3, vwloff: 0, method: 'trap', dt: DT });
          const m = MS.makeModel('level1', 1, { vto: v.vth, kp: 300e-6, lambda: 0.05 });
          const i = clamp(Math.round(v.t * 1e-9 / DT), 0, sim.t.length - 1), pre = sim.t[i] < sim.tsa, vbl = sim.bl[i];
          const iacc = sim.iacc.map((x) => x[i]), vsn = sim.sn.map((x) => x[i]), vwl = sim.wl.map((x) => x[i]);
          const icbl = pre ? -iacc.reduce((p, q) => p + q, 0) : sim.icbl[i], isrc = pre ? 0 : icbl + iacc.reduce((p, q) => p + q, 0);
          const profs = vsn.map((sn, k) => MS.channelProfile(m, vbl, vwl[k], sn, 0, w, l, 33));
          const sText = pre ? '센스앰프 꺼짐: BL이 떠 있고 켜진 셀과 전하를 나눔' : '센스앰프 켜짐: BL을 레일로 밀고 켜진 셀을 같은 값으로 다시 씀';
          return { key, sim, ret: false, sel, bits, levels, cbl, vh, i, tshow: sim.t[i], pre, vbl, vsn, vwl, iacc, icbl, isrc, profs, sText, cblValue: MS.si(cbl, 'F'),
            dvHand: handDv(levels, sel, v.cs, cbl), vdd: VDD, qmax: 1.2 };
        }
        // retention of the victim cell (cell a): the neighbours pull the bit line to the active level when they are accessed
        const victim = a, data1 = bits[a] === 1, nOther = bits.filter((x, k) => k !== a && x === (data1 ? 0 : 1)).length, duty = v.act * nOther / N;
        const q = { vdd: VDD, vpp: v.vpp, vth: v.vth, wlr: 1, cs: v.cs, cbl, voff: 0.02, n: 1.3, ij: v.ij, vwl: v.vwl, data1, duty };
        const key = JSON.stringify(['t', bits, a, v.vpp, v.vth, v.cs, v.cw, v.cj, v.vwl, v.ij, v.act]);
        let rt = prev && prev.key === key ? prev.rt : null;
        if (!rt) {
          const r = MS.dramRetention(q), fs = lin(0, 1, 11).map((f) => MS.dramRetention(Object.assign({}, q, { duty: f })).tret);
          const vths = lin(0.4, 1.0, 13), tv = vths.map((x) => MS.dramRetention(Object.assign({}, q, { vth: x })).tret);
          rt = { r, fs, vths, tv };
        }
        const r = rt.r, vsnV = vAt(r, v.tr), me = MS.makeModel('ekv', 1, { vto: v.vth, kp: 300e-6, n: 1.3, lambda: 0.05 }), vact = data1 ? 0 : VDD;
        const vsn = levels.slice(); vsn[victim] = vsnV;
        const iacc = vsn.map((sn, k) => MS.evaluate(me, vact, v.vwl, sn, 0, w, l).id);
        const profs = vsn.map((sn, k) => MS.channelProfile(me, vact, v.vwl, sn, 0, w, l, 33));
        const i0 = Math.abs(MS.evaluate(me, vact, v.vwl, levels[victim], 0, w, l).id) * duty + Math.abs(MS.evaluate(me, VDD / 2, v.vwl, levels[victim], 0, w, l).id) * (1 - duty) + (data1 ? v.ij * (1 - Math.exp(-levels[victim] / MS.VT)) : 0);
        return { key, rt, ret: true, bits, levels, cbl, vh, victim, data1, nOther, duty, tshow: v.tr, vbl: vact, vsn, vwl: bits.map(() => v.vwl), iacc, icbl: 0, isrc: iacc.reduce((p, q) => p + q, 0), profs, i0,
          sText: '워드라인이 모두 꺼져 있음: 점 = 서브문턱 누설(대개 너무 작아 보이지 않음). BL은 이웃 접근 때의 레벨로 표시', cblValue: MS.si(cbl, 'F'), vdd: VDD, qmax: 1.2 };
      },
      onTick: (dt, ctl, v) => {
        if (v.mode === 'ret') { let x = ctl.tr.get() * Math.exp(dt); if (x > 1e3) x = 1e-3; ctl.tr.set(x); return true; }
        let t = ctl.t.get() + dt * 1.2; if (t > 12) t = 0; ctl.t.set(t); return true;
      },
      vrange: (s, v) => [Math.min(0, v.vwl), Math.max(VDD, v.vpp)],
      readout: (s, v) => {
        if (s.ret) {
          const r = s.rt.r, lost = s.data1 ? s.vsn[s.victim] <= r.vlim : s.vsn[s.victim] >= r.vlim;
          const rs = [['관찰하는 셀', `셀 ${s.victim} (저장값 ${s.data1 ? 1 : 0})`], ['이웃 중 BL을 그 셀에 불리하게 끄는 셀 수', `${s.nOther} / ${N - 1}`, s.data1 ? '저장값 0인 이웃: 접근되면 BL = 0 V' : '저장값 1인 이웃: 접근되면 BL = Vdd'],
            ['BL이 불리한 레벨에 머무는 비율 f', s.duty.toFixed(3), `활동도 ${v.act.toFixed(2)} × ${s.nOther}/${N}`], ['Cbl', MS.si(s.cbl, 'F'), `센싱 한계 V_lim = ${r.vlim.toFixed(3)} V (센스앰프 오프셋 20 mV 가정)`], ['처음 누설 (시간 평균)', fIs(s.i0)],
            ['경과 시간 / 그때의 V(SN)', `${fT(v.tr)} / ${fV(s.vsn[s.victim])}`, lost ? '한계를 넘어 데이터 손실' : '아직 읽을 수 있음']];
          if (s.data1) rs.push(['유지 시간 t_ret', fT(r.tret), r.tret > 0 ? `64 ms의 ${(r.tret / 64e-3).toPrecision(3)}배` : '센싱 불가']);
          else rs.push(['유지 시간 t_ret', isFinite(r.tret) ? fT(r.tret) : '한계에 도달하지 않음']);
          return rows(rs);
        }
        const sim = s.sim, sel = s.sel, bitsSel = sel.map((k) => s.bits[k]), differ = sel.length === 2 && bitsSel[0] !== bitsSel[1];
        const unsel = s.vsn.map((x, k) => (sel.includes(k) ? 0 : Math.abs(x - sim.lvl0[k]))), un = Math.max(0, ...unsel);
        const rs = [['켜진 워드라인', sel.map((k) => 'WL' + k).join(' + ')], ['Cbl = Cw + N·Cj', MS.si(s.cbl, 'F'), `${MS.si(v.cw, 'F')} + ${N} × ${MS.si(v.cj, 'F')}`],
          ['전하 공유 신호 ΔV (시뮬레이션)', `${(sim.dv * 1e3).toFixed(2)} mV`, `손 계산 Σ Cs(Vk − Vdd/2)/(Cbl + ${sel.length}·Cs) = ${(s.dvHand * 1e3).toFixed(2)} mV`],
          ['센스앰프 판정', sim.bit ? '1' : '0', sel.map((k) => `셀 ${k}: 저장값 ${s.bits[k]}`).join(', ')],
          ['끝의 셀 값', sel.map((k) => `셀 ${k} = ${sim.final[k].toFixed(2)} V`).join(', ')],
          ['켜지지 않은 셀의 변화', un < 1e-9 ? '0 V' : `${(un * 1e3).toFixed(3)} mV`, '열린 액세스 트랜지스터는 전류를 흘리지 않음(Level 1)']];
        let html = rows(rs);
        if (sim.corrupted.length) html += `<p class="ia-warn">셀 ${sim.corrupted.join(', ')}의 데이터가 파괴되었습니다: ${differ ? '서로 다른 값을 가진 두 셀이 동시에 열리면 한 값으로 덮어써집니다.' : '센스앰프가 잘못 판정했습니다(신호 &lt; 오프셋).'}</p>`;
        return html;
      },
      plots: [
        { h: 250, draw: (p, s, v) => {
          if (s.ret) {
            const r = s.rt.r, ts = r.ts.slice(), vs = r.vs.slice(); ts[0] = 1e-3;
            if (!isFinite(r.tret) && ts[ts.length - 1] < 1e3) { ts.push(1e3); vs.push(vs[vs.length - 1]); }
            p.begin({ xlabel: '쓰기 후 경과 시간 [s]', ylabel: 'V(SN) [V]', xlog: true, xlim: [1e-3, 1e3], ylim: [-0.05, VDD * 1.08], title: `셀 ${s.victim}의 저장 전압 (이웃 활동 반영)` });
            p.hline(r.vlim, { color: '#b03a00' }).text(1.3e-3, r.vlim + 0.03, '센싱 한계', { color: '#b03a00' }).vline(64e-3, { color: '#7570b3' }).text(7e-2, 0.12, '64 ms', { color: '#7570b3' });
            p.line(ts, vs, { color: '#1f3b73', width: 2.6 }).marker(Math.max(v.tr, 1.01e-3), s.vsn[s.victim], {}).end();
          } else {
            const t = s.sim.t.map((x) => x * 1e9), L = [{ color: '#1f3b73', label: 'BL' }, { color: '#1f3b73', dash: [2, 2], label: 'BLB (기준)' }];
            p.begin({ xlabel: 't [ns]', ylabel: '전압 [V]', xlim: [0, 12], ylim: [-0.05, Math.max(VDD, v.vpp) * 1.05], title: '켜진 셀만 변하고 나머지는 그대로' });
            p.line(t, s.sim.wl[s.sel[0]], { color: '#8a91a0', dash: [5, 3], width: 1.5 }).line(t, s.sim.bl, { color: '#1f3b73', width: 2.4 }).line(t, s.sim.blb, { color: '#1f3b73', dash: [2, 2], width: 1.5 });
            s.sim.sn.forEach((x, k) => { const on = s.sel.includes(k); p.line(t, x, { color: COL[k], width: on ? 2.6 : 1.4, dash: on ? null : [6, 3] }); L.push({ color: COL[k], dash: on ? null : [6, 3], label: `SN${k}${on ? ' (켜짐)' : ''}` }); });
            p.vline(s.tshow * 1e9, { color: '#d73027' }).legend(L, 'right').end();
          }
        } },
        { h: 230, draw: (p, s, v) => {
          if (s.ret) {
            p.begin({ xlabel: 'BL이 불리한 레벨에 머무는 비율 f', ylabel: '유지 시간 [s]', xlim: [0, 1], ylim: [1e-3, 1e3], ylog: true, title: '이웃이 바쁠수록 짧아진다' });
            p.hline(64e-3, { color: '#7570b3' }).text(0.02, 0.09, '64 ms', { color: '#7570b3' }).line(lin(0, 1, 11), s.rt.fs.map((x) => (isFinite(x) && x > 0 ? x : NaN)), { color: '#d95f02', width: 2.6 }).marker(s.duty, Math.max(isFinite(s.rt.r.tret) ? s.rt.r.tret : 1e3, 1.1e-3), { label: '현재', dy: 16 }).end();
          } else {
            const ns = [1, 2, 3, 4, 6, 8, 12, 16, 32, 64, 128, 256], lv = s.levels;
            p.begin({ xlabel: '비트라인에 붙은 셀 수 N', ylabel: '읽기 신호 |ΔV| [mV]', xlog: true, xlim: [1, 256], ylim: [0, 100], title: 'N이 늘면 Cbl이 커져 신호가 줄어든다 (손 계산)' });
            p.line(ns, ns.map((n) => Math.abs(handDv([s.vh], [0], v.cs, v.cw + n * v.cj)) * 1e3), { color: '#1f3b73', width: 2.6 }).hline(Math.abs(v.voff) * 1e3, { color: '#b03a00' }).text(1.15, Math.abs(v.voff) * 1e3 + 4, '센스앰프 오프셋', { color: '#b03a00' })
              .marker(N, Math.abs(handDv([s.vh], [0], v.cs, s.cbl)) * 1e3, { label: `N = ${N}`, dy: -10 }).end();
          }
        } },
        { h: 220, draw: (p, s, v) => {
          if (s.ret) {
            p.begin({ xlabel: '액세스 트랜지스터 Vth [V]', ylabel: '유지 시간 [s]', xlim: [0.4, 1.0], ylim: [1e-3, 1e4], ylog: true, title: 'Vth가 높을수록 오래 유지한다 (현재 f 기준)' });
            p.hline(64e-3, { color: '#7570b3' }).line(s.rt.vths, s.rt.tv.map((x) => (isFinite(x) && x > 0 ? x : NaN)), { color: '#1b9e77', width: 2.6 }).marker(v.vth, Math.max(isFinite(s.rt.r.tret) ? s.rt.r.tret : 1e4, 1.1e-3), { label: '현재', dy: 16 }).end();
          } else {
            const t = s.sim.t.map((x) => x * 1e9), all = s.sim.iacc.flatMap((x, k) => (s.sel.includes(k) ? x : [])).map((x) => x * 1e6), lo = Math.min(0, ...all), hi = Math.max(0, ...all), pad = 0.08 * (hi - lo) + 1;
            p.begin({ xlabel: 't [ns]', ylabel: '전류 [µA]', xlim: [0, 12], ylim: [lo - pad, hi + pad], title: '켜진 셀의 액세스 전류 i(BL→SN): 양수 = 충전, 음수 = 방전' });
            p.hline(0, { color: '#c3c9d4', dash: [], width: 1 });
            s.sel.forEach((k) => p.line(t, s.sim.iacc[k].map((x) => x * 1e6), { color: COL[k], width: 2.2 }));
            p.vline(s.tshow * 1e9, { color: '#d73027' }).legend(s.sel.map((k) => ({ color: COL[k], label: `셀 ${k}` })), 'right').end();
          }
        } },
      ],
      build3d: (sc, s) => S3.dramArray(sc, { vdd: VDD, vbl: s.vbl, vmin: s.vmin, vmax: s.vmax, phase: s.phase,
        cells: s.vsn.map((sn, k) => ({ v: { s: sn, d: s.vbl, g: s.vwl[k], b: 0 }, prof: s.profs[k], I: s.iacc[k], qmax: s.qmax, vsn: sn, vwl: s.vwl[k], names: { s: 'SN' + k, g: 'WL' + k } })) }),
      scene: { yaw: -0.6, pitch: 0.55, height: 330 },
      cap3d: '3D: 셀이 비트라인(위의 긴 막대)을 따라 나란히 있고 각 셀에 자기 워드라인이 있습니다. 탱크의 채워진 높이 = 저장 전압, 색 = 전위, 점 = 전류.',
      schem: (svgEl) => { const r = arraySchem(svgEl, N); return { s: r.s, update: (s) => r.update(s) }; },
      foot: '읽기는 Level 1 시뮬레이션(trap, 10 ps)과 이상화한 센스앰프(시정수 Cbl/gm, 오프셋)입니다. 유지 시간은 레슨 11과 같은 EKV 누설 ODE에 “이웃 접근으로 BL이 불리한 레벨에 있는 시간 비율 f”를 더한 것이고 활동도는 가상의 값입니다.',
    });
  }
  G.IA.W.l12a = makeL12(2);
  G.IA.W.l12b = makeL12(4);
})(typeof window !== 'undefined' ? window : globalThis);
