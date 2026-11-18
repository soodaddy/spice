'use strict';
/* ia_l11.js - lesson 11 widget: DRAM 1T1C cell (write, charge-sharing read with a latch sense amplifier, retention). */
(function (G) {
  const { makeWidget, fI, rows } = G.IA, MS = G.MS, S3 = G.Scene3D, { svg } = G.UI, clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const lin = (a, b, n) => Array.from({ length: n }, (_, i) => a + (b - a) * i / (n - 1));
  const BETA = (wlr) => 300e-6 * wlr, DT = 10e-12;
  const MODES = [['write1', '쓰기: 1 기록'], ['write0', '쓰기: 0 기록'], ['read1', '읽기: 저장값 1'], ['read0', '읽기: 저장값 0'], ['ret1', '유지(retention): 저장값 1'], ['ret0', '유지(retention): 저장값 0']];
  const fIs = (I) => (Math.abs(I) < 1e-21 ? '0 A' : (I < 0 ? '−' : '') + MS.si(Math.abs(I), 'A', 3));   // leakage lives at fA/aA: fI() would print 0 below 1 fA
  const fV = (v) => v.toFixed(3) + ' V', fT = (t) => (isFinite(t) ? MS.si(t, 's') : '∞');

  /** equivalent circuit: bit line with its capacitance Cbl and the SA / write driver, access NMOS (gate = word line), storage node SN and Cs */
  function dramSchem(svgEl) {
    const s = new G.Schem(svgEl, 380, 300), m = s.mos(120, 150, { size: 20, label: 'M1' });
    const wBL = s.wire([[318, 40], [240, 40]]), wBL2 = s.wire([[240, 40], [152, 40]]), wD = s.wire([[152, 40], [152, 122]]), wS = s.wire([[152, 178], [152, 205]]), wCs = s.wire([[152, 245], [152, 262]]), wCsb = s.wire([[152, 205], [152, 245]], { width: 0.1 });
    const wCb1 = s.wire([[240, 40], [240, 70]]), wCb2 = s.wire([[240, 110], [240, 150]]), wCbb = s.wire([[240, 70], [240, 110]], { width: 0.1 });
    const wWL = s.wire([[40, 150], [120, 150]], { width: 2.8 });
    wCsb.path.setAttribute('stroke', 'none'); wCbb.path.setAttribute('stroke', 'none');
    s.capacitor(152, 205, 245, 'Cs'); s.capacitor(240, 70, 110, 'Cbl'); s.ground(152, 262); s.ground(240, 150); s.dot(152, 40); s.dot(240, 40);
    s.g1.append(svg('rect', { x: 318, y: 22, width: 56, height: 36, rx: 5, fill: '#e8e0f5', stroke: '#1f3b73', 'stroke-width': 1.8 }));
    s.text(346, 38, 'SA /', { size: 10, anchor: 'middle', weight: 600 }); s.text(346, 51, '드라이버', { size: 9, anchor: 'middle', weight: 500 });
    s.text(8, 134, 'WL (워드라인)', { size: 11, color: '#b03a00' }); s.text(40, 26, 'BL (비트라인)', { size: 11, color: '#b03a00' }); s.text(166, 262, '플레이트', { size: 9, weight: 500, color: '#4a5160' });
    const bWL = s.badge(8, 168, 'WL'), bBL = s.badge(60, 56, 'BL'), bSN = s.badge(166, 196, 'SN');
    const tI = s.text(146, 96, '', { color: '#b03a00', size: 10.5, anchor: 'end' }), tC = s.text(252, 134, '', { color: '#b03a00', size: 10 }), tS = s.text(10, 292, '', { size: 10, weight: 500, color: '#4a5160' });
    return { s, update(st) {
      const { vmin, vmax } = st;
      wBL.set(st.vbl, st.isrc, vmin, vmax); wBL2.set(st.vbl, st.iacc, vmin, vmax); wD.set(st.vbl, st.iacc, vmin, vmax); wS.set(st.vsn, st.iacc, vmin, vmax); wCs.set(0, st.iacc, vmin, vmax); wCsb.I = st.iacc;
      wCb1.set(st.vbl, st.icbl, vmin, vmax); wCb2.set(0, st.icbl, vmin, vmax); wCbb.I = st.icbl; wWL.set(st.vwl, 0, vmin, vmax);
      bWL.set(st.vwl, vmin, vmax); bBL.set(st.vbl, vmin, vmax); bSN.set(st.vsn, vmin, vmax);
      tI.textContent = `i(BL→SN) = ${fIs(st.iacc)}`; tC.textContent = st.ret ? '' : `iCbl = ${fI(st.icbl)}`; tS.textContent = st.sText || '';
    } };
  }

  // the offset acts AGAINST the stored bit (worst case): +voff for a stored 1, -voff for a stored 0
  const baseQ = (v, data1) => ({ vdd: v.vdd, vpp: v.vpp, vth: v.vth, wlr: v.wlr, cs: v.cs, cbl: v.cbl, voff: data1 === false ? -v.voff : v.voff, gmsa: v.gmsa, vwloff: v.vwl });
  /** V(SN) at time t of a retention curve (linear in t on the first segment, linear in log t afterwards) */
  function vAt(r, t) {
    const ts = r.ts, vs = r.vs, n = ts.length;
    if (t >= ts[n - 1]) return vs[n - 1];
    let k = 1; while (k < n && ts[k] < t) k++;
    const t0 = ts[k - 1], t1 = ts[k], f = t0 <= 0 ? t / t1 : Math.log(t / t0) / Math.log(t1 / t0);
    return vs[k - 1] + (vs[k] - vs[k - 1]) * f;
  }

  G.IA.W.l11 = (root) => makeWidget(root, {
    note: '워드라인(WL)이 올라가면 액세스 트랜지스터가 켜져 비트라인(BL)과 저장 커패시터(Cs)가 연결됩니다. 쓰기·읽기(전하 공유 + 센스앰프)·유지(누설)를 골라 보세요.',
    controls: [
      { type: 'select', id: 'mode', label: '동작', value: 'read1', options: MODES },
      { id: 't', label: '시간 t (쓰기·읽기)', min: 0, max: 12, step: 0.01, value: 3.9, fmt: (v) => v.toFixed(2) + ' ns' },
      { id: 'tr', label: '경과 시간 (유지)', min: 1e-3, max: 1e3, log: true, value: 0.05, fmt: (v) => MS.si(v, 's') },
      { type: 'play', id: 'play' },
      { id: 'vdd', label: 'Vdd', min: 0.8, max: 1.5, step: 0.05, value: 1.2, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'vpp', label: 'Vpp (WL 높은 값)', min: 1.0, max: 3.0, step: 0.05, value: 2.0, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'vth', label: '액세스 Vth', min: 0.4, max: 1.0, step: 0.01, value: 0.7, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'wlr', label: '액세스 W/L', min: 0.5, max: 4, log: true, value: 1, fmt: (v) => v.toFixed(2) },
      { id: 'cs', label: 'Cs', min: 10e-15, max: 50e-15, log: true, value: 25e-15, fmt: (v) => MS.si(v, 'F') },
      { id: 'cbl', label: 'Cbl', min: 50e-15, max: 300e-15, log: true, value: 150e-15, fmt: (v) => MS.si(v, 'F') },
      { id: 'voff', label: '센스앰프 오프셋', min: 0, max: 0.06, step: 0.001, value: 0.02, fmt: (v) => (v * 1e3).toFixed(0) + ' mV' },
      { id: 'gmsa', label: '센스앰프 gm (gmn+gmp)', min: 0.5e-3, max: 10e-3, log: true, value: 2e-3, fmt: (v) => MS.si(v, 'S') },
      { id: 'vwl', label: 'WL 낮은 값 (유지)', min: -0.6, max: 0.2, step: 0.01, value: 0, fmt: (v) => v.toFixed(2) + ' V' },
      { id: 'nn', label: 'n (서브문턱 기울기)', min: 1.1, max: 1.6, step: 0.01, value: 1.3, fmt: (v) => v.toFixed(2) },
      { id: 'ij', label: '접합 누설 Ij', min: 1e-17, max: 1e-14, log: true, value: 0.2e-15, fmt: (v) => MS.si(v, 'A') },
      { type: 'select', id: 'blhold', label: '유지 중 BL (유지 모드)', value: 'worst', options: [['worst', '최악: 1 저장 시 0 V, 0 저장 시 Vdd'], ['pre', 'Vdd/2 (대기 중 precharge)']] },
    ],
    compute: (v, prev) => {
      const ret = v.mode.startsWith('ret'), vh = Math.min(v.vdd, v.vpp - v.vth), vblp = v.vdd / 2, w = v.wlr * 1e-7, l = 1e-7;
      if (!ret) {
        const key = JSON.stringify([v.mode, v.vdd, v.vpp, v.vth, v.wlr, v.cs, v.cbl, v.voff, v.gmsa, v.vwl]);
        const sim = prev && prev.key === key ? prev.sim : MS.dramSim(Object.assign({ mode: v.mode, method: 'trap', dt: DT }, baseQ(v, v.mode.endsWith('1'))));
        const m = MS.makeModel('level1', 1, { vto: v.vth, kp: 300e-6, lambda: 0.05 });
        const i = clamp(Math.round(v.t * 1e-9 / DT), 0, sim.t.length - 1), read = v.mode.startsWith('read'), pre = read && sim.t[i] < sim.tsa;
        const icblT = sim.icbl.map((x, k) => (read && sim.t[k] < sim.tsa ? -sim.iacc[k] : x));      // before the SA fires the bit line floats: KCL gives iCbl = -i(access)
        const vbl = sim.bl[i], vsn = sim.sn[i], vwl = sim.wl[i], iacc = sim.iacc[i], icbl = icblT[i], isrc = pre ? 0 : icbl + iacc;
        const prof = MS.channelProfile(m, vbl, vwl, vsn, 0, w, l, 33), data1 = v.mode.endsWith('1'), cell = data1 ? vh : 0;
        const sText = read ? (pre ? '센스앰프 꺼짐: BL은 떠 있고 Cs와 전하를 나눔' : '센스앰프 켜짐: BL을 레일로 밀고 셀을 복원') : 'BL = 쓰기 드라이버가 구동';
        return { key, sim, icblT, ret: false, i, tshow: sim.t[i], vbl, vsn, vwl, iacc, icbl, isrc, prof, vh, vblp, cell, data1, read, pre, m, sText, I: iacc, qmax: 1.2, dvHand: (cell - vblp) * v.cs / (v.cs + v.cbl),
          v: { s: vsn, d: vbl, g: vwl, b: 0 }, vdd: v.vdd };
      }
      const data1 = v.mode === 'ret1', vbl = v.blhold === 'pre' ? 'pre' : null;
      const q = Object.assign({ n: v.nn, ij: v.ij, vbl, data1 }, baseQ(v, data1), { vwl: v.vwl, voff: v.voff });
      const key = JSON.stringify(['r', v.mode, v.vdd, v.vpp, v.vth, v.wlr, v.cs, v.cbl, v.voff, v.vwl, v.nn, v.ij, v.blhold]);
      let rt = prev && prev.key === key ? prev.rt : null;
      if (!rt) {
        const r = MS.dramRetention(q), vths = lin(0.4, 1.0, 13), tv = vths.map((x) => MS.dramRetention(Object.assign({}, q, { vth: x, data1: true })).tret);
        const vws = lin(-0.8, 0.3, 45), me = MS.makeModel('ekv', 1, { vto: v.vth, kp: 300e-6, n: v.nn, lambda: 0.05 }), v0 = r.vs[0];
        const iw = vws.map((x) => Math.abs(MS.evaluate(me, r.vbl, x, v0, 0, w, l).id) + (data1 ? v.ij * (1 - Math.exp(-v0 / MS.VT)) : 0));
        rt = { r, vths, tv, vws, iw, v0 };
      }
      const me = MS.makeModel('ekv', 1, { vto: v.vth, kp: 300e-6, n: v.nn, lambda: 0.05 }), r = rt.r;
      const vsn = vAt(r, v.tr);
      const vb = r.vbl, eAcc = MS.evaluate(me, vb, v.vwl, vsn, 0, w, l), ijNow = data1 && vsn > 0 ? v.ij * (1 - Math.exp(-vsn / MS.VT)) : 0, iacc = eAcc.id;
      const prof = MS.channelProfile(me, vb, v.vwl, vsn, 0, w, l, 33), i0 = Math.abs(MS.evaluate(me, vb, v.vwl, rt.v0, 0, w, l).id) + (data1 ? v.ij * (1 - Math.exp(-rt.v0 / MS.VT)) : 0);
      return { key, rt, ret: true, tshow: v.tr, vbl: vb, vsn, vwl: v.vwl, iacc, ijNow, icbl: 0, isrc: iacc, prof, vh, vblp, data1, i0, me, sText: '워드라인이 꺼져 있다: 점 = 서브문턱 누설(대개 너무 작아 보이지 않음)', I: iacc, qmax: 1.2, v: { s: vsn, d: vb, g: v.vwl, b: 0 }, vdd: v.vdd };
    },
    onTick: (dt, ctl, v) => {
      if (v.mode.startsWith('ret')) { let x = ctl.tr.get() * Math.exp(dt * 1.0); if (x > 1e3) x = 1e-3; ctl.tr.set(x); return true; }
      let t = ctl.t.get() + dt * 1.2; if (t > 12) t = 0; ctl.t.set(t); return true;
    },
    vrange: (s, v) => [Math.min(0, v.vwl), Math.max(v.vdd, v.vpp)],
    readout: (s, v) => {
      if (s.ret) {
        const r = s.rt.r, hand = s.data1 ? v.cs * (s.vh - r.vlim) / s.i0 : NaN, lost = s.data1 ? s.vsn <= r.vlim : s.vsn >= r.vlim;
        const rs = [['쓰기 직후 레벨', fV(s.vh), `min(Vdd, Vpp−Vth) = min(${v.vdd.toFixed(2)}, ${(v.vpp - v.vth).toFixed(2)})`], ['센싱 한계', fV(r.vlim), `Vdd/2 ${s.data1 ? '+' : '−'} 오프셋·(Cs+Cbl)/Cs`],
          ['처음 누설 전류', fIs(s.i0), `BL = ${s.vbl.toFixed(2)} V, WL = ${v.vwl.toFixed(2)} V`], ['경과 시간', fT(v.tr), '64 ms = 최악 조건 규격'], ['그때의 V(SN)', fV(s.vsn), lost ? '한계를 넘어 데이터 손실' : '아직 읽을 수 있음']];
        if (s.data1) rs.push(['유지 시간 t_ret (ODE)', fT(r.tret), `손 계산 Cs·ΔV/I = ${fT(hand)}`], ['64 ms 대비', r.tret > 0 ? `${(r.tret / 64e-3).toFixed(2)} ×` : '센싱 불가']);
        else rs.push(['유지 시간 t_ret', isFinite(r.tret) ? fT(r.tret) : '한계에 도달하지 않음', '0은 노드가 오르면 Vgs가 더 음이 되어 누설이 스스로 멈춘다']);
        return rows(rs);
      }
      const sim = s.sim, ok = s.read ? (sim.ok ? '맞음' : '틀림 (오프셋이 신호보다 큼)') : '';
      const rs = [['시간', (s.tshow * 1e9).toFixed(2) + ' ns'], ['WL / BL / SN', `${s.vwl.toFixed(2)} / ${s.vbl.toFixed(3)} / ${s.vsn.toFixed(3)} V`], ['액세스 전류 i(BL→SN)', fIs(s.iacc)]];
      if (!s.read) {
        const lvl = s.data1 ? s.vh : 0, tail = v.vpp > v.vdd + v.vth ? v.cs / (BETA(v.wlr) * (v.vpp - v.vth - v.vdd)) : Infinity;
        rs.push(['기록 가능한 레벨', fV(lvl), s.data1 ? `min(Vdd, Vpp−Vth); Vdd+Vth = ${(v.vdd + v.vth).toFixed(2)} V` : '0 V'], ['8.5 ns의 V(SN)', fV(sim.sn[Math.round(8.5e-9 / DT)]), '쓰기 끝 직전']);
        if (s.data1) rs.push(['꼬리 시정수 Cs/(β(Vpp−Vth−Vdd))', isFinite(tail) ? fT(tail) : '없음', isFinite(tail) ? 'Vdd에 지수적으로 접근' : 'Vpp < Vdd+Vth: Vdd까지 못 오른다']);
        return rows(rs) + (s.data1 && v.vpp < v.vdd + v.vth ? '<p class="ia-warn">Vpp가 Vdd+Vth보다 낮아 1을 완전히 쓰지 못합니다(저장 레벨이 Vpp−Vth).</p>' : '');
      }
      rs.push(['전하 공유 신호 ΔV (시뮬레이션)', `${(sim.dv * 1e3).toFixed(2)} mV`, `손 계산 (Vcell−Vdd/2)·Cs/(Cs+Cbl) = ${(s.dvHand * 1e3).toFixed(2)} mV`], ['센스앰프 오프셋', `${(v.voff * 1e3).toFixed(0)} mV`, `|ΔV| − 오프셋 = ${((Math.abs(sim.dv) - v.voff) * 1e3).toFixed(1)} mV (오프셋은 저장값에 불리한 방향)`],
        ['센스앰프 판정', sim.bit ? '1' : '0', ok], ['재생 시정수 τ = Cbl/gm', MS.si(sim.tau, 's'), `gm = ${MS.si(v.gmsa, 'S')}`], ['복원된 셀 레벨 (끝)', fV(sim.sn[sim.sn.length - 1]), s.data1 ? '다시 쓰기(restore)' : '0 복원']);
      return rows(rs);
    },
    plots: [
      { h: 250, draw: (p, s, v) => {
        if (s.ret) {
          const r = s.rt.r, ts = r.ts.slice(), vs = r.vs.slice(); ts[0] = 1e-3;                       // t = 0 cannot be drawn on a log axis
          if (!isFinite(r.tret) && ts[ts.length - 1] < 1e3) { ts.push(1e3); vs.push(vs[vs.length - 1]); }   // the curve flattens out (self-limiting) instead of ending
          p.begin({ xlabel: '쓰기 후 경과 시간 [s]', ylabel: 'V(SN) [V]', xlog: true, xlim: [1e-3, 1e3], ylim: [-0.05, Math.max(v.vdd, s.vh) * 1.05], title: '저장 노드 전압의 시간 변화 (누설)' });
          p.hline(r.vlim, { color: '#b03a00' }).text(1.3e-3, r.vlim + 0.03, '센싱 한계', { color: '#b03a00' }).vline(64e-3, { color: '#7570b3' }).text(7e-2, (s.data1 ? 0.12 : 0.9) * v.vdd, '64 ms', { color: '#7570b3' });
          p.line(ts, vs, { color: '#1f3b73', width: 2.6 }).marker(Math.max(v.tr, 1.01e-3), s.vsn, {}).end();
        } else {
          const t = s.sim.t.map((x) => x * 1e9), L = [{ color: '#8a91a0', dash: [5, 3], label: 'WL' }, { color: '#1f3b73', label: 'BL' }, { color: '#d95f02', label: 'SN (저장 노드)' }];
          p.begin({ xlabel: 't [ns]', ylabel: '전압 [V]', xlim: [0, 12], ylim: [-0.05, Math.max(v.vdd, v.vpp) * 1.05], title: s.read ? '읽기: 전하 공유 → 센스앰프 → 복원' : '쓰기: 저장 노드가 BL을 따라간다' });
          p.line(t, s.sim.wl, { color: '#8a91a0', dash: [5, 3], width: 1.6 }).line(t, s.sim.bl, { color: '#1f3b73', width: 2.4 });
          if (s.read) { p.line(t, s.sim.blb, { color: '#1f3b73', dash: [2, 2], width: 1.6 }); L.splice(2, 0, { color: '#1f3b73', dash: [2, 2], label: 'BLB (기준)' }); }
          p.line(t, s.sim.sn, { color: '#d95f02', width: 2.4 }).vline(s.tshow * 1e9, { color: '#d73027' }).marker(s.tshow * 1e9, s.vsn, { color: '#d95f02' }).legend(L, 'right').end();
        }
      } },
      { h: 230, draw: (p, s, v) => {
        if (s.ret) {
          p.begin({ xlabel: '액세스 트랜지스터 Vth [V]', ylabel: '유지 시간 (저장값 1) [s]', xlim: [0.4, 1.0], ylim: [1e-3, 1e4], ylog: true, title: 'Vth가 높을수록 오래 유지한다 (지수적)' });
          p.hline(64e-3, { color: '#7570b3' }).text(0.42, 0.09, '64 ms', { color: '#7570b3' }).line(s.rt.vths, s.rt.tv.map((x) => (isFinite(x) && x > 0 ? x : NaN)), { color: '#1b9e77', width: 2.6 }).marker(v.vth, Math.max(s.rt.r.tret, 1.1e-3), { label: '현재', dy: 16 }).end();
        } else {
          p.begin({ xlabel: '비트라인 용량 Cbl [fF]', ylabel: '읽기 신호 |ΔV| [mV]', xlim: [50, 300], ylim: [0, 260], title: '긴 비트라인일수록 신호가 작다: ΔV = (Vcell−Vdd/2)·Cs/(Cs+Cbl)' });
          const cbs = lin(50, 300, 51), vc = Math.abs(s.cell - s.vblp);
          p.line(cbs, cbs.map((c) => vc * 1e3 * v.cs / (v.cs + c * 1e-15)), { color: '#1f3b73', width: 2.6 }).line(cbs, cbs.map((c) => vc * 1e3 * (v.cs * 2) / (v.cs * 2 + c * 1e-15)), { color: '#1b9e77', width: 1.6, dash: [4, 3] }).line(cbs, cbs.map((c) => vc * 1e3 * (v.cs / 2) / (v.cs / 2 + c * 1e-15)), { color: '#d95f02', width: 1.6, dash: [4, 3] })
            .hline(v.voff * 1e3, { color: '#b03a00' }).text(52, v.voff * 1e3 + 8, '센스앰프 오프셋', { color: '#b03a00' }).marker(v.cbl * 1e15, Math.abs(s.dvHand) * 1e3, { label: '현재' })
            .legend([{ color: '#1b9e77', dash: [4, 3], label: `Cs ×2 = ${MS.si(v.cs * 2, 'F')}` }, { color: '#1f3b73', label: `Cs = ${MS.si(v.cs, 'F')}` }, { color: '#d95f02', dash: [4, 3], label: `Cs ÷2 = ${MS.si(v.cs / 2, 'F')}` }], 'right').end();
        }
      } },
      { h: 220, draw: (p, s, v) => {
        if (s.ret) {
          p.begin({ xlabel: 'WL 낮은 값 [V]', ylabel: '누설 전류 [A]', xlim: [-0.8, 0.3], ylim: [1e-19, 1e-9], ylog: true, title: 'WL을 음전압으로 두면 누설이 크게 준다 (서브문턱 기울기)' });
          p.line(s.rt.vws, s.rt.iw, { color: '#d95f02', width: 2.6 }).marker(v.vwl, Math.max(s.i0, 1.1e-19), { label: '현재', dy: 16 }).end();
        } else {
          const t = s.sim.t.map((x) => x * 1e9), a = s.sim.iacc.map((x) => x * 1e6), lo = Math.min(0, ...a), hi = Math.max(0, ...a), pad = 0.08 * (hi - lo) + 1;
          p.begin({ xlabel: 't [ns]', ylabel: '전류 [µA]', xlim: [0, 12], ylim: [lo - pad, hi + pad], title: '액세스 트랜지스터 전류 i(BL→SN): 양수 = 셀 충전, 음수 = 셀 방전' });
          p.hline(0, { color: '#c3c9d4', dash: [], width: 1 }).line(t, a, { color: '#d95f02', width: 2.2 }).vline(s.tshow * 1e9, { color: '#d73027' }).marker(s.tshow * 1e9, s.iacc * 1e6, { color: '#d95f02' }).end();
        }
      } },
    ],
    build3d: (sc, s) => S3.dram(sc, { v: s.v, vmin: s.vmin, vmax: s.vmax, prof: s.prof, I: s.I, qmax: s.qmax, phase: s.phase, vdd: s.vdd, vbl: s.vbl, vsn: s.vsn, vwl: s.vwl }),
    scene: { yaw: -0.62, pitch: 0.5, height: 340 },
    cap3d: '3D 셀: 왼쪽 탱크 = 저장 커패시터(채워진 높이 = 저장 전압), 오른쪽 위 막대 = 비트라인(워드라인과 직각), 점 = 전류. 색 = 전위.',
    schem: (svgEl) => { const r = dramSchem(svgEl); return { s: r.s, update: (s) => r.update(s) }; },
    foot: '쓰기·읽기는 minispice와 같은 시간 격자(trap, 10 ps)의 Level 1 시뮬레이션, 유지 시간은 EKV 서브문턱 누설의 ODE입니다. 센스앰프는 이상화된 래치(시정수 Cbl/gm)입니다.',
  });
})(typeof window !== 'undefined' ? window : globalThis);
